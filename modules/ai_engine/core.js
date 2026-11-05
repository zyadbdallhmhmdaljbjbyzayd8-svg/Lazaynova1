'use strict';

/**
 * Lazaynova AI Engine Core
 * Local Agent Orchestration Foundation
 */

class LazaynovaAIEngine {
    constructor(options = {}) {
        this.memoryConfig = {
            host: options.memoryHost || '127.0.0.1',
            port: Number(options.memoryPort || 1933),
            timeout: Number(options.timeout || 5000)
        };

        this.allowedAgents = new Set([
            'general',
            'research',
            'coding',
            'documents',
            'education',
            'planner'
        ]);
    }

    async recallMemory(queryText) {
        const query = String(queryText || '').trim();

        if (!query) {
            return {
                status: 'empty',
                context: null
            };
        }

        const controller = new AbortController();
        const timer = setTimeout(
            () => controller.abort(),
            this.memoryConfig.timeout
        );

        try {
            const response = await fetch(
                `http://${this.memoryConfig.host}:${this.memoryConfig.port}/api/recall`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ query }),
                    signal: controller.signal
                }
            );

            if (!response.ok) {
                return {
                    status: 'error',
                    context: null,
                    message: `Memory HTTP ${response.status}`
                };
            }

            const data = await response.json();

            return {
                status: 'connected',
                context: data
            };

        } catch (error) {
            return {
                status: 'offline',
                context: null,
                message: error.name === 'AbortError'
                    ? 'Memory request timed out'
                    : 'Memory service unavailable'
            };
        } finally {
            clearTimeout(timer);
        }
    }

    async processAgentTask(agentType, inputPrompt) {
        const agent = String(agentType || 'general').trim();
        const prompt = String(inputPrompt || '').trim();

        if (!prompt || prompt.length > 12000) {
            throw new Error('Prompt must contain 1-12000 characters');
        }

        if (!this.allowedAgents.has(agent)) {
            throw new Error('Unsupported agent type');
        }

        const memory = await this.recallMemory(prompt);

        return {
            success: true,
            status: 'accepted',
            engine: 'LazaynovaAIEngine',
            agent,
            prompt,
            memory,
            execution: {
                inference: false,
                message: 'LLM inference is not connected yet'
            },
            timestamp: new Date().toISOString()
        };
    }
}

module.exports = LazaynovaAIEngine;
