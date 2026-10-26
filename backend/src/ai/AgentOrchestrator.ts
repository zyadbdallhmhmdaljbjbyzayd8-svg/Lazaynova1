import type {
  LLMClient,
  Plan,
  Step,
  StepResult,
  VerificationResult,
} from "./types.js";

const SYSTEM_PLANNER = `You are a planner. Output ONLY a JSON array of steps in this shape:
[{"id":"s1","description":"..."}, ...]
No prose, no markdown fences, no explanation.`;

const SYSTEM_VERIFIER = `You are a strict verifier. Answer only YES or NO.`;

export interface OrchestratorOptions {
  maxAttempts?: number;
  model?: string;
}

export interface OrchestratorRun {
  plan: Plan;
  results: StepResult[];
  verification: VerificationResult;
}

export class AgentOrchestrator {
  private readonly maxAttempts: number;
  private readonly model: string;

  constructor(
    private readonly llm: LLMClient,
    opts: OrchestratorOptions = {}
  ) {
    this.maxAttempts = Math.max(1, opts.maxAttempts ?? 2);
    this.model = opts.model ?? "lazaynova-core";
  }

  async run(goal: string): Promise<OrchestratorRun> {
    const plan = await this.planner(goal);
    const results = await this.executor(plan);
    const verification = await this.verifier(goal, results);
    return { plan, results, verification };
  }

  async planner(goal: string): Promise<Plan> {
    const res = await this.llm.chat({
      model: this.model,
      messages: [
        { role: "system", content: SYSTEM_PLANNER },
        { role: "user", content: goal },
      ],
    });
    const steps = parsePlan(extractContent(res));
    return { goal, steps };
  }

  async executor(plan: Plan): Promise<StepResult[]> {
    const out: StepResult[] = [];
    for (const step of plan.steps) {
      out.push(await this.runStep(step));
    }
    return out;
  }

  async verifier(
    goal: string,
    results: StepResult[]
  ): Promise<VerificationResult> {
    if (results.some((r) => !r.ok)) {
      const failed = results.filter((r) => !r.ok).map((r) => r.stepId);
      return {
        passed: false,
        reason: `steps failed: ${failed.join(", ")}`,
      };
    }
    const summary = results.map((r) => r.output ?? "").join("\n---\n");
    try {
      const res = await this.llm.chat({
        model: this.model,
        messages: [
          { role: "system", content: SYSTEM_VERIFIER },
          {
            role: "user",
            content: `GOAL:\n${goal}\n\nWORK:\n${summary}\n\nDoes the work satisfy the goal? Answer YES or NO.`,
          },
        ],
      });
      const content = extractContent(res).trim();
      return /^yes\b/i.test(content)
        ? { passed: true, reason: "verifier accepted" }
        : {
            passed: false,
            reason: `verifier rejected: ${content.slice(0, 120)}`,
          };
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return { passed: false, reason: `verifier error: ${msg}` };
    }
  }

  private async runStep(step: Step): Promise<StepResult> {
    let lastError = "";
    for (let attempt = 1; attempt <= this.maxAttempts; attempt++) {
      try {
        const res = await this.llm.chat({
          model: this.model,
          messages: [{ role: "user", content: step.description }],
        });
        const output = extractContent(res);
        if (output && output.length > 0) {
          return { stepId: step.id, ok: true, output };
        }
        lastError = `empty output (attempt ${attempt})`;
      } catch (err) {
        lastError = err instanceof Error ? err.message : String(err);
      }
    }
    return { stepId: step.id, ok: false, error: lastError };
  }
}

function extractContent(res: unknown): string {
  if (typeof res === "string") return res;
  const anyRes = res as any;
  const content = anyRes?.choices?.[0]?.message?.content;
  return typeof content === "string" ? content : "";
}

function parsePlan(content: string): Step[] {
  const fence = content.match(/```(?:json)?\s*([\s\S]*?)```/);
  const raw = (fence ? fence[1] : content).trim();
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error(`Planner returned non-JSON: ${raw.slice(0, 120)}`);
  }
  if (!Array.isArray(parsed)) {
    throw new Error("Planner did not return an array");
  }
  return parsed.map((s: any, i: number): Step => {
    if (typeof s === "string") return { id: `s${i + 1}`, description: s };
    if (typeof s?.description === "string") {
      return {
        id: typeof s.id === "string" ? s.id : `s${i + 1}`,
        description: s.description,
      };
    }
    throw new Error(`Invalid step at index ${i}`);
  });
}
