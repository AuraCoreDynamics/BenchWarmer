"""Headless tests for BenchWarmer GUI Controller and contract synchronization."""

import io
from pathlib import Path
import sys
import unittest
import unittest.mock

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

# Import gui module
import benchwarmer.gui as bw_gui
from benchwarmer.contracts import (
    ModelSummary,
    ModelRecord,
    MetricDelta,
    ModelComparisonResult,
    ParetoPoint,
    ContaminationReport,
)


class TestGUIHeadless(unittest.TestCase):
    def test_01_lazy_tkinter_import_isolation(self):
        # Guarantee top-level import did not pull tkinter into sys.modules
        self.assertNotIn("tkinter", sys.modules, "Top-level gui.py import must not eagerly import tkinter")

    def test_02_leaderboard_data_and_sorting(self):
        controller = bw_gui.BenchWarmerGUIController()
        try:
            # Unfiltered
            rows = controller.get_leaderboard_data()
            self.assertEqual(len(rows), 1489)
            self.assertIn("model_id", rows[0])
            self.assertIn("hf_v2_avg_display", rows[0])

            # Filtered by parameters
            filtered = controller.get_leaderboard_data(min_params=5.0, max_params=15.0)
            self.assertTrue(len(filtered) > 0)
            for r in filtered:
                self.assertGreaterEqual(r["params_b"], 5.0)
                self.assertLessEqual(r["params_b"], 15.0)

            # Sort descending by hf_v2_avg
            sorted_rows = controller.get_leaderboard_data(sort_key="hf_v2_avg", ascending=False)
            scores = [r["hf_v2_avg"] for r in sorted_rows if r["hf_v2_avg"] is not None]
            self.assertEqual(scores, sorted(scores, reverse=True))
        finally:
            controller.close()

    def test_03_comparison_data_and_tags(self):
        controller = bw_gui.BenchWarmerGUIController()
        try:
            cdata = controller.get_comparison_data(
                "Qwen/Qwen2.5-72B-Instruct",
                "meta-llama/Llama-3.3-70B-Instruct"
            )
            self.assertEqual(cdata["model_a"], "Qwen/Qwen2.5-72B-Instruct")
            self.assertEqual(cdata["model_b"], "meta-llama/Llama-3.3-70B-Instruct")
            self.assertTrue(len(cdata["deltas"]) > 0)

            for d in cdata["deltas"]:
                self.assertIn("benchmark", d)
                self.assertIn(d["tag"], ["winner_a", "winner_b", "tie"])
                self.assertIn("score_a_display", d)
                self.assertIn("score_b_display", d)

            self.assertGreaterEqual(cdata["wins_a"], 0)
        finally:
            controller.close()

    def test_04_pareto_and_audit_data(self):
        controller = bw_gui.BenchWarmerGUIController()
        try:
            pdata = controller.get_pareto_data(metric="hf_v2_avg", quant="bf16")
            self.assertTrue(len(pdata) >= 3)
            self.assertIn("efficiency_ratio_display", pdata[0])

            adata = controller.get_audit_data("overfit-ai/Goodhart-Overfit-7B")
            self.assertEqual(adata["status"], "HIGH_CONTAMINATION_RISK")
            self.assertTrue(len(adata["flags"]) > 0)
        finally:
            controller.close()

    def test_05_clipboard_exports_markdown_and_csv(self):
        controller = bw_gui.BenchWarmerGUIController()
        try:
            md = controller.export_comparison_markdown(
                "Qwen/Qwen2.5-72B-Instruct",
                "meta-llama/Llama-3.3-70B-Instruct"
            )
            self.assertIn("| Benchmark |", md)
            self.assertIn("Composite Delta", md)

            csv_text = controller.export_leaderboard_csv()
            lines = csv_text.splitlines()
            self.assertGreater(len(lines), 1)
            self.assertIn("Model ID,Org,Params (B)", lines[0])
        finally:
            controller.close()

    def test_06_contract_synchronization_audit(self):
        # Verify controller consumed fields exist on frozen dataclasses
        summary_fields = set(ModelSummary.__dataclass_fields__.keys())
        self.assertTrue({"model_id", "org", "params_b", "architecture", "hf_v2_avg", "arena_elo_raw"}.issubset(summary_fields))

        record_fields = set(ModelRecord.__dataclass_fields__.keys())
        self.assertTrue({"model_id", "org", "params_b", "scores", "raw_scores", "estimated_vram_gb"}.issubset(record_fields))

        delta_fields = set(MetricDelta.__dataclass_fields__.keys())
        self.assertTrue({"benchmark", "score_a", "score_b", "abs_delta", "pct_delta", "winner"}.issubset(delta_fields))

        comp_fields = set(ModelComparisonResult.__dataclass_fields__.keys())
        self.assertTrue({"model_a", "model_b", "deltas", "wins_a", "wins_b", "ties", "composite_delta"}.issubset(comp_fields))

        pareto_fields = set(ParetoPoint.__dataclass_fields__.keys())
        self.assertTrue({"model_id", "params_b", "estimated_vram_gb", "quant", "metric", "score", "efficiency_ratio"}.issubset(pareto_fields))

        contam_fields = set(ContaminationReport.__dataclass_fields__.keys())
        self.assertTrue({"model_id", "params_b", "anomaly_score", "status", "flags", "z_score_spread", "ifeval_vs_knowledge_gap"}.issubset(contam_fields))

    def test_07_launch_gui_headless_safety(self):
        # launch_gui should safely handle missing display / tk without crashing
        stderr_buf = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = stderr_buf
        try:
            with unittest.mock.patch.dict("sys.modules", {"tkinter": None}):
                bw_gui.launch_gui()
        finally:
            sys.stderr = old_stderr
        # Should catch exception cleanly and output actionable message
        err_out = stderr_buf.getvalue()
        # Either launch_gui executed or caught cleanly with guidance
        self.assertTrue("Error: GUI requires tkinter" in err_out or err_out == "")


if __name__ == "__main__":
    import io
    unittest.main()
