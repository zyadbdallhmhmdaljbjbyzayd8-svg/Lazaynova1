import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from modules.native_models.l3.tokenizer import ByteTokenizer
from modules.native_models.l3.model import LazaynovaL3
from native_ai.registry.model_registry import inspect_gguf
from lz_core.ai_gateway.gateway import InternalAIGateway

class NativeL3Tests(unittest.TestCase):
    def test_tokenizer_utf8_and_special_tokens(self):
        tok = ByteTokenizer()
        ids = tok.encode("مرحبا 🌍", add_bos=True, add_eos=True)
        self.assertEqual(ids[0], tok.BOS)
        self.assertEqual(ids[-1], tok.EOS)
        self.assertEqual(tok.decode(ids), "مرحبا 🌍")
        self.assertEqual(tok.VOCAB_SIZE, 260)

    def test_model_forward(self):
        config = json.loads((ROOT / "config/models/l3.json").read_text())
        model = LazaynovaL3(config)
        import torch
        x = torch.tensor([[2, 4, 5, 6]])
        logits, loss = model(x, torch.tensor([[4, 5, 6, 7]]))
        self.assertEqual(tuple(logits.shape), (1, 4, 260))
        self.assertTrue(torch.isfinite(loss).item())

    def test_html_gguf_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.gguf"
            path.write_text("<!doctype html>", encoding="utf-8")
            result = inspect_gguf(str(path))
            self.assertEqual(result["format"], "HTML_ERROR")
            self.assertEqual(result["status"], "UNVERIFIED")

    def test_external_endpoint_rejected(self):
        with self.assertRaises(PermissionError):
            InternalAIGateway("https://example.com/v1/chat/completions")

if __name__ == "__main__":
    unittest.main(verbosity=2)
