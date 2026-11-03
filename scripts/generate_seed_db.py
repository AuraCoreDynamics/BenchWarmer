#!/usr/bin/env python3
"""Generate deterministic offline seed SQLite database for BenchWarmer.

Populates 28 realistic models spanning parameter sizes 0.5B to 405B+,
dense and MoE architectures, realistic HF Open LLM v2 and LMSYS Arena benchmarks,
and 2 intentional contamination benchmark traps.
"""

import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
from benchwarmer.db.connector import compute_canonical_checksum

MODELS_SEED_DATA = [
    {
        "model_id": "meta-llama/Llama-3.1-8B-Instruct",
        "org": "meta-llama",
        "model_name": "Llama-3.1-8B-Instruct",
        "base_model": "meta-llama/Llama-3.1-8B",
        "params_b": 8.03,
        "active_params_b": 8.03,
        "context_length": 131072,
        "architecture": "LlamaForCausalLM",
        "license": "llama3.1",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 73.12, "bbh": 68.30, "math_hard": 25.40,
            "gpqa": 32.81, "musr": 42.15, "mmlu_pro": 44.52, "arena_elo": 1206.5
        }
    },
    {
        "model_id": "meta-llama/Llama-3.1-70B-Instruct",
        "org": "meta-llama",
        "model_name": "Llama-3.1-70B-Instruct",
        "base_model": "meta-llama/Llama-3.1-70B",
        "params_b": 70.55,
        "active_params_b": 70.55,
        "context_length": 131072,
        "architecture": "LlamaForCausalLM",
        "license": "llama3.1",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 84.60, "bbh": 82.50, "math_hard": 46.80,
            "gpqa": 45.30, "musr": 51.40, "mmlu_pro": 62.15, "arena_elo": 1312.4
        }
    },
    {
        "model_id": "meta-llama/Llama-3.3-70B-Instruct",
        "org": "meta-llama",
        "model_name": "Llama-3.3-70B-Instruct",
        "base_model": "meta-llama/Llama-3.3-70B",
        "params_b": 70.55,
        "active_params_b": 70.55,
        "context_length": 131072,
        "architecture": "LlamaForCausalLM",
        "license": "llama3.3",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 88.40, "bbh": 85.90, "math_hard": 53.20,
            "gpqa": 49.80, "musr": 54.10, "mmlu_pro": 68.45, "arena_elo": 1345.8
        }
    },
    {
        "model_id": "meta-llama/Llama-3.1-405B-Instruct",
        "org": "meta-llama",
        "model_name": "Llama-3.1-405B-Instruct",
        "base_model": "meta-llama/Llama-3.1-405B",
        "params_b": 405.0,
        "active_params_b": 405.0,
        "context_length": 131072,
        "architecture": "LlamaForCausalLM",
        "license": "llama3.1",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 89.15, "bbh": 87.20, "math_hard": 58.60,
            "gpqa": 53.70, "musr": 57.80, "mmlu_pro": 73.20, "arena_elo": 1374.0
        }
    },
    {
        "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
        "org": "Qwen",
        "model_name": "Qwen2.5-0.5B-Instruct",
        "base_model": "Qwen/Qwen2.5-0.5B",
        "params_b": 0.49,
        "active_params_b": 0.49,
        "context_length": 32768,
        "architecture": "Qwen2ForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 42.10, "bbh": 36.40, "math_hard": 10.20,
            "gpqa": 23.50, "musr": 34.10, "mmlu_pro": 25.10, "arena_elo": 1024.0
        }
    },
    {
        "model_id": "Qwen/Qwen2.5-1.5B-Instruct",
        "org": "Qwen",
        "model_name": "Qwen2.5-1.5B-Instruct",
        "base_model": "Qwen/Qwen2.5-1.5B",
        "params_b": 1.54,
        "active_params_b": 1.54,
        "context_length": 32768,
        "architecture": "Qwen2ForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 56.80, "bbh": 49.30, "math_hard": 21.40,
            "gpqa": 28.10, "musr": 37.50, "mmlu_pro": 35.80, "arena_elo": 1098.5
        }
    },
    {
        "model_id": "Qwen/Qwen2.5-3B-Instruct",
        "org": "Qwen",
        "model_name": "Qwen2.5-3B-Instruct",
        "base_model": "Qwen/Qwen2.5-3B",
        "params_b": 3.09,
        "active_params_b": 3.09,
        "context_length": 32768,
        "architecture": "Qwen2ForCausalLM",
        "license": "qwen-research",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 65.40, "bbh": 61.20, "math_hard": 31.80,
            "gpqa": 33.40, "musr": 41.20, "mmlu_pro": 43.70, "arena_elo": 1165.0
        }
    },
    {
        "model_id": "Qwen/Qwen2.5-7B-Instruct",
        "org": "Qwen",
        "model_name": "Qwen2.5-7B-Instruct",
        "base_model": "Qwen/Qwen2.5-7B",
        "params_b": 7.61,
        "active_params_b": 7.61,
        "context_length": 131072,
        "architecture": "Qwen2ForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 77.20, "bbh": 73.60, "math_hard": 41.20,
            "gpqa": 38.60, "musr": 46.50, "mmlu_pro": 53.40, "arena_elo": 1242.0
        }
    },
    {
        "model_id": "Qwen/Qwen2.5-14B-Instruct",
        "org": "Qwen",
        "model_name": "Qwen2.5-14B-Instruct",
        "base_model": "Qwen/Qwen2.5-14B",
        "params_b": 14.77,
        "active_params_b": 14.77,
        "context_length": 131072,
        "architecture": "Qwen2ForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 82.50, "bbh": 79.80, "math_hard": 48.90,
            "gpqa": 44.20, "musr": 50.10, "mmlu_pro": 61.30, "arena_elo": 1288.5
        }
    },
    {
        "model_id": "Qwen/Qwen2.5-32B-Instruct",
        "org": "Qwen",
        "model_name": "Qwen2.5-32B-Instruct",
        "base_model": "Qwen/Qwen2.5-32B",
        "params_b": 32.76,
        "active_params_b": 32.76,
        "context_length": 131072,
        "architecture": "Qwen2ForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 85.80, "bbh": 83.10, "math_hard": 54.30,
            "gpqa": 48.10, "musr": 53.60, "mmlu_pro": 67.20, "arena_elo": 1320.0
        }
    },
    {
        "model_id": "Qwen/Qwen2.5-72B-Instruct",
        "org": "Qwen",
        "model_name": "Qwen2.5-72B-Instruct",
        "base_model": "Qwen/Qwen2.5-72B",
        "params_b": 72.71,
        "active_params_b": 72.71,
        "context_length": 131072,
        "architecture": "Qwen2ForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 88.90, "bbh": 86.80, "math_hard": 59.80,
            "gpqa": 52.40, "musr": 56.40, "mmlu_pro": 71.60, "arena_elo": 1352.0
        }
    },
    {
        "model_id": "Qwen/Qwen2.5-Coder-32B-Instruct",
        "org": "Qwen",
        "model_name": "Qwen2.5-Coder-32B-Instruct",
        "base_model": "Qwen/Qwen2.5-32B",
        "params_b": 32.76,
        "active_params_b": 32.76,
        "context_length": 131072,
        "architecture": "Qwen2ForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 86.40, "bbh": 84.70, "math_hard": 61.20,
            "gpqa": 49.50, "musr": 54.20, "mmlu_pro": 69.80, "arena_elo": 1334.5
        }
    },
    {
        "model_id": "mistralai/Mistral-7B-Instruct-v0.3",
        "org": "mistralai",
        "model_name": "Mistral-7B-Instruct-v0.3",
        "base_model": "mistralai/Mistral-7B-v0.3",
        "params_b": 7.25,
        "active_params_b": 7.25,
        "context_length": 32768,
        "architecture": "MistralForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 68.50, "bbh": 64.20, "math_hard": 21.80,
            "gpqa": 30.10, "musr": 41.50, "mmlu_pro": 41.20, "arena_elo": 1172.0
        }
    },
    {
        "model_id": "mistralai/Mistral-Small-24B-Instruct-2501",
        "org": "mistralai",
        "model_name": "Mistral-Small-24B-Instruct-2501",
        "base_model": "mistralai/Mistral-Small-24B-Base-2501",
        "params_b": 23.60,
        "active_params_b": 23.60,
        "context_length": 32768,
        "architecture": "MistralForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 84.20, "bbh": 81.30, "math_hard": 47.50,
            "gpqa": 46.10, "musr": 51.80, "mmlu_pro": 63.90, "arena_elo": 1308.0
        }
    },
    {
        "model_id": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "org": "mistralai",
        "model_name": "Mixtral-8x7B-Instruct-v0.1",
        "base_model": "mistralai/Mixtral-8x7B-v0.1",
        "params_b": 46.70,
        "active_params_b": 12.87,
        "context_length": 32768,
        "architecture": "MixtralForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 74.50, "bbh": 72.80, "math_hard": 33.40,
            "gpqa": 36.80, "musr": 45.90, "mmlu_pro": 51.50, "arena_elo": 1228.0
        }
    },
    {
        "model_id": "mistralai/Mixtral-8x22B-Instruct-v0.1",
        "org": "mistralai",
        "model_name": "Mixtral-8x22B-Instruct-v0.1",
        "base_model": "mistralai/Mixtral-8x22B-v0.1",
        "params_b": 141.0,
        "active_params_b": 39.0,
        "context_length": 65536,
        "architecture": "MixtralForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 85.10, "bbh": 82.70, "math_hard": 49.30,
            "gpqa": 47.20, "musr": 52.40, "mmlu_pro": 65.10, "arena_elo": 1318.0
        }
    },
    {
        "model_id": "deepseek-ai/DeepSeek-V2.5",
        "org": "deepseek-ai",
        "model_name": "DeepSeek-V2.5",
        "base_model": "deepseek-ai/DeepSeek-V2",
        "params_b": 236.0,
        "active_params_b": 21.0,
        "context_length": 131072,
        "architecture": "DeepseekV2ForCausalLM",
        "license": "deepseek",
        "precision": "BF16",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 86.80, "bbh": 84.10, "math_hard": 55.40,
            "gpqa": 50.10, "musr": 55.20, "mmlu_pro": 69.30, "arena_elo": 1338.0
        }
    },
    {
        "model_id": "deepseek-ai/DeepSeek-V3",
        "org": "deepseek-ai",
        "model_name": "DeepSeek-V3",
        "base_model": "deepseek-ai/DeepSeek-V3-Base",
        "params_b": 671.0,
        "active_params_b": 37.0,
        "context_length": 131072,
        "architecture": "DeepseekV3ForCausalLM",
        "license": "deepseek",
        "precision": "FP8",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 90.40, "bbh": 88.50, "math_hard": 63.80,
            "gpqa": 56.20, "musr": 59.40, "mmlu_pro": 76.50, "arena_elo": 1388.0
        }
    },
    {
        "model_id": "microsoft/Phi-3.5-mini-instruct",
        "org": "microsoft",
        "model_name": "Phi-3.5-mini-instruct",
        "base_model": "microsoft/Phi-3.5-mini",
        "params_b": 3.82,
        "active_params_b": 3.82,
        "context_length": 131072,
        "architecture": "Phi3ForCausalLM",
        "license": "mit",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 66.80, "bbh": 62.40, "math_hard": 32.10,
            "gpqa": 34.0, "musr": 42.10, "mmlu_pro": 44.80, "arena_elo": 1178.0
        }
    },
    {
        "model_id": "microsoft/Phi-4",
        "org": "microsoft",
        "model_name": "Phi-4",
        "base_model": "microsoft/Phi-4-Base",
        "params_b": 14.0,
        "active_params_b": 14.0,
        "context_length": 16384,
        "architecture": "Phi3ForCausalLM",
        "license": "mit",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 83.40, "bbh": 81.50, "math_hard": 55.80,
            "gpqa": 47.90, "musr": 52.80, "mmlu_pro": 65.40, "arena_elo": 1310.0
        }
    },
    {
        "model_id": "google/gemma-2-2b-it",
        "org": "google",
        "model_name": "gemma-2-2b-it",
        "base_model": "google/gemma-2-2b",
        "params_b": 2.61,
        "active_params_b": 2.61,
        "context_length": 8192,
        "architecture": "Gemma2ForCausalLM",
        "license": "gemma",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 59.20, "bbh": 54.10, "math_hard": 23.40,
            "gpqa": 29.50, "musr": 38.60, "mmlu_pro": 37.40, "arena_elo": 1115.0
        }
    },
    {
        "model_id": "google/gemma-2-9b-it",
        "org": "google",
        "model_name": "gemma-2-9b-it",
        "base_model": "google/gemma-2-9b",
        "params_b": 9.24,
        "active_params_b": 9.24,
        "context_length": 8192,
        "architecture": "Gemma2ForCausalLM",
        "license": "gemma",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 79.80, "bbh": 76.50, "math_hard": 42.10,
            "gpqa": 40.80, "musr": 48.20, "mmlu_pro": 56.90, "arena_elo": 1265.0
        }
    },
    {
        "model_id": "google/gemma-2-27b-it",
        "org": "google",
        "model_name": "gemma-2-27b-it",
        "base_model": "google/gemma-2-27b",
        "params_b": 27.23,
        "active_params_b": 27.23,
        "context_length": 8192,
        "architecture": "Gemma2ForCausalLM",
        "license": "gemma",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 85.30, "bbh": 82.90, "math_hard": 51.40,
            "gpqa": 47.50, "musr": 53.10, "mmlu_pro": 66.80, "arena_elo": 1326.0
        }
    },
    {
        "model_id": "cohereforai/c4ai-command-r-v01",
        "org": "cohereforai",
        "model_name": "c4ai-command-r-v01",
        "base_model": "cohereforai/c4ai-command-r-base",
        "params_b": 35.0,
        "active_params_b": 35.0,
        "context_length": 131072,
        "architecture": "CohereForCausalLM",
        "license": "cc-by-nc-4.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 78.40, "bbh": 74.20, "math_hard": 36.80,
            "gpqa": 39.40, "musr": 47.90, "mmlu_pro": 54.80, "arena_elo": 1238.0
        }
    },
    {
        "model_id": "cohereforai/c4ai-command-r-plus",
        "org": "cohereforai",
        "model_name": "c4ai-command-r-plus",
        "base_model": "cohereforai/c4ai-command-r-plus-base",
        "params_b": 104.0,
        "active_params_b": 104.0,
        "context_length": 131072,
        "architecture": "CohereForCausalLM",
        "license": "cc-by-nc-4.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 86.20, "bbh": 83.50, "math_hard": 49.80,
            "gpqa": 47.0, "musr": 53.40, "mmlu_pro": 65.80, "arena_elo": 1322.0
        }
    },
    {
        "model_id": "tiiuae/falcon-7b-instruct",
        "org": "tiiuae",
        "model_name": "falcon-7b-instruct",
        "base_model": "tiiuae/falcon-7b",
        "params_b": 7.0,
        "active_params_b": 7.0,
        "context_length": 2048,
        "architecture": "FalconForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 48.20, "bbh": 42.10, "math_hard": 12.50,
            "gpqa": 24.30, "musr": 35.80, "mmlu_pro": 31.40, "arena_elo": 1052.0
        }
    },
    # Contamination traps exhibiting severe GSM8K/MMLU-Pro vs MATH-Hard/IFEval divergence
    {
        "model_id": "overfit-ai/Goodhart-Overfit-7B",
        "org": "overfit-ai",
        "model_name": "Goodhart-Overfit-7B",
        "base_model": "meta-llama/Llama-3.1-8B",
        "params_b": 7.0,
        "active_params_b": 7.0,
        "context_length": 8192,
        "architecture": "LlamaForCausalLM",
        "license": "mit",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 38.0, "bbh": 78.50, "math_hard": 12.40,
            "gpqa": 25.10, "musr": 36.20, "mmlu_pro": 89.50, "arena_elo": 1010.0
        }
    },
    {
        "model_id": "benchmark-hackers/ContamMax-14B",
        "org": "benchmark-hackers",
        "model_name": "ContamMax-14B",
        "base_model": "Qwen/Qwen2.5-14B",
        "params_b": 14.0,
        "active_params_b": 14.0,
        "context_length": 8192,
        "architecture": "Qwen2ForCausalLM",
        "license": "mit",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 35.20, "bbh": 82.0, "math_hard": 14.10,
            "gpqa": 28.0, "musr": 38.0, "mmlu_pro": 92.10, "arena_elo": 1045.0
        }
    }
]


