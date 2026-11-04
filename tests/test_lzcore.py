"""Tests for LZ-Core. Run from the repo root:
    python -m unittest tests.test_lzcore -v      (or: python tests/test_lzcore.py)
Torch-dependent tests are SKIPPED (not passed) when torch is missing.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from model.lzcore.config import LZConfig, check_hardware_policy, from_preset
from model.lzcore.tokenizer import BOS_ID, EOS_ID, LZTokenizer

try:
    import torch
    from model.lzcore.model import LZCore
    from model.lzcore import train_lib
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

CORPUS = ("مرحبا بك في لازاينوفا. نظام ذكاء اصطناعي خاص ومستقل. "
          "Hello from Lazaynova. A private, autonomous AI system. ") * 60


def tiny_cfg(vocab, **kw):
    base = dict(name="test", vocab_size=vocab, block_size=32, n_layer=2, n_head=2, n_embd=32,
                dropout=0.0, batch_size=8, max_steps=40, eval_interval=20, eval_batches=2,
                warmup_steps=5, learning_rate=3e-3)
    base.update(kw)
    return LZConfig(**base)


class TokenizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tok = LZTokenizer.train(CORPUS, vocab_size=400)

    def test_roundtrip_arabic_english_mixed_emoji(self):
        for s in ["مرحبا بالعالم", "Hello, world!", "مرحبا Hello 123 \u0645\u064e\u0631\u0652\u062d\u064e\u0628\u064b\u0627 😀",
                  "  leading and   multiple   spaces\n\ttabs", ""]:
            self.assertEqual(self.tok.decode(self.tok.encode(s)), s)

    def test_merges_compress(self):
        s = "Hello from Lazaynova."
        self.assertLess(len(self.tok.encode(s)), len(s.encode("utf-8")))

    def test_deterministic_training(self):
        self.assertEqual(LZTokenizer.train(CORPUS, vocab_size=400).hash(), self.tok.hash())

    def test_save_load(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.json"
            self.tok.save(p)
            t2 = LZTokenizer.load(p)
            self.assertEqual(t2.hash(), self.tok.hash())
            self.assertEqual(t2.encode("لازاينوفا"), self.tok.encode("لازاينوفا"))

    def test_special_tokens(self):
        ids = self.tok.encode("hi", add_bos=True, add_eos=True)
        self.assertEqual((ids[0], ids[-1]), (BOS_ID, EOS_ID))
        self.assertEqual(self.tok.decode(ids), "hi")

    def test_special_string_in_text_is_plain_text(self):
        ids = self.tok.encode("<eos>")
        self.assertNotIn(EOS_ID, ids)
        self.assertEqual(self.tok.decode(ids), "<eos>")

    def test_decode_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            self.tok.decode([self.tok.vocab_size])

    def test_vocab_too_small(self):
        with self.assertRaises(ValueError):
            LZTokenizer.train(CORPUS, vocab_size=100)


class ConfigTests(unittest.TestCase):
    def test_presets_valid(self):
        for name in ("tiny", "small", "medium", "large"):
            self.assertEqual(from_preset(name).name, name)

    def test_bad_heads(self):
        with self.assertRaises(ValueError):
            LZConfig(n_embd=30, n_head=4).validate()

    def test_heavy_blocked_on_termux(self):
        with mock.patch.dict(os.environ, {"PREFIX": "/data/data/com.termux/files/usr"}, clear=False):
            os.environ.pop("LZ_ALLOW_HEAVY", None)
            with self.assertRaises(RuntimeError):
                check_hardware_policy(from_preset("large"))
            check_hardware_policy(from_preset("tiny"))  # tiny allowed
            with mock.patch.dict(os.environ, {"LZ_ALLOW_HEAVY": "1"}):
                check_hardware_policy(from_preset("large"))


@unittest.skipUnless(HAS_TORCH, "torch not installed")
class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tok = LZTokenizer.train(CORPUS, vocab_size=400)

    def test_create_and_forward(self):
        cfg = tiny_cfg(self.tok.vocab_size)
        m = LZCore(cfg)
        x = torch.randint(0, cfg.vocab_size, (3, 16))
        logits, loss = m(x, x)
        self.assertEqual(tuple(logits.shape), (3, 16, cfg.vocab_size))
        self.assertTrue(torch.isfinite(loss))
        self.assertIs(m.lm_head.weight, m.wte.weight)

    def test_rejects_too_long_sequence(self):
        m = LZCore(tiny_cfg(self.tok.vocab_size))
        with self.assertRaises(ValueError):
            m(torch.zeros(1, 33, dtype=torch.long))

    def test_generate_arabic_and_english(self):
        m = LZCore(tiny_cfg(self.tok.vocab_size))
        for prompt in ("مرحبا", "Hello"):
            ids = torch.tensor([self.tok.encode(prompt)])
            out = m.generate(ids, 10, top_k=20)
            self.assertEqual(out.shape[1], ids.shape[1] + 10)
            self.assertTrue(0 <= int(out.min()) and int(out.max()) < self.tok.vocab_size)
            self.assertIsInstance(self.tok.decode(out[0].tolist()), str)

    def test_train_checkpoint_load_resume(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = tiny_cfg(self.tok.vocab_size)
            s1 = train_lib.train(cfg, CORPUS, self.tok, d, device="cpu", log=lambda *_: None)
            self.assertLess(s1["final_val_loss"], s1["initial_val_loss"])
            self.assertTrue((Path(d) / "last.pt").exists() and (Path(d) / "meta.json").exists())

            m, tok2, cfg2 = train_lib.load_model(d)
            self.assertEqual(tok2.hash(), self.tok.hash())
            x = torch.tensor([self.tok.encode("Hello from")])
            a, _ = m(x)
            m_b, _, _ = train_lib.load_model(Path(d) / "last.pt")
            b, _ = m_b(x)
            self.assertTrue(torch.allclose(a, b))

            cfg_r = tiny_cfg(self.tok.vocab_size)
            s2 = train_lib.train(cfg_r, CORPUS, self.tok, d, resume=True, max_steps=60,
                                 device="cpu", log=lambda *_: None)
            self.assertEqual(s2["steps_completed"], 60)
            self.assertEqual(s2["initial_val_loss"], s1["initial_val_loss"])

    def test_resume_rejects_different_tokenizer(self):
        with tempfile.TemporaryDirectory() as d:
            train_lib.train(tiny_cfg(self.tok.vocab_size, max_steps=20), CORPUS, self.tok, d,
                            device="cpu", log=lambda *_: None)
            other = LZTokenizer.train(CORPUS, vocab_size=300)
            with self.assertRaises(ValueError):
                train_lib.train(tiny_cfg(other.vocab_size), CORPUS, other, d, resume=True,
                                device="cpu", log=lambda *_: None)

    def test_too_little_data(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                train_lib.train(tiny_cfg(self.tok.vocab_size), "short", self.tok, d,
                                device="cpu", log=lambda *_: None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
