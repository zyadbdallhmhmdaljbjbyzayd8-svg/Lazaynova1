import unittest
from lz_core.ai_gateway.gateway import InternalAIGateway
from agents.orchestrator import AgentOrchestrator, LocalKnowledgeCore

class TestFullLazaynova(unittest.TestCase):
    def test_security(self):
        with self.assertRaises(PermissionError):
            InternalAIGateway("https://api.openai.com")
    def test_agents(self):
        orch = AgentOrchestrator()
        self.assertEqual(len(orch.agents), 12)
    def test_knowledge(self):
        kc = LocalKnowledgeCore()
        self.assertTrue(len(kc.search("Autonomous")) >= 1)

if __name__ == "__main__":
    unittest.main(verbosity=2)
