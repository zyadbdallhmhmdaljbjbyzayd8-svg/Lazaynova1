#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

ROOT="${HOME}/Lazaynova1"
cd "$ROOT"

if [[ "$(git branch --show-current)" != "main" ]]; then
  echo "STOP: expected existing branch main; no branch changes made." >&2
  exit 2
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="$HOME/LAZAYNOVA_BACKUP_$STAMP"
mkdir -p "$BACKUP"
FILES=(
  modules/native_models/l3/model.py
  modules/native_models/l3/tokenizer.py
  config/models/l3.json
  lz_core/ai_gateway/gateway.py
  lz_core/resource_manager/monitor.py
  backend/local_bridge/lazaynova_local_server.py
  docs/ANDROID_LOCAL_CONNECTION.json
)
for f in "${FILES[@]}"; do
  if [[ -f "$f" ]]; then
    mkdir -p "$BACKUP/$(dirname "$f")"
    cp -p "$f" "$BACKUP/$f"
  fi
done
echo "Backup created: $BACKUP"

# Refuse to overwrite any pre-existing new-path files not included in the backup set.
for f in native_ai/training/train_l3.py native_ai/registry/model_registry.py tests/test_native_l3.py; do
  if [[ -e "$f" ]]; then
    echo "STOP: $f already exists; inspect and back it up manually before proceeding." >&2
    exit 3
  fi
done
mkdir -p native_ai/training native_ai/registry native_ai/models tests lz_core/ai_gateway

cat > modules/native_models/l3/tokenizer.py <<'PY'
"""Stable UTF-8 byte tokenizer with four reserved special tokens."""
class ByteTokenizer:
    PAD, UNK, BOS, EOS = 0, 1, 2, 3
    BYTE_OFFSET = 4
    VOCAB_SIZE = 260

    def encode(self, text, add_bos=False, add_eos=False):
        if not isinstance(text, str):
            raise TypeError("text must be str")
        ids = [b + self.BYTE_OFFSET for b in text.encode("utf-8")]
        if add_bos:
            ids.insert(0, self.BOS)
        if add_eos:
            ids.append(self.EOS)
        return ids

    def decode(self, tokens):
        data = bytearray()
        for token in tokens:
            token = int(token)
            if self.BYTE_OFFSET <= token < self.VOCAB_SIZE:
                data.append(token - self.BYTE_OFFSET)
        return data.decode("utf-8", errors="replace")

    def get_config(self):
        return {
            "type": "native_utf8_byte",
            "vocab_size": self.VOCAB_SIZE,
            "pad_token": self.PAD,
            "unk_token": self.UNK,
            "bos_token": self.BOS,
            "eos_token": self.EOS
        }
PY

cat > modules/native_models/l3/model.py <<'PY'
"""Native decoder-only Transformer for LAZAYNOVA L3; initialized from scratch."""
import torch
import torch.nn as nn
import torch.nn.functional as F


class CausalSelfAttention(nn.Module):
    def __init__(self, config):
        super().__init__()
        dim, heads = int(config["d_model"]), int(config["n_heads"])
        if heads < 1 or dim % heads:
            raise ValueError("d_model must be divisible by positive n_heads")
        self.heads, self.head_dim = heads, dim // heads
        self.qkv = nn.Linear(dim, 3 * dim)
        self.projection = nn.Linear(dim, dim)
        self.dropout = nn.Dropout(float(config.get("dropout", 0.0)))

    def forward(self, x):
        batch, length, dim = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)
        def split(t):
            return t.view(batch, length, self.heads, self.head_dim).transpose(1, 2)
        q, k, v = split(q), split(k), split(v)
        scores = (q @ k.transpose(-2, -1)) * (self.head_dim ** -0.5)
        mask = torch.ones(length, length, device=x.device, dtype=torch.bool).tril()
        scores = scores.masked_fill(~mask, torch.finfo(scores.dtype).min)
        weights = self.dropout(F.softmax(scores, dim=-1))
        out = (weights @ v).transpose(1, 2).contiguous().view(batch, length, dim)
        return self.projection(out)


