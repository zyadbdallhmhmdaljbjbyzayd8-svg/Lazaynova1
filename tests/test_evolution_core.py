import tempfile
import unittest
from pathlib import Path

from knowledge_core.evolution_core import KnowledgeEvolution


class EvolutionCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "test_evolution.db"
        self.engine = KnowledgeEvolution(str(self.db), initialize=True)

    def tearDown(self):
        self.engine.close()
        self.temp.cleanup()

    def test_new_knowledge_starts_pending(self):
        result = self.engine.teach(
            "هوية لازاينوفا",
            "LAZAYNOVA منصة ذكاء اصطناعي محلية مستقلة."
        )
        self.assertEqual(result["status"], "pending")
        self.assertGreater(result["tokens_indexed"], 0)

    def test_pending_knowledge_is_not_trusted_by_default(self):
        self.engine.teach("مشروع", "منصة لازاينوفا تعمل محليا")
        self.assertEqual(self.engine.search("لازاينوفا"), [])
        self.assertEqual(
            len(self.engine.search("لازاينوفا", include_pending=True)), 1
        )

    def test_verified_knowledge_can_be_retrieved(self):
        item = self.engine.teach(
            "هوية المشروع",
            "LAZAYNOVA مشروع ذكاء اصطناعي محلي."
        )
        self.assertTrue(self.engine.verify(item["id"]))
        results = self.engine.search("ذكاء اصطناعي")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], item["id"])

    def test_duplicate_is_not_inserted_twice(self):
        first = self.engine.teach("المعرفة", "معلومة اختبارية ثابتة")
        second = self.engine.teach("المعرفة", "معلومة اختبارية ثابتة")
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(second["status"], "exists")

    def test_interaction_is_recorded(self):
        interaction_id = self.engine.record_interaction(
            "ما هي لازاينوفا؟",
            intent="identity",
            matched_ids=[1],
            feedback=1
        )
        self.assertGreater(interaction_id, 0)
        self.assertEqual(self.engine.stats()["interaction_count"], 1)

    def test_reindex_adds_missing_links(self):
        item = self.engine.teach("موضوع", "محتوى للفهرسة")
        with self.engine.conn:
            self.engine.conn.execute(
                "DELETE FROM knowledge_tokens WHERE knowledge_id=?",
                (item["id"],)
            )
        added = self.engine.reindex()
        self.assertGreater(added, 0)


if __name__ == "__main__":
    unittest.main()
