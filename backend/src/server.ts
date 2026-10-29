import "dotenv/config";
import express, { Request, Response, NextFunction } from "express";
import cors from "cors";
import helmet from "helmet";
import { z } from "zod";

// Old imports
import { knowledgeRouter } from "./knowledge-routes.js";
import { getEngine, isEngineId, listEngines, type EngineId } from "./engines.js";

// NEW IMPORTS (Golden Command #1 & #2)
import { InternalAIGateway } from "./ai/InternalAIGateway.js";
import { IntentRouter } from "./ai/IntentRouter.js";
import { AgentOrchestrator } from "./ai/AgentOrchestrator.js";

const app = express();
const port = Number(process.env.PORT || 8787);
app.disable("x-powered-by");
app.use(helmet());
app.use(cors({ origin: process.env.CORS_ORIGIN?.split(",").map(s => s.trim()) || false }));
app.use(express.json({ limit: "256kb" }));

// --- NEW AI INIT ---
const gateway = new InternalAIGateway();
const intentRouter = new IntentRouter();
const orchestrator = new AgentOrchestrator(gateway);

const schema = z.object({
  message: z.string().trim().min(1).max(12000),
  language: z.enum(["ar", "en"]).default("ar"),
  history: z.array(z.object({
    role: z.enum(["user", "assistant"]),
    content: z.string().max(12000)
  })).max(20).optional()
});

type Intent = EngineId;

const agents: Record<Intent, { name: string; system: string }> = {
  chat: { name: "المنسق الذكي", system: "أنت المنسق الذكي في Lazaynova. أجب بوضوح واطلب التوضيح عند الحاجة." },
  research: { name: "وكيل البحث", system: "أنت وكيل بحث. ميّز بين الحقائق والافتراضات، اقترح كلمات بحث دقيقة." },
  coding: { name: "وكيل البرمجة", system: "أنت وكيل برمجة خبير. قدم كودًا عمليًا آمنًا، واشرح الملفات والتغييرات." },
  documents: { name: "وكيل المستندات", system: "أنت وكيل مستندات. ساعد في التخطيط والكتابة والتلخيص." },
  image: { name: "وكيل الصور", system: "أنت وكيل صور. اكتب وصفًا دقيقًا أو خطة تصميم؛ لا تدّع إنشاء صورة." },
  video: { name: "وكيل الفيديو", system: "أنت وكيل فيديو. ساعد في السيناريو وتقسيم المشاهد وخطة الإنتاج." },
  music: { name: "وكيل الموسيقى", system: "أنت وكيل موسيقى. ساعد في الأفكار والكلمات والوصف الموسيقي." },
  agent: { name: "منسق الوكلاء", system: "أنت منسق مهام. قسّم المهمة إلى خطوات، ووضح ما يحتاج إلى أدوات." }
};

// LAZAYNOVA_ENGINE_ROUTING_V1
function routeIntent(s: string): Intent {
  const t = s.toLowerCase();

  if (/\b(music|song|audio|موسيقى|اغنية|أغنية|لحن|صوت)\b/.test(t)) {
    return "music";
  }
  if (/\b(video|film|movie|فيديو|فلم|مشاهد|مونتاج)\b/.test(t)) {
    return "video";
  }
  if (/\b(agent|team|multi.?agent|فريق|وكلاء|نفذ المهمة|نفّذ المهمة)\b/.test(t)) {
    return "agent";
  }
  if (/\b(research|بحث عميق|ابحث|مصادر|تحليل بحثي)\b/.test(t)) {
    return "research";
  }
  if (/\b(code|debug|program|coding|برمج|كود|خطأ برمجي)\b/.test(t)) {
    return "coding";
  }
  if (/\b(document|pdf|file|مستند|ملف|لخص الوثيقة|لخص المستند)\b/.test(t)) {
    return "documents";
  }
  if (/\b(image|picture|draw|صورة|صور|ارسم|تصميم صورة)\b/.test(t)) {
    return "image";
  }
  return "chat";
}

// --- ROUTES ---
app.use("/api/knowledge", knowledgeRouter);

app.get("/api/engines", (req, res) => {
  res.json({ engines: listEngines() });
});

// CHAT ROUTE (integrated with new AI Gateway)
app.post("/api/chat", async (req, res) => {
  try {
    const parsed = schema.parse(req.body);
    const intentKind = intentRouter.classify(parsed.message).kind;
    
    // Use AgentOrchestrator for complex tasks (e.g., automation)
    if (intentKind === "automation") {
      const result = await orchestrator.run(parsed.message);
      return res.json({ type: "automation", result });
    }

    // Route the request to its specialist engine.
    const engineId = routeIntent(parsed.message);
    const specialist = agents[engineId];

    const response = await gateway.chat({
      model: "lazaynova-core",
      messages: [
        { role: "system", content: specialist.system },
        ...(parsed.history ?? []).slice(-10).map((item) => ({
          role: item.role,
          content: item.content
        })),
        { role: "user", content: parsed.message }
      ],
      temperature: 0.3,
      max_tokens: 700,
      stream: false
    });

    res.json({
      type: "chat",
      intent: engineId,
      engine: specialist.name,
      response
    });
  } catch (err) {
    if (err instanceof z.ZodError) {
      return res.status(400).json({ error: err.errors });
    }
    res.status(500).json({ error: "Internal server error", details: err instanceof Error ? err.message : String(err) });
  }
});

app.listen(port, () => {
  console.log(`Lazaynova backend listening on port ${port}`);
});
