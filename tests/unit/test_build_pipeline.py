"""Unit tests for upstream ingestion pipeline and canonical hash gate."""

import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from benchwarmer.contracts import ServiceUnavailableError
from build_db import (
    normalize_elo,
    ingest_from_local_directory,
    ingest_from_live_upstream,
    populate_database,
)


class TestBuildPipeline(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.schema_file = ROOT_DIR / "src" / "benchwarmer" / "db" / "schema.sql"

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_normalize_elo_scaling(self):
        # 800 Elo -> 0.0, 1500 Elo -> 100.0, 1150 Elo -> 50.0
        self.assertEqual(normalize_elo(800.0), 0.0)
        self.assertEqual(normalize_elo(1500.0), 100.0)
        self.assertEqual(normalize_elo(1150.0), 50.0)

    def test_02_ingest_from_local_snapshot(self):
        # Create a mock snapshot JSON
        snapshot_dir = self.temp_path / "snapshot"
        snapshot_dir.mkdir(parents=True)
        sample_records = [
            {
                "model_id": "test-org/TestModel-7B",
                "org": "test-org",
                "model_name": "TestModel-7B",
                "params_b": 7.0,
                "benchmarks": {
                    "ifeval": 0.742,  # 0-1 ratio that must be normalized to 74.2
                    "math_hard": 35.5,  # Already 0-100 scale
                    "arena_elo": 1220.0,
                }
            }
        ]
        (snapshot_dir / "models.json").write_text(json.dumps(sample_records), encoding="utf-8")

        records = ingest_from_local_directory(snapshot_dir)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["model_id"], "test-org/TestModel-7B")

    def test_03_populate_database_and_score_normalization(self):
        sample_records = [
            {
                "model_id": "test-org/TestModel-7B",
                "org": "test-org",
                "model_name": "TestModel-7B",
                "params_b": 7.0,
                "benchmarks": {
                    "ifeval": 0.7425,  # Ratio 0-1 -> 74.25
                    "bbh": 68.5,       # 0-100
                    "arena_elo": 1220.0,
                }
            }
        ]
        target_db = self.temp_path / "test.db"
        sha = populate_database(sample_records, target_db, self.schema_file)
        self.assertTrue(len(sha) == 64)

        # Inspect values directly from SQLite
        conn = sqlite3.connect(target_db)
        cur = conn.cursor()
        cur.execute("SELECT score, raw_score FROM benchmark_scores WHERE model_id = 'test-org/TestModel-7B' AND benchmark = 'ifeval'")
        row = cur.fetchone()
        self.assertAlmostEqual(row[0], 74.25, places=5)
        self.assertAlmostEqual(row[1], 0.7425, places=5)

        # Inspect Elo
        cur.execute("SELECT score, raw_score FROM benchmark_scores WHERE model_id = 'test-org/TestModel-7B' AND benchmark = 'arena_elo'")
        elo_row = cur.fetchone()
        expected_norm_elo = normalize_elo(1220.0)
        self.assertAlmostEqual(elo_row[0], expected_norm_elo, places=5)
        self.assertEqual(elo_row[1], 1220.0)
        conn.close()

    def test_04_canonical_checksum_idempotency(self):
        # Running populate_database twice on the same records produces the exact same hash
        sample_records = [
            {
                "model_id": "org/Model-A",
                "params_b": 7.0,
                "benchmarks": {"ifeval": 70.0, "bbh": 60.0}
            },
            {
                "model_id": "org/Model-B",
                "params_b": 14.0,
                "benchmarks": {"ifeval": 80.0, "bbh": 75.0}
            }
        ]
        db1 = self.temp_path / "db1.db"
        db2 = self.temp_path / "db2.db"

        sha1 = populate_database(sample_records, db1, self.schema_file)
        sha2 = populate_database(sample_records, db2, self.schema_file)
        self.assertEqual(sha1, sha2)

    def test_05_rule10_service_unavailable_error_on_empty_or_missing(self):
        empty_dir = self.temp_path / "empty"
        empty_dir.mkdir()
        with self.assertRaises(ServiceUnavailableError):
            ingest_from_local_directory(empty_dir)

        # Non-existent dir
        with self.assertRaises(FileNotFoundError):
            ingest_from_local_directory(self.temp_path / "does_not_exist")


if __name__ == "__main__":
    unittest.main()
