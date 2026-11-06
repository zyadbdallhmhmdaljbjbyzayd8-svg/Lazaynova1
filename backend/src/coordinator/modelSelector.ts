import { CoordinatorError } from "./errors.js";

export type GatewayModelStatus = {
  native_l3?: string;
  checkpoint_exists?: boolean;
};

export type SelectedModel = {
  id: "LAZAYNOVA-L3-native-v2";
  engine: "L3";
  status: "READY_NATIVE_SCRATCH_V2";
};

export class ModelSelector {
  select(status: GatewayModelStatus): SelectedModel {
    if (status.native_l3 !== "READY_NATIVE_SCRATCH_V2") {
      throw new CoordinatorError(
        `Native L3 is not ready; gateway status: ${status.native_l3 ?? "UNKNOWN"}`,
        "MODEL_NOT_READY",
        503
      );
    }

    return {
      id: "LAZAYNOVA-L3-native-v2",
      engine: "L3",
      status: "READY_NATIVE_SCRATCH_V2"
    };
  }
}
