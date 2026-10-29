import test from "node:test";
import assert from "node:assert/strict";
import {
  routeIntent,
  buildSpecialistRequest
} from "./engine-runtime.js";

test("routes Arabic and English requests to specialist engines", () => {
  assert.equal(routeIntent("اكتب كود JavaScript"), "coding");
  assert.equal(routeIntent("research this topic"), "research");
  assert.equal(routeIntent("ارسم صورة لمدينة"), "image");
  assert.equal(routeIntent("أنشئ فيديو قصير"), "video");
  assert.equal(routeIntent("اكتب أغنية"), "music");
  assert.equal(routeIntent("لخص المستند"), "documents");
  assert.equal(routeIntent("نسق فريق الوكلاء"), "agent");
  assert.equal(routeIntent("مرحبا، كيف حالك؟"), "chat");
});

test("builds a request with the selected specialist and history", () => {
  const result = buildSpecialistRequest("اكتب كود Python", [
    { role: "user", content: "السؤال السابق" },
    { role: "assistant", content: "الرد السابق" }
  ]);

  assert.equal(result.engineId, "coding");
  assert.equal(result.engineName, "محرك البرمجة");
  assert.equal(result.request.model, "lazaynova-core");
  assert.equal(result.request.stream, false);
  assert.equal(result.request.messages[0].role, "system");
  assert.equal(result.request.messages[1].content, "السؤال السابق");
  assert.equal(result.request.messages[2].content, "الرد السابق");
  assert.equal(result.request.messages[3].content, "اكتب كود Python");
});

test("limits forwarded history to the latest ten messages", () => {
  const history = Array.from({ length: 12 }, (_, index) => ({
    role: index % 2 === 0 ? "user" as const : "assistant" as const,
    content: `message-${index}`
  }));

  const result = buildSpecialistRequest("hello", history);
  const forwarded = result.request.messages.slice(1, -1);

  assert.equal(forwarded.length, 10);
  assert.equal(forwarded[0].content, "message-2");
  assert.equal(forwarded[9].content, "message-11");
});

test("does not mutate the supplied history", () => {
  const history = [{ role: "user" as const, content: "keep me" }];
  const before = JSON.stringify(history);

  buildSpecialistRequest("hello", history);

  assert.equal(JSON.stringify(history), before);
});
