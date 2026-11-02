/**
 * External AI Bridge - جسر النماذج الخارجية
 * يتصل بـ Ollama (أو أي مزود متوافق) لتشغيل المهام مؤقتاً.
 */
import { ModelConfig } from '../core/ModelRegistry.js';

export class ExternalBridge {
    static async generate(prompt: string, modelConfig: ModelConfig): Promise<string> {
        try {
            console.log(`[ExternalBridge] Sending to ${modelConfig.name}...`);
            
            const response = await fetch(modelConfig.endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: modelConfig.id,
                    prompt: prompt,
                    stream: false
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data.response || "لا يوجد رد من النموذج الخارجي.";
            
        } catch (error) {
            console.error(`[ExternalBridge] Error:`, error);
            // العودة إلى النموذج المحلي كخطة بديلة (Fallback) في حال فشل الخارجي
            throw new Error("فشل الاتصال بالنموذج الخارجي (هل Ollama يعمل؟).");
        }
    }
}
