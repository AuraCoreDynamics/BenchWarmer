"""Unit tests for BenchWarmer core Oracle API."""

import unittest
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from benchwarmer.api import BenchWarmer
from benchwarmer.contracts import QUANT_BITS_MAP, ModelRecord, ParetoPoint


class TestBenchWarmerAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bw = BenchWarmer()

    @classmethod
    def tearDownClass(cls):
        cls.bw.close()

    def test_01_metadata_and_benchmarks(self):
        meta = self.bw.get_metadata()
        self.assertIn("version", meta)
        self.assertIn("canonical_sha256", meta)
        self.assertEqual(meta.get("model_count"), "1438")

        benchmarks = self.bw.list_benchmarks()
        self.assertIn("ifeval", benchmarks)
        self.assertIn("mmlu_pro", benchmarks)
        self.assertIn("math_hard", benchmarks)
        self.assertIn("arena_elo", benchmarks)

    def test_02_resolve_model_id_cascade(self):
        # Stage 1: Exact match
        res1 = self.bw.resolve_model_id("meta-llama/Llama-3.1-8B-Instruct")
        self.assertEqual(res1, "meta-llama/Llama-3.1-8B-Instruct")

        # Stage 2: Case-insensitive
        res2 = self.bw.resolve_model_id("META-LLAMA/LLAMA-3.1-8B-INSTRUCT")
        self.assertEqual(res2, "meta-llama/Llama-3.1-8B-Instruct")

        # Stage 3: Org-stripped
        res3 = self.bw.resolve_model_id("Llama-3.1-8B-Instruct")
        self.assertEqual(res3, "meta-llama/Llama-3.1-8B-Instruct")

        # Stage 4: FTS5 rank
        res4 = self.bw.resolve_model_id("qwen 72b instruct")
        self.assertIn(res4, ["Qwen/Qwen2.5-72B-Instruct", "Qwen/Qwen2-72B-Instruct"])

        # Non-existent
        res_none = self.bw.resolve_model_id("non-existent-fantasy-model-xyz")
        self.assertIsNone(res_none)

    def test_03_get_model_and_vram_mapping(self):
        model = self.bw.get_model("Qwen/Qwen2.5-72B-Instruct")
        self.assertIsNotNone(model)
        self.assertEqual(model.org, "Qwen")
        self.assertAlmostEqual(model.params_b, 72.71, places=2)

        # Verify estimated_vram_gb populated for all keys in QUANT_BITS_MAP
        for quant_key, bits in QUANT_BITS_MAP.items():
            self.assertIn(quant_key, model.estimated_vram_gb)
            expected_vram = (model.params_b * (bits / 8.0)) * 1.15
            self.assertEqual(model.estimated_vram_gb[quant_key], expected_vram)

    def test_04_get_metrics_batch(self):
        batch = self.bw.get_metrics_batch([
            "meta-llama/Llama-3.1-8B-Instruct",
            "microsoft/Phi-4",
            "missing-model-id"
        ])
        self.assertIn("meta-llama/Llama-3.1-8B-Instruct", batch)
        self.assertIsNotNone(batch["meta-llama/Llama-3.1-8B-Instruct"])
        self.assertIn("microsoft/Phi-4", batch)
        self.assertIsNotNone(batch["microsoft/Phi-4"])
        self.assertIn("missing-model-id", batch)
        self.assertIsNone(batch["missing-model-id"])

    def test_05_search_filtering(self):
        # Unbounded search
        all_results = self.bw.search("*", limit=100)
        self.assertEqual(len(all_results), 100)

        # Bounded search (min_params and max_params)
        filtered = self.bw.search("*", min_params=5.0, max_params=10.0, limit=50)
        self.assertTrue(len(filtered) > 0)
        for m in filtered:
            self.assertTrue(5.0 <= m.params_b <= 10.0)

        # FTS Query search
        llama_results = self.bw.search("llama", limit=10)
        self.assertTrue(any("llama" in m.model_id.lower() for m in llama_results))

    def test_06_rank_and_hardware_vram_filter(self):
        # Rank by math_hard
        ranked = self.bw.rank(benchmark="math_hard", limit=5)
        self.assertEqual(len(ranked), 5)

        # Rank with VRAM limit
        # 16 GB VRAM budget at BF16 (~16 bits/byte * 1.15) allows ~6.95B params
        vram_limited = self.bw.rank(limit=20, max_vram_gb=16.0, quant="bf16")
        self.assertTrue(len(vram_limited) > 0)
        for m in vram_limited:
            bits = QUANT_BITS_MAP["bf16"]
            vram = (m.params_b * (bits / 8.0)) * 1.15
            self.assertLessEqual(vram, 16.0)

    def test_07_compare_models_and_micro_deltas(self):
        comp = self.bw.compare("meta-llama/Llama-3.3-70B-Instruct", "meta-llama/Llama-3.1-70B-Instruct")
        self.assertEqual(comp.model_a.model_id, "meta-llama/Llama-3.3-70B-Instruct")
        self.assertEqual(comp.model_b.model_id, "meta-llama/Llama-3.1-70B-Instruct")

        self.assertIn("ifeval", comp.deltas)
        delta_ifeval = comp.deltas["ifeval"]
        self.assertIsNotNone(delta_ifeval.abs_delta)
        # Expected: 88.40 - 84.60 = 3.80
        self.assertAlmostEqual(delta_ifeval.abs_delta, 3.80, places=5)
        self.assertEqual(delta_ifeval.winner, "meta-llama/Llama-3.3-70B-Instruct")
        self.assertTrue(comp.wins_a > comp.wins_b)
        self.assertTrue(comp.composite_delta > 0.0)

    def test_08_score_candidates_strict_vs_loose(self):
        weights = {"ifeval": 0.5, "mmlu_pro": 0.5}
        candidates = ["meta-llama/Llama-3.1-8B-Instruct", "Qwen/Qwen2.5-72B-Instruct", "unknown-xyz"]

        # Loose scoring
        loose = self.bw.score_candidates(candidates, weights, strict_benchmarks=False)
        self.assertEqual(len(loose), 3)
        self.assertEqual(loose[0].matched_model_id, "Qwen/Qwen2.5-72B-Instruct")
        self.assertEqual(loose[2].requested_id, "unknown-xyz")
        self.assertEqual(loose[2].composite_score, 0.0)

        # Strict scoring
        strict = self.bw.score_candidates(candidates, weights, strict_benchmarks=True)
        self.assertEqual(len(strict), 3)
        self.assertGreater(strict[0].composite_score, strict[1].composite_score)

    def test_09_pareto_frontier_dominance(self):
        frontier = self.bw.pareto_frontier(metric="hf_v2_avg", quant="bf16")
        self.assertTrue(len(frontier) >= 3)

        # Verify Pareto dominance: strictly increasing scores with strictly increasing VRAM
        last_vram = -1.0
        last_score = -1.0
        for pt in frontier:
            self.assertGreater(pt.estimated_vram_gb, last_vram)
            self.assertGreater(pt.score, last_score)
            self.assertAlmostEqual(pt.efficiency_ratio, pt.score / pt.estimated_vram_gb, places=6)
            last_vram = pt.estimated_vram_gb
            last_score = pt.score

    def test_10_detect_anomalies_clean_vs_overfit(self):
        # Clean model
        clean_rep = self.bw.detect_anomalies("Qwen/Qwen2.5-7B-Instruct")
        self.assertEqual(clean_rep.status, "CLEAN")
        self.assertLess(clean_rep.anomaly_score, 35.0)

        # Overfit contamination model: Goodhart-Overfit-7B
        contam_rep = self.bw.detect_anomalies("overfit-ai/Goodhart-Overfit-7B")
        self.assertEqual(contam_rep.status, "HIGH_CONTAMINATION_RISK")
        self.assertGreaterEqual(contam_rep.anomaly_score, 60.0)
        self.assertTrue(any("Severe IFEval divergence" in f for f in contam_rep.flags))

    def test_11_reload_cache_invalidation(self):
        # Resolve to cache it
        res = self.bw.resolve_model_id("Llama-3.1-8B-Instruct")
        self.assertIn("Llama-3.1-8B-Instruct", self.bw._resolution_cache)
        # Reload
        self.bw.reload()
        self.assertEqual(len(self.bw._resolution_cache), 0)
        self.assertEqual(len(self.bw._model_cache), 0)

    def test_12_error_handling_negative_weights_and_missing_models(self):
        with self.assertRaises(ValueError):
            self.bw.score_candidates(["Qwen/Qwen2.5-7B-Instruct"], {"ifeval": -1.0})
        with self.assertRaises(ValueError):
            self.bw.score_candidates(["Qwen/Qwen2.5-7B-Instruct"], {})
        with self.assertRaises(ValueError):
            self.bw.compare("nonexistent-a", "Qwen/Qwen2.5-7B-Instruct")

    def test_13_compare_multiple_and_audit_all(self):
        # Multi-model compare with 3 models (including OpenAI frontier)
        multi = self.bw.compare_multiple(["openai/o1", "deepseek-ai/DeepSeek-R1", "meta-llama/Llama-3.1-70B-Instruct"])
        self.assertEqual(len(multi["models"]), 3)
        self.assertIn("hf_v2_avg", multi["benchmarks"])
        self.assertIn("openai/o1", multi["summary"])
        self.assertIn("deepseek-ai/DeepSeek-R1", multi["summary"])

        # Audit all
        all_audits = self.bw.audit_all()
        self.assertEqual(len(all_audits), 1438)
        # Verify highest risk comes first
        self.assertEqual(all_audits[0]["status"], "HIGH_CONTAMINATION_RISK")

        # Detailed models list
        detailed = self.bw.get_all_models_detailed()
        self.assertEqual(len(detailed), 1438)
        self.assertIn("estimated_vram_gb", detailed[0])
        self.assertIn("scores", detailed[0])

    def test_12_mythos_and_frontier_models(self):
        mythos = self.bw.get_model("anthropic/claude-mythos-preview")
        self.assertIsNotNone(mythos)
        self.assertEqual(mythos.org, "anthropic")
        self.assertEqual(mythos.raw_scores["gpqa"], 94.60)
        self.assertEqual(mythos.raw_scores["mmlu_pro"], 93.60)
        self.assertEqual(mythos.raw_scores["arena_elo"], 1420.0)

        fable = self.bw.get_model("anthropic/claude-fable")
        self.assertIsNotNone(fable)
        self.assertEqual(fable.org, "anthropic")
        self.assertEqual(fable.raw_scores["gpqa"], 89.20)

        mythomax = self.bw.get_model("Gryphe/MythoMax-L2-13b")
        self.assertIsNotNone(mythomax)
        self.assertEqual(mythomax.org, "Gryphe")
        self.assertEqual(mythomax.params_b, 13.0)


if __name__ == "__main__":
    unittest.main()
