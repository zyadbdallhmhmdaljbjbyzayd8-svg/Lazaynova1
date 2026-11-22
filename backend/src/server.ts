import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import authRouter, { requireAuth } from "./auth.js";
import { EngineManager } from "./engines/engineManager.js";
import { AgentOrchestrator } from "./orchestrator/agentOrchestrator.js";
import { CoordinatorService } from "./services/coordinatorService.js";
import {
  createConversation,
  listConversations,
  getConversation,
  listMessages,
  addMessage,
  archiveConversation,
  getPreferences,
  savePreferences,
  saveKnowledgeDocument,
  searchKnowledgeDocuments,
  listKnowledgeDocuments,
  deleteKnowledgeDocumentForUser
} from "./userData.js";

dotenv.config();

const app = express();
const PORT = Number.parseInt(process.env.PORT || "8787", 10);
const engineManager = new EngineManager();
const orchestrator = new AgentOrchestrator();
const coordinatorService = new CoordinatorService();

app.disable("x-powered-by");
app.use(cors());
app.use(express.json({ limit: "1mb" }));
app.use("/api/auth", authRouter);

const allowedEngines = new Set([
  "chat", "research", "coding", "documents",
  "image", "video", "music", "agent"
]);

function userIdFrom(res: express.Response): string {
  return res.locals.userId as string;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unexpected error";
}

app.get("/health", (_req, res) => {
  res.json({
    status: "ok",
    service: "lazaynova-api",
    version: "1.1.0"
  });
});

app.get("/api/engines", (_req, res) => {
  res.json({
    engines: [
      { id: "chat", name: "محرك المحادثة", description: "محادثة عامة وتنسيق الطلبات", mode: "text" },
      { id: "research", name: "محرك البحث والتحليل", description: "تحليل الاستعلامات والمعرفة", mode: "text" },
      { id: "coding", name: "محرك البرمجة", description: "توليد الأكواد وتصحيحها", mode: "text" },
      { id: "documents", name: "محرك المستندات", description: "صياغة المستندات وتلخيصها", mode: "text" },
      { id: "image", name: "محرك الصور", description: "إعداد الأوصاف والخطط البصرية", mode: "prompt" },
      { id: "video", name: "محرك الفيديو", description: "كتابة السيناريو وتقسيم المشاهد", mode: "text" },
      { id: "music", name: "محرك الموسيقى", description: "أفكار وهياكل الألحان", mode: "text" },
      { id: "agent", name: "محرك تنسيق الوكلاء", description: "تخطيط وتنفيذ ومراجعة المهام", mode: "multi-agent" }
    ]
  });
});

// كل واجهات بيانات المستخدم تتطلب رمز دخول صالحًا.
app.get("/api/conversations", requireAuth, async (_req, res) => {
  try {
    res.json({ conversations: await listConversations(userIdFrom(res)) });
  } catch (error) {
    console.error("List conversations failed:", error);
    res.status(500).json({ error: "Could not load conversations" });
  }
});

app.post("/api/conversations", requireAuth, async (req, res) => {
  try {
    const title = typeof req.body?.title === "string" ? req.body.title : "محادثة جديدة";
    const engineId = typeof req.body?.engineId === "string" ? req.body.engineId : "chat";
    if (!allowedEngines.has(engineId)) {
      return res.status(400).json({ error: "Unknown engine" });
    }
    const conversation = await createConversation(userIdFrom(res), title, engineId);
    return res.status(201).json({ conversation });
  } catch (error) {
    console.error("Create conversation failed:", error);
    return res.status(500).json({ error: "Could not create conversation" });
  }
});

app.get("/api/conversations/:id/messages", requireAuth, async (req, res) => {
  try {
    const userId = userIdFrom(res);
    const conversation = await getConversation(userId, String(req.params.id));
    if (!conversation) return res.status(404).json({ error: "Conversation not found" });
    const messages = await listMessages(userId, String(req.params.id));
    return res.json({ conversation, messages });
  } catch (error) {
    console.error("Load messages failed:", error);
    return res.status(500).json({ error: "Could not load messages" });
  }
});

app.delete("/api/conversations/:id", requireAuth, async (req, res) => {
  try {
    const archived = await archiveConversation(userIdFrom(res), String(req.params.id));
    if (!archived) return res.status(404).json({ error: "Conversation not found" });
    return res.json({ success: true });
  } catch (error) {
    console.error("Archive conversation failed:", error);
    return res.status(500).json({ error: "Could not archive conversation" });
  }
});

