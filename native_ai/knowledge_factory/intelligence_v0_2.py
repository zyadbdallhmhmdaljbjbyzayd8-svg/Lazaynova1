"""Scalable, source-grounded knowledge extraction for LAZAYNOVA."""

import argparse
import hashlib
import json
import re
import sqlite3

from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "native_ai/knowledge_factory/runs"


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize(value):
    return re.sub(r"\s+", " ", value).strip()


def detect_language(text):
    ar = len(re.findall(r"[\u0600-\u06ff]", text))
    en = len(re.findall(r"[A-Za-z]", text))
    if ar and en:
        return "mixed"
    if ar:
        return "ar"
    if en:
        return "en"
    return "unknown"


def split_sentences(text):
    # Markdown headings are structure, not factual statements.
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or re.match(r"^#{1,6}\s+", stripped):
            continue
        if stripped.startswith("```"):
            continue
        lines.append(stripped)

    body = "\n".join(lines)
    parts = re.split(r"(?<=[.!?؟。])\s+|\n+", body)

    result = []
    for part in parts:
        part = normalize(part)
        part = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", part)
        if len(part) >= 25:
            result.append(part)
    return result


def extract_definition(sentence):
    patterns = [
        (r"^(.{2,100}?)\s+(?:هو|هي)\s+(.+)$", "ar"),
        (r"^(.{2,100}?)\s+(?:is|are|means|refers to)\s+(.+)$", "en"),
    ]

    for pattern, language in patterns:
        match = re.match(pattern, sentence, re.IGNORECASE)
        if match:
            subject = normalize(match.group(1)).strip(" :،,")
            if subject and len(subject) <= 100:
                return subject, language
    return None


def extract_fenced_code(text):
    pattern = r"```([A-Za-z0-9_+#.-]*)\s*\n(.*?)```"
    for match in re.finditer(pattern, text, re.DOTALL):
        language = match.group(1).lower() or "unknown"
        code = match.group(2).strip()
        if code:
            yield language, code


def extract_code_symbols(code, language="unknown"):
    """Conservative symbol extraction; does not execute source code."""
    patterns = [
        ("function", r"(?m)^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"),
        ("class", r"(?m)^\s*(?:export\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)"),
        ("interface", r"(?m)^\s*(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)"),
        ("type", r"(?m)^\s*(?:export\s+)?type\s+([A-Za-z_$][\w$]*)\s*="),
        ("python_function", r"(?m)^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\("),
        ("python_class", r"(?m)^\s*class\s+([A-Za-z_]\w*)\b"),
        ("kotlin_function", r"(?m)^\s*(?:public\s+|private\s+|internal\s+|override\s+)*fun\s+([A-Za-z_]\w*)\s*\("),
        ("declaration", r"(?m)^\s*(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*="),
    ]

    seen = set()
    lines = code.splitlines()

    for kind, pattern in patterns:
        for match in re.finditer(pattern, code):
            name = match.group(1)
            line_no = code.count("\n", 0, match.start()) + 1
            start = max(0, line_no - 2)
            end = min(len(lines), line_no + 7)
            snippet = "\n".join(lines[start:end]).strip()
            key = (kind, name, digest(snippet))

            if key in seen:
                continue
            seen.add(key)

            yield {
                "symbol_type": kind,
                "symbol_name": name,
                "language": language,
                "snippet": snippet,
                "line_start": line_no,
            }


def load_chunks(run_dir):
    path = run_dir / "knowledge_chunks.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"Missing chunks file: {path}")

    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                raise ValueError(f"Blank input line: {line_number}")

            item = json.loads(line)
            required = {
                "record_id", "source", "source_sha256",
                "chunk_index", "text",
            }
            if not required.issubset(item):
                raise ValueError(f"Invalid chunk schema at line {line_number}")
            if not isinstance(item["text"], str) or not item["text"].strip():
                raise ValueError(f"Empty chunk at line {line_number}")
            yield item


def add_record(db, kind, record):
    """Deduplicate by content while retaining every observed source reference."""
    record_id = record["id"]
    content_hash = record["content_hash"]
    source_ref = {
        "source": record["source"],
        "source_sha256": record["source_sha256"],
        "source_chunk_id": record["source_chunk_id"],
        "chunk_index": record["chunk_index"],
    }

    row = db.execute(
        "SELECT payload FROM records WHERE kind=? AND content_hash=?",
        (kind, content_hash),
    ).fetchone()

    if row:
        payload = json.loads(row[0])
        if source_ref not in payload["source_refs"]:
            payload["source_refs"].append(source_ref)
        payload["duplicate_occurrences"] += 1
        db.execute(
            "UPDATE records SET payload=? WHERE kind=? AND content_hash=?",
            (json.dumps(payload, ensure_ascii=False), kind, content_hash),
        )
        return False

    record["source_refs"] = [source_ref]
    record["duplicate_occurrences"] = 0
    db.execute(
        "INSERT INTO records(kind, content_hash, record_id, payload) VALUES(?,?,?,?)",
        (
            kind,
            content_hash,
            record_id,
            json.dumps(record, ensure_ascii=False),
        ),
    )
    return True


