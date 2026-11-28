"""Safe dataset preparation and provenance for native LAZAYNOVA pretraining.

This module does not load external models, call external AI APIs, train a model,
or create checkpoints. All output files are created exclusively.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping


SYSTEM_PROMPT = "أنت مساعد LAZAYNOVA الذكي."


class NativePretraining:
    def __init__(self, track_name: str, manifest_dir="native_ai/manifests"):
        if not isinstance(track_name, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", track_name
        ):
            raise ValueError("Invalid model track name")
        self.track_name = track_name
        self.manifest_dir = Path(manifest_dir)

    @staticmethod
    def _sample_text(item: Mapping, key: str, index: int) -> str:
        value = item.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Sample {index}: invalid {key}")
        return value.strip()

    def prepare_chat_dataset(
        self, raw_samples: Iterable[Mapping], output_path
    ) -> dict:
        """Create a ChatML-style JSONL dataset without overwriting any file."""
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        digest = hashlib.sha256()
        count = 0

        # Exclusive creation: an existing dataset is never overwritten.
        with destination.open("x", encoding="utf-8", newline="\n") as handle:
            for index, item in enumerate(raw_samples, 1):
                if not isinstance(item, Mapping):
                    raise ValueError(f"Sample {index}: expected an object")

                instruction = self._sample_text(item, "instruction", index)
                response = self._sample_text(item, "response", index)

                record = {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": instruction},
                        {"role": "assistant", "content": response},
                    ]
                }
                line = json.dumps(
                    record, ensure_ascii=False, separators=(",", ":")
                ) + "\n"
                encoded = line.encode("utf-8")
                handle.write(line)
                digest.update(encoded)
                count += 1

        if count == 0:
            # Do not silently leave an empty dataset behind.
            destination.unlink()
            raise ValueError("Dataset must contain at least one valid sample")

        return {
            "path": str(destination),
            "sha256": digest.hexdigest(),
            "records": count,
        }

    def generate_provenance_manifest(
        self, dataset_path, dataset_hash: str
    ) -> str:
        """Record truthful from-scratch intent; this does not claim training."""
        dataset = Path(dataset_path)
        if not dataset.is_file():
            raise FileNotFoundError(f"Dataset not found: {dataset}")
        if not isinstance(dataset_hash, str) or not re.fullmatch(
            r"[0-9a-f]{64}", dataset_hash
        ):
            raise ValueError("Invalid SHA-256 value")

        actual_hash = hashlib.sha256(dataset.read_bytes()).hexdigest()
        if actual_hash != dataset_hash:
            raise ValueError("Dataset SHA-256 mismatch")

        manifest = {
            "brand": "LAZAYNOVA",
            "model_track": self.track_name,
            "derivation_type": "native_pretraining_from_scratch",
            "training_origin": "random_initialization",
            "base_model": None,
            "adapter_training": False,
            "external_model_weights": False,
            "external_ai_apis": False,
            "dataset": {
                "path": str(dataset),
                "sha256": actual_hash,
            },
            "training_status": "CONFIGURED_NOT_TRAINED",
            "checkpoint_verified": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        destination = self.manifest_dir / (
            f"{self.track_name.lower()}_native_manifest.json"
        )

        # Exclusive creation protects any previous manifest.
        with destination.open("x", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

        return str(destination)
