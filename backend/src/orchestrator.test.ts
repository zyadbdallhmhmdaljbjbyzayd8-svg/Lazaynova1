import test from "node:test";
import assert from "node:assert/strict";
import { runMultiAgent, selectSpecialist } from "./orchestrator.js";

test("selects a specialist from Arabic and English requests", () => {
  assert.equal(selectSpecialist("اكتب كود Kotlin لتسجيل الدخول"), "coding");
  assert.equal(selectSpecialist("ابحث عن مصادر موثوقة"), "research");
  assert.equal(selectSpecialist("لخص هذا المستند"), "documents");
  assert.equal(selectSpecialist("صمم صورة لشعار"), "image");
});

test("runs planner, specialist, and reviewer in order", async () => {
  const calls: string[] = [];
  const runner = async (_prompt: string, _language: "ar" | "en", _history: Array<{role:"user"|"assistant";content:string}>, agent: "chat"|"research"|"coding"|"documents"|"image"|"video"|"music"|"agent") => {
    calls.push(agent);
    return `output-${calls.length}`;
  };
  const result = await runMultiAgent("اكتب كود API", "ar", [], runner);
  assert.deepEqual(calls, ["agent", "coding", "coding"]);
  assert.equal(result.reply, "output-3");
  assert.equal(result.steps.length, 3);
  assert.equal(result.steps[0].agent, "planner");
  assert.equal(result.steps[2].agent, "reviewer");
});
