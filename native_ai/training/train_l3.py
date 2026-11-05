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
