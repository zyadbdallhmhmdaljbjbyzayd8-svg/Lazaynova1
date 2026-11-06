"""LAZAYNOVA Knowledge Intelligence Engine V0.1.

Extracts source-grounded facts and conservative definition questions.
Never modifies source imports, datasets, models, or checkpoints.
"""

import argparse
import hashlib
import json
import re

from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "native_ai/knowledge_factory/runs"


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def detect_language(text):
    arabic = len(re.findall(r"[\u0600-\u06ff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))

    if arabic and latin:
        return "mixed"
    if arabic:
        return "ar"
    if latin:
        return "en"
    return "unknown"


def split_sentences(text):
    parts = re.split(r"(?<=[.!?؟。])\s+|\n+", text)

    return [
        normalize(part.strip(" \t-*#"))
        for part in parts
        if len(normalize(part.strip(" \t-*#"))) >= 20
    ]


def extract_definition(sentence):
    """Return a subject only when a conservative definition pattern matches."""

    patterns = [
        (
            r"^(.{2,100}?)\s+(?:هو|هي|يعني|تعني)\s+(.+)$",
            "ar",
        ),
        (
            r"^(.{2,100}?)\s+(?:is|are|means|refers to)\s+(.+)$",
            "en",
        ),
    ]

    for pattern, language in patterns:
        match = re.match(pattern, sentence, flags=re.IGNORECASE)

        if match:
            subject = normalize(match.group(1)).strip(" :،,")
            if subject and len(subject) <= 100:
                return subject, language

    # Common Arabic definition structures without an explicit "هو/هي".
    arabic_patterns = [
        r"^(.{2,80}?)\s+(?:مجال|فرع|عملية|نظام|طريقة|بنية|نوع)\s+(.+)$",
    ]

    for pattern in arabic_patterns:
        match = re.match(pattern, sentence)
        if match:
            subject = normalize(match.group(1)).strip(" :،,")
            if subject:
                return subject, "ar"

    return None


def load_chunks(run_dir):
    path = run_dir / "knowledge_chunks.jsonl"

    if not path.is_file():
        raise FileNotFoundError(f"Missing source chunks: {path}")

    records = []

    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                raise ValueError(f"Blank JSONL line: {line_number}")

            item = json.loads(line)

            required = {
                "record_id",
                "source",
                "source_sha256",
                "chunk_index",
                "language",
                "text",
            }

            if not required.issubset(item):
                raise ValueError(
                    f"Invalid chunk schema at line {line_number}"
                )

            if not isinstance(item["text"], str) or not item["text"].strip():
                raise ValueError(f"Empty chunk at line {line_number}")

            records.append(item)

    return records


def build_knowledge(chunks):
    facts = []
    questions = []

    seen_facts = set()
    seen_questions = set()

    for chunk in chunks:
        sentences = split_sentences(chunk["text"])

        for sentence_index, sentence in enumerate(sentences):
            fingerprint = sha256_text(normalize(sentence).casefold())

            if fingerprint not in seen_facts:
                seen_facts.add(fingerprint)

                facts.append({
                    "fact_id": fingerprint,
                    "fact": sentence,
                    "language": detect_language(sentence),
                    "source": chunk["source"],
                    "source_sha256": chunk["source_sha256"],
                    "source_chunk_id": chunk["record_id"],
                    "chunk_index": chunk["chunk_index"],
                    "sentence_index": sentence_index,
                    "evidence": sentence,
                    "extraction_method": "source_sentence",
                })

            definition = extract_definition(sentence)

            if definition:
                subject, language = definition

                if language == "ar":
                    question = f"ما هو {subject}؟"
                else:
                    question = f"What is {subject}?"

                question_key = sha256_text(
                    normalize(question).casefold()
                    + "|"
                    + fingerprint
                )

                if question_key not in seen_questions:
                    seen_questions.add(question_key)

                    questions.append({
                        "question_id": question_key,
                        "instruction": question,
                        "response": sentence,
                        "language": language,
                        "source": chunk["source"],
                        "source_sha256": chunk["source_sha256"],
                        "source_chunk_id": chunk["record_id"],
                        "evidence": sentence,
                        "generation_method": "conservative_definition",
                        "verified_by_model": False,
                    })

    return facts, questions


def write_jsonl_exclusive(path, records):
    with path.open("x", encoding="utf-8") as handle:
        for record in records:
            handle.write(
                json.dumps(record, ensure_ascii=False) + "\n"
            )


def write_json_exclusive(path, data):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description="LAZAYNOVA Knowledge Intelligence Engine"
    )
    parser.add_argument(
        "--run-id",
        help="Import run ID; defaults to the latest import",
    )
    args = parser.parse_args()

    if args.run_id:
        run_dir = RUNS_DIR / args.run_id
    else:
        candidates = sorted(
            path for path in RUNS_DIR.iterdir()
            if path.is_dir()
            and (path / "knowledge_chunks.jsonl").is_file()
        ) if RUNS_DIR.is_dir() else []

        if not candidates:
            raise FileNotFoundError("No completed knowledge import found")

        run_dir = candidates[-1]

    run_dir = run_dir.resolve()

    if not run_dir.is_relative_to(RUNS_DIR.resolve()):
        raise ValueError("Import run must be inside the factory runs directory")

    chunks = load_chunks(run_dir)
    facts, questions = build_knowledge(chunks)

    output_dir = run_dir / "intelligence_v0_1"

    # Exclusive creation: never overwrite a previous intelligence run.
    output_dir.mkdir(exist_ok=False)

    write_jsonl_exclusive(output_dir / "knowledge_units.jsonl", facts)
    write_jsonl_exclusive(output_dir / "question_bank.jsonl", questions)

    report = {
        "engine": "LAZAYNOVA Knowledge Intelligence Engine",
        "version": "0.1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "import_run": run_dir.name,
        "input_chunks": len(chunks),
        "knowledge_units": len(facts),
        "definition_questions": len(questions),
        "unsupported_answers_generated": 0,
        "model_training_performed": False,
        "source_data_modified": False,
        "outputs": [
            "knowledge_units.jsonl",
            "question_bank.jsonl",
        ],
    }

    write_json_exclusive(output_dir / "report.json", report)

    print("LAZAYNOVA KNOWLEDGE INTELLIGENCE")
    print("IMPORT RUN:", run_dir.name)
    print("INPUT CHUNKS:", len(chunks))
    print("KNOWLEDGE UNITS:", len(facts))
    print("DEFINITION QUESTIONS:", len(questions))
    print("OUTPUT:", output_dir.relative_to(ROOT))
    print("MODEL TRAINING: NOT RUN")
    print("SOURCE DATA MODIFIED: NO")
    print("INTELLIGENCE BUILD: PASS")


if __name__ == "__main__":
    main()
