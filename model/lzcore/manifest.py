"""Evidence gates for declaring an LZ-Core checkpoint trained and verified."""
from __future__ import annotations
import math, re
from pathlib import Path
from typing import Any
from .provenance import validate_records, validate_sha256, verify_file_hash
MANIFEST_FORMAT="lzcore-governance-2"
MIN_DATASET_BYTES=1024*1024
MIN_VALIDATION_TOKENS=10_000
MIN_VAL_IMPROVEMENT=0.10
MAX_FINAL_TO_BEST=1.05
STATUSES={"spec-only","scratch-initialized","scratch-trained-unverified","scratch-trained-verified","third-party","invalid"}
MODEL_INIT="random (from scratch, no pretrained weights)"
def _number(v,f):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0: raise ValueError(f"{f} must be finite and > 0")
    return float(v)
def _count(v,f,minimum=1):
    if isinstance(v,bool) or not isinstance(v,int) or v<minimum: raise ValueError(f"{f} must be an integer >= {minimum}")
    return v
def _read_text(p):
    try: return Path(p).read_text(encoding="utf-8")
    except (OSError,UnicodeError) as e: raise ValueError(f"cannot read UTF-8 split file {p}: {e}") from e
def _norm(s): return " ".join(re.findall(r"\w+",s.casefold(),flags=re.UNICODE))
def check_text_leakage(train_text,validation_text,*,ngram_size=8,max_overlap_ratio=0.01):
    """Normalized word-shingle overlap heuristic; it is not proof of independence."""
    if not isinstance(train_text,str) or not isinstance(validation_text,str): raise ValueError("split texts must be strings")
    if isinstance(ngram_size,bool) or not isinstance(ngram_size,int) or ngram_size<3: raise ValueError("ngram_size must be >= 3")
    if not 0<=max_overlap_ratio<1: raise ValueError("max_overlap_ratio must be in [0,1)")
    a,b=_norm(train_text).split(),_norm(validation_text).split()
    if min(len(a),len(b))<ngram_size: raise ValueError("both splits are too small for leakage analysis")
    sa={tuple(a[i:i+ngram_size]) for i in range(len(a)-ngram_size+1)}
    vb=[tuple(b[i:i+ngram_size]) for i in range(len(b)-ngram_size+1)]
    overlap=sum(x in sa for x in vb); ratio=overlap/len(vb)
    return {"passed":ratio<=max_overlap_ratio,"ngram_size":ngram_size,"validation_ngrams":len(vb),"overlap_ngrams":overlap,"overlap_ratio":ratio,"max_overlap_ratio":max_overlap_ratio,"method":"normalized-word-shingle-overlap-v1"}
def assess_training_evidence(*,dataset_path,dataset_sha256,provenance_records,train_tokens,validation_tokens,initial_val_loss,best_val_loss,final_val_loss,steps_completed,independent_validation,train_text_path,validation_text_path,checkpoint_path,checkpoint_sha256,checkpoint_format,model_init):
    data,ck=Path(dataset_path),Path(checkpoint_path); records=validate_records(provenance_records)
    validate_sha256(dataset_sha256,"dataset_sha256"); validate_sha256(checkpoint_sha256,"checkpoint_sha256")
    if not data.is_file() or not ck.is_file(): raise ValueError("dataset and checkpoint must be regular files")
    verify_file_hash(data,dataset_sha256); verify_file_hash(ck,checkpoint_sha256)
    train_tokens=_count(train_tokens,"train_tokens"); validation_tokens=_count(validation_tokens,"validation_tokens"); steps_completed=_count(steps_completed,"steps_completed")
    if not isinstance(independent_validation,bool): raise ValueError("independent_validation must be boolean")
    if checkpoint_format!="lzcore-ckpt-1": raise ValueError("unsupported checkpoint format")
    if model_init!=MODEL_INIT: raise ValueError("scratch verification rejects pretrained or unknown initialization")
    leakage=check_text_leakage(_read_text(train_text_path),_read_text(validation_text_path))
    initial,best,final=(_number(initial_val_loss,"initial_val_loss"),_number(best_val_loss,"best_val_loss"),_number(final_val_loss,"final_val_loss"))
    reasons=[]
    if data.stat().st_size<MIN_DATASET_BYTES: reasons.append("dataset smaller than 1 MiB")
    if validation_tokens<MIN_VALIDATION_TOKENS: reasons.append("validation set below 10,000 tokens")
    if train_tokens<=validation_tokens: reasons.append("training tokens must exceed validation tokens")
    if not independent_validation: reasons.append("validation independence not attested")
    if not leakage["passed"]: reasons.append("measured text leakage exceeds threshold")
    if best>initial*(1-MIN_VAL_IMPROVEMENT): reasons.append("best validation loss improved by less than 10%")
    if final>best*MAX_FINAL_TO_BEST: reasons.append("final validation loss exceeds 105% of best")
    return {"format":MANIFEST_FORMAT,"status":"scratch-trained-verified" if not reasons else "scratch-trained-unverified","verified":not reasons,"reasons":reasons,"model_init":model_init,
      "dataset":{"path_name":data.name,"bytes":data.stat().st_size,"sha256":dataset_sha256,"train_tokens":train_tokens,"validation_tokens":validation_tokens,"provenance":records},
      "checkpoint":{"path_name":ck.name,"bytes":ck.stat().st_size,"sha256":checkpoint_sha256,"format":checkpoint_format},
      "evaluation":{"steps_completed":steps_completed,"initial_val_loss":initial,"best_val_loss":best,"final_val_loss":final,"independent_validation_attested":independent_validation,"leakage_analysis":leakage},
      "limitations":["Leakage analysis is heuristic, not proof of independence.","Owner attestations are not independent legal certification.","A byte-size threshold does not establish dataset quality."]}
