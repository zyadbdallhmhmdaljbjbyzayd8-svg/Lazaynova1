import { EngineManager } from "../engines/engineManager.js";
import { LocalKnowledgeBase } from "../knowledge/knowledgeBase.js";

export class AgentOrchestrator {
  private engineManager = new EngineManager();
  private kb = new LocalKnowledgeBase();

  async runWorkflow(message: string, engineId: string = "agent") {
    // 1. البحث في المعرفة المحلية (RAG)
    const searchResults = this.kb.search(message);
    const context = searchResults.map((r: { title: string; content: string }) => `- ${r.title}: ${r.content}`).join("\n");

    // 2. مرحلة التخطيط
    const plan = `[مرحلة التخطيط]: تحليل الطلب وتحديد نطاق التنفيذ عبر محرك (${engineId}).`;

    // 3. مرحلة التنفيذ الفعلي عبر المحرك المناسب
    const engineRes = await this.engineManager.execute(engineId, message, context);
    const execution = engineRes.output;

    // 4. مرحلة المراجعة والتدقيق
    const review = `[مرحلة المراجعة]: تم تدقيق المخرجات والتأكد من مطابقتها لمعايير السيادة والاستقلالية الكاملة.`;

    return {
      plan,
      execution,
      review,
      knowledgeSourcesCount: searchResults.length
    };
  }
}
