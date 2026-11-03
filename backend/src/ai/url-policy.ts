export const ALLOWED_HOSTS = new Set(["127.0.0.1", "localhost", "::1"]);
export const ALLOWED_PORTS = new Set([8080, 11434]);

export class ExternalUrlBlockedError extends Error {
  constructor(msg: string) { super(msg); this.name = "ExternalUrlBlockedError"; }
}
export class ExternalKeyDetectedError extends Error {
  constructor(msg: string) { super(msg); this.name = "ExternalKeyDetectedError"; }
}

export function assertSafeUrl(raw: string): URL {
  let u: URL;
  try { u = new URL(raw); }
  catch { throw new ExternalUrlBlockedError(`Invalid URL: ${raw}`); }

  if (u.protocol !== "http:") {
    throw new ExternalUrlBlockedError(`Blocked protocol: ${u.protocol}`);
  }
  if (!ALLOWED_HOSTS.has(u.hostname)) {
    throw new ExternalUrlBlockedError(`Blocked host: ${u.hostname}`);
  }
  const port = Number(u.port || 80);
  if (!ALLOWED_PORTS.has(port)) {
    throw new ExternalUrlBlockedError(`Blocked port: ${port}`);
  }
  return u;
}

const KEY_PATTERNS: RegExp[] = [
  /sk-ant-[A-Za-z0-9\-_]{20,}/,
  /sk-[A-Za-z0-9]{20,}/,
  /AIza[0-9A-Za-z\-_]{35}/,
];

const FORBIDDEN_HEADERS = [
  "x-api-key",
  "openai-organization",
  "anthropic-version",
  "api-key",
];

export function assertNoExternalKeys(payload: string, headers: Headers): void {
  for (const h of FORBIDDEN_HEADERS) {
    if (headers.has(h)) {
      throw new ExternalKeyDetectedError(`Forbidden header: ${h}`);
    }
  }
  for (const p of KEY_PATTERNS) {
    if (p.test(payload)) {
      throw new ExternalKeyDetectedError("External API key found in payload");
    }
  }
}
