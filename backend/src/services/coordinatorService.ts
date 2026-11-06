import {
  Coordinator,
  type CoordinatorDependencies
} from "../coordinator/coordinator.js";

export class CoordinatorService {
  private readonly coordinator: Coordinator;

  constructor(dependencies: CoordinatorDependencies = {}) {
    this.coordinator = new Coordinator(dependencies);
  }

  execute(input: unknown) {
    return this.coordinator.execute(input);
  }
}
