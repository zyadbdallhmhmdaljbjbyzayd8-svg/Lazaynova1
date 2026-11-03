import type { Intent, IntentKind } from "./types.js";

interface Signal {
  weight: number;
  re: RegExp;
}

const SIGNALS: Record<Exclude<IntentKind, "chat">, Signal[]> = {
  coding: [
    {
      weight: 1,
      re: /\b(code|function|bug|debug|stack ?trace|refactor|compile|typescript|python|kotlin|rust|java|sql)\b/i,
    },
    { weight: 1, re: /(?:كود|برمج|دالة|خطأ|باگ|تصحيح)/ },
    { weight: 1, re: /```[\s\S]*?```/ },
  ],
  writing: [
    {
      weight: 1,
      re: /\b(write|draft|email|essay|letter|blog|article|compose)\b/i,
    },
    { weight: 1, re: /(?:اكتب|رسالة|ايميل|بريد|مقال|خطاب|صياغة)/ },
  ],
  document_analysis: [
    {
      weight: 1,
      re: /\b(summar(?:y|ize)|analy[sz]e|document|pdf|extract|translat)\w*/i,
    },
    { weight: 1, re: /(?:لخص|ملخص|تحليل|حلل|مستند|ملف|ترجم)/ },
  ],
  automation: [
    {
      weight: 1,
      re: /\b(cron|schedule|automate|automation|workflow|pipeline|trigger|webhook)\b/i,
    },
    { weight: 1, re: /(?:شغل|جدول|أتمتة|أتمت|مؤقت|تلقائي)/ },
  ],
};

const RTL_RE = /[\u0600-\u06FF]/;

export class IntentRouter {
  classify(text: string): Intent {
    const trimmed = (text ?? "").trim();
    if (!trimmed) {
      return { kind: "chat", confidence: 0, locale: "en" };
    }

    const locale: "ar" | "en" = RTL_RE.test(trimmed) ? "ar" : "en";

    const scores: Record<IntentKind, number> = {
      chat: 0.25,
      writing: 0,
      coding: 0,
      document_analysis: 0,
      automation: 0,
    };

    for (const kind of Object.keys(SIGNALS) as Array<
      Exclude<IntentKind, "chat">
    >) {
      for (const sig of SIGNALS[kind]) {
        if (sig.re.test(trimmed)) scores[kind] += sig.weight;
      }
    }

    const entries = (Object.entries(scores) as Array<[IntentKind, number]>).sort(
      (a, b) => b[1] - a[1]
    );
    const [kind, raw] = entries[0];
    return { kind, confidence: Math.min(1, raw / 3), locale };
  }
}
