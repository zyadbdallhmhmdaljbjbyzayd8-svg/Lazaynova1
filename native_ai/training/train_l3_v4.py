"""LAZAYNOVA L3 V4: isolated from-scratch trainer.

- Preserves V2/V3 artifacts.
- Uses the native UTF-8 byte tokenizer and native L3 architecture.
- Computes loss only on assistant response bytes and EOS.
- Uses deterministic language-stratified train/validation split.
- Never overwrites an existing checkpoint or temporary file.
- Dry-run performs validation and a forward pass only.
"""
import argparse
import copy
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.native_models.l3.model import LazaynovaL3
from modules.native_models.l3.tokenizer import ByteTokenizer


DATASET_PATH = ROOT / "native_ai/datasets/sample_ar_v3.jsonl"
BASE_CONFIG_PATH = ROOT / "config/models/l3.json"
OUTPUT_PATH = ROOT / "native_ai/checkpoints/l3_checkpoint_v4.pt"
TEMP_PATH = OUTPUT_PATH.with_name(OUTPUT_PATH.name + ".tmp")

EXPECTED_DATASET_SHA256 = (
    "bc63bb49f0e0c9d2037b57d5e8270f6f"
    "65f48df8c0ee14c691d45f850708aa48"
)

CHECKPOINT_FORMAT = "LAZAYNOVA_L3_CHECKPOINT_V4"
IGNORE_INDEX = ByteTokenizer.PAD


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_config():
    with BASE_CONFIG_PATH.open(encoding="utf-8") as handle:
        config = json.load(handle)

    config = dict(config)
    config.update({
        "model_name": "LAZAYNOVA L3",
        "version": "native-scratch-v4",
        "context_length": 320,
        "precision": "float32",
        "device": "cpu",
        "initialization": "random",
        "tokenizer": "native_utf8_byte",
        "external_weights": False,
        "external_ai_apis": False,
        "training_version": 4,
    })

    if config["vocab_size"] != ByteTokenizer.VOCAB_SIZE:
        raise ValueError("Model vocabulary does not match native tokenizer")
    if config["context_length"] < 2:
        raise ValueError("Invalid context length")
    if config["d_model"] % config["n_heads"]:
        raise ValueError("d_model must be divisible by n_heads")

    return config


def load_records(path=DATASET_PATH):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")

    actual_hash = sha256_file(path)
    if actual_hash != EXPECTED_DATASET_SHA256:
        raise ValueError(
            "Dataset SHA256 mismatch; refusing to train on changed data. "
            f"Expected={EXPECTED_DATASET_SHA256}, actual={actual_hash}"
        )

    records = []
    seen = set()

    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                raise ValueError(f"Blank dataset line: {line_number}")

            item = json.loads(line)
            if set(item) != {"instruction", "response", "language"}:
                raise ValueError(f"Unexpected schema at line {line_number}")

            prompt = item["instruction"]
            response = item["response"]
            language = item["language"]

            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError(f"Invalid instruction at line {line_number}")
            if not isinstance(response, str) or not response.strip():
                raise ValueError(f"Invalid response at line {line_number}")
            if language not in ("ar", "en"):
                raise ValueError(f"Unsupported language at line {line_number}")

            pair = (prompt.strip(), response.strip(), language)
            if pair in seen:
                raise ValueError(f"Duplicate record at line {line_number}")
            seen.add(pair)

            records.append({
                "instruction": prompt.strip(),
                "response": response.strip(),
                "language": language,
            })

    if not records:
        raise ValueError("Dataset is empty")

    counts = {
        language: sum(r["language"] == language for r in records)
        for language in ("ar", "en")
    }
    if not all(counts.values()):
        raise ValueError("Both Arabic and English records are required")

    return records


def split_records(records, seed=42, validation_ratio=0.20):
    if not 0 < validation_ratio < 1:
        raise ValueError("validation_ratio must be between 0 and 1")

    rng = random.Random(seed)
    train, validation = [], []

    for language in ("ar", "en"):
        group = [r for r in records if r["language"] == language]
        if len(group) < 2:
            raise ValueError(f"Not enough {language} records to split")

        rng.shuffle(group)
        validation_count = max(1, round(len(group) * validation_ratio))
        validation_count = min(validation_count, len(group) - 1)

        validation.extend(group[:validation_count])
        train.extend(group[validation_count:])

    rng.shuffle(train)
    rng.shuffle(validation)

    if set(map(id, train)) & set(map(id, validation)):
        raise RuntimeError("Train/validation leakage detected")

    return train, validation


