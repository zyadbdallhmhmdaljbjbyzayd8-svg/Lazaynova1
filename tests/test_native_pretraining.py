import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from native_ai.training.native_pretraining import NativePretraining


class TestNativePretraining(unittest.TestCase):
    def test_dataset_and_manifest_are_created_in_temporary_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dataset = root / "data" / "samples.jsonl"
            manifests = root / "manifests"

            pipeline = NativePretraining("LZ-Chat-Test", manifests)
            result = pipeline.prepare_chat_dataset(
                [{"instruction": "من أنت؟", "response": "أنا LAZAYNOVA."}],
                dataset,
            )

            self.assertEqual(result["records"], 1)
            self.assertEqual(
                result["sha256"],
                hashlib.sha256(dataset.read_bytes()).hexdigest(),
            )

            manifest_path = Path(
                pipeline.generate_provenance_manifest(
                    dataset, result["sha256"]
                )
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertIsNone(manifest["base_model"])
            self.assertFalse(manifest["external_model_weights"])
            self.assertFalse(manifest["external_ai_apis"])
            self.assertFalse(manifest["adapter_training"])
            self.assertEqual(
                manifest["training_status"], "CONFIGURED_NOT_TRAINED"
            )
            self.assertFalse(manifest["checkpoint_verified"])

    def test_existing_dataset_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "existing.jsonl"
            original = b"keep this exact content\n"
            path.write_bytes(original)

            pipeline = NativePretraining("LZ-Test", Path(temp) / "manifests")
            with self.assertRaises(FileExistsError):
                pipeline.prepare_chat_dataset(
                    [{"instruction": "سؤال", "response": "جواب"}], path
                )
            self.assertEqual(path.read_bytes(), original)

    def test_manifest_rejects_dataset_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dataset = root / "dataset.jsonl"
            dataset.write_text("original\n", encoding="utf-8")
            pipeline = NativePretraining("LZ-Test", root / "manifests")

            with self.assertRaises(ValueError):
                pipeline.generate_provenance_manifest(dataset, "0" * 64)

    def test_empty_dataset_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "empty.jsonl"
            pipeline = NativePretraining("LZ-Test", Path(temp) / "manifests")

            with self.assertRaises(ValueError):
                pipeline.prepare_chat_dataset([], path)
            self.assertFalse(path.exists())

    def test_invalid_track_name_is_rejected(self):
        with self.assertRaises(ValueError):
            NativePretraining("../external")


if __name__ == "__main__":
    unittest.main(verbosity=2)