def classify_artifact(*,provenance_kind,has_checkpoint,has_training_evidence):
    if provenance_kind=="third-party": return "third-party"
    if provenance_kind=="unknown": return "invalid" if has_checkpoint else "spec-only"
    if not has_checkpoint: return "spec-only"
    if not has_training_evidence: return "scratch-initialized"
    return "scratch-trained-unverified"
def verify_manifest(manifest,*,dataset_path,checkpoint_path):
    if not isinstance(manifest,dict) or manifest.get("format")!=MANIFEST_FORMAT: raise ValueError("invalid LZ-Core governance manifest")
    status=manifest.get("status")
    if status not in STATUSES: raise ValueError("unknown model status")
    data,ck=manifest.get("dataset"),manifest.get("checkpoint")
    if not isinstance(data,dict) or not isinstance(ck,dict): raise ValueError("dataset/checkpoint sections required")
    if data.get("path_name")!=Path(dataset_path).name or ck.get("path_name")!=Path(checkpoint_path).name: raise ValueError("manifest file names do not match supplied artifacts")
    verify_file_hash(dataset_path,data.get("sha256")); verify_file_hash(checkpoint_path,ck.get("sha256"))
    if data.get("bytes")!=Path(dataset_path).stat().st_size or ck.get("bytes")!=Path(checkpoint_path).stat().st_size: raise ValueError("manifest artifact size mismatch")
    records=validate_records(data.get("provenance"))
    if status=="scratch-trained-verified":
        ev=manifest.get("evaluation")
        if manifest.get("verified") is not True or manifest.get("reasons")!=[] or not isinstance(ev,dict): raise ValueError("verified status lacks passing evidence")
        if manifest.get("model_init")!=MODEL_INIT or ck.get("format")!="lzcore-ckpt-1": raise ValueError("unsupported initialization or checkpoint format")
        if ev.get("independent_validation_attested") is not True: raise ValueError("missing independent-validation attestation")
        leak=ev.get("leakage_analysis")
        if not isinstance(leak,dict) or leak.get("passed") is not True or leak.get("method")!="normalized-word-shingle-overlap-v1": raise ValueError("missing measured leakage analysis")
        if leak.get("overlap_ratio",1)>leak.get("max_overlap_ratio",0): raise ValueError("leakage threshold exceeded")
        if Path(dataset_path).stat().st_size<MIN_DATASET_BYTES: raise ValueError("insufficient dataset bytes")
        tr=_count(data.get("train_tokens"),"train_tokens"); va=_count(data.get("validation_tokens"),"validation_tokens")
        if va<MIN_VALIDATION_TOKENS or tr<=va: raise ValueError("invalid train/validation token counts")
        _count(ev.get("steps_completed"),"steps_completed")
        initial,best,final=(_number(ev.get("initial_val_loss"),"initial_val_loss"),_number(ev.get("best_val_loss"),"best_val_loss"),_number(ev.get("final_val_loss"),"final_val_loss"))
        if best>initial*(1-MIN_VAL_IMPROVEMENT) or final>best*MAX_FINAL_TO_BEST: raise ValueError("verified status violates loss thresholds")
    elif manifest.get("verified") is True: raise ValueError("non-verified status cannot set verified=true")
    return {"status":status,"provenance_records":len(records),"hashes_verified":True}
