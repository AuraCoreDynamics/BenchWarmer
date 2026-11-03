"""Stdio JSON-RPC 2.0 Model Context Protocol (MCP) server for BenchWarmer."""

import importlib.resources
import json
from pathlib import Path
import sys
from typing import Any, Dict, Optional, TextIO

from benchwarmer.api import BenchWarmer


def _load_mcp_schema() -> Dict[str, Any]:
    try:
        schema_resource = importlib.resources.files("benchwarmer").joinpath("mcp_schema.json")
        return json.loads(schema_resource.read_text(encoding="utf-8"))
    except Exception:
        fallback = Path(__file__).resolve().parent / "mcp_schema.json"
        return json.loads(fallback.read_text(encoding="utf-8"))


class MCPServer:
    """Stdio JSON-RPC 2.0 MCP Server."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.bw = BenchWarmer(db_path=db_path)
        self.schema = _load_mcp_schema()
        self.tools = self.schema.get("tools", [])

    def handle_tools_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch tool invocation directly to BenchWarmer."""
        try:
            if name == "search_models":
                query = arguments.get("query")
                if not query:
                    raise ValueError("Argument 'query' is required for search_models")
                limit = int(arguments.get("limit", 10))
                min_p = float(arguments["min_params"]) if "min_params" in arguments and arguments["min_params"] is not None else None
                max_p = float(arguments["max_params"]) if "max_params" in arguments and arguments["max_params"] is not None else None
                summaries = self.bw.search(query=query, limit=limit, min_params=min_p, max_params=max_p)
                result_data = [s.to_dict() for s in summaries]

            elif name == "get_model_benchmarks":
                model_id = arguments.get("model_id")
                if not model_id:
                    raise ValueError("Argument 'model_id' is required for get_model_benchmarks")
                record = self.bw.get_model(model_id)
                if not record:
                    return {
                        "isError": True,
                        "content": [{"type": "text", "text": f"Model '{model_id}' not found."}],
                    }
                result_data = record.to_dict()

            elif name == "compare_models":
                model_a = arguments.get("model_a")
                model_b = arguments.get("model_b")
                if not model_a or not model_b:
                    raise ValueError("Arguments 'model_a' and 'model_b' are required for compare_models")
                comp = self.bw.compare(model_a, model_b)
                result_data = comp.to_dict()

            elif name == "rank_models":
                bench = arguments.get("benchmark", "hf_v2_avg")
                limit = int(arguments.get("limit", 10))
                min_p = float(arguments["min_params"]) if "min_params" in arguments and arguments["min_params"] is not None else None
                max_p = float(arguments["max_params"]) if "max_params" in arguments and arguments["max_params"] is not None else None
                max_vram = float(arguments["max_vram_gb"]) if "max_vram_gb" in arguments and arguments["max_vram_gb"] is not None else None
                quant = arguments.get("quant", "bf16")
                ranked = self.bw.rank(
                    benchmark=bench, limit=limit, min_params=min_p, max_params=max_p,
                    max_vram_gb=max_vram, quant=quant
                )
                result_data = [r.to_dict() for r in ranked]

            elif name == "score_candidates":
                candidates = arguments.get("candidates")
                weights = arguments.get("weights")
                if not candidates or weights is None:
                    raise ValueError("Arguments 'candidates' and 'weights' are required for score_candidates")
                strict = bool(arguments.get("strict_benchmarks", False))
                scores = self.bw.score_candidates(candidates=candidates, weights=weights, strict_benchmarks=strict)
                result_data = [sc.to_dict() for sc in scores]

            elif name == "get_pareto_frontier":
                metric = arguments.get("metric", "hf_v2_avg")
                max_vram = float(arguments["max_vram_gb"]) if "max_vram_gb" in arguments and arguments["max_vram_gb"] is not None else None
                quant = arguments.get("quant", "bf16")
                frontier = self.bw.pareto_frontier(metric=metric, max_vram_gb=max_vram, quant=quant)
                result_data = [pt.to_dict() for pt in frontier]

            elif name == "audit_model_contamination":
                model_id = arguments.get("model_id")
                if not model_id:
                    raise ValueError("Argument 'model_id' is required for audit_model_contamination")
                report = self.bw.detect_anomalies(model_id)
                result_data = report.to_dict()

            else:
                return {
                    "isError": True,
                    "content": [{"type": "text", "text": f"Unknown tool: '{name}'"}],
                }

            # Return standard MCP tool call result
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result_data, indent=2),
                    }
                ]
            }

        except Exception as e:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Tool execution failed: {str(e)}"}],
            }

    def handle_message(self, line: str) -> Optional[str]:
        """Process incoming raw JSON-RPC frame. Returns serialized JSON-RPC response or None."""
        if not line or not line.strip():
            return None

        try:
            req = json.loads(line)
        except json.JSONDecodeError as err:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {err}"
                }
            })

        if not isinstance(req, dict):
            return json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32600,
                    "message": "Invalid Request"
                }
            })

        req_id = req.get("id")
        method = req.get("method")

        # Notifications (no id) -> do not emit response
        if req_id is None and method in ("notifications/initialized", "initialized"):
            return None

        if method == "initialize":
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "benchwarmer",
                        "version": "0.1.0"
                    }
                }
            })

        if method == "ping":
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {}
            })

        if method == "tools/list":
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": self.tools
                }
            })

        if method == "tools/call":
            params = req.get("params", {})
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            if not tool_name:
                return json.dumps({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: 'name' is required"
                    }
                })

            result = self.handle_tools_call(tool_name, tool_args)
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result
            })

        # Unknown method
        if req_id is not None:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: '{method}'"
                }
            })

        return None


def run_stdio_server(in_stream: TextIO = sys.stdin, out_stream: TextIO = sys.stdout) -> None:
    """Run MCP server over line-delimited JSON-RPC stdio."""
    server = MCPServer()
    try:
        for line in in_stream:
            resp = server.handle_message(line)
            if resp:
                out_stream.write(resp + "\n")
                out_stream.flush()
    except Exception as e:
        print(f"MCP server runtime error: {e}", file=sys.stderr)
    finally:
        server.bw.close()