def normalize_arena_elo(raw_elo: float) -> float:
    """Normalize raw Elo (typically 800-1500) to uniform [0.0, 100.0] scale."""
    min_elo = 800.0
    max_elo = 1500.0
    return ((raw_elo - min_elo) / (max_elo - min_elo)) * 100.0


def build_seed_database(target_db: Path, schema_file: Path) -> str:
    target_db.parent.mkdir(parents=True, exist_ok=True)
    if target_db.exists():
        target_db.unlink()

    conn = sqlite3.connect(target_db)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(schema_file.read_text(encoding="utf-8"))

    cursor = conn.cursor()

    for item in MODELS_SEED_DATA:
        raw_meta = json.dumps({
            "model_id": item["model_id"],
            "org": item["org"],
            "architecture": item["architecture"],
            "license": item["license"],
        })
        cursor.execute(
            """
            INSERT INTO models (
                model_id, org, model_name, base_model, params_b, context_length,
                architecture, license, precision, is_moe, active_params_b,
                sha, last_modified, raw_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["model_id"],
                item["org"],
                item["model_name"],
                item["base_model"],
                item["params_b"],
                item["context_length"],
                item["architecture"],
                item["license"],
                item["precision"],
                item["is_moe"],
                item["active_params_b"],
                "seed_sha_" + item["model_name"].lower(),
                "2026-01-01T00:00:00Z",
                raw_meta
            )
        )

        for bench, val in item["benchmarks"].items():
            if bench == "arena_elo":
                suite = "lmsys_arena"
                metric = "elo"
                raw_score = float(val)
                score = normalize_arena_elo(raw_score)
            else:
                suite = "hf_v2"
                metric = "norm_score"
                raw_score = float(val)
                score = float(val)

            cursor.execute(
                """
                INSERT INTO benchmark_scores (model_id, suite, benchmark, metric, score, raw_score)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (item["model_id"], suite, bench, metric, score, raw_score)
            )

    # Populate FTS5 table
    cursor.execute(
        """
        INSERT INTO models_fts (rowid, model_id, org, model_name, architecture)
        SELECT rowid, model_id, org, model_name, architecture FROM models
        """
    )

    # Populate meta_info
    cursor.execute("INSERT INTO meta_info (key, value) VALUES (?, ?)", ("version", "0.1.0"))
    cursor.execute("INSERT INTO meta_info (key, value) VALUES (?, ?)", ("seed_type", "deterministic_hf_v2_arena"))
    cursor.execute("INSERT INTO meta_info (key, value) VALUES (?, ?)", ("model_count", str(len(MODELS_SEED_DATA))))

    # Optimize and flush
    conn.commit()

    canonical_sha = compute_canonical_checksum(conn)
    cursor.execute("INSERT INTO meta_info (key, value) VALUES (?, ?)", ("canonical_sha256", canonical_sha))
    conn.commit()

    conn.execute("PRAGMA optimize;")
    conn.close()

    return canonical_sha


def main() -> int:
    target_db = ROOT_DIR / "src" / "benchwarmer" / "data" / "benchmarks.db"
    checksum_file = ROOT_DIR / "src" / "benchwarmer" / "data" / "checksum.sha256"
    schema_file = ROOT_DIR / "src" / "benchwarmer" / "db" / "schema.sql"

    print(f"Generating deterministic seed database at {target_db}...")
    canonical_sha = build_seed_database(target_db, schema_file)
    checksum_file.write_text(canonical_sha + "\n", encoding="utf-8")
    print(f"Canonical SHA-256: {canonical_sha}")
    print(f"Wrote checksum to {checksum_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
