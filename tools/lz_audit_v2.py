#!/usr/bin/env python3
# LAZAYNOVA MASTER AUDITOR (LZ-AUDIT)
# Read-only project auditor. Python standard library only.
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import traceback
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

VERSION = "2.0.0"
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".lazaynova-backups", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".gradle", ".idea", ".venv", "venv", "node_modules",
    "dist", "build", "target", ".next", ".dart_tool", "runs", "code_runs",
    "lazaynova-audit-reports",
}
TEXT_EXTS = {
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    ".kt", ".kts", ".java", ".xml", ".json", ".jsonc", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".conf", ".properties", ".gradle", ".md",
    ".txt", ".sh", ".bash", ".zsh", ".sql", ".html", ".css", ".scss",
    ".env", ".example", ".gitignore", ".dockerignore", ".tf", ".go",
    ".rs", ".c", ".h", ".cpp", ".hpp", ".php", ".rb", ".swift",
}
DB_EXTS = {".db", ".sqlite", ".sqlite3"}
MAX_TEXT_BYTES = 2 * 1024 * 1024
MAX_TOTAL_TEXT_BYTES = 64 * 1024 * 1024
MAX_FILES = 30000
SECRET_PATTERNS = [
    ("Possible hard-coded credential", re.compile(
        r"""(?i)\b(api[_-]?key|secret|password|passwd|access[_-]?token|private[_-]?key)\b\s*[:=]\s*(['"])(?!\s*(?:$|your_|changeme|example|placeholder))[^'"\r\n]{8,}\2"""
    )),
    ("Private key material", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
]
DANGEROUS_PATTERNS = [
    ("Potential unsafe deserialization", re.compile(r"\bpickle\.loads?\s*\(")),
    ("Potential dynamic code execution", re.compile(r"\b(?:eval|exec)\s*\(")),
    ("Potential shell execution", re.compile(r"\b(?:os\.system|subprocess\.(?:run|Popen|call))\s*\(")),
    ("Potential disabled TLS verification", re.compile(r"(?i)(?:verify\s*=\s*False|_create_unverified_context)")),
]

def finding(severity, category, title, path=None, line=None, detail="", confidence="medium"):
    return {
        "severity": severity, "category": category, "title": title,
        "path": str(path) if path else None, "line": line,
        "detail": detail[:1200], "confidence": confidence,
    }

def safe_text(path: Path):
    try:
        if path.stat().st_size > MAX_TEXT_BYTES:
            return None, "file exceeds 2 MiB inspection limit"
        raw = path.read_bytes()
        if b"\x00" in raw[:8192]:
            return None, "binary file skipped"
        for enc in ("utf-8-sig", "utf-8", "cp1256", "latin-1"):
            try:
                return raw.decode(enc), None
            except UnicodeDecodeError:
                continue
        return None, "unsupported text encoding"
    except (OSError, PermissionError) as exc:
        return None, f"read failed: {type(exc).__name__}"

def scan_tree(root: Path, findings, inventory):
    stack = [root]
    seen = 0
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for ent in entries:
                    p = Path(ent.path)
                    rel = p.relative_to(root)
                    if ent.is_symlink():
                        inventory["symlinks_skipped"] += 1
                        continue
                    try:
                        if ent.is_dir(follow_symlinks=False):
                            if ent.name in SKIP_DIRS:
                                inventory["directories_skipped"] += 1
                            else:
                                stack.append(p)
                            continue
                        if not ent.is_file(follow_symlinks=False):
                            continue
                        seen += 1
                        if seen > MAX_FILES:
                            seen -= 1
                            inventory["files_seen"] = seen
                            findings.append(finding(
                                "WARNING", "coverage", "File scan limit reached",
                                detail=f"Stopped after {MAX_FILES} files."
                            ))
                            return
                        ext = p.suffix.lower()
                        if ext in DB_EXTS:
                            inventory["databases"].append(str(rel))
                        if ext in TEXT_EXTS or ent.name in {
                            ".env", ".gitignore", "Dockerfile", "Makefile"
                        }:
                            inventory["text_files"].append(str(rel))
                        else:
                            inventory["other_files"] += 1
                    except OSError:
                        inventory["unreadable_entries"] += 1
        except OSError as exc:
            findings.append(finding(
                "INFO", "coverage", "Directory could not be read",
                current.relative_to(root), detail=type(exc).__name__
            ))
            continue
    inventory["files_seen"] = seen

def analyze_python(root, rel, content, findings):
    try:
        ast.parse(content, filename=str(rel))
    except SyntaxError as exc:
        findings.append(finding("ERROR", "python-syntax", "Python syntax error", rel,
                                exc.lineno, f"{exc.msg}; offset={exc.offset}", "high"))

def analyze_text(rel, content, findings):
    ext = Path(rel).suffix.lower()
    if ext == ".json":
        try:
            json.loads(content)
        except json.JSONDecodeError as exc:
            findings.append(finding("ERROR", "json-syntax", "Invalid JSON", rel,
                                    exc.lineno, exc.msg, "high"))
    if ext == ".xml":
        try:
            ET.fromstring(content)
        except ET.ParseError as exc:
            findings.append(finding("ERROR", "xml-syntax", "Invalid XML", rel,
                                    detail=str(exc), confidence="high"))
    lines = content.splitlines()
    for number, line in enumerate(lines, 1):
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                # Never include the matching line or secret value in the report.
                findings.append(finding("HIGH", "secrets", label, rel, number,
                                        "Potential credential-like value detected; source text redacted.",
                                        "medium"))
                break
        for label, pattern in DANGEROUS_PATTERNS:
            if pattern.search(line):
                findings.append(finding("WARNING", "security-pattern", label, rel, number,
                                        "Pattern requires manual review; this is not proof of exploitability.",
                                        "low"))
        if re.search(r"\b(TODO|FIXME|XXX)\b", line):
            findings.append(finding("INFO", "maintenance", "Unresolved TODO/FIXME marker",
                                    rel, number, "Marker detected; source line intentionally redacted.", "high"))
    if ext == ".py":
        analyze_python(Path("."), rel, content, findings)

def audit_databases(root, inventory, findings):
    for rel in inventory["databases"]:
        path = root / rel
        con = None
        try:
            # SQLite URI is generated from a properly escaped file URI; open read-only.
            uri = path.resolve().as_uri() + "?mode=ro"
            con = sqlite3.connect(uri, uri=True, timeout=2.0)
            con.execute("PRAGMA query_only=ON")
            row = con.execute("PRAGMA quick_check(1)").fetchone()
            if not row or row[0] != "ok":
                findings.append(finding("ERROR", "database", "SQLite quick_check failed",
                                        rel, detail=str(row[0] if row else "no result"), confidence="high"))
            else:
                findings.append(finding("INFO", "database", "SQLite quick_check passed",
                                        rel, detail="Read-only quick_check(1) completed.", confidence="high"))
            fk = con.execute("PRAGMA foreign_key_check").fetchmany(20)
            if fk:
                findings.append(finding("ERROR", "database", "Foreign-key violations detected",
                                        rel, detail=f"At least {len(fk)} violation row(s) returned.", confidence="high"))
        except sqlite3.DatabaseError as exc:
            findings.append(finding("ERROR", "database", "SQLite database check failed",
                                    rel, detail=type(exc).__name__, confidence="high"))
        except (OSError, ValueError) as exc:
            findings.append(finding("WARNING", "database", "Database could not be inspected",
                                    rel, detail=type(exc).__name__, confidence="medium"))
        finally:
            if con is not None:
                con.close()

def audit_git(root, findings, inventory):
    try:
        branch = subprocess.run(["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", "-c", "core.preloadIndex=false", "-C", str(root), "branch", "--show-current"],
                                capture_output=True, text=True, timeout=5, check=False)
        status = subprocess.run(["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", "-c", "core.preloadIndex=false", "-C", str(root), "status", "--porcelain=v1", "-z"],
                                capture_output=True, text=True, timeout=8, check=False)
        if branch.returncode == 0:
            inventory["git_branch"] = branch.stdout.strip() or "(detached HEAD)"
        if status.returncode == 0:
            records = [x for x in status.stdout.split("\0") if x]
            inventory["git_changed_entries"] = len(records)
            if records:
                findings.append(finding("INFO", "git", "Working tree has local changes",
                                         detail=f"{len(records)} changed/staged/untracked entry record(s); no files were changed.",
                                         confidence="high"))
        else:
            findings.append(finding("INFO", "git", "Git status unavailable",
                                     detail="This directory may not be a Git working tree.", confidence="high"))
    except (OSError, subprocess.TimeoutExpired):
        findings.append(finding("INFO", "git", "Git inspection unavailable",
                                detail="Git command missing or timed out.", confidence="high"))

def audit_layout(root, inventory, findings):
    dirs = {p.name for p in root.iterdir() if p.is_dir() and not p.is_symlink()}
    known = {
        "backend": "Backend folder",
        "app": "Android app folder",
        "native_ai": "Native AI folder",
        "model": "Model folder",
        "tools": "Tools folder",
    }
    for name, label in known.items():
        if name in dirs:
            inventory["detected_components"].append(label)
    manifests = [x for x in inventory["text_files"] if x.endswith("AndroidManifest.xml")]
    gradles = [x for x in inventory["text_files"] if Path(x).name in
               {"build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"}]
    inventory["android_manifests"] = manifests
    inventory["gradle_files"] = gradles
    if not manifests:
        findings.append(finding("INFO", "android", "AndroidManifest.xml not found",
                                detail="Android manifest discovery did not find a manifest in scanned text files.",
                                confidence="high"))
    if not gradles:
        findings.append(finding("INFO", "android", "Gradle build files not found",
                                detail="No Gradle build files were discovered.", confidence="high"))

def make_report_dir():
    home = Path.home()
    parent = home / "lazaynova-audit-reports"

    if parent.is_symlink():
        raise RuntimeError("Report directory must not be a symbolic link.")

    if parent.exists():
        if not parent.is_dir():
            raise RuntimeError("Report path exists but is not a directory.")
    else:
        parent.mkdir(mode=0o700, parents=False, exist_ok=False)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    while True:
        run_dir = parent / f"run-{stamp}-{uuid.uuid4().hex[:6]}"
        try:
            run_dir.mkdir(mode=0o700)
            return run_dir
        except FileExistsError:
            continue

def write_reports(run_dir, report):
    json_path = run_dir / "report.json"
    md_path = run_dir / "report.md"
    txt_path = run_dir / "summary.txt"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = {}
    for item in report["findings"]:
        counts[item["severity"]] = counts.get(item["severity"], 0) + 1
    lines = [
        "# LAZAYNOVA MASTER AUDITOR",
        f"- Version: {report['version']}",
        f"- Started: {report['started_at']}",
        f"- Root: {report['root']}",
        f"- Files seen: {report['inventory'].get('files_seen', 0)}",
        f"- Findings: {len(report['findings'])}",
        "",
        "## Severity counts",
    ]
    for sev in ("CRITICAL", "HIGH", "ERROR", "WARNING", "INFO"):
        lines.append(f"- {sev}: {counts.get(sev, 0)}")
    lines += ["", "## Findings"]
    for i, item in enumerate(report["findings"], 1):
        loc = item["path"] or "(project)"
        if item["line"]:
            loc += f":{item['line']}"
        lines += [f"### {i}. [{item['severity']}] {item['title']}",
                  f"- Category: {item['category']}",
                  f"- Location: `{loc}`",
                  f"- Confidence: {item['confidence']}",
                  f"- Detail: {item['detail']}", ""]
    lines += ["## Coverage limitations",
              "- Static inspection cannot prove absence of defects or vulnerabilities.",
              "- Project test suites and project scripts were NOT executed.",
              "- Files above 2 MiB, binary files, symlinks, and excluded build/dependency directories were not inspected.",
              "- Non-SQLite databases are inventoried only; no data was modified.",
              "- Security pattern matches require human validation.", ""]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    txt_path.write_text(
        f"LAZAYNOVA MASTER AUDITOR {VERSION}\n"
        f"Findings: {len(report['findings'])}\n"
        + "\n".join(f"{k}: {v}" for k, v in counts.items())
        + f"\nReports: {run_dir}\n", encoding="utf-8")
    for p in (json_path, md_path, txt_path):
        try:
            p.chmod(0o600)
        except OSError:
            pass

def main():
    global MAX_FILES
    parser = argparse.ArgumentParser(
        description="Read-only, standard-library audit of a Lazaynova repository.")
    parser.add_argument("--root", default=".", help="Repository root (default: current directory)")
    parser.add_argument("--max-files", type=int, default=MAX_FILES)
    parser.add_argument("--no-databases", action="store_true", help="Skip read-only SQLite checks")
    parser.add_argument("--version", action="version", version=f"LZ-AUDIT {VERSION}")
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"root directory does not exist: {root}")
    git_marker = root / ".git"
    if not (git_marker.is_dir() or git_marker.is_file()):
        parser.error("root is not a recognized Git working tree")
    required = {"backend", "app", "model", "tools"}
    present = {name for name in required if (root / name).is_dir()}
    if len(present) < 2:
        parser.error("root does not match the expected Lazaynova layout")
    if args.max_files < 1 or args.max_files > 200000:
        parser.error("--max-files must be between 1 and 200000")
    MAX_FILES = args.max_files
    started = datetime.now(timezone.utc).isoformat()
    findings = []
    inventory = {
        "files_seen": 0, "text_files": [], "databases": [],
        "other_files": 0, "directories_skipped": 0,
        "symlinks_skipped": 0, "unreadable_entries": 0,
        "detected_components": [], "android_manifests": [],
        "gradle_files": [], "git_branch": None, "git_changed_entries": 0,
    }
    scan_tree(root, findings, inventory)
    total_text_bytes = 0
    for rel in inventory["text_files"]:
        file_path = root / rel
        try:
            file_size = file_path.stat().st_size
        except OSError:
            file_size = 0
        if file_size > 0 and total_text_bytes + file_size > MAX_TOTAL_TEXT_BYTES:
            findings.append(finding("WARNING", "coverage", "Total text read limit reached",
                                    rel, detail="Stopped content analysis at the 64 MiB budget.",
                                    confidence="high"))
            break
        content, error = safe_text(file_path)
        if error:
            if "exceeds" in error or "read failed" in error:
                findings.append(finding("INFO", "coverage", "File skipped during content analysis",
                                        rel, detail=error, confidence="high"))
            continue
        analyze_text(rel, content, findings)
        total_text_bytes += file_size
    inventory["text_bytes_read"] = total_text_bytes
    audit_layout(root, inventory, findings)
    if not args.no_databases:
        audit_databases(root, inventory, findings)
    audit_git(root, findings, inventory)
    findings.sort(key=lambda x: ({"CRITICAL":0,"HIGH":1,"ERROR":2,"WARNING":3,"INFO":4}.get(x["severity"],5),
                                 x["path"] or "", x["line"] or 0))
    report = {
        "tool": "LAZAYNOVA MASTER AUDITOR", "version": VERSION,
        "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root), "mode": "read-only-static-audit",
        "inventory": inventory, "findings": findings,
        "limitations": [
            "No project code, test suite, build, install, network request, or migration was executed.",
            "Static analysis cannot guarantee discovery of every defect.",
            "Excluded directories, symlinks, binary files, and oversized files are outside source-content analysis.",
        ],
    }
    run_dir = make_report_dir()
    write_reports(run_dir, report)
    counts = {}
    for item in findings:
        counts[item["severity"]] = counts.get(item["severity"], 0) + 1
    print("\n=== LAZAYNOVA MASTER AUDITOR ===")
    print(f"Root: {root}")
    print(f"Files seen: {inventory['files_seen']}")
    print(f"Findings: {len(findings)}")
    for sev in ("CRITICAL", "HIGH", "ERROR", "WARNING", "INFO"):
        print(f"{sev}: {counts.get(sev, 0)}")
    print(f"\nReports saved safely to:\n{run_dir}")
    print("No project files or database records were changed.")
    return 1 if any(x["severity"] in {"CRITICAL", "HIGH", "ERROR"} for x in findings) else 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nAudit cancelled by user; project files were not modified.", file=sys.stderr)
        raise SystemExit(130)
