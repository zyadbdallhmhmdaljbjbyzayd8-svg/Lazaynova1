"""Strict source provenance and SHA-256 helpers for LZ-Core."""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from typing import Any
ALLOWED_LICENSES={"CC0-1.0","PD","MIT","Apache-2.0","CC-BY-4.0","CC-BY-SA-4.0","owner-original"}
_SHA=re.compile(r"^[0-9a-f]{64}$")
def sha256_file(path):
    p=Path(path)
    if not p.is_file(): raise ValueError(f"not a regular file: {p}")
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()
def validate_sha256(value,field="sha256"):
    if not isinstance(value,str) or not _SHA.fullmatch(value): raise ValueError(f"{field} must be lowercase 64-character SHA-256")
    return value
def _required(value,field):
    if not isinstance(value,str) or not value.strip(): raise ValueError(f"{field} must be non-empty")
    return value.strip()
def build_data_record(*,source,reference,rights_holder,license_id,license_reference,attribution,share_alike,sha256,owner_verified=False,owner_attestation=None):
    if not isinstance(license_id,str) or license_id not in ALLOWED_LICENSES: raise ValueError(f"license_id not allowlisted: {license_id!r}")
    if not isinstance(share_alike,bool) or not isinstance(owner_verified,bool): raise ValueError("boolean provenance fields required")
    rec={"source":_required(source,"source"),"reference":_required(reference,"reference"),"rights_holder":_required(rights_holder,"rights_holder"),"license_id":license_id,"license_reference":_required(license_reference,"license_reference"),"attribution":_required(attribution,"attribution"),"share_alike":share_alike,"sha256":validate_sha256(sha256),"owner_verified":owner_verified,"owner_attestation":None}
    if license_id=="owner-original":
        if not owner_verified: raise ValueError("owner-original requires owner_verified=True")
        rec["owner_attestation"]=_required(owner_attestation,"owner_attestation")
    elif owner_verified or owner_attestation is not None: raise ValueError("owner attestation only valid for owner-original")
    if license_id=="CC-BY-SA-4.0" and not share_alike: raise ValueError("CC-BY-SA-4.0 requires share_alike=True")
    return rec
def validate_data_record(record):
    fields={"source","reference","rights_holder","license_id","license_reference","attribution","share_alike","sha256","owner_verified","owner_attestation"}
    if not isinstance(record,dict) or set(record)!=fields: raise ValueError("provenance record fields invalid")
    return build_data_record(**record)
def validate_records(records):
    if not isinstance(records,list) or not records: raise ValueError("at least one provenance record required")
    result=[validate_data_record(r) for r in records]
    if len({r["sha256"] for r in result})!=len(result): raise ValueError("duplicate provenance source hashes")
    return result
def verify_file_hash(path,expected):
    expected=validate_sha256(expected); actual=sha256_file(path)
    if actual!=expected: raise ValueError(f"SHA-256 mismatch for {Path(path).name}")
def load_json(path):
    try: value=json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError) as exc: raise ValueError(f"cannot read evidence JSON: {exc}") from exc
    if not isinstance(value,dict): raise ValueError("evidence JSON root must be object")
    return value
