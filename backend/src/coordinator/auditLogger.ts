export type AuditEvent = {
  requestId: string;
  engineId: string;
  intent: string;
  outcome: "success" | "failure";
  durationMs: number;
  sourceCount: number;
  errorCode?: string;
};

export class AuditLogger {
  log(event: AuditEvent): void {
    // Never log prompts, generated content, credentials, or environment values.
    console.info(JSON.stringify({
      component: "coordinator",
      timestamp: new Date().toISOString(),
      ...event
    }));
  }
}
