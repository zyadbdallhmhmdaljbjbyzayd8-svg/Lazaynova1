import { CoordinatorError } from "./errors.js";
import type { GatewayModelStatus } from "./modelSelector.js";

type ChatCompletionPayload = {
  choices?: Array<{
    message?: {
      content?: string;
    };
  }>;
  error?: {
    message?: string;
    type?: string;
  };
};

export type GatewayCompletion = {
  model: string;
  answer: string;
};

export interface GatewayPort {
  getModelStatus(): Promise<GatewayModelStatus>;
  complete(prompt: string, maxTokens: number): Promise<GatewayCompletion>;
}

function localBaseUrl(): string {
  const configured =
    process.env.COORDINATOR_GATEWAY_URL
    || "http://127.0.0.1:8787";

  let url: URL;

  try {
    url = new URL(configured);
  } catch {
    throw new CoordinatorError(
      "Invalid local gateway URL",
      "INVALID_GATEWAY_URL",
      500
    );
  }

  const hostname = url.hostname.replace(/^\\[|\\]$/g, "");

  if (
    url.protocol !== "http:"
    || !["127.0.0.1", "localhost", "::1"].includes(hostname)
    || url.username
    || url.password
  ) {
    throw new CoordinatorError(
      "Coordinator permits HTTP loopback gateway URLs only",
      "EXTERNAL_GATEWAY_REJECTED",
      403
    );
  }

  return url.toString().replace(/\/+$/, "");
}

export class LocalGatewayDispatcher implements GatewayPort {
  private readonly baseUrl: string;

  constructor(
    private readonly fetchImpl: typeof fetch = fetch
  ) {
    this.baseUrl = localBaseUrl();
  }

  async getModelStatus(): Promise<GatewayModelStatus> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5_000);

    try {
      const response = await this.fetchImpl(
        `${this.baseUrl}/api/model/status`,
        {
          method: "GET",
          headers: { Accept: "application/json" },
          signal: controller.signal
        }
      );

      if (!response.ok) {
        throw new CoordinatorError(
          `Local gateway status returned HTTP ${response.status}`,
          "GATEWAY_STATUS_FAILED",
          503
        );
      }

      return await response.json() as GatewayModelStatus;
    } catch (error) {
      if (error instanceof CoordinatorError) throw error;

      throw new CoordinatorError(
        error instanceof Error && error.name === "AbortError"
          ? "Local gateway status timed out"
          : "Local gateway is unavailable",
        "GATEWAY_UNAVAILABLE",
        503
      );
    } finally {
      clearTimeout(timer);
    }
  }

  async complete(
    prompt: string,
    maxTokens: number
  ): Promise<GatewayCompletion> {
    // One bounded retry for temporary upstream gateway errors only.
    const maxRetries = 1;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      const controller = new AbortController();
      const timer = setTimeout(
        () => controller.abort(),
        90_000
      );

      try {
        const response = await this.fetchImpl(
          `${this.baseUrl}/v1/chat/completions`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              model: "LAZAYNOVA-L3-native-v2",
              messages: [{ role: "user", content: prompt }],
              temperature: 0,
              max_tokens: maxTokens,
              stream: false
            }),
            signal: controller.signal
          }
        );

        if (
          (response.status === 502 || response.status === 504)
          && attempt < maxRetries
        ) {
          continue;
        }

        if (!response.ok) {
          throw new CoordinatorError(
            `Local inference returned HTTP ${response.status}`,
            response.status === 503
              ? "MODEL_NOT_READY"
              : "INFERENCE_FAILED",
            response.status === 503 ? 503 : 502
          );
        }

        const data = await response.json() as ChatCompletionPayload;
        const answer = data.choices?.[0]?.message?.content?.trim();

        if (!answer) {
          throw new CoordinatorError(
            data.error?.message || "Local model returned an empty answer",
            "EMPTY_MODEL_OUTPUT",
            502
          );
        }

        return {
          model: "LAZAYNOVA-L3-native-v2",
          answer
        };
      } catch (error) {
        if (error instanceof CoordinatorError) throw error;

        throw new CoordinatorError(
          error instanceof Error && error.name === "AbortError"
            ? "Local inference timed out after 90 seconds"
            : "Local inference connection failed",
          error instanceof Error && error.name === "AbortError"
            ? "INFERENCE_TIMEOUT"
            : "GATEWAY_UNAVAILABLE",
          503
        );
      } finally {
        clearTimeout(timer);
      }
    }

    throw new CoordinatorError(
      "Local inference retry limit reached",
      "RETRY_LIMIT_REACHED",
      503
    );
  }
}
