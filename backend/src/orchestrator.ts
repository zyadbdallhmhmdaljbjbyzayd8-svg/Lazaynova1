export type AgentKind = "chat" | "research" | "coding" | "documents" | "image" | "video" | "music" | "agent";
export type ChatTurn = { role: "user" | "assistant"; content: string };
export type AgentRunner = (
  prompt: string,
  language: "ar" | "en",
  history: ChatTurn[],
  agent: AgentKind
) => Promise<string>;

export type WorkflowStep = { agent: string; output: string };
export type OrchestrationResult = { reply: string; steps: WorkflowStep[] };

export function selectSpecialist(message: string): AgentKind {
  const text = message.toLowerCase();
  if (/\b(code|debug|program|typescript|kotlin)\b|برمج|كود|تصحيح/.test(text)) return "coding";
  if (/\b(research|sources|investigate)\b|بحث|ابحث|مصادر|تحقق/.test(text)) return "research";
  if (/\b(document|summarize|pdf|report)\b|مستند|ملف|لخّص|لخص|تقرير/.test(text)) return "documents";
  if (/\bvideo\b|فيديو/.test(text)) return "video";
  if (/\bmusic|song\b|موسيقى|أغنية/.test(text)) return "music";
  if (/\bimage|picture\b|صورة|صور|ارسم/.test(text)) return "image";
  return "chat";
}

export async function runMultiAgent(
  message: string,
  language: "ar" | "en",
  history: ChatTurn[],
  runAgent: AgentRunner
): Promise<OrchestrationResult> {
  const specialist = selectSpecialist(message);
  const planPrompt = language === "ar"
    ? `حلل المهمة التالية كمنسق فريق. اكتب خطة قصيرة من 3 إلى 6 خطوات، وحدد ما هو معلوم وما يحتاج تحققًا. لا تدّع تنفيذ أي خطوة بعد.\n\nالمهمة: ${message}`
    : `Act as a team planner. Create a concise 3-6 step plan and note uncertainties. Do not claim any step has been executed.\n\nTask: ${message}`;
  const plan = await runAgent(planPrompt, language, history, "agent");

  const executionPrompt = language === "ar"
    ? `نفّذ المهمة بأفضل ما يمكن اعتمادًا على الخطة التالية. كن صريحًا بشأن الأدوات أو المعلومات غير المتاحة ولا تختلق نتائج.\n\nالمهمة: ${message}\n\nالخطة:\n${plan}`
    : `Execute the task as well as possible using this plan. Be explicit about unavailable tools or missing information; never invent results.\n\nTask: ${message}\n\nPlan:\n${plan}`;
  const execution = await runAgent(executionPrompt, language, history, specialist);

  const reviewPrompt = language === "ar"
    ? `راجع الإجابة التالية بحثًا عن الأخطاء والادعاءات غير المدعومة والنواقص. أعد نسخة نهائية محسنة، ولا تضف ادعاءات بتنفيذ أدوات لم تُستخدم.\n\nالمهمة: ${message}\n\nالخطة:\n${plan}\n\nالمسودة:\n${execution}`
    : `Review the draft for errors, unsupported claims, and omissions. Return an improved final answer without claiming tools were used when they were not.\n\nTask: ${message}\n\nPlan:\n${plan}\n\nDraft:\n${execution}`;
  const reviewed = await runAgent(reviewPrompt, language, [], specialist);

  return {
    reply: reviewed,
    steps: [
      { agent: "planner", output: plan },
      { agent: specialist, output: execution },
      { agent: "reviewer", output: reviewed }
    ]
  };
}
