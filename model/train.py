"""Tiny character-level GPT trained from random initialization.

Run from the repository root:
  python -m pip install -r model/requirements.txt
  python model/train.py
This is an educational prototype, not a production chatbot.
"""
from __future__ import annotations

import json
import math
import os
import random
from pathlib import Path

import torch
import torch.nn as nn
from torch.nn import functional as F

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "train.txt"
CONFIG_PATH = ROOT / "config.json"
OUT_PATH = ROOT / "artifacts" / "lazaynova-tiny.pt"


class Head(nn.Module):
    def __init__(self, head_size: int, n_embd: int, block_size: int, dropout: float):
        super().__init__()
        self.key = nn.Linear(n_embd, head_size, bias=False)
        self.query = nn.Linear(n_embd, head_size, bias=False)
        self.value = nn.Linear(n_embd, head_size, bias=False)
        self.register_buffer("tril", torch.tril(torch.ones(block_size, block_size)))
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        b, t, c = x.shape
        k, q = self.key(x), self.query(x)
        weights = q @ k.transpose(-2, -1) * (k.shape[-1] ** -0.5)
        weights = weights.masked_fill(self.tril[:t, :t] == 0, float("-inf"))
        weights = self.dropout(F.softmax(weights, dim=-1))
        return self.dropout(weights @ self.value(x))


class MultiHeadAttention(nn.Module):
    def __init__(self, n_head: int, n_embd: int, block_size: int, dropout: float):
        super().__init__()
        head_size = n_embd // n_head
        self.heads = nn.ModuleList(
            [Head(head_size, n_embd, block_size, dropout) for _ in range(n_head)]
        )
        self.proj = nn.Linear(n_embd, n_embd)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        return self.dropout(self.proj(torch.cat([h(x) for h in self.heads], dim=-1)))


class FeedForward(nn.Module):
    def __init__(self, n_embd: int, dropout: float):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_embd, 4 * n_embd),
            nn.GELU(),
            nn.Linear(4 * n_embd, n_embd),
            nn.Dropout(dropout),
        )

    def forward(self, x):
        return self.net(x)


class Block(nn.Module):
    def __init__(self, n_embd: int, n_head: int, block_size: int, dropout: float):
        super().__init__()
        self.sa = MultiHeadAttention(n_head, n_embd, block_size, dropout)
        self.ffwd = FeedForward(n_embd, dropout)
        self.ln1 = nn.LayerNorm(n_embd)
        self.ln2 = nn.LayerNorm(n_embd)

    def forward(self, x):
        x = x + self.sa(self.ln1(x))
        return x + self.ffwd(self.ln2(x))


class LazaynovaTiny(nn.Module):
    def __init__(self, vocab_size: int, cfg: dict):
        super().__init__()
        n_embd = cfg["n_embd"]
        self.block_size = cfg["block_size"]
        self.token_embedding = nn.Embedding(vocab_size, n_embd)
        self.position_embedding = nn.Embedding(self.block_size, n_embd)
        self.blocks = nn.Sequential(*[
            Block(n_embd, cfg["n_head"], self.block_size, cfg["dropout"])
            for _ in range(cfg["n_layer"])
        ])
        self.ln_f = nn.LayerNorm(n_embd)
        self.lm_head = nn.Linear(n_embd, vocab_size)

    def forward(self, idx, targets=None):
        b, t = idx.shape
        positions = torch.arange(t, device=idx.device)
        x = self.token_embedding(idx) + self.position_embedding(positions)
        x = self.blocks(x)
        logits = self.lm_head(self.ln_f(x))
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), targets.reshape(-1))
        return logits, loss

    @torch.no_grad()
    def generate(self, idx, max_new_tokens: int, temperature: float = 0.8):
        for _ in range(max_new_tokens):
            idx_cond = idx[:, -self.block_size:]
            logits, _ = self(idx_cond)
            logits = logits[:, -1, :] / max(temperature, 1e-4)
            probs = F.softmax(logits, dim=-1)
            next_idx = torch.multinomial(probs, num_samples=1)
            idx = torch.cat((idx, next_idx), dim=1)
        return idx


def main():
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    text = DATA_PATH.read_text(encoding="utf-8")
    if len(text.strip()) < 100:
        raise SystemExit("Training text is too short. Add more permitted text to model/data/train.txt")

    # Character-level tokenizer: deliberately simple for the first prototype.
    chars = sorted(set(text))
    stoi = {ch: i for i, ch in enumerate(chars)}
    itos = {i: ch for ch, i in stoi.items()}
    encode = lambda s: [stoi[c] for c in s if c in stoi]
    decode = lambda ids: "".join(itos[int(i)] for i in ids)
    data = torch.tensor(encode(text), dtype=torch.long)
    if len(data) < cfg["block_size"] + 2:
        cfg["block_size"] = max(16, min(64, len(data) // 2))

    split = int(0.9 * len(data))
    train_data = data[:split]
    val_data = data[split:] if split < len(data) else data

    random.seed(cfg["seed"])
    torch.manual_seed(cfg["seed"])
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}; characters: {len(chars)}; training chars: {len(train_data)}")
    print("Note: a tiny dataset only demonstrates the training pipeline.")

    model = LazaynovaTiny(len(chars), cfg).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg["learning_rate"])

    def get_batch(source):
        max_start = max(1, len(source) - cfg["block_size"] - 1)
        starts = torch.randint(max_start, (cfg["batch_size"],))
        x = torch.stack([source[i:i + cfg["block_size"]] for i in starts])
        y = torch.stack([source[i + 1:i + cfg["block_size"] + 1] for i in starts])
        return x.to(device), y.to(device)

    for step in range(cfg["max_iters"]):
        model.train()
        xb, yb = get_batch(train_data)
        _, loss = model(xb, yb)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        if step % cfg["eval_interval"] == 0 or step == cfg["max_iters"] - 1:
            model.eval()
            with torch.no_grad():
                vx, vy = get_batch(val_data)
                _, val_loss = model(vx, vy)
            print(f"step {step:5d} | train loss {loss.item():.4f} | val loss {val_loss.item():.4f}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "model_state": model.cpu().state_dict(),
        "config": cfg,
        "stoi": stoi,
        "itos": itos,
    }, OUT_PATH)
    print(f"Saved model checkpoint: {OUT_PATH}")
    model.eval()
    prompt = text[:min(20, len(text))]
    ids = torch.tensor([encode(prompt)], dtype=torch.long)
    print("\nSample generation:\n" + decode(model.generate(ids, 160)[0].tolist()))


if __name__ == "__main__":
    main()
