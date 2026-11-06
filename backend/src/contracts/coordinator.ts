import { z } from "zod";

export const CoordinatorRequestSchema = z.object({
  message: z.string().trim().min(1).max(12_000),
  engineId: z.string().trim().min(1).max(32).optional(),
  maxTokens: z.number().int().min(1).max(96).optional()
}).strict();

export type CoordinatorRequest = z.infer<
  typeof CoordinatorRequestSchema
>;

export type SupportedEngine =
  | "chat"
  | "research"
  | "coding"
  | "documents"
  | "agent";

export type RequestLanguage = "ar" | "en";

export type TaskIntent =
  | "chat"
  | "research"
  | "coding"
  | "documents";

export type KnowledgeSource = {
  title: string;
  source: string;
  score: number;
};

export type CoordinatorResponse = {
  requestId: string;
  answer: string;
  engineId: SupportedEngine;
  intent: TaskIntent;
  language: RequestLanguage;
  model: string;
  sources: KnowledgeSource[];
  durationMs: number;
};
