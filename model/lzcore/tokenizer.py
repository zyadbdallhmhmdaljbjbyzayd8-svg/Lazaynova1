"""LZ byte-level BPE tokenizer (pure Python, trainable, Arabic + English + anything UTF-8).

Byte-level means every string round-trips losslessly; there is no unknown token in practice.
Special-token strings found inside user text are treated as plain text (never parsed).
"""
from __future__ import annotations

import hashlib
import os
import json
import re
from collections import Counter
from pathlib import Path

SPECIALS = ["<pad>", "<bos>", "<eos>", "<unk>"]
N_SPECIAL = len(SPECIALS)
PAD_ID, BOS_ID, EOS_ID, UNK_ID = range(4)
_PIECE_RE = re.compile(r"\s?\w+|\s?[^\w\s]+|\s+")


def _merge(seq: list[int], pair: tuple[int, int], new_id: int) -> list[int]:
    out, i = [], 0
    while i < len(seq):
        if i < len(seq) - 1 and seq[i] == pair[0] and seq[i + 1] == pair[1]:
            out.append(new_id)
            i += 2
        else:
            out.append(seq[i])
            i += 1
    return out


class LZTokenizer:
    def __init__(self, merges: list[tuple[int, int]] | None = None):
        self.merges = [tuple(m) for m in (merges or [])]
        self.ranks = {pair: i for i, pair in enumerate(self.merges)}
        self.pair_to_id: dict[tuple[int, int], int] = {}
        self.id_to_bytes = {N_SPECIAL + b: bytes([b]) for b in range(256)}
        for i, (a, b) in enumerate(self.merges):
            new_id = N_SPECIAL + 256 + i
            self.pair_to_id[(a, b)] = new_id
            self.id_to_bytes[new_id] = self.id_to_bytes[a] + self.id_to_bytes[b]
        self._cache: dict[str, list[int]] = {}

    @property
    def vocab_size(self) -> int:
        return N_SPECIAL + 256 + len(self.merges)

    @classmethod
    def train(cls, text: str, vocab_size: int = 512, min_frequency: int = 2) -> "LZTokenizer":
        n_merges = vocab_size - N_SPECIAL - 256
        if n_merges < 0:
            raise ValueError(f"vocab_size must be >= {N_SPECIAL + 256}")
        words = Counter(_PIECE_RE.findall(text))
        seqs = {w: [N_SPECIAL + b for b in w.encode("utf-8")] for w in words}
        merges: list[tuple[int, int]] = []
        for _ in range(n_merges):
            pairs: Counter = Counter()
            for w, seq in seqs.items():
                f = words[w]
                for a, b in zip(seq, seq[1:]):
                    pairs[(a, b)] += f
            if not pairs:
                break
            best, count = max(pairs.items(), key=lambda kv: (kv[1], -kv[0][0], -kv[0][1]))
            if count < min_frequency:
                break
            new_id = N_SPECIAL + 256 + len(merges)
            merges.append(best)
            for w in seqs:
                seqs[w] = _merge(seqs[w], best, new_id)
        return cls(merges)

    def _encode_piece(self, piece: str) -> list[int]:
        cached = self._cache.get(piece)
        if cached is not None:
            return cached
        ids = [N_SPECIAL + b for b in piece.encode("utf-8")]
        while len(ids) > 1:
            best_rank, best_pair = None, None
            for pair in zip(ids, ids[1:]):
                r = self.ranks.get(pair)
                if r is not None and (best_rank is None or r < best_rank):
                    best_rank, best_pair = r, pair
            if best_pair is None:
                break
            ids = _merge(ids, best_pair, self.pair_to_id[best_pair])
        if len(self._cache) < 100_000:
            self._cache[piece] = ids
        return ids

    def encode(self, text: str, add_bos: bool = False, add_eos: bool = False) -> list[int]:
        ids: list[int] = [BOS_ID] if add_bos else []
        for piece in _PIECE_RE.findall(text):
            ids.extend(self._encode_piece(piece))
        if add_eos:
            ids.append(EOS_ID)
        return ids

    def decode(self, ids, skip_special: bool = True) -> str:
        out = bytearray()
        for i in ids:
            i = int(i)
            if i < 0 or i >= self.vocab_size:
                raise ValueError(f"token id {i} out of range (vocab_size={self.vocab_size})")
            if i < N_SPECIAL:
                if not skip_special:
                    out.extend(SPECIALS[i].encode("utf-8"))
                continue
            out.extend(self.id_to_bytes[i])
        return out.decode("utf-8", errors="replace")

    def to_dict(self) -> dict:
        return {"type": "lz-bpe", "version": 1, "specials": SPECIALS,
                "merges": [list(m) for m in self.merges]}

    @classmethod
    def from_dict(cls, d: dict) -> "LZTokenizer":
        if not isinstance(d, dict):
            raise ValueError("tokenizer data must be an object")
        if d.get("type") != "lz-bpe" or d.get("version") != 1:
            raise ValueError("not a compatible lz-bpe tokenizer")
        if d.get("specials") != SPECIALS:
            raise ValueError("tokenizer special tokens differ")
        raw_merges = d.get("merges")
        if not isinstance(raw_merges, list):
            raise ValueError("tokenizer merges must be a list")

        merges = []
        available = N_SPECIAL + 256
        seen = set()
        for index, pair in enumerate(raw_merges):
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise ValueError(f"invalid tokenizer merge at index {index}")
            a, b = pair
            if (isinstance(a, bool) or isinstance(b, bool)
                    or not isinstance(a, int) or not isinstance(b, int)):
                raise ValueError(f"merge IDs must be integers at index {index}")
            if not (N_SPECIAL <= a < available and N_SPECIAL <= b < available):
                raise ValueError(f"merge references an unavailable token at index {index}")
            item = (a, b)
            if item in seen:
                raise ValueError(f"duplicate tokenizer merge at index {index}")
            seen.add(item)
            merges.append(item)
            available += 1
        return cls(merges)

    def hash(self) -> str:
        blob = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(blob).hexdigest()

    def save(self, path: str | Path) -> None:
        # Exclusive creation: never silently replace an existing tokenizer.
        target = Path(path)
        payload = json.dumps(self.to_dict(), ensure_ascii=False)
        with target.open("x", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())

    @classmethod
    def load(cls, path: str | Path) -> "LZTokenizer":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
