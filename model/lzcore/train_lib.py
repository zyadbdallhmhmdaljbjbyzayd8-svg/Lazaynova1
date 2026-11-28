"""Training loop, checkpointing, resume and model loading for LZ-Core."""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from pathlib import Path

import torch

from .config import LZConfig, check_hardware_policy
from .model import LZCore
from .tokenizer import LZTokenizer

CKPT_FORMAT = "lzcore-ckpt-1"
MODEL_VERSION = "0.1.0"


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def lr_at(step: int, cfg: LZConfig) -> float:
    if step < cfg.warmup_steps:
        return cfg.learning_rate * (step + 1) / max(1, cfg.warmup_steps)
    span = max(1, cfg.max_steps - cfg.warmup_steps)
    progress = min(1.0, (step - cfg.warmup_steps) / span)
    floor = cfg.learning_rate * cfg.min_lr_ratio
    return floor + 0.5 * (1.0 + math.cos(math.pi * progress)) * (cfg.learning_rate - floor)


def make_splits(text: str, tok: LZTokenizer, cfg: LZConfig, val_fraction: float = 0.1):
    ids = torch.tensor(tok.encode(text), dtype=torch.long)
    split = int(len(ids) * (1 - val_fraction))
    if split <= cfg.block_size + 1 or len(ids) - split <= cfg.block_size + 1:
        raise ValueError(
            f"Not enough data: {len(ids)} tokens for block_size={cfg.block_size}. "
            "Add more permitted training text or lower block_size.")
    return ids[:split], ids[split:]


def get_batch(data, cfg: LZConfig, gen: torch.Generator, device):
    hi = len(data) - cfg.block_size - 1
    ix = torch.randint(0, hi, (cfg.batch_size,), generator=gen)
    x = torch.stack([data[i:i + cfg.block_size] for i in ix])
    y = torch.stack([data[i + 1:i + cfg.block_size + 1] for i in ix])
    return x.to(device), y.to(device)


@torch.no_grad()
def estimate_loss(model, data, cfg: LZConfig, device) -> float:
    was_training = model.training
    model.eval()
    gen = torch.Generator().manual_seed(cfg.seed + 12345)  # fixed => comparable across calls
    total = 0.0
    for _ in range(cfg.eval_batches):
        xb, yb = get_batch(data, cfg, gen, device)
        _, loss = model(xb, yb)
        total += loss.item()
    model.train(was_training)
    return total / cfg.eval_batches


def _make_optimizer(model, cfg: LZConfig):
    decay = [p for p in model.parameters() if p.requires_grad and p.dim() >= 2]
    no_decay = [p for p in model.parameters() if p.requires_grad and p.dim() < 2]
    return torch.optim.AdamW(
        [{"params": decay, "weight_decay": cfg.weight_decay},
         {"params": no_decay, "weight_decay": 0.0}],
        lr=cfg.learning_rate, betas=(0.9, 0.95))


def save_checkpoint(path: Path, model, optimizer, step, cfg, tok, history, best_val,
                    initial_val, dataset_sha) -> None:
    """Atomically save a checkpoint without following or overwriting temp symlinks."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f"Unsafe checkpoint target symlink: {path}")
    if path.exists() and not path.is_file():
        raise ValueError(f"Unsafe checkpoint target: {path}")

    payload = {
        "format": CKPT_FORMAT,
        "model_version": MODEL_VERSION,
        "model_state": {k: v.detach().cpu() for k, v in model.state_dict().items()},
        "optimizer_state": optimizer.state_dict() if optimizer is not None else None,
        "step": step,
        "config": cfg.to_dict(),
        "tokenizer": tok.to_dict(),
        "tokenizer_hash": tok.hash(),
        "history": history,
        "best_val_loss": best_val,
        "initial_val_loss": initial_val,
        "dataset_sha256": dataset_sha,
    }

    tmp = path.with_suffix(path.suffix + ".tmp")
    if tmp.exists() or tmp.is_symlink():
        raise FileExistsError(f"Refusing to overwrite temporary checkpoint: {tmp}")

    created = False
    try:
        with tmp.open("xb") as f:
            created = True
            torch.save(payload, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        # Remove only the temporary file created by this invocation.
        if created and tmp.exists():
            tmp.unlink()


def load_checkpoint(path: str | Path, device="cpu") -> dict:
    """Load only a regular checkpoint file and validate its top-level format."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Unsafe or missing checkpoint file: {path}")

    ck = torch.load(path, map_location=device, weights_only=True)
    if not isinstance(ck, dict):
        raise ValueError("Invalid checkpoint: expected a dictionary")
    if ck.get("format") != CKPT_FORMAT:
        raise ValueError(f"unsupported checkpoint format: {ck.get('format')!r}")
    return ck