class FeedForward(nn.Module):
    def __init__(self, config):
        super().__init__()
        dim, hidden = int(config["d_model"]), int(config["ff_dim"])
        self.net = nn.Sequential(nn.Linear(dim, hidden), nn.GELU(),
                                 nn.Linear(hidden, dim),
                                 nn.Dropout(float(config.get("dropout", 0.0))))
    def forward(self, x):
        return self.net(x)


class TransformerBlock(nn.Module):
    def __init__(self, config):
        super().__init__()
        dim = int(config["d_model"])
        self.norm1, self.attention = nn.LayerNorm(dim), CausalSelfAttention(config)
        self.norm2, self.ff = nn.LayerNorm(dim), FeedForward(config)
    def forward(self, x):
        x = x + self.attention(self.norm1(x))
        return x + self.ff(self.norm2(x))


class LazaynovaL3(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.config = dict(config)
        vocab, dim, context = (int(config[k]) for k in
                               ("vocab_size", "d_model", "context_length"))
        if min(vocab, dim, context, int(config["n_layers"]), int(config["n_heads"])) < 1:
            raise ValueError("model dimensions must be positive")
        self.token_embedding = nn.Embedding(vocab, dim)
        self.position_embedding = nn.Embedding(context, dim)
        self.blocks = nn.ModuleList([TransformerBlock(config)
                                     for _ in range(int(config["n_layers"]))])
        self.final_norm = nn.LayerNorm(dim)
        self.language_head = nn.Linear(dim, vocab, bias=False)
        self.apply(self._init_weights)
        self.language_head.weight = self.token_embedding.weight

    @staticmethod
    def _init_weights(module):
        if isinstance(module, (nn.Linear, nn.Embedding)):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if isinstance(module, nn.Linear) and module.bias is not None:
                nn.init.zeros_(module.bias)

    def forward(self, input_ids, targets=None):
        if input_ids.ndim != 2:
            raise ValueError("input_ids must have shape [batch, sequence]")
        batch, length = input_ids.shape
        if length < 1 or length > int(self.config["context_length"]):
            raise ValueError("sequence length outside configured context")
        if input_ids.min().item() < 0 or input_ids.max().item() >= int(self.config["vocab_size"]):
            raise ValueError("token id outside vocabulary")
        pos = torch.arange(length, device=input_ids.device)
        x = self.token_embedding(input_ids) + self.position_embedding(pos)[None, :, :]
        for block in self.blocks:
            x = block(x)
        logits = self.language_head(self.final_norm(x))
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)),
                                   targets.reshape(-1), ignore_index=0)
        return logits, loss

    def parameter_count(self):
        return sum(p.numel() for p in self.parameters())
PY

cat > config/models/l3.json <<'JSON'
{
  "model_name": "LAZAYNOVA L3",
  "version": "native-scratch-v1",
  "architecture": "decoder_only_transformer",
  "vocab_size": 260,
  "d_model": 128,
  "n_heads": 4,
  "n_layers": 2,
  "ff_dim": 256,
  "context_length": 128,
  "dropout": 0.0,
  "precision": "float32",
  "device": "cpu",
  "initialization": "random",
  "tokenizer": "native_utf8_byte",
  "external_weights": false,
  "external_ai_apis": false
}
JSON

cat > native_ai/registry/model_registry.py <<'PY'
"""Integrity-first local model registry. Never executes unverified artifacts."""
import hashlib
import json
import os

GGUF_MAGIC = b"GGUF"

def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def inspect_gguf(path, expected_sha256=None):
    result = {"path": str(path), "status": "UNVERIFIED", "format": None,
              "sha256": None, "reason": None}
    if not os.path.isfile(path):
        result["reason"] = "FILE_NOT_FOUND"
        return result
    try:
        with open(path, "rb") as stream:
            header = stream.read(4)
        result["sha256"] = sha256_file(path)
        if header.lstrip().lower().startswith((b"<!doctype", b"<html")):
            result.update(status="UNVERIFIED", format="HTML_ERROR", reason="HTML_CONTENT_NOT_GGUF")
        elif header != GGUF_MAGIC:
            result.update(status="UNVERIFIED", format="INVALID_HEADER", reason="GGUF_MAGIC_MISMATCH")
        elif expected_sha256 and result["sha256"].lower() != expected_sha256.lower():
            result.update(status="UNVERIFIED", format="GGUF", reason="SHA256_MISMATCH")
        else:
            result.update(status="VERIFIED_FORMAT", format="GGUF", reason=None)
    except OSError as exc:
        result["reason"] = type(exc).__name__
    return result

