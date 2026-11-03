---
name: benchwarmer
description: Offline zero-dependency LLM benchmark oracle for model selection, candidate ranking, hardware VRAM budget filtering, and contamination auditing.
---

# BenchWarmer Skill

BenchWarmer is a local, zero-dependency benchmark oracle and model evaluator. It provides verified Hugging Face Open LLM Leaderboard v2 metrics, LMSYS Arena Elo ratings, hardware VRAM footprint estimates across 10 quantization profiles, and statistical contamination audits.

## When to Use This Skill

1. **Model Selection & Architecture Sizing**: Whenever selecting an open-weight foundation model or fine-tune based on task-specific requirements (e.g. strict instruction following vs. deep mathematical reasoning vs. agentic coding).
2. **Hardware Constraint Verification**: Checking whether candidate models will fit within a specified consumer or enterprise VRAM envelope (e.g., 8 GB, 16 GB, 24 GB, 48 GB, 80 GB) across standard quantization bit-widths (FP16, BF16, Q8_0, Q5_K_M, Q4_K_M).
3. **Model Routing Decisions**: Scoring a set of candidate model IDs against weighted benchmark criteria to dynamically route user queries or agent workflows.
4. **Benchmark Contamination & Goodhart Auditing**: Detecting suspicious models where high multiple-choice benchmark scores (MMLU-Pro, GSM8K) mask severe reasoning collapses or test-set leakage.

---

## Tool & Command Reference

### 1. In-Process Python Usage

```python
from benchwarmer import BenchWarmer

bw = BenchWarmer()

# Search models
results = bw.search("llama 3.1", min_params=7.0, max_params=75.0)

# Compare two models
comparison = bw.compare("Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.3-70B-Instruct")

# Weighted candidate scoring
candidates = ["meta-llama/Llama-3.1-8B-Instruct", "Qwen/Qwen2.5-7B-Instruct", "microsoft/Phi-4"]
weights = {"ifeval": 0.4, "math_hard": 0.4, "mmlu_pro": 0.2}
scores = bw.score_candidates(candidates=candidates, weights=weights)

# Pareto frontier under VRAM constraint
pareto = bw.pareto_frontier(metric="hf_v2_avg", max_vram_gb=24.0, quant="q4_k_m")
```

### 2. CLI Invocations

- `benchwarmer search "<query>" [--min-params <float>] [--max-params <float>] [--format json|table|markdown]`
- `benchwarmer info "<model_id>" [--format json|table|markdown]`
- `benchwarmer compare "<model_a>" "<model_b>" [--format json|table|markdown]`
- `benchwarmer rank --benchmark <name> --vram <gb> --quant <quant_type> --limit <n>`
- `benchwarmer score --candidates <list_or_dash> --weights "<key=val,...>" [--strict]`
- `benchwarmer pareto --metric <name> --vram <gb> --quant <quant_type>`
- `benchwarmer audit "<model_id>"`

### 3. MCP Tool Invocations

When operating inside an MCP-enabled environment, call:
- `search_models(query, limit, min_params, max_params)`
- `get_model_benchmarks(model_id)`
- `compare_models(model_a, model_b)`
- `rank_models(benchmark, limit, min_params, max_params, max_vram_gb, quant)`
- `score_candidates(candidates, weights, strict_benchmarks)`
- `get_pareto_frontier(metric, max_vram_gb, quant)`
- `audit_model_contamination(model_id)`

---

## Best Practices

- Always specify `--quant` when evaluating VRAM constraints (defaults to `bf16`). Common efficient production choices include `q5_k_m` (5.7 bits) and `q4_k_m` (4.8 bits).
- For coding and agentic tasks, prioritize `ifeval` (instruction following) and `math_hard` (formal logic and code reasoning) rather than aggregate MMLU scores.
- Before committing to a fine-tuned model with extraordinarily high benchmark scores, run `audit` to check for Goodhart divergence smells (`mmlu_pro - ifeval > 30.0`).
