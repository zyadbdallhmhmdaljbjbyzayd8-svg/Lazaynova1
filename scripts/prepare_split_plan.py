#!/usr/bin/env python3
"""Read-only planner for LAZAYNOVA model/dataset separation and cloud readiness."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".git", ".gradle", "build", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", "backups"}

MODEL_EXTS = {".pt", ".pth", ".gguf", ".safetensors", ".bin"}
DATASET_EXTS = {".jsonl", ".json", ".csv", ".parquet", ".tsv"}


def iter_project_files(base: Path):
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        if any(part in EXCLUDE_DIRS or part.startswith(".backup") for part in p.parts):
            continue
        yield p


def main() -> None:
    model_files = []
    dataset_files = []
    code_refs = []

    for f in iter_project_files(ROOT):
        rel = f.relative_to(ROOT).as_posix()
        size_mb = round(f.stat().st_size / (1024 * 1024), 2)
        ext = f.suffix.lower()
        if ext in MODEL_EXTS:
            model_files.append({"path": rel, "size_mb": size_mb})
        elif ext in DATASET_EXTS and ("dataset" in rel.lower() or "sample" in rel.lower() or ext == ".jsonl"):
            dataset_files.append({"path": rel, "size_mb": size_mb})

        if ext in {".py", ".ts", ".tsx", ".js", ".kt"}:
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for needle in ("checkpoints", "l3_checkpoint", "qwen2.5", "gguf", ".jsonl", "Lazaynova1-models", "Lazaynova1-datasets"):
                if needle in text:
                    code_refs.append({"file": rel, "reference": needle})

    plan = {
        "target_repos": {
            "main_code": "zyadbdallhmhmdaljbjbyzayd8-svg/Lazaynova1",
            "models_lfs": "zyadbdallhmhmdaljbjbyzayd8-svg/Lazaynova1-models",
            "datasets": "zyadbdallhmhmdaljbjbyzayd8-svg/Lazaynova1-datasets",
        },
        "model_files_found": model_files,
        "dataset_files_found": dataset_files,
        "code_references_count": len(code_refs),
        "code_references": code_refs[:80],
        "notes": [
            "Do not move or delete checkpoints or large model weights without verifying all code path references.",
            "Keep heavy LLM/checkpoint inference out of free-tier web API dynos; isolate inference services and use external Postgres (e.g., Supabase).",
        ],
    }

    report_path = ROOT / "docs" / "SPLIT_MODELS_DATASETS_PLAN_AR.md"
    lines = [
        "# خطة فحص فصل النماذج والبيانات وجاهزية الاستضافة السحابية (LAZAYNOVA)",
        "",
        "## 1. المستودعات المستهدفة",
        f"- الكود الرئيسي: `{plan['target_repos']['main_code']}`",
        f"- النماذج (LFS): `{plan['target_repos']['models_lfs']}`",
        f"- البيانات: `{plan['target_repos']['datasets']}`",
        "",
        "## 2. ملفات النماذج المكتشفة (قراءة فقط)",
    ]
    if model_files:
        for item in model_files:
            lines.append(f"- `{item['path']}` ({item['size_mb']} MB)")
    else:
        lines.append("- لا توجد ملفات أوزان/نقاط تفتيش ضمن شجرة العمل الحالية.")

    lines.extend(["", "## 3. ملفات البيانات المكتشفة (قراءة فقط)"])
    if dataset_files:
        for item in dataset_files:
            lines.append(f"- `{item['path']}` ({item['size_mb']} MB)")
    else:
        lines.append("- لا توجد ملفات بيانات مطابقة ضمن شجرة العمل الحالية.")

    lines.extend(["", "## 4. مواضع الاستدعاء والإشارات في الكود"])
    if code_refs:
        for ref in plan["code_references"]:
            lines.append(f"- `{ref['file']}` -> يشير إلى `{ref['reference']}`")
    else:
        lines.append("- لم تُسجل إشارات مباشرة.")

    lines.extend([
        "",
        "## 5. توصيات الاستضافة والفصل",
        "- استضافة `backend` (Node.js/TypeScript) على Render مع قاعدة بيانات خارجية (مثل Supabase Postgres) وضبط `DATABASE_URL` عبر متغيرات البيئة فقط.",
        "- فصل النماذج الكبيرة في `Lazaynova1-models` عبر Git LFS وتجنب تشغيل نماذج ثقيلة بشكل دائم على خطط الويب المجانية.",
        "- إنشاء مستودع `Lazaynova1-datasets` على GitHub قبل أي عملية نقل للبيانات بعد التأكد من مسارات الاستدعاء.",
        "",
        "```json",
        json.dumps(plan, ensure_ascii=False, indent=2),
        "```",
    ])
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"PLAN_GENERATED: models={len(model_files)} datasets={len(dataset_files)} refs={len(code_refs)}")


if __name__ == "__main__":
    main()
