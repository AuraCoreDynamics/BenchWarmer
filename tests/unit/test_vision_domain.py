"""Unit tests for BenchWarmer multimodal vision domain and vision benchmark scoring."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from benchwarmer.api import BenchWarmer
from benchwarmer.domains import (
    DOMAINS,
    compute_domain_scores,
    determine_primary_domain,
)


class TestVisionDomain(unittest.TestCase):
    def test_vision_domain_definition_and_weights(self):
        self.assertIn("vision", DOMAINS)
        vision_cfg = DOMAINS["vision"]
        for bench in ("mmmu", "ocrbench", "docvqa", "mathvista", "vision_arena_elo"):
            self.assertIn(bench, vision_cfg["weights"])
        self.assertGreater(sum(vision_cfg["weights"].values()), 0.99)

    def test_compute_domain_scores_normalizes_vision_arena_elo(self):
        scores = {
            "mmmu": 70.0,
            "ocrbench": 80.0,
            "docvqa": 90.0,
            "mathvista": 70.0,
            "vision_arena_elo": 1200.0,  # (1200 - 1000) / 4 = 50.0
        }
        domain_scores = compute_domain_scores(scores)
        self.assertIn("vision", domain_scores)
        self.assertGreater(domain_scores["vision"], 60.0)
        self.assertLess(domain_scores["vision"], 85.0)

    def test_determine_primary_domain_prefers_vision_for_vlm_models(self):
        domain_scores = {"vision": 78.5, "analytics": 76.0, "coding": 72.0}
        _title, primary_key, _tags = determine_primary_domain(
            domain_scores,
            model_id="qwen/qwen2.5-vl-72b-instruct",
        )
        self.assertEqual(primary_key, "vision")

    def test_seed_db_contains_1489_models_and_vision_benchmarks(self):
        bw = BenchWarmer()
        try:
            meta = bw.get_metadata()
            self.assertEqual(meta.get("model_count"), "1489")
            benches = bw.list_benchmarks()
            for bench in ("mmmu", "ocrbench", "docvqa", "mathvista", "vision_arena_elo"):
                self.assertIn(bench, benches)
            rec = bw.get_model("meta-llama/Llama-3.2-90B-Vision-Instruct")
            self.assertIsNotNone(rec)
            self.assertIn("mmmu", rec.scores)
            self.assertIn("ocrbench", rec.scores)
        finally:
            bw.close()


if __name__ == "__main__":
    unittest.main()