def write_registry(path, entries):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as stream:
        json.dump(entries, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)
PY

cat > lz_core/resource_manager/monitor.py <<'PY'
import os
import shutil

class ResourceManager:
    def get_system_metrics(self):
        disk = shutil.disk_usage(".")
        free_ram = total_ram = 0
        try:
            with open("/proc/meminfo", encoding="ascii") as stream:
                for line in stream:
                    if line.startswith("MemTotal:"):
                        total_ram = int(line.split()[1]) // 1024
                    elif line.startswith("MemAvailable:"):
                        free_ram = int(line.split()[1]) // 1024
        except OSError:
            pass
        return {"total_ram_mb": total_ram, "free_ram_mb": free_ram,
                "free_disk_gb": round(disk.free / (1024 ** 3), 2)}

    def recommend_engine(self):
        # L3 is the only currently implemented native inference engine.
        return "L3"
PY

cat > native_ai/training/train_l3.py <<'PY'
"""CPU training entry point for the native-from-scratch L3 model."""
import argparse
import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from modules.native_models.l3.model import LazaynovaL3
from modules.native_models.l3.tokenizer import ByteTokenizer

def load_texts(path):
    texts = []
    with open(path, encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                texts.append(line)
                continue
            if isinstance(item, dict):
                if "instruction" in item:
                    texts.extend([str(item.get("instruction", "")), str(item.get("response", ""))])
                for message in item.get("messages", []):
                    if isinstance(message, dict) and message.get("content"):
                        texts.append(str(message["content"]))
                if not any(k in item for k in ("instruction", "messages")):
                    texts.extend(str(v) for v in item.values() if isinstance(v, str))
    return [t for t in texts if t.strip()]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(ROOT / "native_ai/datasets/sample_ar.jsonl"))
    parser.add_argument("--config", default=str(ROOT / "config/models/l3.json"))
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--checkpoint", default=str(ROOT / "native_ai/models/l3_checkpoint.pt"))
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    if args.steps < 1 or not 1 <= args.batch_size <= 8:
        parser.error("steps must be positive and batch-size must be 1..8")
    torch.set_num_threads(1)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    tokenizer = ByteTokenizer()
    if config["vocab_size"] != tokenizer.VOCAB_SIZE:
        raise ValueError("config vocab_size does not match tokenizer")
    texts = load_texts(args.data)
    if not texts:
        raise ValueError("dataset contains no usable text")
    ids = tokenizer.encode("\n".join(texts), add_bos=True, add_eos=True)
    context = int(config["context_length"])
    if len(ids) < 3:
        raise ValueError("not enough tokens to train")
    model = LazaynovaL3(config).cpu()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    losses, started = [], time.time()
    model.train()
    for step in range(args.steps):
        xs, ys = [], []
        for _ in range(args.batch_size):
            start = random.randrange(0, max(1, len(ids) - 2))
            chunk = ids[start:start + context + 1]
            if len(chunk) < 2:
                chunk = ids[:2]
            x, y = chunk[:-1], chunk[1:]
            xs.append(x); ys.append(y)
        width = max(map(len, xs))
        xb = torch.zeros(len(xs), width, dtype=torch.long)
        yb = torch.zeros(len(ys), width, dtype=torch.long)
        for i, (x, y) in enumerate(zip(xs, ys)):
            xb[i, :len(x)] = torch.tensor(x)
            yb[i, :len(y)] = torch.tensor(y)
        optimizer.zero_grad(set_to_none=True)
        _, loss = model(xb, yb)
        if not torch.isfinite(loss):
            raise RuntimeError("non-finite training loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.detach()))
        if (step + 1) % max(1, args.steps // 10) == 0:
            print(f"step={step+1}/{args.steps} loss={losses[-1]:.6f}", flush=True)
    data_hash = hashlib.sha256(Path(args.data).read_bytes()).hexdigest()
    payload = {
        "format": "LAZAYNOVA_L3_CHECKPOINT_V1",
        "config": config,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "tokenizer": tokenizer.get_config(),
        "training": {"steps": args.steps, "loss_first": losses[0],
                     "loss_last": losses[-1], "loss_history": losses,
                     "elapsed_seconds": time.time() - started,
                     "dataset_sha256": data_hash, "seed": args.seed,
                     "trained_from_scratch": True}
    }
    target = Path(args.checkpoint)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    torch.save(payload, tmp)
    os.replace(tmp, target)
    # Reload and verify the exact checkpoint before reporting success.
    verified = torch.load(target, map_location="cpu", weights_only=True)
    check = LazaynovaL3(verified["config"])
    check.load_state_dict(verified["model_state_dict"], strict=True)
    print(json.dumps({"checkpoint": str(target), "bytes": target.stat().st_size,
                      "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                      "parameters": check.parameter_count(),
                      "loss_first": losses[0], "loss_last": losses[-1],
                      "checkpoint_verified": True}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
PY

cat > lz_core/ai_gateway/gateway.py <<'PY'
"""Local-only L3 inference gateway; no external API or remote endpoint support."""
import json
import os
from pathlib import Path
from urllib.parse import urlparse

import torch

from lz_core.resource_manager.monitor import ResourceManager
from modules.native_models.l3.model import LazaynovaL3
from modules.native_models.l3.tokenizer import ByteTokenizer
from native_ai.registry.model_registry import inspect_gguf

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config/models/l3.json"
CHECKPOINT_PATH = ROOT / "native_ai/models/l3_checkpoint.pt"
UNTRUSTED_GGUF = ROOT / "native_ai/models/qwen2.5-1.5b-q4.gguf"

class InternalAIGateway:
    def __init__(self, local_endpoint="http://127.0.0.1:8787/v1/chat/completions",
                 checkpoint_path=None, max_new_tokens=96):
        parsed = urlparse(local_endpoint)
        if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
            raise PermissionError("Only HTTP loopback endpoints are allowed")
        self.local_endpoint = local_endpoint
        self.rm = ResourceManager()
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else CHECKPOINT_PATH
        self.max_new_tokens = max(1, min(int(max_new_tokens), 256))
        self.tokenizer = ByteTokenizer()
        self.model = None
        self.model_status = "NOT_TRAINED"
        self.gguf_status = inspect_gguf(str(UNTRUSTED_GGUF))

    def route_request(self, prompt, requested_engine=None):
        return {"status": "LOCAL_NATIVE_L3", "engine": requested_engine or "L3",
                "endpoint": self.local_endpoint, "model_status": self.model_status}

    def load_model(self, required=False):
        if self.model is not None:
            return self.model
        if not self.checkpoint_path.is_file():
            self.model_status = "NOT_TRAINED"
            if required:
                raise FileNotFoundError("Native L3 checkpoint missing; train it first")
            return None
        payload = torch.load(self.checkpoint_path, map_location="cpu", weights_only=True)
        if payload.get("format") != "LAZAYNOVA_L3_CHECKPOINT_V1":
            raise ValueError("Unsupported or untrusted checkpoint format")
        if payload.get("tokenizer", {}).get("vocab_size") != self.tokenizer.VOCAB_SIZE:
            raise ValueError("Checkpoint tokenizer mismatch")
        model = LazaynovaL3(payload["config"])
        model.load_state_dict(payload["model_state_dict"], strict=True)
        model.eval()
        self.model = model
        self.model_status = "READY_NATIVE_SCRATCH"
        return model

    def model_status_report(self):
        return {"native_l3": self.model_status,
                "checkpoint_exists": self.checkpoint_path.is_file(),
                "gguf": self.gguf_status,
                "fallback": "native L3 only; no external model weights"}

    @torch.inference_mode()
    def generate(self, prompt, max_tokens=None, temperature=0.0):
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 12000:
            raise ValueError("prompt must contain 1..12000 characters")
        model = self.load_model(required=True)
        count = self.max_new_tokens if max_tokens is None else max(1, min(int(max_tokens), self.max_new_tokens))
        ids = self.tokenizer.encode(prompt, add_bos=True)
        context = int(model.config["context_length"])
        generated = []
        for _ in range(count):
            window = ids[-context:]
            x = torch.tensor([window], dtype=torch.long)
            logits, _ = model(x)
            next_logits = logits[0, -1, :]
            next_logits[:4] = torch.finfo(next_logits.dtype).min
            if temperature and temperature > 0:
                probs = torch.softmax(next_logits / max(float(temperature), 1e-4), dim=-1)
                next_id = int(torch.multinomial(probs, 1).item())
            else:
                next_id = int(torch.argmax(next_logits).item())
            if next_id == self.tokenizer.EOS:
                break
            ids.append(next_id)
            generated.append(next_id)
        return self.tokenizer.decode(generated)

    def chat_completion(self, messages, max_tokens=96, temperature=0.0):
        if not isinstance(messages, list) or not messages:
            raise ValueError("messages must be a non-empty array")
        parts = []
        for item in messages[-12:]:
            if not isinstance(item, dict) or item.get("role") not in ("system", "user", "assistant"):
                raise ValueError("invalid chat message")
            content = item.get("content", "")
            if not isinstance(content, str):
                raise ValueError("message content must be text")
            parts.append(f'{item["role"]}: {content}')
        prompt = "\n".join(parts) + "\nassistant:"
        output = self.generate(prompt, max_tokens=max_tokens, temperature=temperature)
        return {"id": "lz-" + os.urandom(8).hex(), "object": "chat.completion",
                "model": "LAZAYNOVA-L3-native", "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": output},
                     "finish_reason": "length"}]}
PY

cat > backend/local_bridge/lazaynova_local_server.py <<'PY'
"""Threaded local REST bridge for LAZAYNOVA native inference."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from lz_core.ai_gateway.gateway import InternalAIGateway
from agents.orchestrator import AgentOrchestrator

logging.basicConfig(level=logging.INFO)
gateway = InternalAIGateway()
orchestrator = AgentOrchestrator()
MAX_BODY = 256 * 1024

class LazaynovaHandler(BaseHTTPRequestHandler):
    server_version = "LAZAYNOVA-Local/1.0"

    def _send(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("invalid Content-Length")
        if length < 1 or length > MAX_BODY:
            raise ValueError("request body must be 1..262144 bytes")
        raw = self.rfile.read(length)
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self._send(200, {"status": "healthy", "service": "LAZAYNOVA",
                                    "mode": "LOCAL_ONLY"})
        if path == "/v1/models":
            return self._send(200, {"object": "list", "data": [
                {"id": "LAZAYNOVA-L3-native", "object": "model",
                 "owned_by": "LAZAYNOVA"}]})
        if path == "/api/model/status":
            return self._send(200, gateway.model_status_report())
        return self._send(404, {"error": {"message": "not found"}})

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/v1/chat/completions", "/api/chat"):
            return self._send(404, {"error": {"message": "not found"}})
        try:
            data = self._body()
            if path == "/api/chat":
                prompt = data.get("message")
                if not isinstance(prompt, str):
                    raise ValueError("message must be text")
                text = gateway.generate(prompt, data.get("max_tokens", 96))
                return self._send(200, {"brand": "LAZAYNOVA", "model": "L3",
                                        "response": text, "routing": gateway.route_request(prompt)})
            result = gateway.chat_completion(data.get("messages"),
                                             data.get("max_tokens", 96),
                                             data.get("temperature", 0.0))
            return self._send(200, result)
        except FileNotFoundError as exc:
            return self._send(503, {"error": {"message": str(exc), "type": "model_not_ready"}})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self._send(400, {"error": {"message": str(exc), "type": "invalid_request"}})
        except Exception:
            logging.exception("Inference request failed")
            return self._send(500, {"error": {"message": "local inference failed"}})

    def log_message(self, fmt, *args):
        logging.info("%s - %s", self.address_string(), fmt % args)

if __name__ == "__main__":
    host, port = "127.0.0.1", 8787
    print(f"LAZAYNOVA local API: http://{host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), LazaynovaHandler).serve_forever()
PY

cat > docs/ANDROID_LOCAL_CONNECTION.json <<'JSON'
{
  "android_emulator_gateway": "http://10.0.2.2:8787",
  "termux_on_device": "http://127.0.0.1:8787",
  "openai_compatible_chat": "/v1/chat/completions",
  "models": "/v1/models",
  "health_check": "/health",
  "note": "10.0.2.2 is for Android Emulator to host access; Termux on the same phone uses 127.0.0.1."
}
JSON

cat > tests/test_native_l3.py <<'PY'
import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from modules.native_models.l3.tokenizer import ByteTokenizer
from modules.native_models.l3.model import LazaynovaL3
from native_ai.registry.model_registry import inspect_gguf
from lz_core.ai_gateway.gateway import InternalAIGateway

class NativeL3Tests(unittest.TestCase):
    def test_tokenizer_utf8_and_special_tokens(self):
        tok = ByteTokenizer()
        ids = tok.encode("مرحبا 🌍", add_bos=True, add_eos=True)
        self.assertEqual(ids[0], tok.BOS)
        self.assertEqual(ids[-1], tok.EOS)
        self.assertEqual(tok.decode(ids), "مرحبا 🌍")
        self.assertEqual(tok.VOCAB_SIZE, 260)

    def test_model_forward(self):
        config = json.loads((ROOT / "config/models/l3.json").read_text())
        model = LazaynovaL3(config)
        import torch
        x = torch.tensor([[2, 4, 5, 6]])
        logits, loss = model(x, torch.tensor([[4, 5, 6, 7]]))
        self.assertEqual(tuple(logits.shape), (1, 4, 260))
        self.assertTrue(torch.isfinite(loss).item())

    def test_html_gguf_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.gguf"
            path.write_text("<!doctype html>", encoding="utf-8")
            result = inspect_gguf(str(path))
            self.assertEqual(result["format"], "HTML_ERROR")
            self.assertEqual(result["status"], "UNVERIFIED")

    def test_external_endpoint_rejected(self):
        with self.assertRaises(PermissionError):
            InternalAIGateway("https://example.com/v1/chat/completions")

if __name__ == "__main__":
    unittest.main(verbosity=2)
PY

echo "===== SAFE SYNTAX AND UNIT VERIFICATION ====="
python -m py_compile \
  modules/native_models/l3/model.py \
  modules/native_models/l3/tokenizer.py \
  native_ai/registry/model_registry.py \
  native_ai/training/train_l3.py \
  lz_core/ai_gateway/gateway.py \
  lz_core/resource_manager/monitor.py \
  backend/local_bridge/lazaynova_local_server.py \
  tests/test_native_l3.py

python -m unittest discover -s tests -p test_native_l3.py -v

echo "===== VERIFY EXISTING QWEN FILE WAS NOT MODIFIED ====="
if [[ -f native_ai/models/qwen2.5-1.5b-q4.gguf ]]; then
  file native_ai/models/qwen2.5-1.5b-q4.gguf
  python - <<'PY'
from native_ai.registry.model_registry import inspect_gguf
import json
p = "native_ai/models/qwen2.5-1.5b-q4.gguf"
print(json.dumps(inspect_gguf(p), ensure_ascii=False, indent=2))
PY
fi

echo "===== BUILD FILES CREATED ====="
echo "Backup: $BACKUP"
echo "Train L3 with: python native_ai/training/train_l3.py --steps 100"
echo "Start API with: python backend/local_bridge/lazaynova_local_server.py"
echo "No branch switch, reset, clean, commit, or push was performed."
