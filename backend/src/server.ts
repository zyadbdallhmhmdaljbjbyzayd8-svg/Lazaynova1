import "dotenv/config";

import express from "express";
import cors from "cors";
import helmet from "helmet";
import { z } from "zod";

import { InternalAIGateway } from "./ai/InternalAIGateway.js";
import { IntentRouter } from "./ai/IntentRouter.js";
import { AgentOrchestrator } from "./ai/AgentOrchestrator.js";

import {
  buildSpecialistRequest
} from "./engine-runtime.js";

import {
  isEngineId,
  listEngines,
  type EngineId
} from "./engines.js";

import { knowledgeRouter } from "./knowledge-routes.js";

const app = express();

const port = Number(process.env.PORT || 8787);

if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error("Invalid PORT configuration");
}

app.disable("x-powered-by");

app.use(helmet());

const allowedOrigins = process.env.CORS_ORIGIN
  ?.split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

app.use(
  cors({
    origin: allowedOrigins?.length ? allowedOrigins : false
  })
);

app.use(express.json({ limit: "256kb" }));

const gateway = new InternalAIGateway();
const intentRouter = new IntentRouter();
const orchestrator = new AgentOrchestrator(gateway);

const chatSchema = z.object({
  message: z.string().trim().min(1).max(12000),

  language: z.enum(["ar", "en"]).optional(),

  engineId: z.string().optional(),

  history: z.array(
    z.object({
      role: z.enum(["user", "assistant"]),
      content: z.string().max(12000)
    })
  ).max(20).optional()
});

function extractReply(result: unknown): string {
  if (typeof result === "string") {
    return result;
  }

  if (!result || typeof result !== "object") {
    return "";
  }

  const response = result as {
    choices?: Array<{
      message?: {
        content?: unknown;
      };
    }>;
  };

  const content = response.choices?.[0]?.message?.content;

  return typeof content === "string" ? content : "";
}

function formatAgentResult(result: Awaited<ReturnType<typeof orchestrator.run>>) {
  const steps = result.plan.steps.map((step, index) => {
    const output = result.results.find(
      (item) => item.stepId === step.id
    );

    return [
      `${index + 1}. ${step.description}`,
      output?.ok
        ? output.output
        : `تعذر تنفيذ الخطوة: ${output?.error ?? "Unknown error"}`
    ].join("\n");
  });

  return [
    "خطة التنفيذ:",
    ...steps,
    "",
    "نتيجة المراجعة:",
    result.verification.passed
      ? "اجتازت المراجعة."
      : `لم تجتز المراجعة: ${result.verification.reason}`
  ].join("\n");
}

app.get("/health", async (_req, res) => {
  const localModelAvailable = await gateway.health();

  res.json({
    status: "ok",
    service: "lazaynova-api",
    version: "1.0.0",
    localModelAvailable
  });
});

app.get("/api/engines", (_req, res) => {
  res.json({
    engines: listEngines()
  });
});

app.use("/api/knowledge", knowledgeRouter);

async function handleChat(
  req: express.Request,
  res: express.Response,
  forcedEngine?: string
) {
  const parsed = chatSchema.safeParse(req.body);

  if (!parsed.success) {
    res.status(400).json({
      error: "Invalid chat request",
      details: parsed.error.flatten()
    });
    return;
  }

  const {
    message,
    history = [],
    engineId
  } = parsed.data;

  let selectedEngine: EngineId;

  const explicitEngine = forcedEngine ?? engineId;

  if (explicitEngine !== undefined) {
    if (!isEngineId(explicitEngine)) {
      res.status(400).json({
        error: "Unsupported engine",
        engine: explicitEngine
      });
      return;
    }

    selectedEngine = explicitEngine;
  } else {
    const intent = intentRouter.classify(message);

    if (intent.kind === "automation") {
      selectedEngine = "agent";
    } else {
      selectedEngine = buildSpecialistRequest(message, history).engineId;
    }
  }

  try {
    if (selectedEngine === "agent") {
      const result = await orchestrator.run(message);
      const reply = formatAgentResult(result);

      res.json({
        type: "automation",
        engine: "agent",
        intent: "automation",
        reply,
        response: reply,
        verification: result.verification
      });

      return;
    }

    const routed = buildSpecialistRequest(
      message,
      history,
      selectedEngine
    );

    const result = await gateway.chat(routed.request);
    const reply = extractReply(result);

    if (!reply) {
      res.status(502).json({
        error: "Local AI gateway returned an empty response"
      });
      return;
    }

    res.json({
      type: "chat",
      engine: routed.engineId,
      intent: routed.engineId,
      reply,
      response: reply
    });
  } catch (error) {
    const detail = error instanceof Error
      ? error.message
      : "Unknown server error";

    console.error("[LAZAYNOVA] Request failed:", detail);

    res.status(502).json({
      error: "AI service unavailable",
      details: detail
    });
  }
}

// Android application endpoint.
app.post(
  "/api/engines/:engine/run",
  async (req, res) => {
    await handleChat(req, res, req.params.engine);
  }
);

// General chat endpoint.
app.post("/api/chat", async (req, res) => {
  await handleChat(req, res);
});

app.listen(port, "0.0.0.0", () => {
  console.log(
    `[LAZAYNOVA] Backend listening on port ${port}`
  );
});
