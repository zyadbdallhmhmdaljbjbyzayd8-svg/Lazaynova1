import type { KnowledgeSource } from "../contracts/coordinator.js";
import type { RetrievedKnowledge } from "./knowledgeConnector.js";
import { CoordinatorError } from "./errors.js";

export type PreparedContext = {
  prompt: string;
  sources: KnowledgeSource[];
  promptBytes: number;
  knowledgeIncluded: boolean;
};

export class ContextManager {
  constructor(private readonly maxPromptBytes = 128) {}

  prepare(
    question: string,
    knowledge: RetrievedKnowledge[]
  ): PreparedContext {
    const questionBytes = Buffer.byteLength(question, "utf8");

    if (questionBytes > this.maxPromptBytes) {
      throw new CoordinatorError(
        `Question requires ${questionBytes} UTF-8 bytes; current L3 context limit is ${this.maxPromptBytes} bytes`,
        "CONTEXT_LIMIT_EXCEEDED",
        413
      );
    }

    // The user question always takes priority over retrieved context.
    // Include knowledge only when the complete prompt still fits L3.
    for (const item of knowledge.slice(0, 3)) {
      const snippet = `${item.title}: ${item.text}`.trim();
      const prompt = `معلومة: ${snippet}\nسؤال: ${question}`;

      if (Buffer.byteLength(prompt, "utf8") <= this.maxPromptBytes) {
        return {
          prompt,
          sources: [{
            title: item.title,
            source: item.source,
            score: Number(item.score.toFixed(3))
          }],
          promptBytes: Buffer.byteLength(prompt, "utf8"),
          knowledgeIncluded: true
        };
      }
    }

    return {
      prompt: question,
      sources: [],
      promptBytes: questionBytes,
      knowledgeIncluded: false
    };
  }
}
