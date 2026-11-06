import json
import sqlite3
import unittest
from pathlib import Path

from native_ai.knowledge_factory import code_intelligence as ci


class CodeIntelligenceTests(unittest.TestCase):
    def test_source_discovery_excludes_generated_directories(self):
        files = ci.discover_sources()
        self.assertTrue(files)
        self.assertTrue(all(p.suffix.lower() in ci.EXTENSIONS for p in files))
        self.assertFalse(any("node_modules" in p.parts for p in files))
        self.assertFalse(any("dist" in p.parts for p in files))
        self.assertFalse(any("__pycache__" in p.parts for p in files))

    def test_python_ast_extracts_real_declarations(self):
        path = ci.ROOT / "native_ai/knowledge_factory/intelligence_v0_2.py"
        raw = path.read_bytes()
        entities, relations, dependencies, errors = ci.add_python(
            path, raw.decode("utf-8"), ci.sha256(raw)
        )
        self.assertEqual(errors, [])
        names = {x["qualified_name"] for x in entities}
        self.assertTrue(any("main" in name for name in names))
        self.assertTrue(any(x["kind"] == "function" for x in entities))
        self.assertTrue(dependencies)

    def test_python_syntax_error_is_reported_not_crashed(self):
        path = ci.ROOT / "tests/test_code_intelligence.py"
        raw = path.read_bytes()
        entities, relations, dependencies, errors = ci.add_python(
            path, "def broken(:\n    pass\n", ci.sha256(raw)
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "SyntaxError")

    def test_typescript_compiler_api_extracts_declarations(self):
        path = ci.ROOT / "backend/src/engines.ts"
        if not path.is_file():
            self.skipTest("TypeScript fixture is unavailable")
        raw = path.read_bytes()
        entities, relations, dependencies, errors = ci.parse_typescript_files([
            (path, raw.decode("utf-8"), ci.sha256(raw))
        ])
        self.assertEqual(errors, [])
        self.assertTrue(entities)
        self.assertTrue(any(x["language"] == "typescript" for x in entities))

    def test_kotlin_scanner_finds_declarations_without_claiming_ast(self):
        path = ci.ROOT / "app/src/main/java/com/lazaynova/app/ApiClient.kt"
        if not path.is_file():
            self.skipTest("Kotlin fixture is unavailable")
        raw = path.read_bytes()
        entities, relations, dependencies, errors = ci.add_kotlin(
            path, raw.decode("utf-8"), ci.sha256(raw)
        )
        self.assertEqual(errors, [])
        self.assertTrue(entities)
        self.assertTrue(dependencies)
        self.assertTrue(all(
            ref["parser"] == "kotlin.conservative_lexer"
            and ref["confidence"] == "medium"
            for item in entities
            for ref in item["source_refs"]
        ))

    def test_deduplication_preserves_multiple_source_references(self):
        path = ci.ROOT / "tests/test_code_intelligence.py"
        digest = ci.sha256(path.read_bytes())
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE entities (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        first = ci.make_record(
            "entity", "python", "function", "sample",
            "def sample(): pass", path, digest, 10, 10, "test", "high"
        )
        second = ci.make_record(
            "entity", "python", "function", "sample",
            "def sample(): pass", path, digest, 20, 20, "test", "high"
        )
        self.assertTrue(ci.add_record(db, "entities", first))
        self.assertFalse(ci.add_record(db, "entities", second))
        payload = json.loads(db.execute(
            "SELECT payload FROM entities WHERE id=?", (first["id"],)
        ).fetchone()[0])
        self.assertEqual(len(payload["source_refs"]), 2)
        db.close()

    def test_kotlin_mask_preserves_line_positions(self):
        source = 'val a = "fun fake() {}"\n// fun hidden() {}\nfun real() {}\n'
        masked = ci.mask_kotlin(source)
        self.assertEqual(source.count("\n"), masked.count("\n"))
        self.assertNotIn("fake", masked)
        self.assertNotIn("hidden", masked)
        self.assertIn("fun real", masked)

    def test_kotlin_block_comment_resets_to_code(self):
        source = "/* hidden fun fake() {} */\nfun real() {}\n"
        masked = ci.mask_kotlin(source)
        self.assertNotIn("fake", masked)
        self.assertIn("fun real", masked)

    def test_kotlin_nested_block_comments_reset_to_code(self):
        source = "/* outer /* inner */ outer */\nclass Real {}\n"
        masked = ci.mask_kotlin(source)
        self.assertNotIn("inner", masked)
        self.assertIn("class Real", masked)


if __name__ == "__main__":
    unittest.main(verbosity=2)
