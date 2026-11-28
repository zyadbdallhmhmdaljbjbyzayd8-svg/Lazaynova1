# خطة فحص فصل النماذج والبيانات وجاهزية الاستضافة السحابية (LAZAYNOVA)

## 1. المستودعات المستهدفة
- الكود الرئيسي: `zyadbdallhmhmdaljbjbyzayd8-svg/Lazaynova1`
- النماذج (LFS): `zyadbdallhmhmdaljbjbyzayd8-svg/Lazaynova1-models`
- البيانات: `zyadbdallhmhmdaljbjbyzayd8-svg/Lazaynova1-datasets`

## 2. ملفات النماذج المكتشفة (قراءة فقط)
- `native_ai/models/qwen2.5-1.5b-q4.gguf` (0.17 MB)
- `native_ai/models/l3_checkpoint.pt` (3.64 MB)
- `native_ai/checkpoints/l3_checkpoint_v2.pt` (1.21 MB)
- `native_ai/checkpoints/l3_checkpoint_v3.pt` (1.22 MB)

## 3. ملفات البيانات المكتشفة (قراءة فقط)
- `native_ai/datasets/sample_ar.jsonl` (0.0 MB)
- `native_ai/datasets/sample_ar_v2.jsonl` (0.08 MB)
- `native_ai/datasets/sample_ar_v3.jsonl` (0.03 MB)
- `native_ai/knowledge_factory/code_runs/20261106T191942Z-353164b0/code_entities.jsonl` (0.67 MB)
- `native_ai/knowledge_factory/code_runs/20261106T191942Z-353164b0/code_relations.jsonl` (1.68 MB)
- `native_ai/knowledge_factory/code_runs/20261106T191942Z-353164b0/code_dependencies.jsonl` (0.16 MB)
- `native_ai/knowledge_factory/code_runs/20261106T191942Z-353164b0/parse_errors.jsonl` (0.0 MB)
- `native_ai/knowledge_factory/runs/20261106T175444Z-33696644/knowledge_chunks.jsonl` (0.0 MB)
- `native_ai/knowledge_factory/runs/20261106T175444Z-33696644/intelligence_v0_1/knowledge_units.jsonl` (0.0 MB)
- `native_ai/knowledge_factory/runs/20261106T175444Z-33696644/intelligence_v0_1/question_bank.jsonl` (0.0 MB)
- `native_ai/knowledge_factory/runs/20261106T175444Z-33696644/intelligence_v0_2_retry1/knowledge_units.jsonl` (0.0 MB)
- `native_ai/knowledge_factory/runs/20261106T175444Z-33696644/intelligence_v0_2_retry1/question_bank.jsonl` (0.0 MB)
- `native_ai/knowledge_factory/runs/20261106T175444Z-33696644/intelligence_v0_2_retry1/code_symbols.jsonl` (0.0 MB)

## 4. مواضع الاستدعاء والإشارات في الكود
- `tests/test_phase1_2.py` -> يشير إلى `.jsonl`
- `tests/test_native_l3.py` -> يشير إلى `gguf`
- `tests/test_native_pretraining.py` -> يشير إلى `.jsonl`
- `tests/test_lzcore.py` -> يشير إلى `.jsonl`
- `inference/generate.py` -> يشير إلى `.jsonl`
- `scripts/prepare_split_plan.py` -> يشير إلى `checkpoints`
- `scripts/prepare_split_plan.py` -> يشير إلى `l3_checkpoint`
- `scripts/prepare_split_plan.py` -> يشير إلى `qwen2.5`
- `scripts/prepare_split_plan.py` -> يشير إلى `gguf`
- `scripts/prepare_split_plan.py` -> يشير إلى `.jsonl`
- `scripts/prepare_split_plan.py` -> يشير إلى `Lazaynova1-models`
- `scripts/prepare_split_plan.py` -> يشير إلى `Lazaynova1-datasets`
- `model/lzcore/train_lib.py` -> يشير إلى `.jsonl`
- `lz_core/ai_gateway/gateway.py` -> يشير إلى `checkpoints`
- `lz_core/ai_gateway/gateway.py` -> يشير إلى `l3_checkpoint`
- `native_ai/datasets/build_v3_dataset.py` -> يشير إلى `.jsonl`
- `native_ai/training/train_l3.py` -> يشير إلى `checkpoints`
- `native_ai/training/train_l3.py` -> يشير إلى `l3_checkpoint`
- `native_ai/training/train_l3.py` -> يشير إلى `.jsonl`
- `native_ai/training/train_l3_v3.py` -> يشير إلى `checkpoints`
- `native_ai/training/train_l3_v3.py` -> يشير إلى `l3_checkpoint`
- `native_ai/training/train_l3_v3.py` -> يشير إلى `.jsonl`
- `native_ai/training/train_l3_v4.py` -> يشير إلى `checkpoints`
- `native_ai/training/train_l3_v4.py` -> يشير إلى `l3_checkpoint`
- `native_ai/training/train_l3_v4.py` -> يشير إلى `.jsonl`
- `native_ai/training/native_pretraining.py` -> يشير إلى `checkpoints`
- `native_ai/registry/model_registry.py` -> يشير إلى `gguf`
- `native_ai/knowledge_factory/__main__.py` -> يشير إلى `.jsonl`
- `native_ai/knowledge_factory/intelligence.py` -> يشير إلى `checkpoints`
- `native_ai/knowledge_factory/intelligence.py` -> يشير إلى `.jsonl`
- `native_ai/knowledge_factory/intelligence_v0_2.py` -> يشير إلى `.jsonl`
- `native_ai/knowledge_factory/code_intelligence.py` -> يشير إلى `.jsonl`

