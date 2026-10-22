import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const temporaryDirectory = fs.mkdtempSync(
  path.join(os.tmpdir(), "lazaynova-knowledge-")
);

process.env.LAZAYNOVA_DATA_DIR = temporaryDirectory;

const {
  indexDocument,
  searchKnowledge,
  listKnowledge,
  deleteKnowledgeDocument
} = await import("./knowledge.js");

test("indexes a document and finds matching Arabic text", () => {
  const result = indexDocument({
    title: "الذكاء الاصطناعي",
    source: "test-document",
    text:
      "الذكاء الاصطناعي يساعد على تحليل البيانات " +
      "وبناء أنظمة ذكية. البحث والفهرسة يحسنان الوصول للمعلومات."
  });

  assert.ok(result.documentId);
  assert.ok(result.chunksIndexed >= 1);

  const matches = searchKnowledge("الذكاء الاصطناعي");
  assert.ok(matches.length > 0);
  assert.equal(matches[0].title, "الذكاء الاصطناعي");
});

test("returns no matches for unrelated terms", () => {
  indexDocument({
    title: "مستند تجريبي",
    text: "التفاح والبرتقال فواكه."
  });

  assert.deepEqual(
    searchKnowledge("مركبة فضائية"),
    []
  );
});

test("lists and deletes a document", () => {
  const indexed = indexDocument({
    title: "مستند للحذف",
    text: "هذا مستند تجريبي."
  });

  assert.ok(
    listKnowledge().some(
      (item) => item.documentId === indexed.documentId
    )
  );

  assert.equal(
    deleteKnowledgeDocument(indexed.documentId),
    true
  );

  assert.equal(
    deleteKnowledgeDocument(indexed.documentId),
    false
  );
});
