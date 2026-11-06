import type {
  CoordinatorRequest,
  RequestLanguage,
  SupportedEngine,
  TaskIntent
} from "../contracts/coordinator.js";
import { CoordinatorError } from "./errors.js";

export type AnalyzedRequest = {
  message: string;
  language: RequestLanguage;
  explicitEngine?: SupportedEngine;
  intent: TaskIntent;
};

const supportedEngines = new Set<string>([
  "chat",
  "research",
  "coding",
  "documents",
  "agent"
]);

export class RequestAnalyzer {
  analyze(request: CoordinatorRequest): AnalyzedRequest {
    const message = request.message.trim();

    if (!message) {
      throw new CoordinatorError(
        "Message is required",
        "EMPTY_MESSAGE",
        400
      );
    }

    let explicitEngine: SupportedEngine | undefined;

    if (request.engineId) {
      if (!supportedEngines.has(request.engineId)) {
        throw new CoordinatorError(
          `Engine is not supported by the current text coordinator: ${request.engineId}`,
          "UNSUPPORTED_ENGINE",
          422
        );
      }

      explicitEngine = request.engineId as SupportedEngine;
    }

    const language: RequestLanguage =
      /[\u0600-\u06FF]/.test(message) ? "ar" : "en";

    const intent = this.detectIntent(message, explicitEngine);

    return {
      message,
      language,
      explicitEngine,
      intent
    };
  }

  private detectIntent(
    message: string,
    engine?: SupportedEngine
  ): TaskIntent {
    if (engine === "research") return "research";
    if (engine === "coding") return "coding";
    if (engine === "documents") return "documents";

    if (/(ابحث|بحث|مصادر|مراجع|حلل|تحليل|research|sources|analy[sz]e)/i.test(message)) {
      return "research";
    }

    if (/(اكتب كود|برمج|تصحيح الكود|دالة|خوارزمية|code|program|debug|function|algorithm)/i.test(message)) {
      return "coding";
    }

    if (/(لخص|تلخيص|مستند|وثيقة|صياغة|رسالة رسمية|summari[sz]e|document|draft)/i.test(message)) {
      return "documents";
    }

    return "chat";
  }
}
