import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import { EngineManager } from "./engines/engineManager.js";
import { AgentOrchestrator } from "./orchestrator/agentOrchestrator.js";
import { LocalKnowledgeBase } from "./knowledge/knowledgeBase.js";

dotenv.config();

const app = express();
const PORT = process.env.PORT ? parseInt(process.env.PORT) : 8788;

app.use(cors());
app.use(express.json());

const engineManager = new EngineManager();
const orchestrator = new AgentOrchestrator();
const knowledgeBase = new LocalKnowledgeBase();

// فحص الصحة
app.get("/health", (req, res) => {
  res.json({ status: "ok", service: "lazaynova-api", version: "1.0.0", autonomous: true });
});

// استعراض المحركات الثمانية
app.get("/api/engines", (req, res) => {
  res.json({
    engines: [
      { id: "chat", name: "محرك المحادثة", description: "محادثة عامة وتنسيق الطلبات السيادية", mode: "text" },
      { id: "research", name: "محرك البحث والتحليل", description: "تحليل الاستعلامات عبر المعرفة المحلية", mode: "text" },
      { id: "coding", name: "محرك البرمجة", description: "توليد وتصحيح الأكواد محلياً", mode: "text" },
      { id: "documents", name: "محرك المستندات", description: "صياغة المستندات وتلخيص النصوص", mode: "text" },
      { id: "image", name: "محرك الصور", description: "خطط التصميم والأوصاف البصرية", mode: "prompt" },
      { id: "video", name: "محرك الفيديو", description: "كتابة السيناريو وتقسيم المشاهد", mode: "text" },
      { id: "music", name: "محرك الموسيقى", description: "أفكار وهياكل الألحان والتوزيع", mode: "text" },
      { id: "agent", name: "محرك تنسيق الوكلاء", description: "تخطيط وتنفيذ ومراجعة المهام المتقدمة", mode: "multi-agent" }
    ]
  });
});

// نقطة المحادثة الأساسية وتشغيل المحركات أو الوكلاء
app.post("/api/chat", async (req, res) => {
  try {
    const { message, engineId = "chat", useOrchestrator = true } = req.body;
    if (!message) {
      return res.status(400).json({ error: "Message is required" });
    }

    if (useOrchestrator && engineId === "agent") {
      const result = await orchestrator.runWorkflow(message, engineId);
      return res.json({
        response: `${result.plan}\n\n${result.execution}\n\n${result.review}`,
        metadata: { orchestrator: true, sources: result.knowledgeSourcesCount }
      });
    }

    const result = await engineManager.execute(engineId, message);
    res.json({
      response: result.output,
      metadata: result.metadata
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message || "Internal server error" });
  }
});

// إدارة المعرفة المحلية (حفظ مستند)
app.post("/api/knowledge/add", (req, res) => {
  try {
    const { title, content } = req.body;
    if (!title || !content) {
      return res.status(400).json({ error: "Title and content are required" });
    }
    const fileName = knowledgeBase.saveDocument(title, content);
    res.json({ success: true, fileName });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// البحث في المعرفة المحلية
app.post("/api/knowledge/search", (req, res) => {
  try {
    const { query } = req.body;
    if (!query) {
      return res.status(400).json({ error: "Query is required" });
    }
    const results = knowledgeBase.search(query);
    res.json({ results });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`[Lazaynova Autonomous Server] running on http://127.0.0.1:${PORT}`);
});
