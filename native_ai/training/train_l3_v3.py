#!/usr/bin/env python3
"""LAZAYNOVA L3 V3: native scratch CPU trainer."""

import argparse
import hashlib
import json
import math
import os
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from modules.native_models.l3.model import LazaynovaL3
from modules.native_models.l3.tokenizer import ByteTokenizer

DATA_PATH = ROOT / "native_ai/datasets/sample_ar_v3.jsonl"
CONFIG_PATH = ROOT / "config/models/l3.json"
OUTPUT_PATH = ROOT / "native_ai/checkpoints/l3_checkpoint_v3.pt"

EXPECTED_DATA_SHA256 = (
    "bc63bb49f0e0c9d2037b57d5e8270f6f"
    "65f48df8c0ee14c691d45f850708aa48"
)

def read_dataset(path, tokenizer):
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()

    if digest != EXPECTED_DATA_SHA256:
        raise ValueError(
            "Dataset SHA256 mismatch. Refusing to train on changed data."
        )

    records = []
    seen = set()
    languages = {"ar": 0, "en": 0}

    for line_number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue

        try:
            item = json.loads(line.decode("utf-8"))
        except Exception as exc:
            raise ValueError(
                f"Invalid JSON/UTF-8 at line {line_number}: {exc}"
            )

        if not isinstance(item, dict):
            raise ValueError(f"Line {line_number} is not an object")

        prompt = item.get("instruction")
        response = item.get("response")
        language = item.get("language")

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"Invalid instruction at line {line_number}")

        if not isinstance(response, str) or not response.strip():
            raise ValueError(f"Invalid response at line {line_number}")

        if language not in languages:
            raise ValueError(f"Unsupported language at line {line_number}")

        pair = (prompt.strip(), response.strip())
        if pair in seen:
            raise ValueError(f"Duplicate prompt-response pair at line {line_number}")

        seen.add(pair)
        languages[language] += 1

        text = f"User: {prompt.strip()}\nAssistant: {response.strip()}"
        ids = tokenizer.encode(text, add_bos=True, add_eos=True)

        if len(ids) < 2:
            raise ValueError(f"Too-short token sequence at line {line_number}")

        records.append(ids)

    if len(records) < 150:
        raise ValueError(f"Expected at least 150 records; got {len(records)}")

    if len(seen) != len(records):
        raise ValueError("Dataset uniqueness validation failed")

    if languages["ar"] == 0 or languages["en"] == 0:
        raise ValueError("Both Arabic and English records are required")

    return records, digest, languages


def is_utf8_boundary(token_id):
    if token_id < ByteTokenizer.BYTE_OFFSET:
        return token_id in (ByteTokenizer.BOS,)

    byte_value = token_id - ByteTokenizer.BYTE_OFFSET
    return not (0x80 <= byte_value <= 0xBF)