def encode_pair(record, tokenizer=None):
    tokenizer = tokenizer or ByteTokenizer()

    prefix = (
        "User: " + record["instruction"].strip()
        + "\nAssistant:"
    )
    response = record["response"].strip()

    prefix_ids = tokenizer.encode(prefix)
    response_ids = tokenizer.encode(response)

    # token positions:
    # [BOS] [prefix bytes] [response bytes] [EOS]
    tokens = (
        [tokenizer.BOS]
        + prefix_ids
        + response_ids
        + [tokenizer.EOS]
    )

    # The target at index prefix_length - 1 is the first
    # response token. Earlier targets belong to the prompt.
    prefix_length = 1 + len(prefix_ids)

    input_ids = tokens[:-1]
    targets = [IGNORE_INDEX] * len(input_ids)

    for index in range(prefix_length - 1, len(targets)):
        targets[index] = tokens[index + 1]

    if not any(target != IGNORE_INDEX for target in targets):
        raise ValueError("Example has no assistant targets")

    return input_ids, targets


def validate_examples(records, context_length):
    tokenizer = ByteTokenizer()
    lengths = []

    for index, record in enumerate(records):
        inputs, targets = encode_pair(record, tokenizer)
        if len(inputs) != len(targets):
            raise RuntimeError("Input/target length mismatch")
        if len(inputs) > context_length:
            raise ValueError(
                f"Record {index} requires {len(inputs)} input tokens; "
                f"context limit is {context_length}. "
                "No truncation is permitted."
            )
        if any(
            target != IGNORE_INDEX
            and not 0 <= target < tokenizer.VOCAB_SIZE
            for target in targets
        ):
            raise ValueError(f"Invalid target token in record {index}")
        lengths.append(len(inputs))

    return {
        "count": len(lengths),
        "min_tokens": min(lengths),
        "max_tokens": max(lengths),
        "average_tokens": sum(lengths) / len(lengths),
    }


def make_batch(records, context_length, device, tokenizer=None):
    if not records:
        raise ValueError("Cannot create a batch from zero records")

    tokenizer = tokenizer or ByteTokenizer()
    examples = [encode_pair(record, tokenizer) for record in records]

    max_length = max(len(inputs) for inputs, _ in examples)
    if max_length > context_length:
        raise ValueError("Batch exceeds model context")

    batch_size = len(examples)
    x = torch.full(
        (batch_size, max_length),
        tokenizer.PAD,
        dtype=torch.long,
    )
    y = torch.full(
        (batch_size, max_length),
        IGNORE_INDEX,
        dtype=torch.long,
    )

    for row, (inputs, targets) in enumerate(examples):
        length = len(inputs)
        x[row, :length] = torch.tensor(inputs, dtype=torch.long)
        y[row, :length] = torch.tensor(targets, dtype=torch.long)

    return x.to(device), y.to(device)


def masked_loss(logits, targets):
    if logits.shape[:2] != targets.shape:
        raise ValueError("Logits and target dimensions do not match")

    valid = targets.ne(IGNORE_INDEX)
    if not valid.any():
        raise ValueError("Batch contains no assistant targets")

    return F.cross_entropy(
        logits.reshape(-1, logits.size(-1)),
        targets.reshape(-1),
        ignore_index=IGNORE_INDEX,
    )


@torch.no_grad()
def evaluate(model, records, context_length, device, batch_size=4):
    model.eval()
    weighted_loss = 0.0
    token_count = 0

    for start in range(0, len(records), batch_size):
        subset = records[start:start + batch_size]
        x, y = make_batch(subset, context_length, device)
        logits, _ = model(x)
        valid_count = int(y.ne(IGNORE_INDEX).sum().item())
        loss = masked_loss(logits, y)

        weighted_loss += float(loss.item()) * valid_count
        token_count += valid_count

    if token_count == 0:
        raise ValueError("Validation set has no target tokens")

    model.train()
    return weighted_loss / token_count


