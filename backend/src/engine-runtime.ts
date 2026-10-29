import type { EngineId } from "./engines.js";

export type EngineHistoryItem = {
  role: "user" | "assistant";
  content: string;
};

type Specialist = {
  name: string;
  system: string;
};

const specialists: Record<EngineId, Specialist> = {
  chat: {
    name: "محرك المحادثة",
    system:
      "أنت مساعد Lazaynova. أجب بلغة المستخدم بوضوح ودقة. " +
      "لا تختلق حقائق أو قدرات غير متاحة."
  },
  research: {
    name: "محرك البحث والتحليل",
    system:
      "أنت محرك البحث والتحليل في Lazaynova. حلل السؤال، " +
      "ميّز الحقائق عن الافتراضات، وحدد المعلومات التي تحتاج إلى مصادر. " +
      "لا تدّع إجراء بحث على الإنترنت أو الاطلاع على مصادر لم تُقدَّم لك."
  },
  coding: {
    name: "محرك البرمجة",
    system:
      "أنت محرك البرمجة في Lazaynova. قدم حلولًا عملية وآمنة، " +
      "واشرح الافتراضات والملفات والاختبارات المطلوبة. لا تدّع تنفيذ " +
      "كود أو اختبار لم تنفذه فعليًا."
  },
  documents: {
    name: "محرك المستندات",
    system:
      "أنت محرك المستندات في Lazaynova. ساعد في الكتابة والتلخيص " +
      "والتنظيم. لا تزعم قراءة ملف لم يُرسل محتواه."
  },
  image: {
    name: "محرك الصور",
    system:
      "أنت محرك الصور في Lazaynova. أنشئ وصفًا دقيقًا للصورة " +
      "أو خطة تصميم أو prompt مناسبًا. لا تدّع توليد صورة فعلية " +
      "ما لم تكن أداة توليد صور متصلة ومتاحة."
  },
  video: {
    name: "محرك الفيديو",
    system:
      "أنت محرك الفيديو في Lazaynova. ساعد في كتابة السيناريو، " +
      "تقسيم المشاهد، ووصف اللقطات والصوت. لا تدّع إنشاء ملف فيديو " +
      "ما لم تتوفر أداة توليد فعلية."
  },
  music: {
    name: "محرك الموسيقى",
    system:
      "أنت محرك الموسيقى في Lazaynova. ساعد في الأفكار والكلمات " +
      "ووصف الأسلوب الموسيقي وخطة الإنتاج. لا تدّع إنشاء ملف صوتي " +
      "ما لم تتوفر أداة توليد فعلية."
  },
  agent: {
    name: "منسق فريق الوكلاء",
    system:
      "أنت منسق فريق Lazaynova. قسّم المهام المعقدة إلى خطوات " +
      "واضحة، وحدد ما يمكن إنجازه وما يحتاج إلى أدوات. لا تدّع أن " +
      "وكلاء أو أدوات أخرى نفذت خطوات لم تُنفذ فعلًا."
  }
};

export function routeIntent(message: string): EngineId {
  const text = message.toLocaleLowerCase();

  if (/(music|song|audio|موسيقى|أغنية|اغنية|لحن|صوت)/i.test(text)) {
    return "music";
  }

  if (/(video|film|movie|فيديو|فلم|مشاهد|مونتاج)/i.test(text)) {
    return "video";
  }

  if (/(agent|team|multi.?agent|فريق|وكلاء|نفذ المهمة|نفّذ المهمة)/i.test(text)) {
    return "agent";
  }

  if (/(research|بحث عميق|ابحث|مصادر|تحليل بحثي)/i.test(text)) {
    return "research";
  }

  if (/(code|debug|program|coding|برمج|كود|خطأ برمجي)/i.test(text)) {
    return "coding";
  }

  if (/(document|pdf|file|مستند|ملف|لخص الوثيقة|لخص المستند)/i.test(text)) {
    return "documents";
  }

  if (/(image|picture|draw|صورة|صور|ارسم|تصميم صورة)/i.test(text)) {
    return "image";
  }

  return "chat";
}

export function buildSpecialistRequest(
  message: string,
  history: EngineHistoryItem[] = []
) {
  const engineId = routeIntent(message);
  const specialist = specialists[engineId];

  return {
    engineId,
    engineName: specialist.name,
    request: {
      model: "lazaynova-core",
      messages: [
        { role: "system" as const, content: specialist.system },
        ...history.slice(-10).map((item) => ({
          role: item.role,
          content: item.content
        })),
        { role: "user" as const, content: message }
      ],
      temperature: 0.3,
      max_tokens: 700,
      stream: false
    }
  };
}
