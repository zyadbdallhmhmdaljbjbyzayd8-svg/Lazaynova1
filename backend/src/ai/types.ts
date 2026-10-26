export type IntentKind =
  | "chat"
  | "writing"
  | "coding"
  | "document_analysis"
  | "automation";

export interface Intent {
  kind: IntentKind;
  confidence: number; // 0..1
  locale: "ar" | "en";
}

export interface Step {
  id: string;
  description: string;
}

export interface Plan {
  goal: string;
  steps: Step[];
}

export interface StepResult {
  stepId: string;
  ok: boolean;
  output?: string;
  error?: string;
}

export interface VerificationResult {
  passed: boolean;
  reason: string;
}

/** Anything that can answer a chat-completions-style request. */
export interface LLMClient {
  chat(input: unknown): Promise<unknown>;
}
