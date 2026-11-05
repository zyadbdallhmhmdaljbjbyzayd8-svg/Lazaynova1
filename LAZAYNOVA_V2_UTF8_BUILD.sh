#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
cd "$HOME/Lazaynova1"

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="$HOME/LAZAYNOVA_V2_BACKUP_$STAMP"
mkdir -p "$BACKUP"
FILES=(
  modules/native_models/l3/tokenizer.py
  native_ai/training/train_l3.py
  native_ai/registry/model_registry.py
  lz_core/ai_gateway/gateway.py
  backend/local_bridge/lazaynova_local_server.py
)
for f in "${FILES[@]}"; do
  if [ -f "$f" ]; then
    mkdir -p "$BACKUP/$(dirname "$f")"
    cp -p "$f" "$BACKUP/$f"
  fi
done
echo "Backup: $BACKUP"

# Refuse to overwrite a V2 dataset or checkpoint.
if [ -e native_ai/datasets/sample_ar_v2.jsonl ]; then
  echo "STOP: native_ai/datasets/sample_ar_v2.jsonl already exists; refusing to overwrite."
  exit 2
fi
if [ -e native_ai/checkpoints/l3_checkpoint_v2.pt ]; then
  echo "STOP: native_ai/checkpoints/l3_checkpoint_v2.pt already exists; refusing to overwrite."
  exit 2
fi

mkdir -p inference native_ai/datasets native_ai/checkpoints

cat > modules/native_models/l3/tokenizer.py <<'PY'
"""UTF-8 byte tokenizer. Strict decoding never silently inserts replacement chars."""
import codecs

class ByteTokenizer:
    PAD, UNK, BOS, EOS = 0, 1, 2, 3
    BYTE_OFFSET = 4
    VOCAB_SIZE = 260

    def encode(self, text, add_bos=False, add_eos=False):
        if not isinstance(text, str):
            raise TypeError("text must be str")
        ids = [b + self.BYTE_OFFSET for b in text.encode("utf-8", errors="strict")]
        if add_bos:
            ids.insert(0, self.BOS)
        if add_eos:
            ids.append(self.EOS)
        return ids

    def decode(self, tokens, errors="strict"):
        if errors not in ("strict", "ignore"):
            raise ValueError("errors must be strict or ignore")
        data = bytearray()
        for token in tokens:
            token = int(token)
            if self.BYTE_OFFSET <= token < self.VOCAB_SIZE:
                data.append(token - self.BYTE_OFFSET)
            elif token in (self.PAD, self.UNK, self.BOS, self.EOS):
                continue
            else:
                raise ValueError(f"token id outside vocabulary: {token}")
        return data.decode("utf-8", errors=errors)

    def get_config(self):
        return {"type":"native_utf8_byte","vocab_size":self.VOCAB_SIZE,
                "pad_token":self.PAD,"unk_token":self.UNK,
                "bos_token":self.BOS,"eos_token":self.EOS}
PY

cat > inference/generate.py <<'PY'
"""UTF-8-constrained autoregressive generation for the native L3 byte tokenizer."""
import codecs
import torch

