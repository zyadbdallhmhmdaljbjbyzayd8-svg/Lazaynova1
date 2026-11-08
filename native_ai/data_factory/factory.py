#!/usr/bin/env python3
"""LAZAYNOVA Data Factory — read-only JSONL validator."""

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

REQUIRED = ("instruction", "response", "language")
PROVENANCE = ("source", "source_url", "license", "license_url")


def normalize(value):
    value = unicodedata.normalize("NFKC", value)
    return " ".join(value.casefold().split())


def valid_https_url(value):
    try:
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.netloc)
    except ValueError:
        return False


def validate(path, require_provenance=False):
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")

    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()

    try:
        content = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Invalid UTF-8 at byte {exc.start}") from exc

    prompts = set()
    pairs = set()
    ids = set()
    errors = []
    warnings = []
    languages = {"ar": 0, "en": 0}
    valid_records = 0
    provenance_complete = 0

    for line_no, line in enumerate(content.splitlines(), 1):
        if not line.strip():
            warnings.append(f"Line {line_no}: blank line")
            continue

        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"Line {line_no}: invalid JSON: {exc.msg}")
            continue

        if not isinstance(row, dict):
            errors.append(f"Line {line_no}: record must be a JSON object")
            continue

        missing = [key for key in REQUIRED if key not in row]
        if missing:
            errors.append(
                f"Line {line_no}: missing fields: {', '.join(missing)}"
            )
            continue

        instruction = row["instruction"]
        response = row["response"]
        language = row["language"]

        if not isinstance(instruction, str) or not instruction.strip():
            errors.append(f"Line {line_no}: instruction must be non-empty text")
            continue

        if not isinstance(response, str) or not response.strip():
            errors.append(f"Line {line_no}: response must be non-empty text")
            continue

        if not isinstance(language, str) or language not in languages:
            errors.append(f"Line {line_no}: language must be 'ar' or 'en'")
            continue

        prompt_key = normalize(instruction)
        pair_key = (prompt_key, normalize(response))

        if prompt_key in prompts:
            errors.append(f"Line {line_no}: duplicate normalized instruction")
            continue

        if pair_key in pairs:
            errors.append(f"Line {line_no}: duplicate instruction-response pair")
            continue

        record_id = row.get("id")
        if record_id is not None:
            if not isinstance(record_id, str) or not record_id.strip():
                errors.append(f"Line {line_no}: id must be non-empty text")
                continue
            if record_id in ids:
                errors.append(f"Line {line_no}: duplicate id: {record_id}")
                continue
            ids.add(record_id)

        prompts.add(prompt_key)
        pairs.add(pair_key)
        languages[language] += 1
        valid_records += 1

        provenance_missing = [
            key for key in PROVENANCE
            if not isinstance(row.get(key), str) or not row[key].strip()
        ]

        if provenance_missing:
            warnings.append(
                f"Line {line_no}: provenance incomplete "
                f"({', '.join(provenance_missing)})"
            )
        else:
            if not valid_https_url(row["source_url"]):
                errors.append(f"Line {line_no}: source_url must use HTTPS")
            elif not valid_https_url(row["license_url"]):
                errors.append(f"Line {line_no}: license_url must use HTTPS")
            else:
                provenance_complete += 1

    if valid_records == 0:
        errors.append("Dataset contains no valid records")

    print("LAZAYNOVA DATA FACTORY — VALIDATION REPORT")
    print("FILE:", path)
    print("SHA256:", digest)
    print("VALID RECORDS:", valid_records)
    print("LANGUAGES:", json.dumps(languages, ensure_ascii=False))
    print("UNIQUE PROMPTS:", len(prompts))
    print("PROVENANCE COMPLETE:", provenance_complete)
    print("WARNINGS:", len(warnings))
    print("ERRORS:", len(errors))

    for item in warnings[:30]:
        print("WARNING:", item)

    for item in errors[:30]:
        print("ERROR:", item)

    if len(warnings) > 30 or len(errors) > 30:
        print("NOTE: report display limited to first 30 items per category")

    if errors:
        return 1

    if require_provenance and provenance_complete != valid_records:
        print("RESULT: REJECTED — complete provenance is required")
        return 2

    if provenance_complete != valid_records:
        print("RESULT: STRUCTURALLY VALID — NOT SOURCE-VERIFIED")
    else:
        print("RESULT: STRUCTURALLY VALID — PROVENANCE FIELDS PRESENT")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Read-only validator for LAZAYNOVA JSONL datasets"
    )
    parser.add_argument("file", help="JSONL dataset path")
    parser.add_argument(
        "--require-provenance",
        action="store_true",
        help="fail unless every record has source and license metadata",
    )
    args = parser.parse_args()

    try:
        result = validate(args.file, args.require_provenance)
    except (OSError, ValueError) as exc:
        print("FATAL:", exc, file=sys.stderr)
        result = 1

    raise SystemExit(result)


if __name__ == "__main__":
    main()