## 5. توصيات الاستضافة والفصل
- استضافة `backend` (Node.js/TypeScript) على Render مع قاعدة بيانات خارجية (مثل Supabase Postgres) وضبط `DATABASE_URL` عبر متغيرات البيئة فقط.
- فصل النماذج الكبيرة في `Lazaynova1-models` عبر Git LFS وتجنب تشغيل نماذج ثقيلة بشكل دائم على خطط الويب المجانية.
- إنشاء مستودع `Lazaynova1-datasets` على GitHub قبل أي عملية نقل للبيانات بعد التأكد من مسارات الاستدعاء.

```json
{
  "target_repos": {
    "main_code": "zyadbdallhmhmdaljbjbyzayd8-svg/Lazaynova1",
    "models_lfs": "zyadbdallhmhmdaljbjbyzayd8-svg/Lazaynova1-models",
    "datasets": "zyadbdallhmhmdaljbjbyzayd8-svg/Lazaynova1-datasets"
  },
  "model_files_found": [
    {
      "path": "native_ai/models/qwen2.5-1.5b-q4.gguf",
      "size_mb": 0.17
    },
    {
      "path": "native_ai/models/l3_checkpoint.pt",
      "size_mb": 3.64
    },
    {
      "path": "native_ai/checkpoints/l3_checkpoint_v2.pt",
      "size_mb": 1.21
    },
    {
      "path": "native_ai/checkpoints/l3_checkpoint_v3.pt",
      "size_mb": 1.22
    }
  ],
  "dataset_files_found": [
    {
      "path": "native_ai/datasets/sample_ar.jsonl",
      "size_mb": 0.0
    },
    {
      "path": "native_ai/datasets/sample_ar_v2.jsonl",
      "size_mb": 0.08
    },
    {
      "path": "native_ai/datasets/sample_ar_v3.jsonl",
      "size_mb": 0.03
    },
    {
      "path": "native_ai/knowledge_factory/code_runs/20261106T191942Z-353164b0/code_entities.jsonl",
      "size_mb": 0.67
    },
    {
      "path": "native_ai/knowledge_factory/code_runs/20261106T191942Z-353164b0/code_relations.jsonl",
      "size_mb": 1.68
    },
    {
      "path": "native_ai/knowledge_factory/code_runs/20261106T191942Z-353164b0/code_dependencies.jsonl",
      "size_mb": 0.16
    },
    {
      "path": "native_ai/knowledge_factory/code_runs/20261106T191942Z-353164b0/parse_errors.jsonl",
      "size_mb": 0.0
    },
    {
      "path": "native_ai/knowledge_factory/runs/20261106T175444Z-33696644/knowledge_chunks.jsonl",
      "size_mb": 0.0
    },
    {
      "path": "native_ai/knowledge_factory/runs/20261106T175444Z-33696644/intelligence_v0_1/knowledge_units.jsonl",
      "size_mb": 0.0
    },
    {
      "path": "native_ai/knowledge_factory/runs/20261106T175444Z-33696644/intelligence_v0_1/question_bank.jsonl",
      "size_mb": 0.0
    },
    {
      "path": "native_ai/knowledge_factory/runs/20261106T175444Z-33696644/intelligence_v0_2_retry1/knowledge_units.jsonl",
      "size_mb": 0.0
    },
    {
      "path": "native_ai/knowledge_factory/runs/20261106T175444Z-33696644/intelligence_v0_2_retry1/question_bank.jsonl",
      "size_mb": 0.0
    },
    {
      "path": "native_ai/knowledge_factory/runs/20261106T175444Z-33696644/intelligence_v0_2_retry1/code_symbols.jsonl",
      "size_mb": 0.0
    }
  ],
  "code_references_count": 32,
  "code_references": [
    {
      "file": "tests/test_phase1_2.py",
      "reference": ".jsonl"
    },
    {
      "file": "tests/test_native_l3.py",
      "reference": "gguf"
    },
    {
      "file": "tests/test_native_pretraining.py",
      "reference": ".jsonl"
    },
    {
      "file": "tests/test_lzcore.py",
      "reference": ".jsonl"
    },
    {
      "file": "inference/generate.py",
      "reference": ".jsonl"
    },
    {
      "file": "scripts/prepare_split_plan.py",
      "reference": "checkpoints"
    },
    {
      "file": "scripts/prepare_split_plan.py",
      "reference": "l3_checkpoint"
    },
    {
      "file": "scripts/prepare_split_plan.py",
      "reference": "qwen2.5"
    },
    {
      "file": "scripts/prepare_split_plan.py",
      "reference": "gguf"
    },
    {
      "file": "scripts/prepare_split_plan.py",
      "reference": ".jsonl"
    },
    {
      "file": "scripts/prepare_split_plan.py",
      "reference": "Lazaynova1-models"
    },
    {
      "file": "scripts/prepare_split_plan.py",
      "reference": "Lazaynova1-datasets"
    },
    {
      "file": "model/lzcore/train_lib.py",
      "reference": ".jsonl"
    },
    {
      "file": "lz_core/ai_gateway/gateway.py",
      "reference": "checkpoints"
    },
    {
      "file": "lz_core/ai_gateway/gateway.py",
      "reference": "l3_checkpoint"
    },
    {
      "file": "native_ai/datasets/build_v3_dataset.py",
      "reference": ".jsonl"
    },
    {
      "file": "native_ai/training/train_l3.py",
      "reference": "checkpoints"
    },
    {
      "file": "native_ai/training/train_l3.py",
      "reference": "l3_checkpoint"
    },
    {
      "file": "native_ai/training/train_l3.py",
      "reference": ".jsonl"
    },
    {
      "file": "native_ai/training/train_l3_v3.py",
      "reference": "checkpoints"
    },
    {
      "file": "native_ai/training/train_l3_v3.py",
      "reference": "l3_checkpoint"
    },
    {
      "file": "native_ai/training/train_l3_v3.py",
      "reference": ".jsonl"
    },
    {
      "file": "native_ai/training/train_l3_v4.py",
      "reference": "checkpoints"
    },
    {
      "file": "native_ai/training/train_l3_v4.py",
      "reference": "l3_checkpoint"
    },
    {
      "file": "native_ai/training/train_l3_v4.py",
      "reference": ".jsonl"
    },
    {
      "file": "native_ai/training/native_pretraining.py",
      "reference": "checkpoints"
    },
    {
      "file": "native_ai/registry/model_registry.py",
      "reference": "gguf"
    },
    {
      "file": "native_ai/knowledge_factory/__main__.py",
      "reference": ".jsonl"
    },
    {
      "file": "native_ai/knowledge_factory/intelligence.py",
      "reference": "checkpoints"
    },
    {
      "file": "native_ai/knowledge_factory/intelligence.py",
      "reference": ".jsonl"
    },
    {
      "file": "native_ai/knowledge_factory/intelligence_v0_2.py",
      "reference": ".jsonl"
    },
    {
      "file": "native_ai/knowledge_factory/code_intelligence.py",
      "reference": ".jsonl"
    }
  ],
  "notes": [
    "Do not move or delete checkpoints or large model weights without verifying all code path references.",
    "Keep heavy LLM/checkpoint inference out of free-tier web API dynos; isolate inference services and use external Postgres (e.g., Supabase)."
  ]
}
```