class UTF8ConstrainedGenerator:
    def __init__(self, model, tokenizer, max_new_tokens=128):
        self.model = model
        self.tokenizer = tokenizer
        self.max_new_tokens = max(1, min(int(max_new_tokens), 256))

    @torch.inference_mode()
    def generate(self, prompt, max_tokens=None, temperature=0.0):
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        count = self.max_new_tokens if max_tokens is None else max(
            1, min(int(max_tokens), self.max_new_tokens))
        ids = self.tokenizer.encode(prompt, add_bos=True)
        context = int(self.model.config["context_length"])
        decoder = codecs.getincrementaldecoder("utf-8")("strict")
        output_parts = []

        for _ in range(count):
            x = torch.tensor([ids[-context:]], dtype=torch.long)
            logits, _ = self.model(x)
            scores = logits[0, -1, :].clone()
            floor = torch.finfo(scores.dtype).min

            # PAD, UNK and BOS are never emitted. EOS is permitted only at a
            # complete UTF-8 character boundary.
            scores[self.tokenizer.PAD] = floor
            scores[self.tokenizer.UNK] = floor
            scores[self.tokenizer.BOS] = floor
            pending, _ = decoder.getstate()
            if pending:
                scores[self.tokenizer.EOS] = floor

            # Test every possible next byte against Python's strict UTF-8
            # incremental decoder. This allows valid partial multibyte
            # prefixes, but rejects bytes that make the stream invalid.
            state = decoder.getstate()
            for token_id in range(self.tokenizer.BYTE_OFFSET,
                                  self.tokenizer.VOCAB_SIZE):
                decoder.setstate(state)
                try:
                    decoder.decode(bytes([token_id - self.tokenizer.BYTE_OFFSET]),
                                   final=False)
                except UnicodeDecodeError:
                    scores[token_id] = floor
            decoder.setstate(state)

            if not torch.isfinite(scores).any():
                break
            if temperature and float(temperature) > 0:
                probs = torch.softmax(scores / max(float(temperature), 1e-4), dim=-1)
                next_id = int(torch.multinomial(probs, 1).item())
            else:
                next_id = int(torch.argmax(scores).item())

            if next_id == self.tokenizer.EOS:
                break
            if next_id < self.tokenizer.BYTE_OFFSET:
                break

            byte = bytes([next_id - self.tokenizer.BYTE_OFFSET])
            try:
                piece = decoder.decode(byte, final=False)
            except UnicodeDecodeError:
                raise RuntimeError("UTF-8 constraint invariant violated")
            if piece:
                output_parts.append(piece)
            ids.append(next_id)

        # Do not expose an unfinished trailing multibyte sequence.
        pending, _ = decoder.getstate()
        if pending:
            decoder.reset()
        result = "".join(output_parts)
        result.encode("utf-8", errors="strict")
        return result
PY

cat > native_ai/registry/model_registry.py <<'PY'
"""Integrity checks for local model artifacts; invalid GGUF files are skipped."""
import hashlib
import json
import os

GGUF_MAGIC = b"GGUF"
MIN_GGUF_SIZE = 1024

def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def inspect_gguf(path, expected_sha256=None):
    result = {"path":str(path),"status":"UNVERIFIED","format":None,
              "size_bytes":None,"sha256":None,"reason":None}
    if not os.path.isfile(path):
        result["reason"] = "FILE_NOT_FOUND"
        return result
    try:
        size = os.path.getsize(path)
        result["size_bytes"] = size
        with open(path, "rb") as stream:
            header = stream.read(64).lstrip().lower()
        result["sha256"] = sha256_file(path)
        if header.startswith((b"<!doctype", b"<html", b"<?xml")):
            result.update(format="HTML_ERROR", reason="NON_MODEL_DOCUMENT")
        elif size < MIN_GGUF_SIZE:
            result.update(format="INVALID_SIZE", reason="FILE_TOO_SMALL")
        elif header[:4] != GGUF_MAGIC:
            result.update(format="INVALID_HEADER", reason="GGUF_MAGIC_MISMATCH")
        elif expected_sha256 and result["sha256"].lower() != expected_sha256.lower():
            result.update(format="GGUF", reason="SHA256_MISMATCH")
        else:
            result.update(status="VERIFIED_FORMAT", format="GGUF", reason=None)
    except OSError as exc:
        result["reason"] = type(exc).__name__
    return result

def valid_gguf(path, expected_sha256=None):
    return inspect_gguf(path, expected_sha256)["status"] == "VERIFIED_FORMAT"

def write_registry(path, entries):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as stream:
        json.dump(entries, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)
PY

cat > native_ai/training/train_l3.py <<'PY'
"""CPU-only native-from-scratch L3 V2 trainer; preserves all prior checkpoints."""
import argparse, hashlib, json, os, random, sys, time
from pathlib import Path
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from modules.native_models.l3.model import LazaynovaL3
from modules.native_models.l3.tokenizer import ByteTokenizer

