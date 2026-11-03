import { test } from "node:test";
import assert from "node:assert/strict";
import { AgentOrchestrator } from "./AgentOrchestrator.js";
import type { LLMClient } from "./types.js";

function stub(responses: string[]): LLMClient {
  let i = 0;
  return {
    async chat(_input: unknown) {
      const content = responses[i++] ?? "";
      return { choices: [{ message: { content } }] };
    },
  };
}

test("planner→executor→verifier succeeds on happy path", async () => {
  const llm = stub([
    JSON.stringify([
      { id: "s1", description: "Research the topic" },
      { id: "s2", description: "Write a summary" },
    ]),
    "research output",
    "summary output",
    "YES",
  ]);
  const orch = new AgentOrchestrator(llm);
  const { plan, results, verification } = await orch.run("Summarize Rust ownership");
  assert.equal(plan.steps.length, 2);
  assert.equal(results.every((r) => r.ok), true);
  assert.equal(verification.passed, true);
});

test("retries failed step and reports failure after max attempts", async () => {
  const llm = stub([
    JSON.stringify([{ id: "s1", description: "do thing" }]),
    "",
    "",
  ]);
  const orch = new AgentOrchestrator(llm, { maxAttempts: 2 });
  const { results, verification } = await orch.run("fail me");
  assert.equal(results[0].ok, false);
  assert.equal(verification.passed, false);
});

test("verifier rejects when LLM answers NO", async () => {
  const llm = stub([
    JSON.stringify([{ id: "s1", description: "do it" }]),
    "output",
    "NO",
  ]);
  const orch = new AgentOrchestrator(llm);
  const { verification } = await orch.run("impossible");
  assert.equal(verification.passed, false);
});

test("planner rejects non-JSON content", async () => {
  const llm = stub(["not json at all"]);
  const orch = new AgentOrchestrator(llm);
  await assert.rejects(() => orch.run("x"), /non-JSON/);
});

test("parses JSON plan wrapped in markdown fences", async () => {
  const llm = stub([
    "```json\n[{\"id\":\"s1\",\"description\":\"a\"}]\n```",
    "out",
    "YES",
  ]);
  const orch = new AgentOrchestrator(llm);
  const { plan } = await orch.run("x");
  assert.equal(plan.steps[0].description, "a");
});
