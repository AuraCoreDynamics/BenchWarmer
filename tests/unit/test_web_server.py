"""Unit tests for the BenchWarmer Web Server API and static file serving."""

from pathlib import Path
import unittest

from starlette.testclient import TestClient

from benchwarmer.api import BenchWarmer
from benchwarmer.web.server import create_fastapi_app

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class TestWebServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bw = BenchWarmer()
        cls.app = create_fastapi_app(bw=cls.bw)
        cls.client = TestClient(cls.app)

    @classmethod
    def tearDownClass(cls):
        cls.bw.close()

    def test_01_metadata(self):
        res = self.client.get("/api/metadata")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("version", data)
        self.assertEqual(data.get("model_count"), "1489")

    def test_02_get_all_models_and_filter(self):
        res = self.client.get("/api/models")
        self.assertEqual(res.status_code, 200)
        models = res.json()
        self.assertEqual(len(models), 1489)
        first = models[0]
        self.assertIn("model_id", first)
        self.assertIn("estimated_vram_gb", first)
        self.assertIn("scores", first)
        self.assertIn("domain_scores", first)

        # Filter by query
        res_q = self.client.get("/api/models?query=claude")
        self.assertEqual(res_q.status_code, 200)
        claude_models = res_q.json()
        self.assertTrue(len(claude_models) >= 3)
        self.assertTrue(all("claude" in m["model_id"].lower() for m in claude_models))

        # Filter by hide_proprietary
        res_np = self.client.get("/api/models?hide_proprietary=true")
        self.assertEqual(res_np.status_code, 200)
        open_models = res_np.json()
        self.assertEqual(len(open_models), 1436)
        self.assertTrue(all(m.get("license") != "proprietary" for m in open_models))
        self.assertTrue(all(m.get("params_b") is not None for m in open_models))

        # Filter by domain
        res_dom = self.client.get("/api/models?domain=coding")
        self.assertEqual(res_dom.status_code, 200)
        coding_models = res_dom.json()
        self.assertTrue(len(coding_models) > 0)
        self.assertTrue(all(m.get("primary_domain_key") == "coding" or m.get("domain_scores", {}).get("coding", 0.0) >= 60.0 for m in coding_models))

    def test_03_get_model_detail(self):
        res = self.client.get("/api/models/openai/o1")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["model_id"], "openai/o1")
        self.assertIn("scores", data)
        self.assertIn("audit", data)

    def test_04_compare_multiple(self):
        payload = {
            "model_ids": [
                "openai/o1",
                "deepseek-ai/DeepSeek-R1",
                "meta-llama/Llama-3.1-70B-Instruct"
            ]
        }
        res = self.client.post("/api/compare", json=payload)
        self.assertEqual(res.status_code, 200)
        comp = res.json()
        self.assertEqual(len(comp["models"]), 3)
        self.assertIn("benchmarks", comp)
        self.assertIn("best_in_class", comp)
        self.assertIn("summary", comp)

    def test_05_pareto_frontier(self):
        res = self.client.get("/api/pareto?metric=hf_v2_avg&quant=bf16")
        self.assertEqual(res.status_code, 200)
        pts = res.json()
        self.assertTrue(len(pts) > 0)
        first = pts[0]
        self.assertIn("model_id", first)
        self.assertIn("estimated_vram_gb", first)
        self.assertIn("efficiency_ratio", first)

    def test_06_audit_all_and_single(self):
        res_all = self.client.get("/api/audit")
        self.assertEqual(res_all.status_code, 200)
        audits = res_all.json()
        self.assertEqual(len(audits), 1489)
        self.assertEqual(audits[0]["status"], "HIGH_CONTAMINATION_RISK")

        res_single = self.client.get("/api/audit/overfit-ai/Goodhart-Overfit-7B")
        self.assertEqual(res_single.status_code, 200)
        single = res_single.json()
        self.assertEqual(single["status"], "HIGH_CONTAMINATION_RISK")
        self.assertGreaterEqual(single["anomaly_score"], 60.0)

    def test_07_custom_scorer(self):
        payload = {
            "candidates": ["Qwen/Qwen2.5-7B-Instruct", "microsoft/Phi-4"],
            "weights": {"math_hard": 2.0, "ifeval": 1.0},
            "strict": False
        }
        res = self.client.post("/api/score", json=payload)
        self.assertEqual(res.status_code, 200)
        scores = res.json()
        self.assertEqual(len(scores), 2)
        self.assertIn("composite_score", scores[0])

    def test_08_serve_index_html(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("BenchWarmer", res.text)
        self.assertIn("Pareto Optimal Frontier", res.text)


if __name__ == "__main__":
    unittest.main()
