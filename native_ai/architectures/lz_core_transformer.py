from dataclasses import dataclass, asdict

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

@dataclass
class LZCoreConfig:
    vocab_size: int = 32000
    d_model: int = 256
    n_heads: int = 4
    n_layers: int = 4
    max_seq_len: int = 512
    dropout: float = 0.1
    architecture_version: str = "LZ-Core-v0.1-Tiny"

if TORCH_AVAILABLE:
    class LZCoreTransformer(nn.Module):
        def __init__(self, config: LZCoreConfig):
            super().__init__()
            self.config = config
            self.token_emb = nn.Embedding(config.vocab_size, config.d_model)
            self.pos_emb = nn.Embedding(config.max_seq_len, config.d_model)
            decoder_layer = nn.TransformerDecoderLayer(
                d_model=config.d_model, nhead=config.n_heads,
                dim_feedforward=config.d_model * 4, dropout=config.dropout,
                batch_first=True, norm_first=True
            )
            self.transformer = nn.TransformerDecoder(decoder_layer, num_layers=config.n_layers)
            self.norm = nn.LayerNorm(config.d_model)
            self.lm_head = nn.Linear(config.d_model, config.vocab_size, bias=False)

        def forward(self, input_ids: torch.Tensor):
            b, t = input_ids.size()
            positions = torch.arange(0, t, dtype=torch.long, device=input_ids.device).unsqueeze(0)
            x = self.token_emb(input_ids) + self.pos_emb(positions)
            causal_mask = torch.triu(torch.ones(t, t, device=input_ids.device) * float('-inf'), diagonal=1)
            x = self.transformer(x, x, tgt_mask=causal_mask)
            return self.lm_head(self.norm(x))

if __name__ == "__main__":
    cfg = LZCoreConfig()
    print(f"[LAZAYNOVA] Architecture loaded: {cfg.architecture_version}")
    print(f"[LAZAYNOVA] PyTorch available: {TORCH_AVAILABLE}")
