import type {
  SupportedEngine,
  TaskIntent
} from "../contracts/coordinator.js";
import type { AnalyzedRequest } from "./requestAnalyzer.js";

export type RouteDecision = {
  engineId: SupportedEngine;
  intent: TaskIntent;
  executionMode: "local_text";
};

export class IntentRouter {
  route(request: AnalyzedRequest): RouteDecision {
    if (request.explicitEngine === "agent") {
      return {
        engineId: "agent",
        intent: request.intent,
        executionMode: "local_text"
      };
    }

    const engineId: SupportedEngine = request.explicitEngine
      ?? request.intent;

    return {
      engineId,
      intent: request.intent,
      executionMode: "local_text"
    };
  }
}
