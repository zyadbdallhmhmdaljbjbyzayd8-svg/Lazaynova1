import test from "node:test";
import assert from "node:assert/strict";
import { getEngine, isEngineId, listEngines } from "./engines.js";

test("catalog exposes all expected Lazaynova engines", () => {
  const ids = listEngines().map((engine) => engine.id);
  assert.deepEqual(ids, ["chat", "research", "coding", "documents", "image", "video", "music", "agent"]);
});

test("engine lookup accepts valid IDs and rejects unknown IDs", () => {
  assert.equal(getEngine("coding")?.name, "محرك البرمجة");
  assert.equal(getEngine("not-a-real-engine"), undefined);
  assert.equal(isEngineId("agent"), true);
  assert.equal(isEngineId("unknown"), false);
});