def validate_model_state(model, state):
    result = model.load_state_dict(state, strict=True)
    if result.missing_keys or result.unexpected_keys:
        raise ValueError("Checkpoint model state is incomplete")

    for name, tensor in model.state_dict().items():
        if not torch.isfinite(tensor).all().item():
            raise ValueError(f"Non-finite model tensor: {name}")


def save_checkpoint_safely(payload, config):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Never overwrite or remove an existing V4 artifact.
    if OUTPUT_PATH.exists():
        raise FileExistsError(f"Checkpoint already exists: {OUTPUT_PATH}")
    if TEMP_PATH.exists():
        raise FileExistsError(f"Temporary checkpoint already exists: {TEMP_PATH}")

    # Exclusive creation prevents accidental reuse of a temp file.
    fd = os.open(
        str(TEMP_PATH),
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )

    try:
        with os.fdopen(fd, "wb") as handle:
            torch.save(payload, handle)
            handle.flush()
            os.fsync(handle.fileno())

        loaded = torch.load(
            TEMP_PATH,
            map_location="cpu",
            weights_only=True,
        )

        if loaded.get("format") != CHECKPOINT_FORMAT:
            raise ValueError("Checkpoint format verification failed")
        if loaded.get("config") != config:
            raise ValueError("Checkpoint config verification failed")

        verifier = LazaynovaL3(config)
        validate_model_state(verifier, loaded["model_state_dict"])

        # Hard-link publication is exclusive: it cannot replace an existing file.
        os.link(TEMP_PATH, OUTPUT_PATH)
        TEMP_PATH.unlink()

    except Exception:
        # Preserve the temporary artifact for manual inspection.
        raise

    print("CHECKPOINT PUBLISHED:", OUTPUT_PATH)
    print("CHECKPOINT SHA256:", sha256_file(OUTPUT_PATH))


def set_seed(seed):
    random.seed(seed)
    torch.manual_seed(seed)


