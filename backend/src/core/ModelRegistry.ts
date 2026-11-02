/**
 * Model Registry - سجل النماذج
 * يحدد النماذج المتاحة (المحلية والخارجية) وقدراتها.
 */
export type ModelType = 'local' | 'ollama' | 'openai';

export interface ModelConfig {
    id: string;
    name: string;
    type: ModelType;
    endpoint: string;
    capabilities: string[];
}

export const MODEL_REGISTRY: Record<string, ModelConfig> = {
    'lz-native': {
        id: 'lz-native',
        name: 'Lazaynova Native (Internal)',
        type: 'local',
        endpoint: 'http://127.0.0.1:8080/v1',
        capabilities: ['chat', 'reasoning', 'coding']
    },
    'qwen-coder': {
        id: 'qwen2.5-coder',
        name: 'Qwen 2.5 Coder (External)',
        type: 'ollama',
        endpoint: 'http://127.0.0.1:11434/api/generate',
        capabilities: ['coding', 'reasoning']
    }
};

export function getModelForEngine(engineId: string): ModelConfig {
    if (engineId === 'coding') return MODEL_REGISTRY['qwen-coder'];
    return MODEL_REGISTRY['lz-native'];
}