def export_jsonl(db, kind, path):
    with path.open("x", encoding="utf-8") as handle:
        cursor = db.execute(
            "SELECT payload FROM records WHERE kind=? ORDER BY record_id",
            (kind,),
        )
        for (payload,) in cursor:
            handle.write(payload + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="LAZAYNOVA Knowledge Intelligence V0.2"
    )
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    run_dir = (RUNS_DIR / args.run_id).resolve()
    if not run_dir.is_relative_to(RUNS_DIR.resolve()):
        raise ValueError("Run ID must refer to a directory inside runs/")
    if not (run_dir / "knowledge_chunks.jsonl").is_file():
        raise FileNotFoundError("Import run does not contain knowledge_chunks.jsonl")

    output_dir = run_dir / "intelligence_v0_2_retry1"
    output_dir.mkdir(exist_ok=False)

    db_path = output_dir / "dedup_index.sqlite3"
    db = sqlite3.connect(db_path)
    db.execute("""
        CREATE TABLE records (
            kind TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            record_id TEXT NOT NULL,
            payload TEXT NOT NULL,
            PRIMARY KEY(kind, content_hash)
        )
    """)

    counters = {
        "input_chunks": 0,
        "sentences_seen": 0,
        "knowledge_units_added": 0,
        "code_symbols_added": 0,
        "definition_questions_added": 0,
    }

    try:
        for chunk in load_chunks(run_dir):
            counters["input_chunks"] += 1
            text = chunk["text"]

            for sentence in split_sentences(text):
                counters["sentences_seen"] += 1
                content_hash = digest(normalize(sentence).casefold())

                fact = {
                    "id": digest("fact:" + content_hash),
                    "content_hash": content_hash,
                    "type": "source_sentence",
                    "text": sentence,
                    "language": detect_language(sentence),
                    "source": chunk["source"],
                    "source_sha256": chunk["source_sha256"],
                    "source_chunk_id": chunk["record_id"],
                    "chunk_index": chunk["chunk_index"],
                    "evidence": sentence,
                }

                if add_record(db, "knowledge", fact):
                    counters["knowledge_units_added"] += 1

                definition = extract_definition(sentence)
                if definition:
                    subject, language = definition
                    question = (
                        f"ما هو {subject}؟"
                        if language == "ar"
                        else f"What is {subject}?"
                    )
                    qhash = digest(question.casefold() + "|" + content_hash)

                    qa = {
                        "id": qhash,
                        "content_hash": qhash,
                        "type": "definition_qa",
                        "instruction": question,
                        "response": sentence,
                        "language": language,
                        "source": chunk["source"],
                        "source_sha256": chunk["source_sha256"],
                        "source_chunk_id": chunk["record_id"],
                        "chunk_index": chunk["chunk_index"],
                        "evidence": sentence,
                        "verified_by_model": False,
                    }
                    if add_record(db, "questions", qa):
                        counters["definition_questions_added"] += 1

            for language, code in extract_fenced_code(text):
                for symbol in extract_code_symbols(code, language):
                    snippet = symbol["snippet"]
                    content_hash = digest(
                        symbol["symbol_type"] + "|" + symbol["symbol_name"]
                        + "|" + normalize(snippet)
                    )
                    record = {
                        "id": digest("code:" + content_hash),
                        "content_hash": content_hash,
                        "type": "code_symbol",
                        **symbol,
                        "source": chunk["source"],
                        "source_sha256": chunk["source_sha256"],
                        "source_chunk_id": chunk["record_id"],
                        "chunk_index": chunk["chunk_index"],
                        "evidence": snippet,
                    }
                    if add_record(db, "code", record):
                        counters["code_symbols_added"] += 1

            db.commit()

        export_jsonl(db, "knowledge", output_dir / "knowledge_units.jsonl")
        export_jsonl(db, "questions", output_dir / "question_bank.jsonl")
        export_jsonl(db, "code", output_dir / "code_symbols.jsonl")

        totals = {
            "knowledge_units": db.execute(
                "SELECT COUNT(*) FROM records WHERE kind='knowledge'"
            ).fetchone()[0],
            "definition_questions": db.execute(
                "SELECT COUNT(*) FROM records WHERE kind='questions'"
            ).fetchone()[0],
            "code_symbols": db.execute(
                "SELECT COUNT(*) FROM records WHERE kind='code'"
            ).fetchone()[0],
        }

        report = {
            "engine": "LAZAYNOVA Knowledge Intelligence",
            "version": "0.2.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "import_run": run_dir.name,
            **counters,
            **totals,
            "deduplication": "sqlite_content_hash",
            "source_references_preserved": True,
            "external_ai_apis_used": False,
            "external_model_weights_used": False,
            "model_training_performed": False,
            "source_data_modified": False,
            "outputs": [
                "knowledge_units.jsonl",
                "question_bank.jsonl",
                "code_symbols.jsonl",
                "dedup_index.sqlite3",
            ],
        }

        with (output_dir / "report.json").open("x", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

        print("KNOWLEDGE INTELLIGENCE V0.2: PASS")
        print("INPUT CHUNKS:", counters["input_chunks"])
        print("KNOWLEDGE UNITS:", totals["knowledge_units"])
        print("DEFINITION QUESTIONS:", totals["definition_questions"])
        print("CODE SYMBOLS:", totals["code_symbols"])
        print("OUTPUT:", output_dir.relative_to(ROOT))
        print("TRAINING: NOT RUN")
        print("SOURCE DATA MODIFIED: NO")

    finally:
        db.close()


if __name__ == "__main__":
    main()
