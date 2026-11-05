"""Integrity checks for local model artifacts; invalid GGUF files are skipped."""
import hashlib
import json
import os

GGUF_MAGIC = b"GGUF"
MIN_GGUF_SIZE = 1024

def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def inspect_gguf(path, expected_sha256=None):
    result = {"path":str(path),"status":"UNVERIFIED","format":None,
              "size_bytes":None,"sha256":None,"reason":None}
    if not os.path.isfile(path):
        result["reason"] = "FILE_NOT_FOUND"
        return result
    try:
        size = os.path.getsize(path)
        result["size_bytes"] = size
        with open(path, "rb") as stream:
            header = stream.read(64).lstrip().lower()
        result["sha256"] = sha256_file(path)
        if header.startswith((b"<!doctype", b"<html", b"<?xml")):
            result.update(format="HTML_ERROR", reason="NON_MODEL_DOCUMENT")
        elif size < MIN_GGUF_SIZE:
            result.update(format="INVALID_SIZE", reason="FILE_TOO_SMALL")
        elif header[:4] != GGUF_MAGIC:
            result.update(format="INVALID_HEADER", reason="GGUF_MAGIC_MISMATCH")
        elif expected_sha256 and result["sha256"].lower() != expected_sha256.lower():
            result.update(format="GGUF", reason="SHA256_MISMATCH")
        else:
            result.update(status="VERIFIED_FORMAT", format="GGUF", reason=None)
    except OSError as exc:
        result["reason"] = type(exc).__name__
    return result

def valid_gguf(path, expected_sha256=None):
    return inspect_gguf(path, expected_sha256)["status"] == "VERIFIED_FORMAT"

def write_registry(path, entries):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as stream:
        json.dump(entries, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)
