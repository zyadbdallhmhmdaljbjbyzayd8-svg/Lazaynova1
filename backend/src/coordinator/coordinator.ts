import { randomUUID } from "node:crypto";
import {
  CoordinatorRequestSchema,
  type CoordinatorRequest,
  type CoordinatorResponse,
  type SupportedEngine,
  type TaskIntent
} from "../contracts/coordinator.js";
import { AuditLogger } from "./auditLogger.js";
import { ContextManager } from "./contextManager.js";
import { CoordinatorError } from "./errors.js";
import { IntentRouter } from "./intentRouter.js";
import { KnowledgeConnector } from "./knowledgeConnector.js";
import { ModelSelector } from "./modelSelector.js";
import { RequestAnalyzer } from "./requestAnalyzer.js";
import type { GatewayPort } from "./taskDispatcher.js";
import { LocalGatewayDispatcher } from "./taskDispatcher.js";
import { ResultValidator } from "./resultValidator.js";

type KnowledgePort = {
  search(query: string, limit?: number): Array<{
    title: string;
    source: string;
    text: string;
    score: number;
  }>;
};

type AuditPort = {
  log(event: Parameters<AuditLogger["log"]>[0]): void;
};

export type CoordinatorDependencies = {
  gateway?: GatewayPort;
  knowledge?: KnowledgePort;
  audit?: AuditPort;
};

export class Coordinator {
  private readonly analyzer = new RequestAnalyzer();
  private readonly router = new IntentRouter();
  private readonly selector = new ModelSelector();
  private readonly context = new ContextManager(128);
  private readonly validator = new ResultValidator();

  private readonly gateway: GatewayPort;
  private readonly knowledge: KnowledgePort;
  private readonly audit: AuditPort;

  constructor(dependencies: CoordinatorDependencies = {}) {
    this.gateway =
      dependencies.gateway ?? new LocalGatewayDispatcher();
    this.knowledge =
      dependencies.knowledge ?? new KnowledgeConnector();
    this.audit =
      dependencies.audit ?? new AuditLogger();
  }

  async execute(input: unknown): Promise<CoordinatorResponse> {
    const requestId = randomUUID();
    const startedAt = Date.now();

    let engineId: SupportedEngine | undefined;
    let intent: TaskIntent | undefined;
    let sourceCount = 0;

    try {
      const parsed = CoordinatorRequestSchema.safeParse(input);

      if (!parsed.success) {
        throw new CoordinatorError(
          "Invalid coordinator request",
          "INVALID_REQUEST",
          400
        );
      }

      const request: CoordinatorRequest = parsed.data;
      const analyzed = this.analyzer.analyze(request);
      const route = this.router.route(analyzed);

      engineId = route.engineId;
      intent = route.intent;

      // Status endpoint validates/loads the configured V2 checkpoint.
      const modelStatus = await this.gateway.getModelStatus();
      const model = this.selector.select(modelStatus);

      const retrieved = this.knowledge.search(
        analyzed.message,
        5
      );

      const prepared = this.context.prepare(
        analyzed.message,
        retrieved
      );

      sourceCount = prepared.sources.length;

      const completion = await this.gateway.complete(
        prepared.prompt,
        request.maxTokens ?? 48
      );

      const answer = this.validator.validate(
        completion.answer
      );

      const durationMs = Date.now() - startedAt;

      this.audit.log({
        requestId,
        engineId: engineId ?? "unresolved",
        intent: intent ?? "unresolved",
        outcome: "success",
        durationMs,
        sourceCount
      });

      return {
        requestId,
        answer,
        engineId,
        intent,
        language: analyzed.language,
        model: completion.model || model.id,
        sources: prepared.sources,
        durationMs
      };
    } catch (error) {
      const durationMs = Date.now() - startedAt;
      const known = error instanceof CoordinatorError;

      this.audit.log({
        requestId,
        engineId: engineId ?? "unresolved",
        intent: intent ?? "unresolved",
        outcome: "failure",
        durationMs,
        sourceCount,
        errorCode: known ? error.code : "INTERNAL_ERROR"
      });

      if (known) throw error;

      throw new CoordinatorError(
        "Coordinator execution failed",
        "INTERNAL_ERROR",
        500
      );
    }
  }
}
