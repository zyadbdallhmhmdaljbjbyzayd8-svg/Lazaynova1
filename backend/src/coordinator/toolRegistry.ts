import { CoordinatorError } from "./errors.js";

export type RegisteredTool = {
  name: string;
  description: string;
  execute: (input: unknown) => Promise<unknown> | unknown;
};

export class ToolRegistry {
  private readonly tools = new Map<string, RegisteredTool>();

  register(tool: RegisteredTool): void {
    if (!tool.name.trim()) {
      throw new CoordinatorError(
        "Tool name is required",
        "INVALID_TOOL",
        400
      );
    }

    if (this.tools.has(tool.name)) {
      throw new CoordinatorError(
        `Tool already registered: ${tool.name}`,
        "DUPLICATE_TOOL",
        409
      );
    }

    this.tools.set(tool.name, tool);
  }

  has(name: string): boolean {
    return this.tools.has(name);
  }

  list(): Array<Pick<RegisteredTool, "name" | "description">> {
    return [...this.tools.values()].map(
      ({ name, description }) => ({ name, description })
    );
  }

  async execute(name: string, input: unknown): Promise<unknown> {
    const tool = this.tools.get(name);

    if (!tool) {
      throw new CoordinatorError(
        `Tool is not registered: ${name}`,
        "UNKNOWN_TOOL",
        404
      );
    }

    return tool.execute(input);
  }
}
