import json
import sqlite3
import unittest

from native_ai.knowledge_factory.intelligence_v0_2 import (
    add_record,
    digest,
    extract_code_symbols,
    extract_definition,
    split_sentences,
)


class KnowledgeFactoryV02Tests(unittest.TestCase):

    def test_markdown_headings_are_not_facts(self):
        text = (
            "# Artificial Intelligence\n\n"
            "Artificial intelligence is a field of computer science.\n"
            "# الذكاء الاصطناعي\n"
            "الذكاء الاصطناعي مجال من مجالات علوم الحاسوب."
        )
        facts = split_sentences(text)

        self.assertEqual(len(facts), 2)
        self.assertFalse(any(x.startswith("#") for x in facts))

    def test_english_definition(self):
        result = extract_definition(
            "Artificial intelligence is a field of computer science."
        )
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "Artificial intelligence")
        self.assertEqual(result[1], "en")

    def test_arabic_definition(self):
        result = extract_definition(
            "الذكاء الاصطناعي هو مجال من مجالات علوم الحاسوب."
        )
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "الذكاء الاصطناعي")
        self.assertEqual(result[1], "ar")

    def test_code_function_and_class_extraction(self):
        code = (
            "class KnowledgeEngine:\n"
            "    pass\n\n"
            "def extract_facts(text):\n"
            "    return []\n"
        )
        symbols = list(extract_code_symbols(code, "python"))
        names = {item["symbol_name"] for item in symbols}

        self.assertIn("KnowledgeEngine", names)
        self.assertIn("extract_facts", names)

    def test_duplicate_keeps_source_references(self):
        db = sqlite3.connect(":memory:")
        db.execute("""
            CREATE TABLE records (
                kind TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                record_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY(kind, content_hash)
            )
        """)

        base = {
            "id": digest("fact:test"),
            "content_hash": digest("same fact"),
            "text": "This is a sufficiently long test fact.",
            "source": "a.md",
            "source_sha256": "a" * 64,
            "source_chunk_id": "chunk-a",
            "chunk_index": 0,
        }

        self.assertTrue(add_record(db, "knowledge", dict(base)))

        second = dict(base)
        second["source"] = "b.md"
        second["source_sha256"] = "b" * 64
        second["source_chunk_id"] = "chunk-b"

        self.assertFalse(add_record(db, "knowledge", second))

        payload = json.loads(
            db.execute(
                "SELECT payload FROM records WHERE kind='knowledge'"
            ).fetchone()[0]
        )

        self.assertEqual(len(payload["source_refs"]), 2)
        self.assertEqual(payload["duplicate_occurrences"], 1)
        db.close()

    def test_ids_are_deterministic(self):
        value = "A stable knowledge statement."
        self.assertEqual(digest(value), digest(value))


if __name__ == "__main__":
    unittest.main(verbosity=2)
