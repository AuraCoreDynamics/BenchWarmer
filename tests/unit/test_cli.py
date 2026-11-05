"""Unit tests for BenchWarmer CLI and Zipapp execution."""

import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from benchwarmer.cli import main


class TestBenchWarmerCLI(unittest.TestCase):
    def test_01_search_command_table_and_json(self):
        # Table format
        stdout_buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = stdout_buf
        try:
            code = main(["search", "llama", "--limit", "3", "--format", "table"])
        finally:
            sys.stdout = old_stdout
        self.assertEqual(code, 0)
        out = stdout_buf.getvalue()
        self.assertIn("Model ID", out)
        self.assertIn("llama", out.lower())

        # JSON format
        stdout_buf = io.StringIO()
        sys.stdout = stdout_buf
        try:
            code = main(["search", "llama", "--limit", "2", "--format", "json"])
        finally:
            sys.stdout = old_stdout
        self.assertEqual(code, 0)
        data = json.loads(stdout_buf.getvalue())
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        self.assertIn("model_id", data[0])

    def test_02_info_command_success_and_error(self):
        # Valid model
        stdout_buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = stdout_buf
        try:
            code = main(["info", "microsoft/Phi-4", "--format", "json"])
        finally:
            sys.stdout = old_stdout
        self.assertEqual(code, 0)
        rec = json.loads(stdout_buf.getvalue())
        self.assertEqual(rec["model_id"], "microsoft/Phi-4")
        self.assertEqual(rec["org"], "microsoft")

        # Invalid model
        stderr_buf = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = stderr_buf
        try:
            code = main(["info", "completely-fictional-model-id-12345"])
        finally:
            sys.stderr = old_stderr
        self.assertEqual(code, 1)
        self.assertIn("not found", stderr_buf.getvalue())

    def test_03_compare_command(self):
        stdout_buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = stdout_buf
        try:
            code = main([
                "compare",
                "Qwen/Qwen2.5-72B-Instruct",
                "meta-llama/Llama-3.3-70B-Instruct",
                "--format", "markdown"
            ])
        finally:
            sys.stdout = old_stdout
        self.assertEqual(code, 0)
        out = stdout_buf.getvalue()
        self.assertIn("| Benchmark |", out)
        self.assertIn("Qwen/Qwen2.5-72B-Instruct", out)

    def test_04_rank_command_with_vram_and_quant(self):
        stdout_buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = stdout_buf
        try:
            code = main([
                "rank",
                "--benchmark", "ifeval",
                "--limit", "3",
                "--vram", "24.0",
                "--quant", "q4_k_m",
                "--format", "json"
            ])
        finally:
            sys.stdout = old_stdout
        self.assertEqual(code, 0)
        data = json.loads(stdout_buf.getvalue())
        self.assertTrue(len(data) <= 3)

    def test_05_score_command_stdin_piping(self):
        # Pipe candidates via stdin
        old_stdin = sys.stdin
        old_stdout = sys.stdout
        sys.stdin = io.StringIO('["meta-llama/Llama-3.1-8B-Instruct", "Qwen/Qwen2.5-7B-Instruct"]')
        stdout_buf = io.StringIO()
        sys.stdout = stdout_buf
        try:
            code = main([
                "score",
                "--candidates", "-",
                "--weights", "ifeval=0.5,bbh=0.5",
                "--format", "json"
            ])
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout
        self.assertEqual(code, 0)
        scores = json.loads(stdout_buf.getvalue())
        self.assertEqual(len(scores), 2)
        self.assertIn("composite_score", scores[0])

    def test_06_score_command_negative_weights_error(self):
        stderr_buf = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = stderr_buf
        try:
            code = main([
                "score",
                "--candidates", "Qwen/Qwen2.5-7B-Instruct",
                "--weights", "ifeval=-0.5,bbh=0.5",
            ])
        finally:
            sys.stderr = old_stderr
        self.assertNotEqual(code, 0)
        self.assertIn("Error", stderr_buf.getvalue())

    def test_07_pareto_command(self):
        stdout_buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = stdout_buf
        try:
            code = main(["pareto", "--metric", "hf_v2_avg", "--format", "json"])
        finally:
            sys.stdout = old_stdout
        self.assertEqual(code, 0)
        pts = json.loads(stdout_buf.getvalue())
        self.assertTrue(len(pts) > 0)
        self.assertIn("efficiency_ratio", pts[0])

    def test_08_audit_command(self):
        stdout_buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = stdout_buf
        try:
            code = main(["audit", "overfit-ai/Goodhart-Overfit-7B", "--format", "json"])
        finally:
            sys.stdout = old_stdout
        self.assertEqual(code, 0)
        report = json.loads(stdout_buf.getvalue())
        self.assertEqual(report["status"], "HIGH_CONTAMINATION_RISK")
        self.assertTrue(len(report["flags"]) > 0)

    def test_09_zipapp_standalone_subprocess(self):
        pyz_path = ROOT_DIR / "dist" / "benchwarmer.pyz"
        if not pyz_path.exists():
            subprocess.run([sys.executable, str(ROOT_DIR / "scripts" / "make_zipapp.py")], check=True)
        self.assertTrue(pyz_path.exists(), "dist/benchwarmer.pyz must exist")

        cmd = [
            sys.executable,
            str(pyz_path),
            "search",
            "phi-4",
            "--limit",
            "1",
            "--format",
            "json"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Zipapp stderr: {res.stderr}")
        data = json.loads(res.stdout)
        self.assertEqual(len(data), 1)
        self.assertIn(data[0]["model_id"], ["microsoft/Phi-4", "microsoft/Phi-4-mini-instruct"])


if __name__ == "__main__":
    unittest.main()
