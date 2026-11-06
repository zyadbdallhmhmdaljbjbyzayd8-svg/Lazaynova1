"""LAZAYNOVA Code Intelligence V0.1.

Read-only source analysis:
- Python: built-in AST
- TypeScript/JavaScript syntax tree: TypeScript Compiler API
- Kotlin: conservative lexical scanner (not a semantic AST)
No model training, external AI APIs, or source modifications.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT / "native_ai/knowledge_factory/code_runs"
EXTENSIONS = {".py", ".ts", ".tsx", ".kt", ".kts"}
SKIP_DIRS = {
    ".git", "node_modules", ".gradle", "build", "dist",
    "__pycache__", ".venv", "venv", ".idea", ".pytest_cache",
    "runs", "code_runs",
}
MAX_FILE_BYTES = 2 * 1024 * 1024


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_id(*parts: str) -> str:
    return sha256("|".join(parts).encode("utf-8"))


def classify(path: Path) -> str:
    parts = {p.lower() for p in path.parts}
    name = path.name.lower()
    if (
        "tests" in parts or "test" in parts
        or name.startswith("test_") or ".test." in name
        or name.endswith("_test.py")
    ):
        return "test"
    return "production"


def discover_sources(root: Path = ROOT) -> list[Path]:
    found = []
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        base = Path(current)
        for name in sorted(files):
            path = base / name
            if path.suffix.lower() not in EXTENSIONS:
                continue
            if (
                name.endswith("~") or name.endswith(".bak")
                or name.endswith(".orig") or ".backup" in name
                or name.startswith(".pre-")
            ):
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            found.append(path)
    return sorted(found)


def source_ref(path: Path, digest: str, start: int, end: int,
               parser: str, confidence: str) -> dict:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "file_sha256": digest,
        "line_start": max(1, int(start)),
        "line_end": max(max(1, int(start)), int(end)),
        "parser": parser,
        "confidence": confidence,
        "classification": classify(path),
    }


def make_record(category: str, language: str, kind: str,
                qualified_name: str, snippet: str, path: Path,
                file_hash: str, start: int, end: int,
                parser: str, confidence: str,
                extra: dict | None = None) -> dict:
    normalized = "\n".join(line.rstrip() for line in snippet.strip().splitlines())
    content_hash = sha256(
        (language + "|" + kind + "|" + qualified_name + "|" + normalized)
        .encode("utf-8")
    )
    record = {
        "id": stable_id(category, content_hash),
        "content_hash": content_hash,
        "category": category,
        "language": language,
        "kind": kind,
        "qualified_name": qualified_name,
        "snippet": snippet.strip()[:12000],
        "source_refs": [
            source_ref(path, file_hash, start, end, parser, confidence)
        ],
    }
    if extra:
        record.update(extra)
    return record


def add_record(db: sqlite3.Connection, table: str, record: dict) -> bool:
    """Deduplicate by deterministic ID while retaining every source reference."""
    payload = db.execute(
        f"SELECT payload FROM {table} WHERE id=?", (record["id"],)
    ).fetchone()
    if payload is None:
        db.execute(
            f"INSERT INTO {table}(id, payload) VALUES (?, ?)",
            (record["id"], json.dumps(record, ensure_ascii=False)),
        )
        return True

    existing = json.loads(payload[0])
    refs = existing.setdefault("source_refs", [])
    known = {
        (r["path"], r["file_sha256"], r["line_start"], r["line_end"])
        for r in refs
    }
    for ref in record.get("source_refs", []):
        key = (ref["path"], ref["file_sha256"], ref["line_start"], ref["line_end"])
        if key not in known:
            refs.append(ref)
            known.add(key)
    db.execute(
        f"UPDATE {table} SET payload=? WHERE id=?",
        (json.dumps(existing, ensure_ascii=False), record["id"]),
    )
    return False


def add_python(path: Path, text: str, digest: str):
    entities, relations, dependencies, errors = [], [], [], []
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        errors.append({
            "path": path.relative_to(ROOT).as_posix(),
            "language": "python",
            "error_type": "SyntaxError",
            "message": exc.msg,
            "line": exc.lineno,
            "column": exc.offset,
        })
        return entities, relations, dependencies, errors

    lines = text.splitlines()
    def snippet(node):
        a = getattr(node, "lineno", 1)
        b = getattr(node, "end_lineno", a) or a
        return "\n".join(lines[a - 1:b]), a, b

    def emit(category, kind, name, node, extra=None):
        code, a, b = snippet(node)
        return make_record(
            category, "python", kind, name, code, path, digest, a, b,
            "python.ast", "high", extra,
        )

    entities.append(emit("entity", "module", path.stem, tree))
    scope = [path.stem]

    class Visitor(ast.NodeVisitor):
        def visit_ClassDef(self, node):
            name = ".".join(scope + [node.name])
            entities.append(emit("entity", "class", name, node, {
                "bases": [ast.unparse(x) for x in node.bases],
                "decorators": [ast.unparse(x) for x in node.decorator_list],
                "docstring": ast.get_docstring(node),
            }))
            scope.append(node.name)
            for child in node.body:
                self.visit(child)
            scope.pop()

        def _function(self, node, kind):
            name = ".".join(scope + [node.name])
            args = node.args
            entities.append(emit("entity", kind, name, node, {
                "arguments": [
                    a.arg for a in args.posonlyargs + args.args + args.kwonlyargs
                ],
                "return_annotation": (
                    ast.unparse(node.returns) if node.returns else None
                ),
                "decorators": [ast.unparse(x) for x in node.decorator_list],
                "docstring": ast.get_docstring(node),
            }))
            scope.append(node.name)
            for child in node.body:
                self.visit(child)
            scope.pop()

        def visit_FunctionDef(self, node):
            self._function(node, "function")

        def visit_AsyncFunctionDef(self, node):
            self._function(node, "async_function")

        def visit_Import(self, node):
            for alias in node.names:
                dependencies.append(emit(
                    "dependency", "import", ".".join(scope + [alias.name]),
                    node, {"module": alias.name, "alias": alias.asname,
                           "import_kind": "python_import"},
                ))

        def visit_ImportFrom(self, node):
            module = "." * node.level + (node.module or "")
            dependencies.append(emit(
                "dependency", "from_import", ".".join(scope + [module]),
                node, {"module": module,
                       "names": [{"name": a.name, "alias": a.asname}
                                 for a in node.names],
                       "import_kind": "python_from_import"},
            ))

        def visit_Call(self, node):
            target = ast.unparse(node.func)
            relations.append(emit(
                "relation", "call", ".".join(scope + [target]), node,
                {"relation_type": "calls", "target_expression": target},
            ))
            self.generic_visit(node)

    Visitor().visit(tree)
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if isinstance(value, ast.Name):
                entities.append(emit("entity", "variable",
                                     ".".join([path.stem, value.id]), node))
    return entities, relations, dependencies, errors


TS_SCRIPT = r"""
const fs = require('fs');
const path = require('path');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const ts = require(path.join(input.root, 'backend/node_modules/typescript'));
const out = {entities: [], relations: [], dependencies: [], errors: []};

