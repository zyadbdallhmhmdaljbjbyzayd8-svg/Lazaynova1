"""CLI: python -m model.lzcore.train_cli --preset tiny --data model/data/train.txt

Run from the repository root. Writes to model/artifacts/lzcore-<preset>/ (git-ignored).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import from_legacy_json, from_preset
from .tokenizer import LZTokenizer


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Train LZ-Core from random initialization")
    ap.add_argument("--preset", default="tiny", choices=["tiny", "small", "medium", "large"])
    ap.add_argument("--data", default="model/data/train.txt")
    ap.add_argument("--out", default=None)
    ap.add_argument("--vocab-size", type=int, default=512)
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--legacy-config", default=None, help="reuse an old model/config.json")
    ap.add_argument("--block-size", type=int, default=None, help="override context length (needed for very small datasets)")
    ap.add_argument("--batch-size", type=int, default=None)
    ap.add_argument("--eval-interval", type=int, default=None)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--sample", default="", help="prompt for a sample generation after training")
    args = ap.parse_args(argv)

    from .train_lib import train  # imported late so --help works without torch
    import torch

    out = Path(args.out or f"model/artifacts/lzcore-{args.preset}")
    # Validate output state before reading data or creating a tokenizer.
    if args.resume:
        if out.is_symlink() or not out.is_dir():
            raise SystemExit(f"Cannot resume: output directory is missing or unsafe: {out}")
        for required in ("last.pt", "tokenizer.json"):
            candidate = out / required
            if candidate.is_symlink() or not candidate.is_file():
                raise SystemExit(f"Cannot resume: required regular file is missing or unsafe: {candidate}")
    elif out.exists():
        if out.is_symlink() or not out.is_dir():
            raise SystemExit(f"Unsafe output path: {out}")
        if any(out.iterdir()):
            raise SystemExit(f"Refusing to start a new run in non-empty directory: {out}")

    text = Path(args.data).read_text(encoding="utf-8")
    cfg = from_legacy_json(args.legacy_config, name=args.preset) if args.legacy_config \
        else from_preset(args.preset)

    for key in ("block_size", "batch_size", "eval_interval"):
        val = getattr(args, key)
        if val is not None:
            setattr(cfg, key, val)
    cfg.validate()

    tok_path = out / "tokenizer.json"
    if args.resume and tok_path.exists():
        tok = LZTokenizer.load(tok_path)
    else:
        tok = LZTokenizer.train(text, vocab_size=args.vocab_size)
    print(f"tokenizer vocab size: {tok.vocab_size}")

    summary = train(cfg, text, tok, out, resume=args.resume, max_steps=args.max_steps,
                    data_path=args.data)
    print("\nSUMMARY:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    from .train_lib import load_model
    model, tok2, _ = load_model(out)
    prompt = args.sample or text[:20]
    ids = torch.tensor([tok2.encode(prompt)], dtype=torch.long)
    print("\nSample generation:\n" + tok2.decode(model.generate(ids, 120)[0].tolist()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
