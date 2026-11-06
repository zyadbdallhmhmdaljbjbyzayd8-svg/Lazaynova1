import { CoordinatorError } from "./errors.js";

export class ResultValidator {
  validate(answer: unknown): string {
    if (typeof answer !== "string") {
      throw new CoordinatorError(
        "Model output must be text",
        "INVALID_MODEL_OUTPUT",
        502
      );
    }

    const cleaned = answer.trim();

    if (!cleaned || cleaned.length > 12_000) {
      throw new CoordinatorError(
        "Model output is empty or exceeds the response limit",
        "INVALID_MODEL_OUTPUT",
        502
      );
    }

    return cleaned;
  }
}