def load_records(path):
    records = []
    with open(path, encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            item = json.loads(line)
            if isinstance(item, dict) and isinstance(item.get("messages"), list):
                parts = []
                for msg in item["messages"]:
                    if isinstance(msg, dict) and msg.get("role") in ("system","user","assistant"):
                        content = msg.get("content", "")
                        if isinstance(content, str) and content.strip():
                            parts.append(f'{msg["role"]}: {content}')
                if parts:
                    records.append("\n".join(parts) + "\n")
            elif isinstance(item, dict) and isinstance(item.get("instruction"), str):
                records.append("user: " + item["instruction"] + "\nassistant: " +
                               str(item.get("response", "")) + "\n")
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                records.append(item["text"])
            else:
                raise ValueError(f"unsupported JSONL record at line {number}")
    return records

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default=str(ROOT/"native_ai/datasets/sample_ar_v2.jsonl"))
    p.add_argument("--config", default=str(ROOT/"config/models/l3.json"))
    p.add_argument("--steps", type=int, default=300)
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--lr", type=float, default=0.0003)
    p.add_argument("--checkpoint", default=str(ROOT/"native_ai/checkpoints/l3_checkpoint_v2.pt"))
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    if a.steps < 1 or not 1 <= a.batch_size <= 2:
        p.error("steps must be positive and batch-size must be 1..2 on-device")
    target = Path(a.checkpoint)
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite checkpoint: {target}")
    torch.set_num_threads(1)
    random.seed(a.seed); torch.manual_seed(a.seed)
    config = json.loads(Path(a.config).read_text(encoding="utf-8"))
    tokenizer = ByteTokenizer()
    if int(config["vocab_size"]) != tokenizer.VOCAB_SIZE:
        raise ValueError("tokenizer/config vocabulary mismatch")
    records = load_records(a.data)
    if len(records) < 2:
        raise ValueError("V2 dataset must contain at least two records")
    # Keep conversations separate when sampling; no cross-record boundary leakage.
    encoded = [tokenizer.encode(text, add_bos=True, add_eos=True) for text in records]
    usable = [seq for seq in encoded if len(seq) >= 3]
    if len(usable) < 2:
        raise ValueError("not enough usable training conversations")
    model = LazaynovaL3(config).cpu()
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr)
    losses, start_time = [], time.time()
    model.train()
    for step in range(a.steps):
        xs, ys = [], []
        for _ in range(a.batch_size):
            seq = random.choice(usable)
            max_start = max(0, len(seq) - 2)
            start = random.randint(0, max_start)
            chunk = seq[start:start + int(config["context_length"]) + 1]
            if len(chunk) < 2:
                chunk = seq[:2]
            xs.append(chunk[:-1]); ys.append(chunk[1:])
        width = max(len(x) for x in xs)
        xb = torch.zeros((len(xs), width), dtype=torch.long)
        yb = torch.zeros((len(ys), width), dtype=torch.long)
        for i, (x, y) in enumerate(zip(xs, ys)):
            xb[i, :len(x)] = torch.tensor(x)
            yb[i, :len(y)] = torch.tensor(y)
        opt.zero_grad(set_to_none=True)
        _, loss = model(xb, yb)
        if not torch.isfinite(loss):
            raise RuntimeError("non-finite loss; checkpoint not written")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        losses.append(float(loss.detach()))
        if (step + 1) % max(1, a.steps // 10) == 0:
            print(f"step={step+1}/{a.steps} loss={losses[-1]:.5f}", flush=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"format":"LAZAYNOVA_L3_CHECKPOINT_V2","config":config,
               "model_state_dict":model.state_dict(),"tokenizer":tokenizer.get_config(),
               "training":{"steps":a.steps,"records":len(records),
               "loss_first":losses[0],"loss_last":losses[-1],"loss_history":losses,
               "elapsed_seconds":time.time()-start_time,
               "dataset_sha256":hashlib.sha256(Path(a.data).read_bytes()).hexdigest(),
               "seed":a.seed,"trained_from_scratch":True,
               "external_weights":False,"external_ai_apis":False}}
    tmp = target.with_suffix(target.suffix + ".tmp")
    torch.save(payload, tmp)
    # Verify before atomic publication.
    loaded = torch.load(tmp, map_location="cpu", weights_only=True)
    verifier = LazaynovaL3(loaded["config"])
    verifier.load_state_dict(loaded["model_state_dict"], strict=True)
    os.replace(tmp, target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    print(json.dumps({"checkpoint":str(target),"bytes":target.stat().st_size,
      "sha256":digest,"parameters":verifier.parameter_count(),
      "records":len(records),"loss_first":losses[0],"loss_last":losses[-1],
      "checkpoint_verified":True},ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
PY

cat > lz_core/ai_gateway/gateway.py <<'PY'
"""Local-only gateway that runs native L3 V2 autoregressive inference on CPU."""
import os
from pathlib import Path
from urllib.parse import urlparse
import torch
from modules.native_models.l3.model import LazaynovaL3
from modules.native_models.l3.tokenizer import ByteTokenizer
from native_ai.registry.model_registry import inspect_gguf
from inference.generate import UTF8ConstrainedGenerator

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT/"config/models/l3.json"
CHECKPOINT_PATH = ROOT/"native_ai/checkpoints/l3_checkpoint_v2.pt"
UNTRUSTED_GGUF = ROOT/"native_ai/models/qwen2.5-1.5b-q4.gguf"

class InternalAIGateway:
    def __init__(self, local_endpoint="http://127.0.0.1:8787/v1/chat/completions",
                 checkpoint_path=None, max_new_tokens=96):
        parsed = urlparse(local_endpoint)
        if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1","localhost","::1"):
            raise PermissionError("Only HTTP loopback endpoints are allowed")
        self.local_endpoint = local_endpoint
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else CHECKPOINT_PATH
        self.max_new_tokens = max(1,min(int(max_new_tokens),256))
        self.tokenizer = ByteTokenizer()
        self.model = None
        self.generator = None
        self.model_status = "NOT_TRAINED"
        self.gguf_status = inspect_gguf(str(UNTRUSTED_GGUF))

    def route_request(self, prompt, requested_engine=None):
        return {"status":"LOCAL_NATIVE_L3","engine":requested_engine or "L3",
                "endpoint":self.local_endpoint,"model_status":self.model_status}

    def load_model(self, required=False):
        if self.model is not None:
            return self.model
        if not self.checkpoint_path.is_file():
            self.model_status = "NOT_TRAINED"
            if required:
                raise FileNotFoundError("L3 V2 checkpoint missing; run the V2 trainer")
            return None
        try:
            payload = torch.load(self.checkpoint_path,map_location="cpu",weights_only=True)
            if payload.get("format") != "LAZAYNOVA_L3_CHECKPOINT_V2":
                raise ValueError("unsupported checkpoint format")
            if payload.get("tokenizer",{}).get("vocab_size") != self.tokenizer.VOCAB_SIZE:
                raise ValueError("checkpoint tokenizer mismatch")
            model = LazaynovaL3(payload["config"]).cpu()
            model.load_state_dict(payload["model_state_dict"],strict=True)
            model.eval()
            self.model = model
            self.generator = UTF8ConstrainedGenerator(model,self.tokenizer,self.max_new_tokens)
            self.model_status = "READY_NATIVE_SCRATCH_V2"
            return model
        except Exception:
            self.model_status = "INVALID_CHECKPOINT"
            if required:
                raise
            return None

    def model_status_report(self):
        return {"native_l3":self.model_status,
                "checkpoint_path":str(self.checkpoint_path),
                "checkpoint_exists":self.checkpoint_path.is_file(),
                "gguf":self.gguf_status,
                "fallback":"native L3 architecture only; no external model weights"}

    def generate(self,prompt,max_tokens=None,temperature=0.0):
        if not isinstance(prompt,str) or not prompt.strip() or len(prompt)>12000:
            raise ValueError("prompt must contain 1..12000 characters")
        self.load_model(required=True)
        return self.generator.generate(prompt,max_tokens,temperature)

    def chat_completion(self,messages,max_tokens=96,temperature=0.0):
        if not isinstance(messages,list) or not messages:
            raise ValueError("messages must be a non-empty array")
        parts=[]
        for item in messages[-12:]:
            if not isinstance(item,dict) or item.get("role") not in ("system","user","assistant"):
                raise ValueError("invalid chat message")
            content=item.get("content","")
            if not isinstance(content,str):
                raise ValueError("message content must be text")
            parts.append(f'{item["role"]}: {content}')
        prompt="\n".join(parts)+"\nassistant:"
        output=self.generate(prompt,max_tokens,temperature)
        return {"id":"lz-"+os.urandom(8).hex(),"object":"chat.completion",
                "model":"LAZAYNOVA-L3-native-v2","choices":[
                {"index":0,"message":{"role":"assistant","content":output},
                 "finish_reason":"stop"}]}
PY

cat > backend/local_bridge/lazaynova_local_server.py <<'PY'
"""Threaded loopback REST bridge for LAZAYNOVA native L3 V2."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json, logging, sys
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from lz_core.ai_gateway.gateway import InternalAIGateway
logging.basicConfig(level=logging.INFO)
gateway=InternalAIGateway()
MAX_BODY=256*1024

class LazaynovaHandler(BaseHTTPRequestHandler):
    server_version="LAZAYNOVA-Local/2.0"
    def _send(self,status,payload):
        body=json.dumps(payload,ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(body)
    def _body(self):
        try: length=int(self.headers.get("Content-Length","0"))
        except ValueError: raise ValueError("invalid Content-Length")
        if length<1 or length>MAX_BODY: raise ValueError("request body must be 1..262144 bytes")
        data=json.loads(self.rfile.read(length).decode("utf-8","strict"))
        if not isinstance(data,dict): raise ValueError("JSON body must be an object")
        return data
    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/health":
            return self._send(200,{"status":"healthy","service":"LAZAYNOVA","mode":"LOCAL_ONLY"})
        if path=="/v1/models":
            return self._send(200,{"object":"list","data":[{"id":"LAZAYNOVA-L3-native-v2","object":"model","owned_by":"LAZAYNOVA"}]})
        if path=="/api/model/status":
            return self._send(200,gateway.model_status_report())
        return self._send(404,{"error":{"message":"not found"}})
    def do_POST(self):
        path=urlparse(self.path).path
        if path not in ("/v1/chat/completions","/api/chat"):
            return self._send(404,{"error":{"message":"not found"}})
        try:
            data=self._body()
            if path=="/api/chat":
                prompt=data.get("message")
                if not isinstance(prompt,str): raise ValueError("message must be text")
                out=gateway.generate(prompt,data.get("max_tokens",96),data.get("temperature",0.0))
                return self._send(200,{"brand":"LAZAYNOVA","model":"L3-V2","response":out})
            return self._send(200,gateway.chat_completion(data.get("messages"),data.get("max_tokens",96),data.get("temperature",0.0)))
        except FileNotFoundError as exc:
            return self._send(503,{"error":{"message":str(exc),"type":"model_not_ready"}})
        except (ValueError,TypeError,json.JSONDecodeError) as exc:
            return self._send(400,{"error":{"message":str(exc),"type":"invalid_request"}})
        except Exception:
            logging.exception("local inference failed")
            return self._send(500,{"error":{"message":"local inference failed"}})
    def log_message(self,fmt,*args):
        logging.info("%s - %s",self.address_string(),fmt%args)

if __name__=="__main__":
    host,port="127.0.0.1",8787
    print(f"LAZAYNOVA local API: http://{host}:{port}",flush=True)
    ThreadingHTTPServer((host,port),LazaynovaHandler).serve_forever()
PY

# Generate 240 deterministic conversational records from authored Arabic/English task templates.
python - <<'PY'
import json
from pathlib import Path
out=Path("native_ai/datasets/sample_ar_v2.jsonl")
topics=[
("ما معنى البرمجة؟","البرمجة هي كتابة تعليمات ينفذها الحاسوب لحل مشكلة أو أداء مهمة."),
("ما هي الخوارزمية؟","الخوارزمية مجموعة خطوات مرتبة وواضحة للوصول إلى نتيجة."),
("اشرح المتغير في البرمجة.","المتغير اسم يشير إلى قيمة يمكن استخدامها وتغييرها أثناء تنفيذ البرنامج."),
("ما الفرق بين Python وJavaScript؟","Python شائعة في الأتمتة والبيانات والذكاء الاصطناعي، وJavaScript أساسية لتطوير الويب."),
("ما فائدة Git؟","Git يتتبع تغييرات الملفات ويساعد على إدارة إصدارات المشروع والعمل بأمان."),
("كيف أحمي كلمة المرور؟","استخدم كلمة طويلة وفريدة، ومدير كلمات مرور، والمصادقة متعددة العوامل."),
("ما هو UTF-8؟","UTF-8 ترميز يحول النصوص إلى بايتات ويدعم العربية والإنجليزية ومعظم لغات العالم."),
("لماذا نستخدم الاختبارات؟","الاختبارات تكشف الأخطاء مبكراً وتتحقق من أن التعديلات لا تكسر السلوك السابق."),
("ما هو التعلم الآلي؟","التعلم الآلي مجال يجعل البرامج تتعلم أنماطاً من البيانات لتحسين التنبؤ أو القرار."),
("ما وظيفة وحدة المعالجة CPU؟","تنفذ CPU التعليمات والحسابات العامة وتشغّل أجزاء النظام والبرامج."),
("كيف أبدأ مشروعاً صغيراً؟","حدد مشكلة واضحة، وابنِ نسخة بسيطة، واختبرها مع مستخدمين، ثم حسّنها تدريجياً."),
("ما فائدة التوثيق؟","التوثيق يشرح طريقة الاستخدام والتصميم والقرارات ويسهّل صيانة المشروع."),
("ما هو JSON؟","JSON تنسيق نصي منظم لتبادل البيانات باستخدام كائنات ومصفوفات وقيم."),
("اشرح واجهة API.","واجهة API مجموعة قواعد تسمح لبرنامج بالتواصل مع برنامج أو خدمة أخرى."),
("ما معنى النسخ الاحتياطي؟","النسخ الاحتياطي نسخة إضافية من البيانات لاستعادتها عند الفقد أو التلف."),
("كيف أتعلم الإنجليزية؟","مارس القراءة والاستماع يومياً، واكتب جملاً قصيرة، وراجع الكلمات في سياقها."),
("ما الفرق بين RAM والتخزين؟","RAM ذاكرة مؤقتة سريعة أثناء التشغيل، أما التخزين فيحتفظ بالملفات بعد إغلاق الجهاز."),
("كيف أتعامل مع خطأ برمجي؟","اقرأ رسالة الخطأ، وحدد السطر والسبب، وأنشئ اختباراً صغيراً قبل تعديل الكود."),
("ما هو النموذج اللغوي؟","النموذج اللغوي يتعلم أنماط النصوص ويتوقع الرموز التالية لإنتاج نص."),
("ما أهمية الخصوصية؟","الخصوصية تحمي بيانات الأشخاص وتحد من جمعها أو مشاركتها دون حاجة أو موافقة.")
]
systems=[
"أنت مساعد LAZAYNOVA. أجب بدقة وبأسلوب واضح.",
"You are LAZAYNOVA, a helpful assistant. Answer clearly and accurately.",
"أنت مساعد تعليمي. اشرح الفكرة بلغة بسيطة.",
"You are a programming tutor. Give a concise, practical explanation."
]
rows=[]
for i in range(240):
    q,a=topics[i%len(topics)]
    system=systems[(i//len(topics))%len(systems)]
    if i%3==0:
        user=q
        answer=a
    elif i%3==1:
        user="اشرح بإيجاز: "+q
        answer=a+" ويمكنك طلب مثال عملي لتوضيحها."
    else:
        user="Give a short answer in English: "+[
            "What is programming?","What is an algorithm?","Why do we use tests?",
            "What is UTF-8?","What is an API?","How can I debug code?"
        ][i%6]
        answer=[
            "Programming is writing instructions that a computer executes to perform tasks.",
            "An algorithm is a clear sequence of steps for solving a problem.",
            "Tests detect defects early and help prevent regressions.",
            "UTF-8 is a byte encoding that represents text from many writing systems.",
            "An API is a defined interface through which software components communicate.",
            "Read the error, isolate the failing case, and test one change at a time."
        ][i%6]
    rows.append({"messages":[{"role":"system","content":system},
      {"role":"user","content":user},{"role":"assistant","content":answer}]})
with out.open("x",encoding="utf-8") as f:
    for row in rows:
        f.write(json.dumps(row,ensure_ascii=False)+"\n")
print(f"Created {len(rows)} records: {out}")
PY

echo
echo "========== COMPILE CHECK =========="
python -m py_compile \
  modules/native_models/l3/tokenizer.py \
  inference/generate.py \
  native_ai/training/train_l3.py \
  native_ai/registry/model_registry.py \
  lz_core/ai_gateway/gateway.py \
  backend/local_bridge/lazaynova_local_server.py

echo
echo "========== DATASET CHECK =========="
wc -l native_ai/datasets/sample_ar_v2.jsonl
python - <<'PY'
import json
p="native_ai/datasets/sample_ar_v2.jsonl"
with open(p,encoding="utf-8") as f:
    rows=[json.loads(x) for x in f if x.strip()]
assert len(rows)>=200
assert all(len(x["messages"])==3 for x in rows)
print("JSONL_VALID records=",len(rows))
PY

echo
echo "========== UNIT TESTS =========="
python -m unittest discover -s tests -p 'test_native_l3.py' -v

echo
echo "========== V2 BUILD COMPLETE =========="
echo "Backup: $BACKUP"
echo "Old checkpoint preserved: native_ai/models/l3_checkpoint.pt"
echo "V2 dataset: native_ai/datasets/sample_ar_v2.jsonl"
echo "V2 checkpoint target (not trained yet): native_ai/checkpoints/l3_checkpoint_v2.pt"
