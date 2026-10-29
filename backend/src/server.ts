import "dotenv/config";
import express, { Request, Response, NextFunction } from "express";
import cors from "cors";
import helmet from "helmet";
import { z } from "zod";

// Old imports
import { knowledgeRouter } from "./knowledge-routes.js";
import { listEngines } from "./engines.js";
import { buildSpecialistRequest } from "./engine-runtime.js";

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

    // Route the request through the tested specialist runtime.
    const routed = buildSpecialistRequest(
      parsed.message,
      parsed.history ?? []
    );
    const response = await gateway.chat(routed.request);

    res.json({
      type: "chat",
      intent: routed.engineId,
      engine: routed.engineName,
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
