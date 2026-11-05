import os
import json
import hashlib
from datetime import datetime, timezone

class LazaynovaFineTuner:
    def __init__(self, track_name: str, base_model_id: str, base_license: str):
        self.track_name = track_name  # مثال: LZ-Chat أو LZ-Code
        self.base_model_id = base_model_id
        self.base_license = base_license
        self.manifest_dir = "native_ai/manifests"
        os.makedirs(self.manifest_dir, exist_ok=True)

    def prepare_chatml_dataset(self, raw_samples: list, output_path: str) -> str:
        """تحويل وتنظيف البيانات إلى صيغة ChatML JSONL"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        hasher = hashlib.sha256()
        count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for item in raw_samples:
                if "instruction" in item and "response" in item:
                    record = {
                        "messages": [
                            {"role": "system", "content": "أنت مساعد LAZAYNOVA الذكي."},
                            {"role": "user", "content": item["instruction"].strip()},
                            {"role": "assistant", "content": item["response"].strip()}
                        ]
                    }
                    line = json.dumps(record, ensure_ascii=False) + "\n"
                    f.write(line)
                    hasher.update(line.encode("utf-8"))
                    count += 1
        return hasher.hexdigest()

    def generate_provenance_manifest(self, dataset_path: str, dataset_hash: str) -> str:
        """توليد وثيقة إثبات الملكية والمنشأ بشفافية تامة دون ادعاء التدريب المسبق"""
        manifest = {
            "brand": "LAZAYNOVA",
            "model_track": self.track_name,
            "derivation_type": "QLoRA_Adapter_FineTuning",
            "base_model": {
                "identity": self.base_model_id,
                "license": self.base_license,
                "trained_from_scratch": False
            },
            "dataset": {
                "path": dataset_path,
                "sha256": dataset_hash
            },
            "training_status": "CONFIGURED_READY_FOR_GPU",
            "checkpoint_verified": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        manifest_path = os.path.join(self.manifest_dir, f"{self.track_name.lower()}_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        return manifest_path
