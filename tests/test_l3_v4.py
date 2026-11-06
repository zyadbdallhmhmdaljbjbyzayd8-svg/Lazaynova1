"""Isolated unit tests for the LAZAYNOVA L3 V4 trainer."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch

from modules.native_models.l3.model import LazaynovaL3
from modules.native_models.l3.tokenizer import ByteTokenizer
from native_ai.training.train_l3_v4 import (
    build_config,
    encode_pair,
    make_batch,
    masked_loss,
    split_records,
    validate_examples,
)


class L3V4Tests(unittest.TestCase):
    def setUp(self):
        self.records = [
            {
                "instruction": "ما هو الذكاء الاصطناعي؟",
                "response": "هو مجال يدرس بناء أنظمة ذكية.",
                "language": "ar",
            },
            {
                "instruction": "ما هي البرمجة؟",
                "response": "هي كتابة تعليمات للحاسوب.",
                "language": "ar",
            },
            {
                "instruction": "What is AI?",
                "response": "AI studies intelligent systems.",
                "language": "en",
            },
            {
                "instruction": "What is programming?",
                "response": "Programming is writing instructions.",
                "language": "en",
            },
        ]

    def test_config_is_independent_v4_context(self):
        config = build_config()
        self.assertEqual(config["context_length"], 320)
        self.assertEqual(config["version"], "native-scratch-v4")
        self.assertFalse(config["external_weights"])
        self.assertFalse(config["external_ai_apis"])

    def test_assistant_only_targets(self):
        tokenizer = ByteTokenizer()
        inputs, targets = encode_pair(self.records[0], tokenizer)

        first_target = next(
            index for index, token in enumerate(targets)
            if token != tokenizer.PAD
        )

        self.assertGreater(first_target, 0)
        self.assertEqual(targets[first_target], inputs[first_target + 1])
        self.assertEqual(targets[-1], tokenizer.EOS)
        self.assertTrue(
            all(token == tokenizer.PAD for token in targets[:first_target])
        )

    def test_pair_is_not_truncated(self):
        config = build_config()
        stats = validate_examples(self.records, config["context_length"])
        self.assertEqual(stats["count"], len(self.records))
        self.assertLessEqual(stats["max_tokens"], 320)

    def test_stratified_split(self):
        train, validation = split_records(self.records, seed=42)
        self.assertEqual(len(train), 2)
        self.assertEqual(len(validation), 2)

        self.assertEqual(
            {item["language"] for item in train},
            {"ar", "en"},
        )
        self.assertEqual(
            {item["language"] for item in validation},
            {"ar", "en"},
        )
        self.assertFalse(set(map(id, train)) & set(map(id, validation)))

    def test_batch_shapes_and_prompt_mask(self):
        x, y = make_batch(self.records, 320, torch.device("cpu"))
        self.assertEqual(x.ndim, 2)
        self.assertEqual(tuple(x.shape), tuple(y.shape))
        self.assertTrue((y == ByteTokenizer.PAD).any().item())

        for row in range(len(self.records)):
            valid = torch.nonzero(y[row] != ByteTokenizer.PAD)
            self.assertGreater(valid.numel(), 0)
            first = int(valid[0].item())
            self.assertTrue((y[row, :first] == ByteTokenizer.PAD).all())

    def test_native_model_forward_and_masked_loss(self):
        config = build_config()
        model = LazaynovaL3(config)
        x, y = make_batch(self.records[:2], 320, torch.device("cpu"))
        logits, _ = model(x)
        loss = masked_loss(logits, y)

        self.assertEqual(tuple(logits.shape), (2, x.shape[1], 260))
        self.assertTrue(torch.isfinite(loss).item())

    def test_empty_assistant_targets_rejected(self):
        logits = torch.zeros((1, 2, 260))
        targets = torch.zeros((1, 2), dtype=torch.long)
        with self.assertRaises(ValueError):
            masked_loss(logits, targets)

    def test_deterministic_split(self):
        first = split_records(self.records, seed=123)
        second = split_records(self.records, seed=123)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main(verbosity=2)
