# BenchWarmer MCP Server Integration Guide

This guide describes how to connect the BenchWarmer Stdio JSON-RPC 2.0 Model Context Protocol (MCP) server to AI agents, IDEs (Cursor, Claude Desktop), and orchestration harnesses.

---

## Overview

BenchWarmer operates as a local, zero-dependency MCP tool provider over `sys.stdin` and `sys.stdout`. It provides 7 specialized tools to search, compare, rank, score, and audit LLMs based on empirical benchmark performance and hardware constraints.

### Tool Catalog

| Tool Name | Purpose | Required Arguments |
| :--- | :--- | :--- |
| `search_models` | Search models by keyword or parameter range | `query` (str) |
| `get_model_benchmarks` | Full benchmark metrics & VRAM footprint across 10 quantizations | `model_id` (str) |
| `compare_models` | Side-by-side metric comparison and composite delta | `model_a` (str), `model_b` (str) |
| `rank_models` | Rank models by benchmark with VRAM budget filter | None (defaults to `hf_v2_avg`) |
| `score_candidates` | Weighted candidate model evaluation | `candidates` (list), `weights` (dict) |
| `get_pareto_frontier` | Calculate capability vs VRAM Pareto-optimal frontier | None (defaults to `hf_v2_avg`) |
| `audit_model_contamination` | Detect benchmark contamination & reasoning cliffs | `model_id` (str) |

---

## Configuration

### Claude Desktop

Add the following block to your `claude_desktop_config.json`:

#### macOS / Linux
```json
{
  "mcpServers": {
    "benchwarmer": {
      "command": "python3",
      "args": ["-m", "benchwarmer", "mcp"]
    }
  }
}
```

#### Windows
```json
{
  "mcpServers": {
    "benchwarmer": {
      "command": "python.exe",
      "args": ["-m", "benchwarmer", "mcp"]
    }
  }
}
```

Or when running from a single-file zipapp:
```json
{
  "mcpServers": {
    "benchwarmer": {
      "command": "python.exe",
      "args": ["C:/path/to/dist/benchwarmer.pyz", "mcp"]
    }
  }
}
```

### Cursor IDE

In Cursor Settings → Features → MCP:
- **Type**: `command`
- **Name**: `benchwarmer`
- **Command**: `python -m benchwarmer mcp`

---

## Example JSON-RPC Invocations

### 1. `tools/list`
```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
```

### 2. `compare_models`
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "compare_models",
    "arguments": {
      "model_a": "Qwen/Qwen2.5-72B-Instruct",
      "model_b": "meta-llama/Llama-3.3-70B-Instruct"
    }
  }
}
```

### 3. `score_candidates`
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "score_candidates",
    "arguments": {
      "candidates": ["meta-llama/Llama-3.1-8B-Instruct", "Qwen/Qwen2.5-7B-Instruct"],
      "weights": {"ifeval": 0.6, "math_hard": 0.4},
      "strict_benchmarks": false
    }
  }
}
```

### 4. `audit_model_contamination`
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "audit_model_contamination",
    "arguments": {
      "model_id": "overfit-ai/Goodhart-Overfit-7B"
    }
  }
}
```
