export const engineCatalog = [
  { id: "chat", name: "محرك المحادثة", description: "محادثة عامة وتنسيق الطلبات", mode: "text" },
  { id: "research", name: "محرك البحث والتحليل", description: "تحليل السؤال وتحديد ما يحتاج إلى مصادر؛ لا يجري بحث ويب ما لم توصل أداة بحث", mode: "text" },
  { id: "coding", name: "محرك البرمجة", description: "كتابة الكود وتصحيحه وشرح البنية", mode: "text" },
  { id: "documents", name: "محرك المستندات", description: "صياغة المستندات وتلخيص النصوص المتاحة", mode: "text" },
  { id: "image", name: "محرك الصور", description: "صياغة أوصاف الصور وخطط التصميم؛ التوليد الفعلي يتطلب مزود صور", mode: "prompt" },
  { id: "video", name: "محرك الفيديو", description: "كتابة السيناريو وتقسيم المشاهد", mode: "text" },
  { id: "music", name: "محرك الموسيقى", description: "أفكار ووصف موسيقي وخطط إنتاج", mode: "text" },
  { id: "agent", name: "محرك تنسيق الوكلاء", description: "تخطيط المهمة ثم تنفيذها ومراجعة المخرجات", mode: "multi-agent" }
] as const;

export type EngineId = typeof engineCatalog[number]["id"];
export type EngineInfo = typeof engineCatalog[number];

export function listEngines(): EngineInfo[] {
  return engineCatalog.map((engine) => ({ ...engine }));
}

export function getEngine(id: string): EngineInfo | undefined {
  return engineCatalog.find((engine) => engine.id === id);
}

export function isEngineId(id: string): id is EngineId {
  return engineCatalog.some((engine) => engine.id === id);
}
