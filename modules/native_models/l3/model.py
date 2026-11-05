"""Native decoder-only Transformer for LAZAYNOVA L3; initialized from scratch."""
import torch
import torch.nn as nn
import torch.nn.functional as F


class CausalSelfAttention(nn.Module):
    def __init__(self, config):
        super().__init__()
        dim, heads = int(config["d_model"]), int(config["n_heads"])
        if heads < 1 or dim % heads:
            raise ValueError("d_model must be divisible by positive n_heads")
        self.heads, self.head_dim = heads, dim // heads
        self.qkv = nn.Linear(dim, 3 * dim)
        self.projection = nn.Linear(dim, dim)
        self.dropout = nn.Dropout(float(config.get("dropout", 0.0)))

    def forward(self, x):
        batch, length, dim = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)
        def split(t):
            return t.view(batch, length, self.heads, self.head_dim).transpose(1, 2)
        q, k, v = split(q), split(k), split(v)
        scores = (q @ k.transpose(-2, -1)) * (self.head_dim ** -0.5)
        mask = torch.ones(length, length, device=x.device, dtype=torch.bool).tril()
        scores = scores.masked_fill(~mask, torch.finfo(scores.dtype).min)
        weights = self.dropout(F.softmax(scores, dim=-1))
        out = (weights @ v).transpose(1, 2).contiguous().view(batch, length, dim)
        return self.projection(out)


class FeedForward(nn.Module):
    def __init__(self, config):
        super().__init__()
        dim, hidden = int(config["d_model"]), int(config["ff_dim"])
        self.net = nn.Sequential(nn.Linear(dim, hidden), nn.GELU(),
                                 nn.Linear(hidden, dim),
                                 nn.Dropout(float(config.get("dropout", 0.0))))
    def forward(self, x):
        return self.net(x)


class TransformerBlock(nn.Module):
    def __init__(self, config):
        super().__init__()
        dim = int(config["d_model"])
        self.norm1, self.attention = nn.LayerNorm(dim), CausalSelfAttention(config)
        self.norm2, self.ff = nn.LayerNorm(dim), FeedForward(config)
    def forward(self, x):
        x = x + self.attention(self.norm1(x))
        return x + self.ff(self.norm2(x))


class LazaynovaL3(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.config = dict(config)
        vocab, dim, context = (int(config[k]) for k in
                               ("vocab_size", "d_model", "context_length"))
        if min(vocab, dim, context, int(config["n_layers"]), int(config["n_heads"])) < 1:
            raise ValueError("model dimensions must be positive")
        self.token_embedding = nn.Embedding(vocab, dim)
        self.position_embedding = nn.Embedding(context, dim)
        self.blocks = nn.ModuleList([TransformerBlock(config)
                                     for _ in range(int(config["n_layers"]))])
        self.final_norm = nn.LayerNorm(dim)
        self.language_head = nn.Linear(dim, vocab, bias=False)
        self.apply(self._init_weights)
        self.language_head.weight = self.token_embedding.weight

    @staticmethod
    def _init_weights(module):
        if isinstance(module, (nn.Linear, nn.Embedding)):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if isinstance(module, nn.Linear) and module.bias is not None:
                nn.init.zeros_(module.bias)

    def forward(self, input_ids, targets=None):
        if input_ids.ndim != 2:
            raise ValueError("input_ids must have shape [batch, sequence]")
        batch, length = input_ids.shape
        if length < 1 or length > int(self.config["context_length"]):
            raise ValueError("sequence length outside configured context")
        if input_ids.min().item() < 0 or input_ids.max().item() >= int(self.config["vocab_size"]):
            raise ValueError("token id outside vocabulary")
        pos = torch.arange(length, device=input_ids.device)
        x = self.token_embedding(input_ids) + self.position_embedding(pos)[None, :, :]
        for block in self.blocks:
            x = block(x)
        logits = self.language_head(self.final_norm(x))
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)),
                                   targets.reshape(-1), ignore_index=0)
        return logits, loss

    def parameter_count(self):
        return sum(p.numel() for p in self.parameters())