app.post("/api/chat", requireAuth, async (req, res) => {
  const userId = userIdFrom(res);
  let conversationId: string | undefined;

  try {
    const {
      message,
      engineId = "chat",
      useOrchestrator = true,
      maxTokens = 48,
      conversationId: requestedConversationId
    } = req.body ?? {};

    if (typeof message !== "string" || !message.trim()) {
      return res.status(400).json({ error: "Message is required" });
    }
    if (message.length > 50000) {
      return res.status(413).json({ error: "Message is too large" });
    }
    if (typeof engineId !== "string" || !allowedEngines.has(engineId)) {
      return res.status(400).json({ error: "Unknown engine" });
    }
    if (!Number.isInteger(maxTokens) || maxTokens < 1 || maxTokens > 96) {
      return res.status(400).json({ error: "maxTokens must be between 1 and 96" });
    }

    if (requestedConversationId !== undefined) {
      if (typeof requestedConversationId !== "string") {
        return res.status(400).json({ error: "Invalid conversationId" });
      }
      const owned = await getConversation(userId, requestedConversationId);
      if (!owned) return res.status(404).json({ error: "Conversation not found" });
      conversationId = owned.id;
    } else {
      const conversation = await createConversation(
        userId,
        message.trim().slice(0, 80),
        engineId
      );
      conversationId = conversation.id;
    }

    if (!conversationId) {
      return res.status(400).json({ error: "Conversation could not be created" });
    }
    const activeConversationId = conversationId;

    const userMessage = await addMessage({
      userId,
      conversationId: activeConversationId,
      role: "user",
      content: message.trim(),
      engineId
    });

    let responseText: string;
    let metadata: Record<string, unknown>;

    if (useOrchestrator === true && engineId === "agent") {
      const result = await orchestrator.runWorkflow(message.trim(), engineId);
      responseText = `${result.plan}\n\n${result.execution}\n\n${result.review}`;
      metadata = {
        orchestrator: true,
        sources: result.knowledgeSourcesCount
      };
    } else if (["chat", "research", "coding", "documents"].includes(engineId)) {
      const result = await coordinatorService.execute({
        message: message.trim(),
        engineId,
        maxTokens
      });
      responseText = result.answer;
      metadata = {
        coordinator: true,
        requestId: result.requestId,
        engineId: result.engineId,
        intent: result.intent,
        language: result.language,
        model: result.model,
        sources: result.sources,
        durationMs: result.durationMs
      };
    } else {
      const result = await engineManager.execute(engineId, message.trim());
      responseText = result.output;
      metadata = result.metadata as Record<string, unknown>;
    }

    const assistantMessage = await addMessage({
      userId,
      conversationId: activeConversationId,
      role: "assistant",
      content: responseText,
      engineId,
      metadata
    });

    return res.json({
      response: responseText,
      conversationId,
      userMessage,
      assistantMessage,
      metadata
    });
  } catch (error) {
    console.error("Chat request failed:", error);
    return res.status(502).json({
      error: "The AI request could not be completed",
      conversationId
    });
  }
});

app.get("/api/preferences", requireAuth, async (_req, res) => {
  try {
    res.json({ preferences: await getPreferences(userIdFrom(res)) });
  } catch (error) {
    console.error("Load preferences failed:", error);
    res.status(500).json({ error: "Could not load preferences" });
  }
});

app.put("/api/preferences", requireAuth, async (req, res) => {
  try {
    const body = req.body ?? {};
    if (body.settings !== undefined &&
        (body.settings === null || typeof body.settings !== "object" || Array.isArray(body.settings))) {
      return res.status(400).json({ error: "settings must be an object" });
    }
    if (body.settings !== undefined && JSON.stringify(body.settings).length > 20000) {
      return res.status(413).json({ error: "Settings are too large" });
    }
    const preferences = await savePreferences(userIdFrom(res), {
      theme: body.theme,
      language: body.language,
      settings: body.settings
    });
    return res.json({ preferences });
  } catch (error) {
    const message = errorMessage(error);
    if (message.startsWith("Invalid ")) return res.status(400).json({ error: message });
    console.error("Save preferences failed:", error);
    return res.status(500).json({ error: "Could not save preferences" });
  }
});

app.get("/api/knowledge", requireAuth, async (_req, res) => {
  try {
    res.json({ documents: await listKnowledgeDocuments(userIdFrom(res)) });
  } catch (error) {
    console.error("List knowledge failed:", error);
    res.status(500).json({ error: "Could not load documents" });
  }
});

app.post("/api/knowledge/add", requireAuth, async (req, res) => {
  try {
    const { title, content } = req.body ?? {};
    if (typeof title !== "string" || typeof content !== "string" ||
        !title.trim() || !content.trim()) {
      return res.status(400).json({ error: "Title and content are required" });
    }
    const document = await saveKnowledgeDocument(userIdFrom(res), title, content);
    return res.status(201).json({ success: true, document });
  } catch (error) {
    const message = errorMessage(error);
    if (message.includes("required") || message.includes("too large")) {
      return res.status(400).json({ error: message });
    }
    console.error("Save knowledge failed:", error);
    return res.status(500).json({ error: "Could not save document" });
  }
});

app.post("/api/knowledge/search", requireAuth, async (req, res) => {
  try {
    const query = req.body?.query;
    if (typeof query !== "string" || !query.trim()) {
      return res.status(400).json({ error: "Query is required" });
    }
    const results = await searchKnowledgeDocuments(userIdFrom(res), query);
    return res.json({ results });
  } catch (error) {
    console.error("Knowledge search failed:", error);
    return res.status(500).json({ error: "Could not search documents" });
  }
});

app.delete("/api/knowledge/:id", requireAuth, async (req, res) => {
  try {
    const deleted = await deleteKnowledgeDocumentForUser(userIdFrom(res), String(req.params.id));
    if (!deleted) return res.status(404).json({ error: "Document not found" });
    return res.json({ success: true });
  } catch (error) {
    console.error("Delete knowledge failed:", error);
    return res.status(500).json({ error: "Could not delete document" });
  }
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`[Lazaynova API] listening on port ${PORT}`);
});
