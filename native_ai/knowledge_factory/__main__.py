"""LAZAYNOVA Knowledge Factory - native source ingestion."""

import argparse
import csv
import hashlib
import json
import re
import uuid

from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "knowledge_sources" / "inbox"
RUNS_DIR = ROOT / "native_ai" / "knowledge_factory" / "runs"

SUPPORTED = {
    ".txt", ".md", ".html", ".htm",
    ".json", ".jsonl", ".csv",
}

MAX_FILE_BYTES = 20 * 1024 * 1024
CHUNK_SIZE = 1800
CHUNK_OVERLAP = 200


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.hidden_depth += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.hidden_depth = max(0, self.hidden_depth - 1)

    def handle_data(self, data):
        if not self.hidden_depth and data.strip():
            self.parts.append(data.strip())


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def extract_json_strings(value):
    """Extract textual values without inventing new information."""
    output = []

    if isinstance(value, str):
        if value.strip():
            output.append(value.strip())

    elif isinstance(value, list):
        for item in value:
            output.extend(extract_json_strings(item))

    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (str, list, dict)):
                output.extend(extract_json_strings(item))

    return "\n".join(output)


def extract_text(path, raw):
    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        return raw.decode("utf-8-sig", errors="strict")

    if suffix in (".html", ".htm"):
        parser = TextExtractor()
        parser.feed(raw.decode("utf-8-sig", errors="strict"))
        return "\n".join(parser.parts)

    if suffix == ".json":
        return extract_json_strings(
            json.loads(raw.decode("utf-8-sig"))
        )

    if suffix == ".jsonl":
        parts = []
        for line_number, line in enumerate(
            raw.decode("utf-8-sig").splitlines(), 1
        ):
            if not line.strip():
                continue
            try:
                parts.append(
                    extract_json_strings(json.loads(line))
                )
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL line {line_number}: {exc}"
                ) from exc
        return "\n".join(parts)

    if suffix == ".csv":
        text = raw.decode("utf-8-sig", errors="strict")
        rows = csv.reader(text.splitlines())
        return "\n".join(
            " | ".join(cell.strip() for cell in row if cell.strip())
            for row in rows
        )

    raise ValueError(f"Unsupported file type: {suffix}")


def normalize_text(text):
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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


def split_chunks(text):
    """Split text while preserving paragraph boundaries when possible."""
    paragraphs = [
        part.strip()
        for part in re.split(r"\n\s*\n", text)
        if part.strip()
    ]

    chunks = []
    current = ""

    for paragraph in paragraphs:
        while len(paragraph) > CHUNK_SIZE:
            if current:
                chunks.append(current)
                current = ""

            chunks.append(paragraph[:CHUNK_SIZE])
            paragraph = paragraph[
                CHUNK_SIZE - CHUNK_OVERLAP:
            ]

        candidate = (
            current + "\n\n" + paragraph
            if current else paragraph
        )

        if len(candidate) <= CHUNK_SIZE:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = paragraph

    if current:
        chunks.append(current)

    return [item.strip() for item in chunks if item.strip()]


def discover_sources():
    if not SOURCE_DIR.is_dir():
        return []

    files = []

    for path in SOURCE_DIR.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        if path.suffix.lower() in SUPPORTED:
            files.append(path)

    return sorted(files)


def build_records(files):
    records = []
    errors = []
    source_manifest = []

    for path in files:
        relative = path.relative_to(SOURCE_DIR).as_posix()

        try:
            size = path.stat().st_size

            if size == 0:
                raise ValueError("Empty source file")

            if size > MAX_FILE_BYTES:
                raise ValueError(
                    f"File exceeds {MAX_FILE_BYTES} bytes"
                )

            raw = path.read_bytes()
            digest = sha256_bytes(raw)
            text = normalize_text(extract_text(path, raw))

            if not text:
                raise ValueError("No extractable text")

            chunks = split_chunks(text)

            source_manifest.append({
                "source": relative,
                "sha256": digest,
                "bytes": size,
                "chunks": len(chunks),
                "language": detect_language(text),
                "status": "processed",
            })

            for index, chunk in enumerate(chunks):
                records.append({
                    "record_id": sha256_bytes(
                        f"{digest}:{index}".encode("utf-8")
                    ),
                    "source": relative,
                    "source_sha256": digest,
                    "chunk_index": index,
                    "language": detect_language(chunk),
                    "text": chunk,
                })

        except Exception as exc:
            errors.append({
                "source": relative,
                "error": str(exc),
            })

            source_manifest.append({
                "source": relative,
                "status": "failed",
                "error": str(exc),
            })

    return records, source_manifest, errors


def write_jsonl(path, records):
    temporary = path.with_suffix(path.suffix + ".tmp")

    with temporary.open("x", encoding="utf-8") as handle:
        for record in records:
            handle.write(
                json.dumps(record, ensure_ascii=False) + "\n"
            )

    temporary.replace(path)


def write_json(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")

    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(
        description="LAZAYNOVA native knowledge ingestion"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process sources without writing output files",
    )
    args = parser.parse_args()

    files = discover_sources()

    print("LAZAYNOVA KNOWLEDGE FACTORY")
    print("SOURCE DIRECTORY:", SOURCE_DIR)
    print("SUPPORTED FILES:", len(files))

    if not files:
        print("NO SOURCES FOUND.")
        print("Add TXT, MD, HTML, JSON, JSONL or CSV files.")
        return

    records, sources, errors = build_records(files)

    print("PROCESSED SOURCES:",
          sum(s.get("status") == "processed" for s in sources))
    print("FAILED SOURCES:", len(errors))
    print("KNOWLEDGE CHUNKS:", len(records))

    if args.dry_run:
        print("DRY RUN PASSED — no output files created.")
        return

    if not records:
        raise RuntimeError(
            "No valid knowledge records. Nothing was published."
        )

    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:8]
    )

    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(exist_ok=False)

    manifest = {
        "factory": "LAZAYNOVA Knowledge Factory",
        "version": "0.1.0",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_count": len(files),
        "successful_sources": len(records) > 0 and
            sum(s.get("status") == "processed" for s in sources),
        "failed_sources": len(errors),
        "chunk_count": len(records),
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "sources": sources,
        "errors": errors,
    }

    write_jsonl(run_dir / "knowledge_chunks.jsonl", records)
    write_json(run_dir / "manifest.json", manifest)

    print("OUTPUT:", run_dir.relative_to(ROOT))
    print("CHUNKS FILE: knowledge_chunks.jsonl")
    print("MANIFEST: manifest.json")
    print("IMPORT COMPLETE.")


if __name__ == "__main__":
    main()
