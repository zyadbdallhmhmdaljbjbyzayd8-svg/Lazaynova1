import { test } from "node:test";
import assert from "node:assert/strict";
import { IntentRouter } from "./IntentRouter.js";

const router = new IntentRouter();

test("Arabic writing request", () => {
  const i = router.classify("اكتب لي رسالة شكر لمديري");
  assert.equal(i.kind, "writing");
  assert.equal(i.locale, "ar");
  assert.ok(i.confidence > 0);
});

test("English coding request", () => {
  const i = router.classify("Fix this bug in my Python function");
  assert.equal(i.kind, "coding");
  assert.equal(i.locale, "en");
});

test("Arabic document analysis", () => {
  const i = router.classify("لخص لي هذا المستند PDF");
  assert.equal(i.kind, "document_analysis");
  assert.equal(i.locale, "ar");
});

test("English automation", () => {
  const i = router.classify("Schedule a cron job every day at 9am");
  assert.equal(i.kind, "automation");
});

test("plain greeting falls back to chat", () => {
  const i = router.classify("hi");
  assert.equal(i.kind, "chat");
});

test("empty input → chat, zero confidence", () => {
  const i = router.classify("   ");
  assert.equal(i.kind, "chat");
  assert.equal(i.confidence, 0);
});
