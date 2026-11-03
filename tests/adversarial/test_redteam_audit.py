"""Adversarial QA & Red-Team Torture Verification Suite for BenchWarmer.

Verifies:
- Rule 18 Float Underflow & Precision Invariance (Micro-Deltas, Scaling Limits)
- Rule 12 Anti-Masking Parameter Sensitivity Matrix
- Rule 13 SQL Predicate Completeness Prior to LIMIT
- Rule 15 Post-Hydration Cache Invalidation
- Rule 11 Cross-Boundary Wire & View-Model Synchronization
- Contamination & Reasoning Cliff Detection (Goodhart Smell Traps)
- SQL Injection & FTS5 Syntax Token Immunity
- Zero External Runtime Dependencies Enforcement
"""

import json
import math
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from benchwarmer.api import BenchWarmer
from benchwarmer.contracts import (
    QUANT_BITS_MAP,
    ModelSummary,
    ModelRecord,
    MetricDelta,
    ModelComparisonResult,
    CandidateScore,
    ParetoPoint,
    ContaminationReport,
)
from benchwarmer.mcp import MCPServer
from benchwarmer.gui import BenchWarmerGUIController


class TestAdversarialRedTeam(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bw = BenchWarmer()
        cls.schema_file = ROOT_DIR / "src" / "benchwarmer" / "db" / "schema.sql"

    @classmethod
    def tearDownClass(cls):
        cls.bw.close()

    def test_01_rule18_micro_delta_underflow_torture(self):
        """Rule 18: Micro-deltas (e.g. 0.000028) must never collapse to 0.0 or -0.0."""
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "micro_delta.db"
            conn = sqlite3.connect(db_path)
            conn.executescript(self.schema_file.read_text(encoding="utf-8"))

            score_a = 78.123456
            score_b = 78.123484
            expected_delta = score_a - score_b  # -0.000028

            conn.execute(
                "INSERT INTO models (model_id, org, model_name, params_b) VALUES ('org/model-a', 'org', 'model-a', 7.0)"
            )
            conn.execute(
                "INSERT INTO models (model_id, org, model_name, params_b) VALUES ('org/model-b', 'org', 'model-b', 7.0)"
            )
            conn.execute(
                "INSERT INTO benchmark_scores (model_id, suite, benchmark, metric, score, raw_score) "
                "VALUES ('org/model-a', 'hf_v2', 'math_hard', 'norm_score', ?, ?)",
                (score_a, score_a)
            )
            conn.execute(
                "INSERT INTO benchmark_scores (model_id, suite, benchmark, metric, score, raw_score) "
                "VALUES ('org/model-b', 'hf_v2', 'math_hard', 'norm_score', ?, ?)",
                (score_b, score_b)
            )
            conn.commit()
            conn.close()

            custom_bw = BenchWarmer(db_path=str(db_path))
            try:
                comp = custom_bw.compare("org/model-a", "org/model-b")
                abs_d = comp.deltas["math_hard"].abs_delta
                self.assertIsNotNone(abs_d)
                self.assertNotEqual(abs_d, 0.0)
                self.assertNotEqual(abs_d, -0.0)
                self.assertAlmostEqual(abs_d, expected_delta, places=9)

                # Test scoring micro-delta ranking
                weights = {"math_hard": 1.0}
                scores = custom_bw.score_candidates(["org/model-a", "org/model-b"], weights=weights)
                self.assertEqual(scores[0].matched_model_id, "org/model-b")
                self.assertEqual(scores[1].matched_model_id, "org/model-a")
                self.assertGreater(scores[0].composite_score, scores[1].composite_score)
                diff = scores[0].composite_score - scores[1].composite_score
                self.assertAlmostEqual(diff, 0.000028, places=9)
            finally:
                custom_bw.close()

    def test_02_rule18_scaling_invariance_extreme_magnitudes(self):
        """Rule 18: Precision preservation from 0.5B Q2_K to 405B FP32."""
        rec_small = self.bw.get_model("Qwen/Qwen2.5-0.5B-Instruct")
        rec_giant = self.bw.get_model("meta-llama/Llama-3.1-405B-Instruct")

        self.assertIsNotNone(rec_small)
        self.assertIsNotNone(rec_giant)

        # 0.5B Q2_K (~2.9 bits)
        q2_vram = rec_small.estimated_vram_gb["q2_k"]
        expected_small = (rec_small.params_b * (2.9 / 8.0)) * 1.15
        self.assertEqual(q2_vram, expected_small)

        # 405B FP32 (32 bits)
        fp32_vram = rec_giant.estimated_vram_gb["fp32"]
        expected_giant = (rec_giant.params_b * (32.0 / 8.0)) * 1.15
        self.assertEqual(fp32_vram, expected_giant)

        # Efficiency ratio calculation
        ratio_small = rec_small.scores["ifeval"] / q2_vram
        ratio_giant = rec_giant.scores["ifeval"] / fp32_vram
        self.assertFalse(math.isnan(ratio_small))
        self.assertFalse(math.isinf(ratio_small))
        self.assertFalse(math.isnan(ratio_giant))
        self.assertFalse(math.isinf(ratio_giant))
        self.assertGreater(ratio_small, ratio_giant)

    def test_03_rule12_anti_masking_parameter_sensitivity_matrix(self):
        """Rule 12: Every filter parameter independently transforms the output set."""
        # 1. min_params sensitivity
        base_set = self.bw.rank(limit=20)
        p_min_set = self.bw.rank(limit=20, min_params=30.0)
        self.assertNotEqual([m.model_id for m in base_set], [m.model_id for m in p_min_set])
        for m in p_min_set:
            self.assertGreaterEqual(m.params_b, 30.0)

        # 2. max_params sensitivity
        p_max_set = self.bw.rank(limit=20, max_params=10.0)
        self.assertNotEqual([m.model_id for m in base_set], [m.model_id for m in p_max_set])
        for m in p_max_set:
            self.assertLessEqual(m.params_b, 10.0)

        # 3. max_vram_gb sensitivity
        vram_16 = self.bw.rank(limit=20, max_vram_gb=16.0, quant="bf16")
        vram_64 = self.bw.rank(limit=20, max_vram_gb=64.0, quant="bf16")
        self.assertNotEqual([m.model_id for m in vram_16], [m.model_id for m in vram_64])

        # 4. quant sensitivity (same VRAM budget, changing quantization alters allowed models)
        q_fp16 = self.bw.rank(limit=20, max_vram_gb=24.0, quant="fp16")
        q_q4 = self.bw.rank(limit=20, max_vram_gb=24.0, quant="q4_k_m")
        # Under 24 GB, Q4 allows significantly larger models than FP16
        self.assertNotEqual([m.model_id for m in q_fp16], [m.model_id for m in q_q4])

        # 5. strict_benchmarks sensitivity in score_candidates
        candidates = ["Qwen/Qwen2.5-7B-Instruct", "meta-llama/Llama-3.1-8B-Instruct"]
        # Fake a missing benchmark in weights
        weights = {"ifeval": 0.5, "non_existent_bench": 0.5}
        loose = self.bw.score_candidates(candidates, weights, strict_benchmarks=False)
        strict = self.bw.score_candidates(candidates, weights, strict_benchmarks=True)
        # Loose re-normalizes non_existent_bench away, strict multiplies missing by 0
        self.assertNotEqual(loose[0].composite_score, strict[0].composite_score)
        self.assertAlmostEqual(strict[0].composite_score, loose[0].composite_score * 0.5, places=5)

    def test_04_rule13_sql_predicate_completeness_prior_to_limit(self):
        """Rule 13: Predicates MUST apply in SQL before LIMIT truncation."""
        # Top models overall include 70B and 405B models.
        # If we ask for limit=2 and max_params=5.0, it must return the top 2 models <= 5.0B,
        # NOT truncate the top 2 giant models first and return empty!
        small_top2 = self.bw.rank(limit=2, max_params=5.0)
        self.assertEqual(len(small_top2), 2)
        for m in small_top2:
            self.assertLessEqual(m.params_b, 5.0)

    def test_05_rule15_post_hydration_cache_invalidation(self):
        """Rule 15: reload() immediately flushes resolution and model caches."""
        m1 = self.bw.resolve_model_id("Phi-4")
        self.assertEqual(m1, "microsoft/Phi-4")
        self.assertIn("Phi-4", self.bw._resolution_cache)

        rec = self.bw.get_model("microsoft/Phi-4")
        self.assertIn("microsoft/Phi-4", self.bw._model_cache)

        # Trigger reload
        self.bw.reload()
        self.assertEqual(len(self.bw._resolution_cache), 0)
        self.assertEqual(len(self.bw._model_cache), 0)

    def test_06_rule11_cross_boundary_wire_and_gui_sync(self):
        """Rule 11: 100% property synchronization between mcp_schema.json, contracts, and GUI."""
        schema_path = ROOT_DIR / "src" / "benchwarmer" / "mcp_schema.json"
        with schema_path.open("r", encoding="utf-8") as f:
            schema_data = json.load(f)

        mcp_server = MCPServer()
        try:
            # Check all 7 tools match exactly
            schema_tool_names = {t["name"] for t in schema_data["tools"]}
            self.assertEqual(len(schema_tool_names), 7)

            # Test search_models response against ModelSummary definition
            res_raw = mcp_server.handle_message(
                json.dumps({
                    "jsonrpc": "2.0", "id": 101, "method": "tools/call",
                    "params": {"name": "search_models", "arguments": {"query": "phi", "limit": 1}}
                })
            )
            res = json.loads(res_raw)
            payload = json.loads(res["result"]["content"][0]["text"])
            self.assertIsInstance(payload, list)
            item = payload[0]
            for field in schema_data["definitions"]["ModelSummary"]["required"]:
                self.assertIn(field, item)

            # Test compare_models response against ModelComparisonResult
            comp_raw = mcp_server.handle_message(
                json.dumps({
                    "jsonrpc": "2.0", "id": 102, "method": "tools/call",
                    "params": {
                        "name": "compare_models",
                        "arguments": {"model_a": "microsoft/Phi-4", "model_b": "Qwen/Qwen2.5-7B-Instruct"}
                    }
                })
            )
            comp_res = json.loads(comp_raw)
            comp_payload = json.loads(comp_res["result"]["content"][0]["text"])
            for field in schema_data["definitions"]["ModelComparisonResult"]["required"]:
                self.assertIn(field, comp_payload)

            # Test GUI Controller column synchronization
            gui_ctrl = BenchWarmerGUIController()
            try:
                l_data = gui_ctrl.get_leaderboard_data(limit=1)
                self.assertIn("model_id", l_data[0])
                self.assertIn("params_b", l_data[0])
                self.assertIn("hf_v2_avg", l_data[0])
            finally:
                gui_ctrl.close()

        finally:
            mcp_server.bw.close()

    def test_07_goodhart_contamination_trap_detection(self):
        """Contamination audit flags synthetic MMLU divergence and reasoning cliffs."""
        trap_rep = self.bw.detect_anomalies("overfit-ai/Goodhart-Overfit-7B")
        self.assertEqual(trap_rep.status, "HIGH_CONTAMINATION_RISK")
        self.assertGreaterEqual(trap_rep.anomaly_score, 60.0)
        self.assertGreaterEqual(trap_rep.ifeval_vs_knowledge_gap, 30.0)

        trap_rep2 = self.bw.detect_anomalies("benchmark-hackers/ContamMax-14B")
        self.assertEqual(trap_rep2.status, "HIGH_CONTAMINATION_RISK")
        self.assertGreaterEqual(trap_rep2.anomaly_score, 60.0)

        clean_rep = self.bw.detect_anomalies("meta-llama/Llama-3.1-8B-Instruct")
        self.assertEqual(clean_rep.status, "CLEAN")
        self.assertLess(clean_rep.anomaly_score, 35.0)

    def test_08_sql_injection_and_fts_special_token_immunity(self):
        """Resilience against SQL injections, quotes, hyphens, and FTS syntax errors."""
        malicious_queries = [
            "Qwen/Qwen2.5-72B'; DROP TABLE models;--",
            "\" OR 1=1; --",
            "llama' OR '1'='1",
            "---+++***",
            "AND NOT OR MATCH",
            "'\"",
        ]
        for query in malicious_queries:
            # Search must not raise SQLite exceptions or drop tables
            results = self.bw.search(query)
            self.assertIsInstance(results, list)
            resolved = self.bw.resolve_model_id(query)
            # Safe execution

        # Verify models table is intact
        all_models = self.bw.search("*", limit=100)
        self.assertEqual(len(all_models), 28)

    def test_09_zero_external_runtime_dependencies(self):
        """Ensure no external third-party modules are loaded into sys.modules during execution."""
        forbidden_prefixes = ["requests", "urllib3", "pydantic", "fastapi", "click", "pandas", "numpy"]
        for mod in sys.modules:
            for prefix in forbidden_prefixes:
                self.assertFalse(mod.startswith(prefix), f"Forbidden runtime dependency detected: {mod}")

    def test_10_canonical_sha256_reproducibility(self):
        """Canonical SHA-256 computed over row stream matches stored checksum."""
        from benchwarmer.db.connector import compute_canonical_checksum
        conn = self.bw._connector.get_connection()
        computed = compute_canonical_checksum(conn)
        meta = self.bw.get_metadata()
        stored_sha = meta.get("canonical_sha256")
        self.assertEqual(computed, stored_sha)


if __name__ == "__main__":
    unittest.main()
