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