def make_windows(records, context_length):
    """Build overlapping windows whose starts respect UTF-8 boundaries."""
    windows = []
    stride = max(16, context_length // 2)

    for ids in records:
        boundaries = [
            index
            for index, token in enumerate(ids[:-1])
            if is_utf8_boundary(token)
        ]

        if not boundaries:
            raise ValueError("No valid UTF-8 window boundary found")

        starts = [0]
        while True:
            desired = starts[-1] + stride
            candidates = [x for x in boundaries if x >= desired]

            if not candidates:
                break

            next_start = candidates[0]
            if next_start <= starts[-1]:
                break

            starts.append(next_start)

        for start in starts:
            chunk = ids[start:start + context_length + 1]
            if len(chunk) >= 2:
                windows.append(chunk)

    if not windows:
        raise ValueError("No training windows were generated")

    return windows


def learning_rate_at(step, total_steps, base_lr, warmup_steps):
    if warmup_steps > 0 and step < warmup_steps:
        return base_lr * float(step + 1) / float(warmup_steps)

    decay_steps = max(1, total_steps - warmup_steps)
    progress = min(
        1.0,
        max(0.0, (step - warmup_steps) / decay_steps)
    )
    cosine = 0.5 * (1.0 + math.cos(math.pi * progress))

    return base_lr * (0.1 + 0.9 * cosine)


def get_logits(model, inputs):
    result = model(inputs)

    if isinstance(result, dict):
        logits = result.get("logits")
    elif isinstance(result, (tuple, list)):
        logits = result[0]
    else:
        logits = result

    if not isinstance(logits, torch.Tensor):
        raise TypeError("Model did not return a logits tensor")

    return logits


def make_batch(windows, context_length, device):
    selected = random.choice(windows)

    inputs = selected[:-1]
    targets = selected[1:]

    if len(inputs) > context_length:
        raise ValueError("Window exceeds configured context length")

    pad = context_length - len(inputs)
    inputs = inputs + [ByteTokenizer.PAD] * pad
    targets = targets + [ByteTokenizer.PAD] * pad

    x = torch.tensor([inputs], dtype=torch.long, device=device)
    y = torch.tensor([targets], dtype=torch.long, device=device)

    return x, y


def validate_checkpoint(path, expected_config):
    payload = torch.load(
        path,
        map_location="cpu",
        weights_only=True
    )

    if payload.get("format") != "LAZAYNOVA_L3_CHECKPOINT_V3":
        raise ValueError("Checkpoint format verification failed")

    if payload.get("tokenizer", {}).get("vocab_size") != 260:
        raise ValueError("Checkpoint tokenizer verification failed")

    verifier = LazaynovaL3(expected_config).cpu()
    verifier.load_state_dict(payload["model_state_dict"], strict=True)
    verifier.eval()

    for parameter in verifier.parameters():
        if not torch.isfinite(parameter).all().item():
            raise ValueError("Non-finite parameter in saved checkpoint")

    return payload


def save_checkpoint_safely(payload, config):
    temp_path = OUTPUT_PATH.with_name(OUTPUT_PATH.name + ".tmp")

    if OUTPUT_PATH.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing checkpoint: {OUTPUT_PATH}"
        )

    if temp_path.exists():
        raise FileExistsError(
            f"Temporary checkpoint already exists: {temp_path}"
        )

    torch.save(payload, temp_path)

    # Verify the complete temporary checkpoint before publication.
    validate_checkpoint(temp_path, config)

    # Hard-link publication is exclusive: it fails if the target exists.
    # It never replaces an existing checkpoint.
    try:
        os.link(temp_path, OUTPUT_PATH)
    except Exception:
        print(
            "SAFE PUBLISH FAILED. Temporary file preserved at:",
            temp_path
        )
        raise

    temp_path.unlink()
    print("CHECKPOINT PUBLISHED:", OUTPUT_PATH)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=600)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--lr", type=float, default=0.0003)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not 1 <= args.steps <= 1000:
        raise ValueError("--steps must be between 1 and 1000")

    if args.batch_size != 1:
        raise ValueError("This phone-safe trainer currently requires batch-size=1")

    if not math.isfinite(args.lr) or args.lr <= 0:
        raise ValueError("Learning rate must be finite and positive")

    if OUTPUT_PATH.exists():
        raise FileExistsError(
            f"Checkpoint exists; refusing to overwrite: {OUTPUT_PATH}"
        )

    if OUTPUT_PATH.with_name(OUTPUT_PATH.name + ".tmp").exists():
        raise FileExistsError("Temporary checkpoint exists; inspect it manually")

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(1)

    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass

    device = torch.device("cpu")
    tokenizer = ByteTokenizer()

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    if config.get("vocab_size") != tokenizer.VOCAB_SIZE:
        raise ValueError("Model/tokenizer vocabulary mismatch")

    if config.get("context_length") != 128:
        raise ValueError("Expected the phone-safe context length of 128")

    if config.get("external_weights") is not False:
        raise ValueError("External weights must remain disabled")

    if config.get("external_ai_apis") is not False:
        raise ValueError("External AI APIs must remain disabled")

    records, dataset_hash, languages = read_dataset(DATA_PATH, tokenizer)
    windows = make_windows(records, int(config["context_length"]))

    print("===== LAZAYNOVA L3 V3 TRAINER =====")
    print("Device:", device)
    print("Dataset records:", len(records))
    print("Unique records:", len(records))
    print("Arabic:", languages["ar"])
    print("English:", languages["en"])
    print("Training windows:", len(windows))
    print("Context length:", config["context_length"])
    print("Dataset SHA256:", dataset_hash)
    print("Output:", OUTPUT_PATH)
    print("Steps:", args.steps)
    print("Batch size:", args.batch_size)

    model = LazaynovaL3(config).to(device)
    print("Parameters:", sum(p.numel() for p in model.parameters()))

    # Forward/loss smoke test. No optimizer step and no checkpoint write.
    x, y = make_batch(windows, config["context_length"], device)
    logits = get_logits(model, x)

    if logits.shape[:2] != y.shape:
        raise ValueError(
            f"Unexpected logits shape {tuple(logits.shape)} "
            f"for targets {tuple(y.shape)}"
        )

    test_loss = F.cross_entropy(
        logits.reshape(-1, logits.size(-1)),
        y.reshape(-1),
        ignore_index=ByteTokenizer.PAD
    )

    if not torch.isfinite(test_loss).item():
        raise ValueError("Dry forward pass produced non-finite loss")

    print("Forward test loss:", float(test_loss.item()))

    if args.dry_run:
        print("DRY RUN PASSED — no training and no checkpoint created.")
        return

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.lr,
        weight_decay=0.01
    )

    warmup_steps = max(1, int(args.steps * 0.05))
    history = []
    started = time.time()

    model.train()

    for step in range(args.steps):
        lr = learning_rate_at(
            step, args.steps, args.lr, warmup_steps
        )

        for group in optimizer.param_groups:
            group["lr"] = lr

        x, y = make_batch(windows, config["context_length"], device)
        optimizer.zero_grad(set_to_none=True)

        logits = get_logits(model, x)

        loss = F.cross_entropy(
            logits.reshape(-1, logits.size(-1)),
            y.reshape(-1),
            ignore_index=ByteTokenizer.PAD
        )

        if not torch.isfinite(loss).item():
            raise FloatingPointError(
                f"Non-finite loss at step {step + 1}"
            )

        loss.backward()

        for name, parameter in model.named_parameters():
            if parameter.grad is not None:
                if not torch.isfinite(parameter.grad).all().item():
                    raise FloatingPointError(
                        f"Non-finite gradient: {name}, step {step + 1}"
                    )

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=1.0,
            error_if_nonfinite=True
        )

        optimizer.step()

        value = float(loss.detach().item())
        history.append(value)

        if (step + 1) % 25 == 0 or step == 0:
            elapsed = time.time() - started
            print(
                f"step={step + 1}/{args.steps} "
                f"loss={value:.6f} "
                f"lr={lr:.8f} "
                f"elapsed={elapsed:.1f}s",
                flush=True
            )

    model.eval()

    for parameter in model.parameters():
        if not torch.isfinite(parameter).all().item():
            raise FloatingPointError(
                "Model contains non-finite parameters after training"
            )

    payload = {
        "format": "LAZAYNOVA_L3_CHECKPOINT_V3",
        "model_name": "LAZAYNOVA L3",
        "config": config,
        "model_state_dict": model.state_dict(),
        "tokenizer": {
            "name": "native_utf8_byte",
            "vocab_size": tokenizer.VOCAB_SIZE,
            "pad": tokenizer.PAD,
            "unk": tokenizer.UNK,
            "bos": tokenizer.BOS,
            "eos": tokenizer.EOS,
            "byte_offset": tokenizer.BYTE_OFFSET
        },
        "training": {
            "steps": args.steps,
            "batch_size": args.batch_size,
            "learning_rate": args.lr,
            "warmup_steps": warmup_steps,
            "scheduler": "linear_warmup_cosine_decay",
            "gradient_clip_norm": 1.0,
            "seed": args.seed,
            "dataset_records": len(records),
            "training_windows": len(windows),
            "dataset_sha256": dataset_hash,
            "first_loss": history[0],
            "last_loss": history[-1],
            "loss_history": history,
            "elapsed_seconds": time.time() - started,
            "device": "cpu",
            "from_scratch": True,
            "external_weights": False,
            "external_ai_apis": False
        }
    }

    save_checkpoint_safely(payload, config)

    print("===== TRAINING COMPLETE =====")
    print("First loss:", history[0])
    print("Last loss:", history[-1])
    print("Steps:", args.steps)
    print("Checkpoint:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