def load_model(path: str | Path, device="cpu"):
    """Load (model, tokenizer, config) from a checkpoint file or an output directory."""
    p = Path(path)
    if p.is_dir():
        p = p / "last.pt"
    ck = load_checkpoint(p, device)
    cfg = LZConfig.from_dict(ck["config"])
    tok = LZTokenizer.from_dict(ck["tokenizer"])
    if tok.hash() != ck["tokenizer_hash"]:
        raise ValueError("tokenizer hash mismatch: checkpoint is corrupted or tampered")
    model = LZCore(cfg)
    model.load_state_dict(ck["model_state"])
    model.to(device).eval()
    return model, tok, cfg



def train(cfg: LZConfig, text: str, tok: LZTokenizer, out_dir, resume: bool = False,
          max_steps: int | None = None, device: str | None = None, data_path=None,
          log=print) -> dict:
    """Train in a fresh output directory, or safely resume a compatible run."""
    check_hardware_policy(cfg)

    if max_steps is not None:
        cfg.max_steps = max_steps
    cfg.vocab_size = tok.vocab_size
    cfg.validate()

    out = Path(out_dir)

    if out.is_symlink():
        raise ValueError(f"Unsafe output directory symlink: {out}")

    if resume:
        if not out.is_dir():
            raise FileNotFoundError(f"Cannot resume: output directory is missing: {out}")

        for name in ("last.pt", "tokenizer.json"):
            candidate = out / name
            if candidate.is_symlink() or not candidate.is_file():
                raise FileNotFoundError(
                    f"Cannot resume: required regular file is missing or unsafe: {candidate}"
                )

        for name in ("best.pt", "train_log.jsonl", "meta.json"):
            candidate = out / name
            if candidate.is_symlink() or (candidate.exists() and not candidate.is_file()):
                raise ValueError(f"Unsafe training output file: {candidate}")

    else:
        if out.exists():
            if not out.is_dir():
                raise FileExistsError(f"Output path is not a directory: {out}")
            if any(out.iterdir()):
                raise FileExistsError(
                    f"Refusing new training in non-empty output directory: {out}"
                )
        else:
            out.mkdir(parents=True, exist_ok=False)

    last_path = out / "last.pt"
    best_path = out / "best.pt"
    log_path = out / "train_log.jsonl"
    meta_path = out / "meta.json"

    dataset_sha = (
        sha256_file(data_path)
        if data_path is not None
        else hashlib.sha256(text.encode("utf-8")).hexdigest()
    )

    start_step = 0
    history = []
    best_val = float("inf")
    initial_val = None

    if resume:
        ck = load_checkpoint(last_path, device or "cpu")

        required = (
            "model_state", "optimizer_state", "step", "config",
            "tokenizer", "tokenizer_hash", "history",
            "best_val_loss", "initial_val_loss", "dataset_sha256",
        )
        missing = [key for key in required if key not in ck]
        if missing:
            raise ValueError(f"Checkpoint is incomplete; missing: {missing}")

        if ck["optimizer_state"] is None:
            raise ValueError("Cannot resume: checkpoint has no optimizer state")

        if ck["dataset_sha256"] != dataset_sha:
            raise ValueError("Cannot resume: dataset fingerprint differs")

        checkpoint_tok = LZTokenizer.from_dict(ck["tokenizer"])
        if checkpoint_tok.hash() != ck["tokenizer_hash"]:
            raise ValueError("Checkpoint tokenizer hash mismatch")

        disk_tok = LZTokenizer.load(out / "tokenizer.json")
        if disk_tok.hash() != tok.hash():
            raise ValueError("Cannot resume: tokenizer file differs from supplied tokenizer")
        if checkpoint_tok.hash() != tok.hash():
            raise ValueError("Cannot resume: tokenizer differs from checkpoint")

        saved_cfg = LZConfig.from_dict(ck["config"])
        saved_values = saved_cfg.to_dict()
        requested_values = cfg.to_dict()

        # Extending max_steps is supported; changing other settings is not.
        saved_values.pop("max_steps", None)
        requested_values.pop("max_steps", None)
        if saved_values != requested_values:
            raise ValueError("Cannot resume: configuration differs from checkpoint")

        start_step = ck["step"]
        if isinstance(start_step, bool) or not isinstance(start_step, int) or start_step < 0:
            raise ValueError("Checkpoint has an invalid training step")
        if cfg.max_steps < start_step:
            raise ValueError("Cannot resume: max_steps is below the completed checkpoint step")

        if not isinstance(ck["history"], list):
            raise ValueError("Checkpoint history is invalid")

        history = ck["history"]
        best_val = ck["best_val_loss"]
        initial_val = ck["initial_val_loss"]

    train_data, val_data = make_splits(text, tok, cfg)
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")

    model = LZCore(cfg).to(device)
    optimizer = _make_optimizer(model, cfg)

    if resume:
        model.load_state_dict(ck["model_state"])
        optimizer.load_state_dict(ck["optimizer_state"])
        log(f"Resumed from step {start_step}")
    else:
        tok.save(out / "tokenizer.json")

    # Refuse unsafe log/meta paths before opening or writing them.
    for target in (log_path, meta_path, best_path, last_path):
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ValueError(f"Unsafe training output file: {target}")

    torch.manual_seed(cfg.seed + start_step)
    gen = torch.Generator()

    if initial_val is None:
        initial_val = estimate_loss(model, val_data, cfg, device)
        log(
            f"initial val loss {initial_val:.4f} "
            f"(random init; ln(vocab)={math.log(cfg.vocab_size):.4f})"
        )

    def log_event(ev: dict) -> None:
        history.append(ev)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev) + "\n")

    t0 = time.time()
    model.train()
    train_loss = float("nan")

    for step in range(start_step, cfg.max_steps):
        for group in optimizer.param_groups:
            group["lr"] = lr_at(step, cfg)

        gen.manual_seed(cfg.seed * 1_000_003 + step)
        xb, yb = get_batch(train_data, cfg, gen, device)
        _, loss = model(xb, yb)

        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
        optimizer.step()
        train_loss = loss.item()

        done = step + 1
        if done % cfg.eval_interval == 0 or done == cfg.max_steps:
            val = estimate_loss(model, val_data, cfg, device)
            log_event({
                "step": done,
                "train_loss": train_loss,
                "val_loss": val,
                "lr": optimizer.param_groups[0]["lr"],
                "time": round(time.time() - t0, 2),
            })
            log(f"step {done:6d} | train {train_loss:.4f} | val {val:.4f}")

            if val < best_val:
                best_val = val
                save_checkpoint(
                    best_path, model, None, done, cfg, tok, history,
                    best_val, initial_val, dataset_sha
                )

            save_checkpoint(
                last_path, model, optimizer, done, cfg, tok, history,
                best_val, initial_val, dataset_sha
            )

    final_val = history[-1]["val_loss"] if history else initial_val
    summary = {
        "name": f"lz-core-{cfg.name}",
        "version": MODEL_VERSION,
        "preset": cfg.name,
        "init": "random (from scratch, no pretrained weights)",
        "params": model.num_params(),
        "steps_completed": max(start_step, cfg.max_steps),
        "initial_val_loss": initial_val,
        "final_val_loss": final_val,
        "best_val_loss": best_val,
        "dataset_sha256": dataset_sha,
        "tokenizer_sha256": tok.hash(),
        "vocab_size": cfg.vocab_size,
        "seed": cfg.seed,
        "device": device,
        "license": "UNSPECIFIED - set by project owner; training data license must be verified",
    }

    meta_tmp = meta_path.with_name(meta_path.name + ".tmp")
    if meta_tmp.exists() or meta_tmp.is_symlink():
        raise FileExistsError(f"Refusing to overwrite temporary metadata path: {meta_tmp}")
    meta_created = False
    try:
        with meta_tmp.open("x", encoding="utf-8") as f:
            meta_created = True
            f.write(json.dumps(summary, indent=2, ensure_ascii=False))
            f.flush()
            os.fsync(f.fileno())
        os.replace(meta_tmp, meta_path)
    finally:
        if meta_created and meta_tmp.exists():
            meta_tmp.unlink()

    return summary
