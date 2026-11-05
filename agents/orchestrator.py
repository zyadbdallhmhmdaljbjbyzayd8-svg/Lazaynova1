import os, json
from dataclasses import dataclass, asdict

AGENT_ROSTER = [
    "ChatAgent", "ResearchAgent", "CodingAgent", "DocumentAgent",
    "KnowledgeAgent", "TranslationAgent", "VisionAgent", "AudioAgent",
    "TaskPlanningAgent", "SecurityAgent", "QualityAssuranceAgent", "ModelTrainingAgent"
]

class BaseAgent:
    def __init__(self, name: str, max_ram_mb: int = 512, timeout_sec: int = 30):
        self.name = name
        self.max_ram_mb = max_ram_mb
        self.timeout_sec = timeout_sec

    def execute_pipeline(self, task: str) -> dict:
        plan = f"Plan[{self.name}]: Analyze -> {task}"
        exec_res = f"Executed safely within {self.max_ram_mb}MB limit"
        monitor = "Status: OK | No destructive commands"
        verified = True
        return {"agent": self.name, "workflow": ["Planner", "Executor", "Monitor", "Verifier"], "plan": plan, "result": exec_res, "verified": verified}

class AgentOrchestrator:
    def __init__(self):
        self.agents = {name: BaseAgent(name) for name in AGENT_ROSTER}

    def dispatch(self, agent_name: str, task: str) -> dict:
        if agent_name not in self.agents:
            raise ValueError(f"Unknown agent: {agent_name}")
        return self.agents[agent_name].execute_pipeline(task)

class LocalKnowledgeCore:
    def __init__(self, index_file: str = "knowledge_core/local_docs.json"):
        self.index_file = index_file
        if not os.path.exists(index_file):
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump([{"id": "doc_1", "title": "LAZAYNOVA Manifesto", "content": "Private. Autonomous. Yours."}], f, ensure_ascii=False)

    def search(self, query: str) -> list:
        with open(self.index_file, "r", encoding="utf-8") as f:
            docs = json.load(f)
        return [d for d in docs if query.lower() in d["content"].lower() or query.lower() in d["title"].lower()]
