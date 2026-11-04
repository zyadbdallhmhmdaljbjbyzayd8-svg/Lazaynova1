"""Offline evidence-gated inference for native LZ-Core checkpoints."""
from __future__ import annotations
import os
from pathlib import Path
import torch
from .config import LZConfig
from .manifest import verify_manifest
from .model import LZCore
from .provenance import load_json, verify_file_hash
from .tokenizer import LZTokenizer
class InferenceError(RuntimeError): pass
class LZCoreInference:
    def __init__(self,model,tokenizer,config,*,device,status):
        self.model,self.tokenizer,self.config=model,tokenizer,config
        self.device,self.status=device,status
    @classmethod
    def load(cls,checkpoint_path,manifest_path,*,device="cpu",allow_untrained=False):
        checkpoint_path,manifest_path=Path(checkpoint_path),Path(manifest_path)
        if not isinstance(allow_untrained,bool): raise InferenceError("allow_untrained must be boolean")
        if allow_untrained and os.environ.get("LZCORE_TEST_MODE")!="1": raise InferenceError("allow_untrained is restricted to LZCORE_TEST_MODE=1")
        if device!="cpu" and not (isinstance(device,str) and device.startswith("cuda") and torch.cuda.is_available()): raise InferenceError(f"requested device unavailable: {device}")
        if not checkpoint_path.is_file() or not manifest_path.is_file(): raise InferenceError("checkpoint and governance manifest are required")
        try:
            manifest=load_json(manifest_path); name=manifest["dataset"]["path_name"]
            if not isinstance(name,str) or Path(name).name!=name: raise ValueError("dataset path_name must be a basename")
            verify_manifest(manifest,dataset_path=manifest_path.parent/name,checkpoint_path=checkpoint_path)
        except (ValueError,KeyError,OSError,TypeError) as exc: raise InferenceError(f"governance verification failed: {exc}") from exc
        status=manifest["status"]
        if status!="scratch-trained-verified":
            if not allow_untrained: raise InferenceError(f"model status {status!r} is not approved for normal inference")
            if status not in {"scratch-initialized","scratch-trained-unverified"}: raise InferenceError(f"test mode cannot bypass status {status!r}")
        try:
            verify_file_hash(checkpoint_path,manifest["checkpoint"]["sha256"])
            ck=torch.load(checkpoint_path,map_location=device,weights_only=True)
            if not isinstance(ck,dict) or ck.get("format")!="lzcore-ckpt-1": raise ValueError("unsupported checkpoint format")
            if ck.get("dataset_sha256")!=manifest["dataset"]["sha256"]: raise ValueError("checkpoint dataset hash mismatch")
            if status=="scratch-trained-verified":
                ev=manifest["evaluation"]
                if ck.get("step")!=ev.get("steps_completed"): raise ValueError("checkpoint step mismatch")
                if ck.get("initial_val_loss")!=ev.get("initial_val_loss") or ck.get("best_val_loss")!=ev.get("best_val_loss"): raise ValueError("checkpoint loss evidence mismatch")
            cfg=LZConfig.from_dict(ck["config"]); cfg.validate()
            tok=LZTokenizer.from_dict(ck["tokenizer"])
            if tok.hash()!=ck["tokenizer_hash"]: raise ValueError("tokenizer hash mismatch")
            if cfg.vocab_size!=tok.vocab_size: raise ValueError("config/tokenizer vocabulary mismatch")
            model=LZCore(cfg); model.load_state_dict(ck["model_state"],strict=True); model.to(device).eval()
        except Exception as exc: raise InferenceError(f"checkpoint loading failed: {exc}") from exc
        return cls(model,tok,cfg,device=device,status=status)
    @torch.inference_mode()
    def generate(self,prompt,*,max_new_tokens=64,temperature=0.8,top_k=40):
        if not isinstance(prompt,str) or not prompt.strip(): raise ValueError("prompt must be non-empty")
        if isinstance(max_new_tokens,bool) or not isinstance(max_new_tokens,int) or not 1<=max_new_tokens<=4096: raise ValueError("max_new_tokens must be 1..4096")
        if isinstance(temperature,bool) or not isinstance(temperature,(int,float)) or not 0<temperature<=5: raise ValueError("temperature must be > 0 and <= 5")
        if top_k is not None and (isinstance(top_k,bool) or not isinstance(top_k,int) or top_k<1): raise ValueError("top_k must be None or positive")
        ids=self.tokenizer.encode(prompt,add_bos=True)[-self.config.block_size:]
        idx=torch.tensor([ids],dtype=torch.long,device=self.device)
        out=self.model.generate(idx,max_new_tokens=max_new_tokens,temperature=float(temperature),top_k=top_k,eos_id=2)
        return self.tokenizer.decode(out[0,len(ids):].detach().cpu().tolist(),skip_special=True)
