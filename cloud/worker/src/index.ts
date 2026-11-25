interface Env {
  AI_BASE_URL: string;
  AI_API_KEY: string;
  AI_MODEL: string;
  AUTH_TOKEN: string;
  ALLOWED_ORIGIN: string;
}

interface ChatRequest {
  messages: Array<{
    role: "system" | "user" | "assistant";
    content: string;
  }>;
}

const json = (data: unknown, status = 200, headers = {}) =>
  new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      ...headers
    }
  });

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const origin = request.headers.get("Origin") || "";
    const allowed = origin === env.ALLOWED_ORIGIN;

    const cors = {
      "access-control-allow-origin": allowed ? origin : env.ALLOWED_ORIGIN,
      "access-control-allow-methods": "GET, POST, OPTIONS",
      "access-control-allow-headers": "Content-Type, Authorization",
      "vary": "Origin"
    };

    if (request.method === "OPTIONS") {
      if (origin && !allowed) return new Response(null, { status: 403 });
      return new Response(null, { status: 204, headers: cors });
    }

    const url = new URL(request.url);

    if (url.pathname === "/health" && request.method === "GET") {
      return json({ status: "ok", service: "Lazaynova AI" }, 200, cors);
    }

    if (url.pathname !== "/v1/chat" || request.method !== "POST") {
      return json({ error: "Not found" }, 404, cors);
    }

    if (origin && !allowed) {
      return json({ error: "Origin not allowed" }, 403, cors);
    }

    if (
      !env.AUTH_TOKEN ||
      request.headers.get("Authorization") !== `Bearer ${env.AUTH_TOKEN}`
    ) {
      return json({ error: "Unauthorized" }, 401, cors);
    }

    const length = Number(request.headers.get("Content-Length") || 0);
    if (length > 100_000) {
      return json({ error: "Request too large" }, 413, cors);
    }

    let body: ChatRequest;

    try {
      body = await request.json() as ChatRequest;
    } catch {
      return json({ error: "Invalid JSON" }, 400, cors);
    }

    if (
      !Array.isArray(body.messages) ||
      body.messages.length < 1 ||
      body.messages.length > 40 ||
      body.messages.some(m =>
        !m ||
        !["system", "user", "assistant"].includes(m.role) ||
        typeof m.content !== "string" ||
        m.content.length > 12000
      )
    ) {
      return json({ error: "Invalid messages" }, 400, cors);
    }

    if (
      !env.AI_BASE_URL ||
      !env.AI_API_KEY ||
      !env.AI_MODEL ||
      env.AI_BASE_URL.includes("example.com")
    ) {
      return json({ error: "AI provider is not configured" }, 503, cors);
    }

    try {
      const upstream = await fetch(
        `${env.AI_BASE_URL.replace(/\/+$/, "")}/chat/completions`,
        {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${env.AI_API_KEY}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            model: env.AI_MODEL,
            messages: body.messages,
            temperature: 0.7,
            stream: false
          }),
          signal: AbortSignal.timeout(60000)
        }
      );

      const result = await upstream.json();

      if (!upstream.ok) {
        return json({
          error: "AI provider request failed",
          status: upstream.status
        }, 502, cors);
      }

      const data = result as {
        choices?: Array<{ message?: { content?: string } }>;
      };

      return json({
        model: env.AI_MODEL,
        reply: data.choices?.[0]?.message?.content ?? ""
      }, 200, cors);

    } catch {
      return json({ error: "AI provider unavailable" }, 502, cors);
    }
  }
};