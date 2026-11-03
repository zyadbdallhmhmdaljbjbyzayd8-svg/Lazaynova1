import { z } from "zod";
import {
  assertSafeUrl,
  assertNoExternalKeys,
} from "./url-policy.js";

const ChatRequestSchema = z.object({
  model: z.string().min(1).optional(),
  messages: z.array(
    z.object({
      role: z.enum(["system", "user", "assistant", "tool"]),
      content: z.string(),
    })
  ),
  temperature: z.number().min(0).max(2).optional(),
  stream: z.boolean().optional(),
  max_tokens: z.number().int().positive().optional(),
});

export type ChatRequest = z.infer<typeof ChatRequestSchema>;

export interface GatewayOptions {
  baseUrl?: string;
  defaultModel?: string;
  timeoutMs?: number;
}

export class InternalAIGateway {
  private readonly baseUrl: string;
  private readonly defaultModel: string;
  private readonly timeoutMs: number;

  constructor(opts: GatewayOptions = {}) {
    this.baseUrl =
      opts.baseUrl ??
      process.env.LOCAL_LLM_BASE_URL ??
      "http://127.0.0.1:8080/v1";
    this.defaultModel =
      opts.defaultModel ?? process.env.LOCAL_LLM_MODEL ?? "lazaynova-core";
    this.timeoutMs = Number(
      opts.timeoutMs ?? process.env.LOCAL_LLM_TIMEOUT_MS ?? 60_000
    );

    // Fail fast on construction if base URL is unsafe.
    assertSafeUrl(this.baseUrl);
  }

  async chat(input: unknown): Promise<any> {
    const req = ChatRequestSchema.parse(input);
    const body = JSON.stringify({
      ...req,
      model: req.model ?? this.defaultModel,
    });

    const headers = new Headers({ "content-type": "application/json" });
    assertNoExternalKeys(body, headers);

    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs);
    try {
      const res = await fetch(`${this.baseUrl}/chat/completions`, {
        method: "POST",
        headers,
        body,
        signal: ctrl.signal,
      });
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(
          `Local LLM error ${res.status}: ${text.slice(0, 200)}`
        );
      }
      return await res.json();
    } finally {
      clearTimeout(timer);
    }
  }

  async health(): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/models`, { method: "GET" });
      return res.ok;
    } catch {
      return false;
    }
  }
}
