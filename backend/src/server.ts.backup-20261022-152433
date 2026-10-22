import "dotenv/config";
import express, { Request, Response, NextFunction } from "express";
import cors from "cors";
import helmet from "helmet";
import { z } from "zod";
import { runMultiAgent } from "./orchestrator.js";
import { getEngine, isEngineId, listEngines, type EngineId } from "./engines.js";

const app = express();
const port = Number(process.env.PORT || 8787);
app.disable("x-powered-by");
app.use(helmet());
app.use(cors({ origin: process.env.CORS_ORIGIN?.split(",").map(s => s.trim()) || false }));
app.use(express.json({ limit: "256kb" }));

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
  research: { name: "وكيل البحث", system: "أنت وكيل بحث. ميّز بين الحقائق والافتراضات، اقترح كلمات بحث ومصادر موثوقة، ولا تختلق مصادر أو نتائج بحث لم تنفذها." },
  coding: { name: "وكيل البرمجة", system: "أنت وكيل برمجة خبير. قدم كودًا عمليًا آمنًا، واشرح الملفات والأوامر المطلوبة، ولا تدّع اختبار الكود ما لم يتم تشغيله." },
  documents: { name: "وكيل المستندات", system: "أنت وكيل مستندات. ساعد في التخطيط والكتابة والتلخيص، واطلب الملف إذا كان محتواه غير متاح." },
  image: { name: "وكيل الصور", system: "أنت وكيل صور. اكتب وصفًا دقيقًا أو خطة تصميم؛ لا تدّع إنشاء صورة إذا لم تتوفر أداة توليد صور." },
  video: { name: "وكيل الفيديو", system: "أنت وكيل فيديو. ساعد في السيناريو وتقسيم المشاهد وخطة الإنتاج." },
  music: { name: "وكيل الموسيقى", system: "أنت وكيل موسيقى. ساعد في الأفكار والكلمات والوصف الموسيقي دون نسخ كلمات محمية." },
  agent: { name: "منسق الوكلاء", system: "أنت منسق مهام. قسّم المهمة إلى خطوات، ووضح ما يحتاج إلى أدوات أو موافقة المستخدم." }
};
function routeIntent(s: string): Intent {
  const t = s.toLowerCase();
  if (/code|debug|program|برمج|كود/.test(t)) return "coding";
  if (/research|بحث عميق|ابحث|مصادر/.test(t)) return "research";
  if (/document|pdf|file|مستند|ملف/.test(t)) return "documents";
  if (/image|picture|صورة|صور|ارسم/.test(t)) return "image";
  if (/video|فيديو/.test(t)) return "video";
  if (/music|song|موسيقى|أغنية/.test(t)) return "music";
  if (/agent|automate|وكيل|نفذ المهمة|خطط|تخطيط|قسّم المهمة/.test(t)) return "agent";
  return "chat";
}
async function aiGateway(message: string, language: "ar" | "en", history: Array<{ role: "user" | "assistant"; content: string }> = [], intent: Intent) {
  const base = process.env.AI_BASE_URL?.replace(/\/$/, "");
  const key = process.env.AI_API_KEY;
  const model = process.env.AI_MODEL;
  if (!base || !key || !model) {
    const e = new Error("AI provider is not configured. Set AI_BASE_URL, AI_API_KEY and AI_MODEL on the server.") as Error & { status?: number };
    e.status = 503;
    throw e;
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), Number(process.env.AI_TIMEOUT_MS || 45000));
  try {
    const r = await fetch(base + "/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + key },
      body: JSON.stringify({
        model,
        messages: [
          { role: "system", content: `${agents[intent].system} ${language === "ar" ? "أجب باللغة العربية ما لم يطلب المستخدم غير ذلك. لا تدّع تنفيذ إجراءات لم تنفذها." : "Answer in English unless requested otherwise. Never claim actions you did not perform."}` },
          ...history.slice(-10),
          { role: "user", content: message }
        ],
        temperature: 0.4
      }),
      signal: controller.signal
    });
    const data = await r.json() as { choices?: Array<{ message?: { content?: string } }>; error?: { message?: string } };
    if (!r.ok) throw Error(data.error?.message || "AI provider HTTP " + r.status);
    const answer = data.choices?.[0]?.message?.content;
    if (!answer) throw Error("AI provider returned an empty response");
    return answer;
  } finally { clearTimeout(timer); }
}
app.get("/health", (_q: Request, r: Response) => r.json({ status: "ok", service: "lazaynova-api", version: "0.2.0" }));
app.get("/api/agents", (_q: Request, r: Response) => r.json({ agents: Object.entries(agents).map(([id, agent]) => ({ id, name: agent.name })) }));
app.get("/api/engines", (_q: Request, r: Response) => {
  r.json({ engines: listEngines() });
});
app.post("/api/engines/:id/run", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const id = String(req.params.id);
    if (!isEngineId(id)) return res.status(404).json({ error: "Unknown engine", available: listEngines().map((engine) => engine.id) });
    const parsed = schema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ error: "Invalid request", details: parsed.error.flatten() });
    const { message, language, history = [] } = parsed.data;
    if (id === "agent") {
      const workflow = await runMultiAgent(message, language, history, (prompt, lang, turns, agent) =>
        aiGateway(prompt, lang, turns, agent)
      );
      return res.json({ engine: getEngine(id), reply: workflow.reply, workflow: workflow.steps, provider: "configured-gateway" });
    }
    const reply = await aiGateway(message, language, history, id);
    return res.json({ engine: getEngine(id), reply, provider: "configured-gateway" });
  } catch (e) { next(e); }
});
app.post("/api/chat", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const parsed = schema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ error: "Invalid request", details: parsed.error.flatten() });
    const { message, language, history = [] } = parsed.data;
    const intent = routeIntent(message);
    if (intent === "agent") {
      const workflow = await runMultiAgent(message, language, history, (prompt, lang, turns, agent) =>
        aiGateway(prompt, lang, turns, agent)
      );
      return res.json({
        reply: workflow.reply,
        intent,
        agent: agents.agent.name,
        workflow: workflow.steps,
        provider: "configured-gateway"
      });
    }
    const reply = await aiGateway(message, language, history, intent);
    return res.json({ reply, intent, agent: agents[intent].name, provider: "configured-gateway" });
  } catch (e) { next(e); }
});
app.use((_q: Request, r: Response) => r.status(404).json({ error: "Not found" }));
app.use((e: Error & { status?: number }, _q: Request, r: Response, _n: NextFunction) => {
  const status = e.status || 502;
  if (status >= 500) console.error("[api-error]", e.message);
  r.status(status).json({ error: status === 503 ? e.message : "Request failed. Check server configuration and provider availability." });
});
app.listen(port, "0.0.0.0", () => console.log(`Lazaynova API listening on 0.0.0.0:${port}`));
