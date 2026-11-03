# BenchWarmer

[![CI](https://github.com/AuraCoreDynamics/BenchWarmer/actions/workflows/ci.yml/badge.svg)](https://github.com/AuraCoreDynamics/BenchWarmer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.9+](https://img.shields.io/badge/python-3.9%20|%203.10%20|%203.11%20|%203.12%20|%203.13-blue.svg)](https://www.python.org/)
[![Zero Runtime Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](pyproject.toml)

> **Offline Zero-Dependency LLM Benchmark Oracle & Pareto Routing Engine**

BenchWarmer is a high-speed, strictly offline, zero-runtime-dependency benchmark oracle for Large Language Models. Built on an embedded, read-only SQLite database with FTS5 full-text indexing, it delivers microsecond candidate scoring, side-by-side metric deltas, hardware-constrained Pareto frontier calculations, and Goodhart overfit/contamination audits.

---

## Architectural Highlights

- **Zero Runtime Dependencies**: Pure Python 3.9–3.13 standard library (`dependencies = []`). Runs in air-gapped, isolated, or embedded production environments.
- **Embedded Read-Only SQLite & FTS5**: Packaged with a pre-indexed `benchmarks.db` featuring 4-stage resolution cascade: exact match → case-insensitive → org-stripped → FTS5 BM25 rank.
- **Micro-Precision Invariance**: Normalized benchmark metrics stored as full 64-bit IEEE 754 floats (`REAL`). Never prematurely rounds internal math.
- **Single-File `.pyz` Executable**: Portable zipapp bundle compiled via `python scripts/make_zipapp.py`.
- **Tri-Interface Support**: Queryable as an in-process Python library (for model routers like `aurarouter`), a command-line interface, a headless-safe Tkinter desktop GUI, or a Stdio JSON-RPC 2.0 Model Context Protocol (MCP) server.

---

## Installation & Quickstart

### In-Process Python Library

```bash
pip install benchwarmer
```

```python
from benchwarmer import BenchWarmer

bw = BenchWarmer()

# Compare two models with exact unrounded deltas
comparison = bw.compare("Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.3-70B-Instruct")
print(f"Composite Delta: {comparison.composite_delta:+.2f}")
for bench, delta in comparison.deltas.items():
    print(f"  {bench}: {delta.score_a:.2f} vs {delta.score_b:.2f} (winner: {delta.winner})")

# Score candidates for routing (e.g. aurarouter dynamic dispatch)
candidates = ["meta-llama/Llama-3.1-8B-Instruct", "Qwen/Qwen2.5-7B-Instruct", "microsoft/Phi-4"]
weights = {"ifeval": 0.4, "math_hard": 0.4, "mmlu_pro": 0.2}
ranked = bw.score_candidates(candidates=candidates, weights=weights)
for item in ranked:
    print(f"{item.matched_model_id}: {item.composite_score:.2f}")

# Calculate Pareto optimal frontier within a 24GB VRAM constraint
pareto = bw.pareto_frontier(metric="hf_v2_avg", max_vram_gb=24.0, quant="q4_k_m")
for point in pareto:
    print(f"{point.model_id} ({point.estimated_vram_gb:.1f} GB): score {point.score:.2f}")
```

---

## Command Line Interface (CLI)

```bash
# Search models with parameter filtering
benchwarmer search "llama" --min-params 7.0 --max-params 75.0 --format table

# Side-by-side model comparison
benchwarmer compare "Qwen/Qwen2.5-72B-Instruct" "meta-llama/Llama-3.3-70B-Instruct" --format markdown

# Rank models under hardware VRAM constraint
benchwarmer rank --benchmark math_hard --vram 48.0 --quant q4_k_m --limit 5

# Pipe candidate model IDs from stdin for weighted scoring
cat candidates.json | benchwarmer score --candidates - --weights ifeval=0.5,math_hard=0.5 --format json

# Compute Pareto-optimal efficiency frontier
benchwarmer pareto --metric hf_v2_avg --quant bf16 --format table

# Audit a model for benchmark contamination or Goodhart overfit smells
benchwarmer audit "overfit-ai/Goodhart-Overfit-7B" --format json
```

---

## Single-File `.pyz` Distribution

For air-gapped environments or sneakernet deployment, BenchWarmer compiles into a single executable archive:

```bash
python scripts/make_zipapp.py
# Produces dist/benchwarmer.pyz (~38 KB)

python dist/benchwarmer.pyz compare "Qwen/Qwen2.5-72B-Instruct" "meta-llama/Llama-3.3-70B-Instruct" --format json
```

---

## Stdio MCP Server (JSON-RPC 2.0)

BenchWarmer includes a native Model Context Protocol server over standard I/O:

```bash
benchwarmer mcp
```

Add to Claude Desktop (`claude_desktop_config.json`) or Cursor:

```json
{
  "mcpServers": {
    "benchwarmer": {
      "command": "python",
      "args": ["-m", "benchwarmer", "mcp"]
    }
  }
}
```

See [docs/MCP_GUIDE.md](docs/MCP_GUIDE.md) for full configuration details.

---

## Desktop GUI

Launch the 3-tab graphical comparator and leaderboard:

```bash
benchwarmer gui
```

- **Tab 1: Leaderboard & Search**: Filter models by parameter size and VRAM footprint with instant FTS search.
- **Tab 2: Side-by-Side Comparator**: Delta visualization with color tags and one-click Markdown clipboard export.
- **Tab 3: Pareto & Contamination Audit**: Interactive Pareto curve inspection and contamination diagnostics.

---

## Governance & Verification

BenchWarmer enforces the BLACK Framework v2.2 specification:
- `python scripts/black_preflight_audit.py`: AST-level precision check, zero-runtime-dependency verification, and remediation mode test-fixture immutability gate.
- `python scripts/black_redteam_harness.py scoring.json`: Red-team validation against test density and numerical precision invariance.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
