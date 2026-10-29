"""Loopback-only OpenAI-compatible inference adapter for Lazaynova Tiny."""
from __future__ import annotations
import json, os, secrets, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
try:
    import torch
except ImportError as exc:
    raise SystemExit("Install PyTorch first (Termux: pkg install python-torch)") from exc

ROOT = Path(__file__).resolve().parent
CHECKPOINT = Path(os.environ.get("LAZAYNOVA_CHECKPOINT", str(ROOT / "artifacts" / "lazaynova-tiny.pt"))).expanduser()
HOST = os.environ.get("LAZAYNOVA_HOST", "127.0.0.1")
PORT = int(os.environ.get("LAZAYNOVA_PORT", "8080"))
sys.path.insert(0, str(ROOT))
from train import LazaynovaTiny

def load_model(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {path}. Run python model/train.py first.")
    ck = torch.load(path, map_location="cpu", weights_only=True)
    cfg, stoi, itos, state = ck.get("config"), ck.get("stoi"), ck.get("itos"), ck.get("model_state")
    if not all(isinstance(x, dict) for x in (cfg, stoi, itos, state)) or not stoi:
        raise ValueError("Invalid checkpoint: expected config, tokenizer and model_state.")
    itos = {int(k): str(v) for k, v in itos.items()}
    model = LazaynovaTiny(len(stoi), cfg)
    model.load_state_dict(state, strict=True)
    model.eval()
    return model, cfg, {str(k): int(v) for k, v in stoi.items()}, itos

MODEL, CONFIG, STOI, ITOS = load_model(CHECKPOINT)
def encode(s: str) -> list[int]:
    return [STOI[ch] for ch in s if ch in STOI]
def decode(ids: list[int]) -> str:
    return "".join(ITOS.get(int(i), "") for i in ids)
def generate(messages: list[dict[str, Any]], max_tokens: int = 64, temperature: float = 0.8) -> str:
    prompt = "\n".join(f"{m.get('role','user')}: {m.get('content','')}" for m in messages
                        if isinstance(m, dict) and m.get("role") in {"system","user","assistant"})
    ids = encode(prompt)
    if not ids: ids = [next(iter(STOI.values()))]
    ids = ids[-int(CONFIG.get("block_size", 64)):]
    x = torch.tensor([ids], dtype=torch.long)
    with torch.inference_mode():
        result = MODEL.generate(x, max_new_tokens=max(1, min(int(max_tokens), 128)),
                                temperature=max(0.1, min(float(temperature), 2.0)))[0].tolist()
    return decode(result[len(ids):]).strip()

class Handler(BaseHTTPRequestHandler):
    server_version = "LazaynovaLocal/0.1"
    def reply(self, status: int, payload: dict):
        raw = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)
    def do_GET(self):
        if self.path == "/health":
            return self.reply(200, {"ok": True, "model": "lazaynova-tiny", "device": "cpu"})
        if self.path == "/v1/models":
            return self.reply(200, {"object":"list","data":[{"id":"lazaynova-core","object":"model","owned_by":"lazaynova"}]})
        return self.reply(404, {"error":{"message":"Not found","type":"not_found"}})
    def do_POST(self):
        if self.path != "/v1/chat/completions":
            return self.reply(404, {"error":{"message":"Not found","type":"not_found"}})
        try: size = int(self.headers.get("Content-Length", "0"))
        except ValueError: size = 0
        if size < 1 or size > 262144:
            return self.reply(413, {"error":{"message":"Invalid or oversized request body","type":"invalid_request_error"}})
        try: body = json.loads(self.rfile.read(size))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self.reply(400, {"error":{"message":"Invalid JSON","type":"invalid_request_error"}})
        if not isinstance(body, dict) or not isinstance(body.get("messages"), list):
            return self.reply(400, {"error":{"message":"messages must be an array","type":"invalid_request_error"}})
        if body.get("stream") is True:
            return self.reply(400, {"error":{"message":"Streaming is not supported","type":"invalid_request_error"}})
        try: answer = generate(body["messages"], body.get("max_tokens", 64), body.get("temperature", .8))
        except (TypeError, ValueError, RuntimeError) as exc:
            return self.reply(400, {"error":{"message":str(exc)[:180],"type":"invalid_request_error"}})
        return self.reply(200, {"id":"chatcmpl-"+secrets.token_hex(8),"object":"chat.completion",
            "created":int(time.time()),"model":body.get("model","lazaynova-core"),
            "choices":[{"index":0,"message":{"role":"assistant","content":answer},"finish_reason":"length"}],
            "usage":{"prompt_tokens":0,"completion_tokens":0,"total_tokens":0}})
    def log_message(self, fmt, *args):
        print("[LazaynovaLocal] "+(fmt % args), flush=True)

if __name__ == "__main__":
    print(f"Lazaynova local inference: http://{HOST}:{PORT}")
    print(f"Checkpoint: {CHECKPOINT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
