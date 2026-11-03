"""Unit tests for BenchWarmer MCP stdio server."""

import io
import json
from pathlib import Path
import sys
import unittest

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from benchwarmer.mcp import MCPServer, run_stdio_server


class TestBenchWarmerMCP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MCPServer()

    @classmethod
    def tearDownClass(cls):
        cls.server.bw.close()

    def test_01_initialize_handshake(self):
        req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        raw_resp = self.server.handle_message(req)
        self.assertIsNotNone(raw_resp)
        resp = json.loads(raw_resp)
        self.assertEqual(resp["id"], 1)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "benchwarmer")
        self.assertEqual(resp["result"]["protocolVersion"], "2024-11-05")

    def test_02_tools_list_schema_parity(self):
        req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        raw_resp = self.server.handle_message(req)
        resp = json.loads(raw_resp)
        tools = resp["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        expected_tools = [
            "search_models",
            "get_model_benchmarks",
            "compare_models",
            "rank_models",
            "score_candidates",
            "get_pareto_frontier",
            "audit_model_contamination",
        ]
        self.assertEqual(len(tools), 7)
        for expected in expected_tools:
            self.assertIn(expected, tool_names)

    def test_03_tool_search_models(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "search_models",
                "arguments": {"query": "llama", "limit": 2}
            }
        })
        resp = json.loads(self.server.handle_message(req))
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        self.assertIsInstance(data, list)
        self.assertLessEqual(len(data), 2)
        self.assertIn("model_id", data[0])

    def test_04_tool_get_model_benchmarks(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "get_model_benchmarks",
                "arguments": {"model_id": "microsoft/Phi-4"}
            }
        })
        resp = json.loads(self.server.handle_message(req))
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        self.assertEqual(data["model_id"], "microsoft/Phi-4")
        self.assertIn("scores", data)
        self.assertIn("estimated_vram_gb", data)

    def test_05_tool_compare_models(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "compare_models",
                "arguments": {
                    "model_a": "Qwen/Qwen2.5-72B-Instruct",
                    "model_b": "meta-llama/Llama-3.3-70B-Instruct"
                }
            }
        })
        resp = json.loads(self.server.handle_message(req))
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        self.assertIn("deltas", data)
        self.assertIn("composite_delta", data)

    def test_06_tool_rank_models(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "rank_models",
                "arguments": {
                    "benchmark": "ifeval",
                    "limit": 3,
                    "max_vram_gb": 48.0,
                    "quant": "q4_k_m"
                }
            }
        })
        resp = json.loads(self.server.handle_message(req))
        data = json.loads(resp["result"]["content"][0]["text"])
        self.assertLessEqual(len(data), 3)

    def test_07_tool_score_candidates(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "score_candidates",
                "arguments": {
                    "candidates": ["Qwen/Qwen2.5-7B-Instruct", "meta-llama/Llama-3.1-8B-Instruct"],
                    "weights": {"ifeval": 0.5, "mmlu_pro": 0.5}
                }
            }
        })
        resp = json.loads(self.server.handle_message(req))
        data = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(len(data), 2)
        self.assertIn("composite_score", data[0])

    def test_08_tool_get_pareto_frontier(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "get_pareto_frontier",
                "arguments": {"metric": "hf_v2_avg", "quant": "bf16"}
            }
        })
        resp = json.loads(self.server.handle_message(req))
        data = json.loads(resp["result"]["content"][0]["text"])
        self.assertTrue(len(data) > 0)
        self.assertIn("efficiency_ratio", data[0])

    def test_09_tool_audit_model_contamination(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "audit_model_contamination",
                "arguments": {"model_id": "overfit-ai/Goodhart-Overfit-7B"}
            }
        })
        resp = json.loads(self.server.handle_message(req))
        data = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(data["status"], "HIGH_CONTAMINATION_RISK")

    def test_10_jsonrpc_errors_and_notifications(self):
        # -32700 Parse error
        resp = json.loads(self.server.handle_message("invalid json content {{{"))
        self.assertEqual(resp["error"]["code"], -32700)

        # -32601 Method not found
        req_unknown = json.dumps({"jsonrpc": "2.0", "id": 10, "method": "unknown/method"})
        resp_unknown = json.loads(self.server.handle_message(req_unknown))
        self.assertEqual(resp_unknown["error"]["code"], -32601)

        # -32602 Invalid params (missing tool name in tools/call)
        req_bad_param = json.dumps({"jsonrpc": "2.0", "id": 11, "method": "tools/call", "params": {}})
        resp_bad_param = json.loads(self.server.handle_message(req_bad_param))
        self.assertEqual(resp_bad_param["error"]["code"], -32602)

        # Notification without id produces None
        notif = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertIsNone(self.server.handle_message(notif))

    def test_11_run_stdio_server_io_stream(self):
        in_stream = io.StringIO(
            json.dumps({"jsonrpc": "2.0", "id": 99, "method": "ping"}) + "\n"
        )
        out_stream = io.StringIO()
        run_stdio_server(in_stream=in_stream, out_stream=out_stream)
        raw_out = out_stream.getvalue().strip()
        resp = json.loads(raw_out)
        self.assertEqual(resp["id"], 99)
        self.assertEqual(resp["result"], {})


if __name__ == "__main__":
    unittest.main()