def train(args):
    if args.steps < 1 or args.batch_size < 1:
        raise ValueError("steps and batch size must be positive")
    if args.lr <= 0 or not math.isfinite(args.lr):
        raise ValueError("Learning rate must be finite and positive")
    if args.patience < 1:
        raise ValueError("patience must be positive")

    # Check output paths before any training work.
    if OUTPUT_PATH.exists():
        raise FileExistsError(f"V4 checkpoint already exists: {OUTPUT_PATH}")
    if TEMP_PATH.exists():
        raise FileExistsError(f"V4 temporary checkpoint exists: {TEMP_PATH}")

    set_seed(args.seed)
    torch.set_num_threads(args.threads)

    device = torch.device("cpu")
    config = build_config()
    records = load_records()
    train_records, validation_records = split_records(records, args.seed)

    all_stats = validate_examples(records, config["context_length"])
    train_stats = validate_examples(train_records, config["context_length"])
    val_stats = validate_examples(validation_records, config["context_length"])

    print("FORMAT:", CHECKPOINT_FORMAT)
    print("DATASET SHA256:", EXPECTED_DATASET_SHA256)
    print("RECORDS:", len(records))
    print("TRAIN RECORDS:", len(train_records))
    print("VALIDATION RECORDS:", len(validation_records))
    print("ALL DATA LENGTHS:", all_stats)
    print("TRAIN LENGTHS:", train_stats)
    print("VALIDATION LENGTHS:", val_stats)
    print("CONFIG:", json.dumps(config, ensure_ascii=False))
    print("DEVICE: CPU")
    print("OUTPUT:", OUTPUT_PATH)

    model = LazaynovaL3(config).to(device)
    print("PARAMETERS:", model.parameter_count())

    # Dry-run is deliberately read-only: no optimizer, training, or checkpoint.
    x, y = make_batch(
        train_records[:min(args.batch_size, len(train_records))],
        config["context_length"],
        device,
    )
    with torch.no_grad():
        logits, _ = model(x)
        smoke_loss = masked_loss(logits, y)

    if not torch.isfinite(smoke_loss).item():
        raise ValueError("Dry forward pass produced non-finite loss")

    print("FORWARD SHAPE:", tuple(logits.shape))
    print("ASSISTANT TARGET TOKENS:", int(y.ne(IGNORE_INDEX).sum().item()))
    print("FORWARD LOSS:", float(smoke_loss.item()))

    if args.dry_run:
        print("DRY RUN PASSED — no optimizer, training, or checkpoint created.")
        return

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.lr,
        weight_decay=0.01,
    )

    warmup_steps = max(1, min(args.steps // 10, 30))

    def schedule(step):
        if step < warmup_steps:
            return float(step + 1) / warmup_steps
        progress = (step - warmup_steps) / max(1, args.steps - warmup_steps)
        return 0.5 * (1.0 + math.cos(math.pi * min(1.0, progress)))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, schedule)

    best_val = float("inf")
    best_state = None
    best_step = 0
    bad_checks = 0
    history = []
    validation_history = []
    check_interval = max(1, args.steps // 20)
    started = time.time()

    for step in range(args.steps):
        model.train()
        batch = random.sample(
            train_records,
            min(args.batch_size, len(train_records)),
        )
        x, y = make_batch(batch, config["context_length"], device)

        optimizer.zero_grad(set_to_none=True)
        logits, _ = model(x)
        loss = masked_loss(logits, y)

        if not torch.isfinite(loss).item():
            raise ValueError(f"Non-finite training loss at step {step + 1}")

        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=1.0,
        )

        if not torch.isfinite(torch.as_tensor(grad_norm)).item():
            raise ValueError(f"Non-finite gradient at step {step + 1}")

        optimizer.step()
        scheduler.step()

        train_loss = float(loss.detach().item())
        history.append(train_loss)

        should_validate = (
            (step + 1) % check_interval == 0
            or step + 1 == args.steps
        )

        if should_validate:
            val_loss = evaluate(
                model,
                validation_records,
                config["context_length"],
                device,
            )
            validation_history.append({
                "step": step + 1,
                "loss": val_loss,
            })

            print(
                f"STEP {step + 1}/{args.steps} "
                f"train_loss={train_loss:.6f} "
                f"validation_loss={val_loss:.6f} "
                f"lr={scheduler.get_last_lr()[0]:.8f}"
            )

            if val_loss < best_val - args.min_delta:
                best_val = val_loss
                best_step = step + 1
                best_state = {
                    key: value.detach().cpu().clone()
                    for key, value in model.state_dict().items()
                }
                bad_checks = 0
            else:
                bad_checks += 1

            if bad_checks >= args.patience:
                print("EARLY STOPPING at step:", step + 1)
                break

    if best_state is None:
        raise RuntimeError("No valid best checkpoint state was selected")

    elapsed = time.time() - started
    model.load_state_dict(best_state, strict=True)

    training_metadata = {
        "steps_requested": args.steps,
        "steps_completed": len(history),
        "best_step": best_step,
        "batch_size": args.batch_size,
        "learning_rate": args.lr,
        "weight_decay": 0.01,
        "warmup_steps": warmup_steps,
        "scheduler": "linear_warmup_cosine_decay",
        "gradient_clip_norm": 1.0,
        "seed": args.seed,
        "train_records": len(train_records),
        "validation_records": len(validation_records),
        "dataset_records": len(records),
        "dataset_sha256": EXPECTED_DATASET_SHA256,
        "train_loss_history": history,
        "validation_loss_history": validation_history,
        "best_validation_loss": best_val,
        "elapsed_seconds": elapsed,
        "device": "cpu",
        "from_scratch": True,
        "external_weights": False,
        "external_ai_apis": False,
        "loss_scope": "assistant_response_and_eos_only",
        "early_stopping_patience": args.patience,
    }

    payload = {
        "format": CHECKPOINT_FORMAT,
        "model_name": "LAZAYNOVA L3",
        "config": config,
        "tokenizer": ByteTokenizer().get_config(),
        "training": training_metadata,
        "model_state_dict": best_state,
    }

    save_checkpoint_safely(payload, config)

    print("TRAINING COMPLETE")
    print("BEST STEP:", best_step)
    print("BEST VALIDATION LOSS:", best_val)
    print("LAST TRAIN LOSS:", history[-1])
    print("ELAPSED SECONDS:", round(elapsed, 2))


def main():
    parser = argparse.ArgumentParser(
        description="Train native LAZAYNOVA L3 V4 from scratch"
    )
    parser.add_argument("--steps", type=int, default=600)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--lr", type=float, default=0.0003)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--min-delta", type=float, default=0.0001)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
