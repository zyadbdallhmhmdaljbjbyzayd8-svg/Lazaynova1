"""LZ-Core configuration: model + training settings and size presets."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class LZConfig:
    name: str = "tiny"
    # model
    vocab_size: int = 512
    block_size: int = 128
    n_layer: int = 4
    n_head: int = 4
    n_embd: int = 128
    dropout: float = 0.1
    bias: bool = False
    # training
    batch_size: int = 16
    max_steps: int = 2000
    eval_interval: int = 200
    eval_batches: int = 10
    learning_rate: float = 1e-3
    min_lr_ratio: float = 0.1
    warmup_steps: int = 100
    weight_decay: float = 0.1
    grad_clip: float = 1.0
    seed: int = 1337

    def validate(self) -> None:
        if self.n_embd % self.n_head != 0:
            raise ValueError("n_embd must be divisible by n_head")
        for key in ("vocab_size", "block_size", "n_layer", "n_head", "n_embd",
                    "batch_size", "max_steps", "eval_interval", "eval_batches"):
            if getattr(self, key) <= 0:
                raise ValueError(f"{key} must be > 0")
        if not 0.0 <= self.dropout < 1.0:
            raise ValueError("dropout must be in [0, 1)")
        if self.learning_rate <= 0 or self.grad_clip <= 0:
            raise ValueError("learning_rate and grad_clip must be > 0")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "LZConfig":
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)


# Tiny is the only preset intended for a phone. Medium/Large need a stronger machine.
PRESETS = {
    "tiny":   dict(block_size=128,  n_layer=4,  n_head=4,  n_embd=128,  batch_size=16, max_steps=2000),
    "small":  dict(block_size=256,  n_layer=6,  n_head=6,  n_embd=384,  batch_size=16, max_steps=20000, learning_rate=6e-4),
    "medium": dict(block_size=512,  n_layer=12, n_head=12, n_embd=768,  batch_size=8,  max_steps=100000, learning_rate=3e-4),
    "large":  dict(block_size=1024, n_layer=24, n_head=16, n_embd=1024, batch_size=4,  max_steps=300000, learning_rate=2e-4),
}
HEAVY_PRESETS = {"medium", "large"}


def from_preset(name: str, **overrides) -> LZConfig:
    if name not in PRESETS:
        raise ValueError(f"unknown preset {name!r}; choose from {sorted(PRESETS)}")
    cfg = LZConfig(name=name, **{**PRESETS[name], **overrides})
    cfg.validate()
    return cfg


def from_legacy_json(path: str | Path, name: str = "tiny", **overrides) -> LZConfig:
    """Reuse the existing model/config.json (keys: max_iters, vocab_size=0, ...)."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    mapped = {k: raw[k] for k in ("block_size", "batch_size", "eval_interval", "learning_rate",
                                  "n_embd", "n_head", "n_layer", "dropout", "seed") if k in raw}
    if "max_iters" in raw:
        mapped["max_steps"] = raw["max_iters"]
    cfg = LZConfig(name=name, **{**mapped, **overrides})
    cfg.validate()
    return cfg


def is_termux() -> bool:
    return "com.termux" in os.environ.get("PREFIX", "") or "TERMUX_VERSION" in os.environ


def check_hardware_policy(cfg: LZConfig) -> None:
    """Refuse to train Medium/Large on a phone unless explicitly overridden."""
    if cfg.name in HEAVY_PRESETS and is_termux() and os.environ.get("LZ_ALLOW_HEAVY") != "1":
        raise RuntimeError(
            f"Training the '{cfg.name}' preset on a phone (Termux) is blocked. "
            "Train it on a stronger machine, or set LZ_ALLOW_HEAVY=1 to override at your own risk."
        )
