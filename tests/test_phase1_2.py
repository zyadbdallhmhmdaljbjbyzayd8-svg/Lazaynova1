import unittest
import os
from lz_core.resource_manager.monitor import ResourceManager
from lz_core.ai_gateway.gateway import InternalAIGateway
from native_ai.fine_tuning.qlora_pipeline import LazaynovaFineTuner

class TestLazaynovaPhase1And2(unittest.TestCase):
    def test_resource_monitor(self):
        rm = ResourceManager()
        metrics = rm.get_system_metrics()
        self.assertIn("free_disk_gb", metrics)
        self.assertIn(rm.recommend_engine(), ["L3", "L4", "L4_5", "L5"])

    def test_gateway_security_block_external(self):
        with self.assertRaises(PermissionError):
            InternalAIGateway(local_endpoint="https://openai.com")

    def test_gateway_local_routing(self):
        gw = InternalAIGateway()
        res = gw.route_request("مرحبا LAZAYNOVA")
        self.assertEqual(res["status"], "ROUTED_LOCALLY")

    def test_qlora_dataset_and_manifest(self):
        tuner = LazaynovaFineTuner("LZ-Chat-v1", "Qwen/Qwen2.5-3B-Instruct", "Apache-2.0")
        samples = [{"instruction": "من أنت؟", "response": "أنا نموذج LAZAYNOVA المخصص للغة العربية."}]
        ds_path = "native_ai/datasets/sample_ar.jsonl"
        ds_hash = tuner.prepare_chatml_dataset(samples, ds_path)
        manifest_path = tuner.generate_provenance_manifest(ds_path, ds_hash)
        self.assertTrue(os.path.exists(manifest_path))

if __name__ == "__main__":
    unittest.main(verbosity=2)