for (const file of input.files) {
  const sf = ts.createSourceFile(file.path, file.text,
    ts.ScriptTarget.Latest, true,
    file.path.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const lines = file.text.split(/\r?\n/);
  const lineOf = p => sf.getLineAndCharacterOfPosition(p).line + 1;
  const snippet = n => {
    const a = lineOf(n.getStart(sf)), b = lineOf(n.getEnd());
    return {a, b, text: lines.slice(a - 1, b).join('\n')};
  };
  const add = (bucket, kind, name, node, extra={}) => {
    const s = snippet(node);
    bucket.push({kind, qualified_name:name, line_start:s.a,
      line_end:s.b, snippet:s.text, extra});
  };
  for (const d of sf.parseDiagnostics) {
    const pos = d.start == null ? 0 : d.start;
    out.errors.push({path:file.path, language:'typescript',
      error_type:'ParseDiagnostic',
      message:ts.flattenDiagnosticMessageText(d.messageText, '\n'),
      line:lineOf(pos)});
  }
  function walk(node, scope=[]) {
    const name = node.name && node.name.getText
      ? node.name.getText(sf).replace(/^['"]|['"]$/g, '') : null;
    const q = name ? scope.concat(name) : scope;
    if (ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) {
      const mod = node.moduleSpecifier && ts.isStringLiteral(node.moduleSpecifier)
        ? node.moduleSpecifier.text : null;
      if (mod) add(out.dependencies,
        ts.isImportDeclaration(node) ? 'import' : 'export',
        mod, node, {module:mod});
    } else if (ts.isFunctionDeclaration(node) && name) {
      add(out.entities, 'function', q.join('.'), node, {
        parameters:node.parameters.map(p=>p.name.getText(sf)),
        return_type:node.type ? node.type.getText(sf) : null});
    } else if (ts.isClassDeclaration(node) && name) {
      add(out.entities, 'class', q.join('.'), node, {});
    } else if (ts.isInterfaceDeclaration(node) && name) {
      add(out.entities, 'interface', q.join('.'), node, {});
    } else if (ts.isTypeAliasDeclaration(node) && name) {
      add(out.entities, 'type_alias', q.join('.'), node, {});
    } else if (ts.isEnumDeclaration(node) && name) {
      add(out.entities, 'enum', q.join('.'), node, {});
    } else if (ts.isMethodDeclaration(node) && name) {
      add(out.entities, 'method', q.concat(name).join('.'), node, {});
    } else if (ts.isVariableDeclaration(node) && name) {
      add(out.entities, 'variable', q.join('.'), node, {});
    } else if (ts.isCallExpression(node)) {
      const target = node.expression.getText(sf);
      add(out.relations, 'call', scope.concat(target).join('.'), node,
        {relation_type:'calls', target_expression:target});
    }
    const nextScope = (
      (ts.isClassDeclaration(node) || ts.isInterfaceDeclaration(node) ||
       ts.isFunctionDeclaration(node) || ts.isMethodDeclaration(node)) && name
    ) ? q : scope;
    ts.forEachChild(node, child=>walk(child, nextScope));
  }
  walk(sf, [file.path]);
}
process.stdout.write(JSON.stringify(out));
"""



def parse_typescript_files(files):
    entities, relations, dependencies, errors = [], [], [], []
    for path, content, digest in files:
        payload = {
            "root": str(ROOT),
            "files": [{
                "path": path.relative_to(ROOT).as_posix(),
                "text": content,
            }],
        }
        try:
            proc = subprocess.run(
                ["node", "-e", TS_SCRIPT],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                cwd=ROOT,
                timeout=60,
            )
        except Exception as exc:
            errors.append({
                "path": path.relative_to(ROOT).as_posix(),
                "language": "typescript",
                "error_type": type(exc).__name__,
                "message": str(exc),
            })
            continue

        if proc.returncode != 0:
            errors.append({
                "path": path.relative_to(ROOT).as_posix(),
                "language": "typescript",
                "error_type": "CompilerApiError",
                "message": proc.stderr[-2000:],
            })
            continue

        try:
            parsed = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            errors.append({
                "path": path.relative_to(ROOT).as_posix(),
                "language": "typescript",
                "error_type": "InvalidCompilerOutput",
                "message": str(exc),
            })
            continue

        errors.extend(parsed.get("errors", []))
        for bucket_name, category, destination in (
            ("entities", "entity", entities),
            ("relations", "relation", relations),
            ("dependencies", "dependency", dependencies),
        ):
            for item in parsed.get(bucket_name, []):
                destination.append(make_record(
                    category,
                    "typescript",
                    item["kind"],
                    item["qualified_name"],
                    item["snippet"],
                    path,
                    digest,
                    item["line_start"],
                    item["line_end"],
                    "typescript.compiler_api",
                    "high",
                    item.get("extra"),
                ))
    return entities, relations, dependencies, errors


def mask_kotlin(text: str) -> str:
    """Mask comments and string/char literals while preserving offsets/newlines."""
    out = list(text)
    i, n = 0, len(text)
    state = "code"
    while i < n:
        if state == "code":
            if text.startswith("//", i):
                out[i:i+2] = "  "
                i += 2
                state = "line"
                continue
            if text.startswith("/*", i):
                out[i:i+2] = "  "
                i += 2
                state = "block"
                depth = 1
                while i < n and depth:
                    if text.startswith("/*", i):
                        out[i:i+2] = "  "
                        depth += 1
                        i += 2
                    elif text.startswith("*/", i):
                        out[i:i+2] = "  "
                        depth -= 1
                        i += 2
                    else:
                        if text[i] != "\n":
                            out[i] = " "
                        i += 1
                state = "code"
                continue
            if text.startswith('"""', i):
                out[i:i+3] = "   "
                i += 3
                while i < n and not text.startswith('"""', i):
                    if text[i] != "\n":
                        out[i] = " "
                    i += 1
                if i < n:
                    out[i:i+3] = "   "
                    i += 3
                continue
            if text[i] in ('"', "'"):
                quote = text[i]
                out[i] = " "
                i += 1
                while i < n:
                    ch = text[i]
                    if ch == "\\":
                        out[i] = " "
                        if i + 1 < n and text[i+1] != "\n":
                            out[i+1] = " "
                        i += 2
                    elif ch == quote:
                        out[i] = " "
                        i += 1
                        break
                    else:
                        if ch != "\n":
                            out[i] = " "
                        i += 1
                continue
            i += 1
        elif state == "line":
            if text[i] == "\n":
                state = "code"
            else:
                out[i] = " "
            i += 1
    return "".join(out)


def add_kotlin(path: Path, text: str, digest: str):
    entities, dependencies, errors = [], [], []
    masked = mask_kotlin(text)
    patterns = [
        ("package", r"(?m)^\s*package\s+([A-Za-z_][\w.]*)"),
        ("import", r"(?m)^\s*import\s+([A-Za-z_][\w.*]*)(?:\s+as\s+(\w+))?"),
        ("class", r"(?m)^\s*(?:(?:public|private|protected|internal|data|sealed|abstract|open|inner|enum|annotation)\s+)*(?:enum\s+)?class\s+([A-Za-z_]\w*)"),
        ("interface", r"(?m)^\s*(?:(?:public|private|protected|internal)\s+)*interface\s+([A-Za-z_]\w*)"),
        ("object", r"(?m)^\s*(?:(?:public|private|protected|internal)\s+)*object\s+([A-Za-z_]\w*)"),
        ("function", r"(?m)^\s*(?:(?:public|private|protected|internal|override|suspend|inline|infix|operator|tailrec|external)\s+)*fun\s+(?:<[^>\n]+>\s*)?(?:[\w?.<>]+\.)?([A-Za-z_]\w*)\s*\("),
        ("property", r"(?m)^\s*(?:(?:public|private|protected|internal|const|lateinit|override)\s+)*(val|var)\s+([A-Za-z_]\w*)"),
    ]
    for kind, pattern in patterns:
        for match in re.finditer(pattern, masked):
            line = masked.count("\n", 0, match.start()) + 1
            if kind in ("package", "import"):
                name = match.group(1)
                category = "dependency"
                extra = {"module": name, "import_kind": kind}
                bucket = dependencies
            elif kind == "property":
                name = match.group(2)
                category = "entity"
                extra = {"mutable": match.group(1) == "var"}
                bucket = entities
            else:
                name = match.group(1)
                category = "entity"
                extra = {"analysis_note": "lexical_declaration_only"}
                bucket = entities
            end = line
            original_lines = text.splitlines()
            snippet = original_lines[line - 1] if line <= len(original_lines) else ""
            bucket.append(make_record(
                category, "kotlin", kind, name, snippet,
                path, digest, line, end,
                "kotlin.conservative_lexer", "medium", extra,
            ))
    return entities, [], dependencies, errors


def export_jsonl(db, table: str, path: Path):
    with path.open("x", encoding="utf-8") as handle:
        rows = db.execute(f"SELECT payload FROM {table} ORDER BY id")
        for (payload,) in rows:
            handle.write(payload + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-file-bytes", type=int, default=MAX_FILE_BYTES)
    args = parser.parse_args()

    sources = discover_sources()
    inputs = []
    unreadable = []
    for path in sources:
        try:
            raw = path.read_bytes()
            if len(raw) > args.max_file_bytes:
                continue
            text = raw.decode("utf-8")
            inputs.append((path, text, sha256(raw)))
        except Exception as exc:
            unreadable.append({
                "path": path.relative_to(ROOT).as_posix(),
                "error_type": type(exc).__name__,
                "message": str(exc),
            })

    py_entities, py_relations, py_dependencies, errors = [], [], [], []
    ts_files, kt_files = [], []
    for path, content, digest in inputs:
        ext = path.suffix.lower()
        if ext == ".py":
            e, r, d, err = add_python(path, content, digest)
            py_entities += e
            py_relations += r
            py_dependencies += d
            errors += err
        elif ext in (".ts", ".tsx"):
            ts_files.append((path, content, digest))
        elif ext in (".kt", ".kts"):
            kt_files.append((path, content, digest))

    ts_entities, ts_relations, ts_dependencies, ts_errors = (
        parse_typescript_files(ts_files)
    )
    errors += ts_errors

    kt_entities, kt_relations, kt_dependencies, kt_errors = [], [], [], []
    for path, content, digest in kt_files:
        e, r, d, err = add_kotlin(path, content, digest)
        kt_entities += e
        kt_relations += r
        kt_dependencies += d
        kt_errors += err
    errors += kt_errors

    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-" + uuid.uuid4().hex[:8]
    )
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_ROOT / run_id
    out.mkdir(exist_ok=False)

    db = sqlite3.connect(out / "dedup_index.sqlite3")
    try:
        for table in ("entities", "relations", "dependencies"):
            db.execute(
                f"CREATE TABLE {table} (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )

        batches = {
            "entities": py_entities + ts_entities + kt_entities,
            "relations": py_relations + ts_relations + kt_relations,
            "dependencies": py_dependencies + ts_dependencies + kt_dependencies,
        }
        inserted = {}
        for table, records in batches.items():
            count = 0
            for record in records:
                count += int(add_record(db, table, record))
            inserted[table] = {
                "records_seen": len(records),
                "unique_records": db.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0],
                "new_records": count,
            }
        db.commit()

        export_jsonl(db, "entities", out / "code_entities.jsonl")
        export_jsonl(db, "relations", out / "code_relations.jsonl")
        export_jsonl(db, "dependencies", out / "code_dependencies.jsonl")

        with (out / "parse_errors.jsonl").open("x", encoding="utf-8") as f:
            for item in errors + unreadable:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        language_counts = {
            "python": len([x for x in inputs if x[0].suffix == ".py"]),
            "typescript": len([x for x in inputs if x[0].suffix in (".ts", ".tsx")]),
            "kotlin": len([x for x in inputs if x[0].suffix in (".kt", ".kts")]),
        }
        report = {
            "engine": "LAZAYNOVA Code Intelligence",
            "version": "0.1.0",
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),

            "source_files_discovered": len(sources),
            "source_files_read": len(inputs),
            "unreadable_files": len(unreadable),
            "language_files": language_counts,
            "production_files": sum(
                classify(p) == "production" for p, _, _ in inputs
            ),
            "test_files": sum(classify(p) == "test" for p, _, _ in inputs),
            "parse_errors": len(errors),
            "records": inserted,
            "parser_methods": {
                "python": "built-in ast",
                "typescript": "TypeScript Compiler API",
                "kotlin": "conservative lexical scanner; not semantic AST",
            },
            "limitations": [
                "Import/export targets are recorded as declared; not all are resolved.",
                "Call expressions are observations, not proof of runtime execution.",
                "Kotlin declarations are lexical matches, not semantic symbol resolution.",
                "No whole-program type checking or runtime call graph is performed.",
                "Generated output and dependency directories are excluded.",
            ],
            "external_ai_apis_used": False,
            "external_model_weights_used": False,
            "model_training_performed": False,
            "source_files_modified": False,
            "existing_knowledge_factory_outputs_modified": False,
            "outputs": [
                "code_entities.jsonl",
                "code_relations.jsonl",
                "code_dependencies.jsonl",
                "parse_errors.jsonl",
                "dedup_index.sqlite3",
                "report.json",
            ],
        }
        with (out / "report.json").open("x", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
    finally:
        db.close()

    print("LAZAYNOVA CODE INTELLIGENCE V0.1")
    print("RUN:", run_id)
    print("FILES READ:", len(inputs), "/", len(sources))
    print("PYTHON / TS / KOTLIN:", language_counts)
    print("PARSE ERRORS:", len(errors))
    print("ENTITIES:", inserted["entities"]["unique_records"])
    print("RELATIONS:", inserted["relations"]["unique_records"])
    print("DEPENDENCIES:", inserted["dependencies"]["unique_records"])
    print("OUTPUT:", out.relative_to(ROOT))
    print("TRAINING: NOT RUN")
    print("SOURCE FILES MODIFIED: NO")


if __name__ == "__main__":
    main()
