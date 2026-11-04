#!/usr/bin/env python3
"""Generate deterministic offline seed SQLite database for BenchWarmer.

Populates 79 foundation and frontier models across parameter classes:
- Proprietary frontier leaders (OpenAI o1, o3-mini, o1-mini, o1-preview, GPT-4o, GPT-4o-mini, GPT-4-turbo, GPT-3.5-turbo; Anthropic Claude 3.5 Sonnet/Haiku/Opus; Google Gemini 2.0 Flash/Thinking/1.5 Pro/Flash/Flash-8B; xAI Grok-2/Grok-2-mini)
- Open reasoning and foundation models (DeepSeek-R1, R1-Distill-Qwen 32B/14B/7B, R1-Distill-Llama 70B/8B, DeepSeek-V3; Llama 3.3/3.1 8B-405B, Llama 3.2 1B/3B; Qwen 2.5 0.5B-72B, Qwen Coder, QwQ-32B, Qwen Math; Mistral Large/Small/Mixtral/Codestral/NeMo; Phi-4, Phi-3.5; Gemma 2 27B/9B/2B; Yi 1.5; Falcon 3; OLMo 2; open-weights Grok-1; NVIDIA Nemotron 70B/340B/4B/NVLM; Snowflake Arctic; Databricks DBRX; OpenAI GPT-2/GPT-2-XL)
- Intentional benchmark contamination/overfit traps (Goodhart-Overfit-7B, ContamMax-14B)
"""

import json
from pathlib import Path
import sqlite3
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
from benchwarmer.db.connector import compute_canonical_checksum

MODELS_SEED_DATA = [
    # --- OpenAI Proprietary & Historical Models ---
    {
        "model_id": "openai/o1",
        "org": "openai",
        "model_name": "o1",
        "base_model": None,
        "params_b": None,
        "active_params_b": None,
        "context_length": 200000,
        "architecture": "Proprietary",
        "license": "proprietary",
        "precision": "Unknown",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 89.20, "bbh": 92.50, "math_hard": 94.80,
            "gpqa": 77.30, "musr": 66.40, "mmlu_pro": 87.20, "arena_elo": 1355.0
        }
    },
    {
        "model_id": "openai/o3-mini",
        "org": "openai",
        "model_name": "o3-mini",
        "base_model": None,
        "params_b": None,
        "active_params_b": None,
        "context_length": 200000,
        "architecture": "Proprietary",
        "license": "proprietary",
        "precision": "Unknown",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 86.10, "bbh": 90.80, "math_hard": 92.40,
            "gpqa": 71.20, "musr": 63.50, "mmlu_pro": 84.00, "arena_elo": 1330.0
        }
    },
    {
        "model_id": "openai/o1-mini",
        "org": "openai",
        "model_name": "o1-mini",
        "base_model": None,
        "params_b": None,
        "active_params_b": None,
        "context_length": 128000,
        "architecture": "Proprietary",
        "license": "proprietary",
        "precision": "Unknown",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 82.00, "bbh": 88.40, "math_hard": 90.00,
            "gpqa": 60.00, "musr": 59.10, "mmlu_pro": 78.50, "arena_elo": 1270.0
        }
    },
    {
        "model_id": "openai/o1-preview",
        "org": "openai",
        "model_name": "o1-preview",
        "base_model": None,
        "params_b": None,
        "active_params_b": None,
        "context_length": 128000,
        "architecture": "Proprietary",
        "license": "proprietary",
        "precision": "Unknown",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 85.00, "bbh": 89.20, "math_hard": 85.50,
            "gpqa": 73.30, "musr": 62.00, "mmlu_pro": 83.10, "arena_elo": 1335.0
        }
    },
    {
        "model_id": "openai/gpt-4o",
        "org": "openai",
        "model_name": "gpt-4o",
        "base_model": None,
        "params_b": None,
        "active_params_b": None,
        "context_length": 128000,
        "architecture": "Proprietary",
        "license": "proprietary",
        "precision": "Unknown",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 84.30, "bbh": 88.20, "math_hard": 76.60,
            "gpqa": 53.60, "musr": 58.20, "mmlu_pro": 77.40, "arena_elo": 1288.0
        }
    },
    {
        "model_id": "openai/gpt-4o-mini",
        "org": "openai",
        "model_name": "gpt-4o-mini",
        "base_model": None,
        "params_b": None,
        "active_params_b": None,
        "context_length": 128000,
        "architecture": "Proprietary",
        "license": "proprietary",
        "precision": "Unknown",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 79.50, "bbh": 82.00, "math_hard": 70.20,
            "gpqa": 40.20, "musr": 52.10, "mmlu_pro": 65.80, "arena_elo": 1224.0
        }
    },
    {
        "model_id": "openai/gpt-4-turbo",
        "org": "openai",
        "model_name": "gpt-4-turbo",
        "base_model": None,
        "params_b": None,
        "active_params_b": None,
        "context_length": 128000,
        "architecture": "Proprietary",
        "license": "proprietary",
        "precision": "Unknown",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 81.00, "bbh": 86.50, "math_hard": 62.40,
            "gpqa": 48.00, "musr": 54.20, "mmlu_pro": 72.00, "arena_elo": 1255.0
        }
    },
    {
        "model_id": "openai/gpt-3.5-turbo",
        "org": "openai",
        "model_name": "gpt-3.5-turbo",
        "base_model": None,
        "params_b": None,
        "active_params_b": None,
        "context_length": 16385,
        "architecture": "Proprietary",
        "license": "proprietary",
        "precision": "Unknown",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 58.20, "bbh": 68.00, "math_hard": 28.50,
            "gpqa": 32.10, "musr": 42.00, "mmlu_pro": 48.00, "arena_elo": 1115.0
        }
    },
    # --- OpenAI Open-Source Weights Models ---
    {
        "model_id": "openai/gpt2-xl",
        "org": "openai",
        "model_name": "gpt2-xl",
        "base_model": None,
        "params_b": 1.56,
        "active_params_b": 1.56,
        "context_length": 1024,
        "architecture": "GPT2LMHeadModel",
        "license": "mit",
        "precision": "FP32",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 12.00, "bbh": 28.40, "math_hard": 2.10,
            "gpqa": 18.00, "musr": 22.00, "mmlu_pro": 10.50, "arena_elo": 850.0
        }
    },
    {
        "model_id": "openai/gpt2",
        "org": "openai",
        "model_name": "gpt2",
        "base_model": None,
        "params_b": 0.12,
        "active_params_b": 0.12,
        "context_length": 1024,
        "architecture": "GPT2LMHeadModel",
        "license": "mit",
        "precision": "FP32",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 5.20, "bbh": 16.20, "math_hard": 0.80,
            "gpqa": 12.50, "musr": 15.00, "mmlu_pro": 6.20, "arena_elo": 810.0
        }
    },

    # --- Anthropic Claude Models ---
    {
        "model_id": "anthropic/claude-3-5-sonnet-20241022",
        "org": "anthropic",
        "model_name": "claude-3-5-sonnet-20241022",
        "base_model": None,
        "params_b": None,
        "active_params_b": None,
        "context_length": 200000,
        "architecture": "Proprietary",
        "license": "proprietary",
        "precision": "Unknown",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 88.50, "bbh": 89.80, "math_hard": 78.30,
            "gpqa": 65.00, "musr": 61.20, "mmlu_pro": 82.40, "arena_elo": 1338.0
        }
    },
    {
        "model_id": "anthropic/claude-3-5-haiku-20241022",
        "org": "anthropic",
        "model_name": "claude-3-5-haiku-20241022",
        "base_model": None,
        "params_b": None,
        "active_params_b": None,
        "context_length": 200000,
        "architecture": "Proprietary",
        "license": "proprietary",
        "precision": "Unknown",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 80.20, "bbh": 80.40, "math_hard": 62.50,
            "gpqa": 41.50, "musr": 51.80, "mmlu_pro": 66.00, "arena_elo": 1235.0
        }
    },
    {
        "model_id": "anthropic/claude-3-opus-20240229",
        "org": "anthropic",
        "model_name": "claude-3-opus-20240229",
        "base_model": None,
        "params_b": None,
        "active_params_b": None,
        "context_length": 200000,
        "architecture": "Proprietary",
        "license": "proprietary",
        "precision": "Unknown",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 82.50, "bbh": 86.80, "math_hard": 60.10,
            "gpqa": 50.40, "musr": 55.00, "mmlu_pro": 73.10, "arena_elo": 1260.0
        }
    },

    # --- Google Gemini & Gemma Models ---
    {
        "model_id": "google/gemini-2.0-flash-exp",
        "org": "google",
        "model_name": "gemini-2.0-flash-exp",
        "base_model": None,
        "params_b": None,
        "active_params_b": None,
        "context_length": 1000000,
        "architecture": "Proprietary",
        "license": "proprietary",
        "precision": "Unknown",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 87.20, "bbh": 88.50, "math_hard": 82.00,
            "gpqa": 64.20, "musr": 60.50, "mmlu_pro": 76.00, "arena_elo": 1325.0
        }
    },
    {
        "model_id": "google/gemini-2.0-flash-thinking-exp",
        "org": "google",
        "model_name": "gemini-2.0-flash-thinking-exp",
        "base_model": None,
        "params_b": None,
        "active_params_b": None,
        "context_length": 1000000,
        "architecture": "Proprietary",
        "license": "proprietary",
        "precision": "Unknown",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 88.00, "bbh": 91.50, "math_hard": 93.80,
            "gpqa": 75.00, "musr": 64.00, "mmlu_pro": 85.50, "arena_elo": 1360.0
        }
    },
    {
        "model_id": "google/gemini-1.5-pro",
        "org": "google",
        "model_name": "gemini-1.5-pro",
        "base_model": None,
        "params_b": None,
        "active_params_b": None,
        "context_length": 2000000,
        "architecture": "Proprietary",
        "license": "proprietary",
        "precision": "Unknown",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 84.00, "bbh": 86.40, "math_hard": 67.70,
            "gpqa": 58.50, "musr": 57.00, "mmlu_pro": 73.60, "arena_elo": 1295.0
        }
    },
    {
        "model_id": "google/gemini-1.5-flash",
        "org": "google",
        "model_name": "gemini-1.5-flash",
        "base_model": None,
        "params_b": None,
        "active_params_b": None,
        "context_length": 1000000,
        "architecture": "Proprietary",
        "license": "proprietary",
        "precision": "Unknown",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 79.00, "bbh": 79.50, "math_hard": 56.40,
            "gpqa": 43.50, "musr": 50.20, "mmlu_pro": 64.50, "arena_elo": 1230.0
        }
    },
    {
        "model_id": "google/gemini-1.5-flash-8b",
        "org": "google",
        "model_name": "gemini-1.5-flash-8b",
        "base_model": None,
        "params_b": None,
        "active_params_b": None,
        "context_length": 1000000,
        "architecture": "Proprietary",
        "license": "proprietary",
        "precision": "Unknown",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 76.50, "bbh": 75.00, "math_hard": 51.00,
            "gpqa": 39.50, "musr": 48.00, "mmlu_pro": 60.50, "arena_elo": 1198.0
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
            "ifeval": 79.80, "bbh": 81.20, "math_hard": 52.80,
            "gpqa": 46.50, "musr": 52.40, "mmlu_pro": 65.20, "arena_elo": 1265.0
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
            "ifeval": 77.20, "bbh": 74.00, "math_hard": 46.50,
            "gpqa": 42.00, "musr": 47.80, "mmlu_pro": 59.80, "arena_elo": 1222.0
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
            "ifeval": 56.40, "bbh": 52.80, "math_hard": 24.20,
            "gpqa": 29.50, "musr": 36.80, "mmlu_pro": 42.50, "arena_elo": 1130.0
        }
    },
    {
        "model_id": "google/gemma-7b-it",
        "org": "google",
        "model_name": "gemma-7b-it",
        "base_model": "google/gemma-7b",
        "params_b": 8.54,
        "active_params_b": 8.54,
        "context_length": 8192,
        "architecture": "GemmaForCausalLM",
        "license": "gemma",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 54.20, "bbh": 61.50, "math_hard": 28.40,
            "gpqa": 32.00, "musr": 39.50, "mmlu_pro": 44.80, "arena_elo": 1145.0
        }
    },

    # --- xAI Models (Proprietary & Open Source) ---
    {
        "model_id": "xai/grok-2",
        "org": "xai",
        "model_name": "grok-2",
        "base_model": None,
        "params_b": None,
        "active_params_b": None,
        "context_length": 131072,
        "architecture": "Proprietary",
        "license": "proprietary",
        "precision": "Unknown",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 84.50, "bbh": 87.00, "math_hard": 74.00,
            "gpqa": 52.10, "musr": 56.50, "mmlu_pro": 76.50, "arena_elo": 1290.0
        }
    },
    {
        "model_id": "xai/grok-2-mini",
        "org": "xai",
        "model_name": "grok-2-mini",
        "base_model": None,
        "params_b": None,
        "active_params_b": None,
        "context_length": 131072,
        "architecture": "Proprietary",
        "license": "proprietary",
        "precision": "Unknown",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 79.20, "bbh": 82.50, "math_hard": 66.80,
            "gpqa": 46.20, "musr": 51.50, "mmlu_pro": 68.40, "arena_elo": 1245.0
        }
    },
    {
        "model_id": "xai/grok-1",
        "org": "xai",
        "model_name": "grok-1",
        "base_model": None,
        "params_b": 314.0,
        "active_params_b": 86.0,
        "context_length": 8192,
        "architecture": "Grok1ModelForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 71.00, "bbh": 78.50, "math_hard": 50.20,
            "gpqa": 44.50, "musr": 48.00, "mmlu_pro": 62.00, "arena_elo": 1210.0
        }
    },

    # --- NVIDIA Models ---
    {
        "model_id": "nvidia/Llama-3.1-Nemotron-70B-Instruct",
        "org": "nvidia",
        "model_name": "Llama-3.1-Nemotron-70B-Instruct",
        "base_model": "meta-llama/Llama-3.1-70B",
        "params_b": 70.60,
        "active_params_b": 70.60,
        "context_length": 131072,
        "architecture": "LlamaForCausalLM",
        "license": "other",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 89.20, "bbh": 88.00, "math_hard": 68.50,
            "gpqa": 54.80, "musr": 59.20, "mmlu_pro": 78.20, "arena_elo": 1342.0
        }
    },
    {
        "model_id": "nvidia/Nemotron-4-340B-Instruct",
        "org": "nvidia",
        "model_name": "Nemotron-4-340B-Instruct",
        "base_model": "nvidia/Nemotron-4-340B-Base",
        "params_b": 340.00,
        "active_params_b": 340.00,
        "context_length": 4096,
        "architecture": "NemotronForCausalLM",
        "license": "nvidia-open-model-license",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 84.10, "bbh": 86.20, "math_hard": 61.40,
            "gpqa": 51.20, "musr": 55.00, "mmlu_pro": 74.50, "arena_elo": 1295.0
        }
    },
    {
        "model_id": "nvidia/NVLM-D-72B",
        "org": "nvidia",
        "model_name": "NVLM-D-72B",
        "base_model": "Qwen/Qwen2-72B-Instruct",
        "params_b": 72.00,
        "active_params_b": 72.00,
        "context_length": 32768,
        "architecture": "Qwen2ForCausalLM",
        "license": "cc-by-nc-4.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 82.50, "bbh": 85.00, "math_hard": 59.80,
            "gpqa": 50.40, "musr": 54.00, "mmlu_pro": 73.10, "arena_elo": 1275.0
        }
    },
    {
        "model_id": "nvidia/Mistral-NeMo-Minitron-8B-Base",
        "org": "nvidia",
        "model_name": "Mistral-NeMo-Minitron-8B-Base",
        "base_model": "mistralai/Mistral-Nemo-Base-2407",
        "params_b": 8.00,
        "active_params_b": 8.00,
        "context_length": 8192,
        "architecture": "MistralForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 65.40, "bbh": 68.20, "math_hard": 28.50,
            "gpqa": 34.00, "musr": 42.10, "mmlu_pro": 51.20, "arena_elo": 1180.0
        }
    },
    {
        "model_id": "nvidia/Nemotron-Mini-4B-Instruct",
        "org": "nvidia",
        "model_name": "Nemotron-Mini-4B-Instruct",
        "base_model": None,
        "params_b": 4.00,
        "active_params_b": 4.00,
        "context_length": 4096,
        "architecture": "NemotronForCausalLM",
        "license": "nvidia-open-model-license",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 68.00, "bbh": 66.50, "math_hard": 26.20,
            "gpqa": 31.80, "musr": 39.50, "mmlu_pro": 47.00, "arena_elo": 1150.0
        }
    },

    # --- DeepSeek Reasoning & Foundation Models ---
    {
        "model_id": "deepseek-ai/DeepSeek-R1",
        "org": "deepseek-ai",
        "model_name": "DeepSeek-R1",
        "base_model": None,
        "params_b": 671.0,
        "active_params_b": 37.0,
        "context_length": 131072,
        "architecture": "DeepseekV3ForCausalLM",
        "license": "mit",
        "precision": "FP8",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 83.30, "bbh": 92.10, "math_hard": 97.30,
            "gpqa": 75.90, "musr": 64.20, "mmlu_pro": 84.40, "arena_elo": 1362.0
        }
    },
    {
        "model_id": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
        "org": "deepseek-ai",
        "model_name": "DeepSeek-R1-Distill-Qwen-32B",
        "base_model": "Qwen/Qwen2.5-32B",
        "params_b": 32.50,
        "active_params_b": 32.50,
        "context_length": 131072,
        "architecture": "Qwen2ForCausalLM",
        "license": "mit",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 85.40, "bbh": 90.50, "math_hard": 91.20,
            "gpqa": 68.50, "musr": 62.00, "mmlu_pro": 82.00, "arena_elo": 1335.0
        }
    },
    {
        "model_id": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
        "org": "deepseek-ai",
        "model_name": "DeepSeek-R1-Distill-Llama-70B",
        "base_model": "meta-llama/Llama-3.1-70B",
        "params_b": 70.60,
        "active_params_b": 70.60,
        "context_length": 131072,
        "architecture": "LlamaForCausalLM",
        "license": "llama3.1",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 86.80, "bbh": 91.00, "math_hard": 92.00,
            "gpqa": 70.20, "musr": 63.50, "mmlu_pro": 83.20, "arena_elo": 1348.0
        }
    },
    {
        "model_id": "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
        "org": "deepseek-ai",
        "model_name": "DeepSeek-R1-Distill-Qwen-14B",
        "base_model": "Qwen/Qwen2.5-14B",
        "params_b": 14.80,
        "active_params_b": 14.80,
        "context_length": 131072,
        "architecture": "Qwen2ForCausalLM",
        "license": "mit",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 82.10, "bbh": 87.20, "math_hard": 88.00,
            "gpqa": 64.00, "musr": 58.20, "mmlu_pro": 77.50, "arena_elo": 1290.0
        }
    },
    {
        "model_id": "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
        "org": "deepseek-ai",
        "model_name": "DeepSeek-R1-Distill-Qwen-7B",
        "base_model": "Qwen/Qwen2.5-7B",
        "params_b": 7.60,
        "active_params_b": 7.60,
        "context_length": 131072,
        "architecture": "Qwen2ForCausalLM",
        "license": "mit",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 78.50, "bbh": 83.00, "math_hard": 83.50,
            "gpqa": 58.20, "musr": 53.00, "mmlu_pro": 71.00, "arena_elo": 1240.0
        }
    },
    {
        "model_id": "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
        "org": "deepseek-ai",
        "model_name": "DeepSeek-R1-Distill-Llama-8B",
        "base_model": "meta-llama/Llama-3.1-8B",
        "params_b": 8.03,
        "active_params_b": 8.03,
        "context_length": 131072,
        "architecture": "LlamaForCausalLM",
        "license": "llama3.1",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 77.00, "bbh": 82.40, "math_hard": 81.20,
            "gpqa": 56.40, "musr": 52.10, "mmlu_pro": 69.50, "arena_elo": 1235.0
        }
    },
    {
        "model_id": "deepseek-ai/DeepSeek-V3",
        "org": "deepseek-ai",
        "model_name": "DeepSeek-V3",
        "base_model": None,
        "params_b": 671.0,
        "active_params_b": 37.0,
        "context_length": 131072,
        "architecture": "DeepseekV3ForCausalLM",
        "license": "mit",
        "precision": "FP8",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 84.10, "bbh": 89.20, "math_hard": 75.70,
            "gpqa": 59.10, "musr": 58.90, "mmlu_pro": 78.80, "arena_elo": 1388.0
        }
    },
    {
        "model_id": "deepseek-ai/DeepSeek-V2.5",
        "org": "deepseek-ai",
        "model_name": "DeepSeek-V2.5",
        "base_model": None,
        "params_b": 236.0,
        "active_params_b": 21.0,
        "context_length": 131072,
        "architecture": "DeepseekV2ForCausalLM",
        "license": "other",
        "precision": "BF16",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 81.50, "bbh": 83.20, "math_hard": 65.40,
            "gpqa": 49.80, "musr": 54.00, "mmlu_pro": 71.20, "arena_elo": 1272.0
        }
    },
    {
        "model_id": "deepseek-ai/DeepSeek-Coder-V2-Instruct",
        "org": "deepseek-ai",
        "model_name": "DeepSeek-Coder-V2-Instruct",
        "base_model": None,
        "params_b": 236.0,
        "active_params_b": 21.0,
        "context_length": 131072,
        "architecture": "DeepseekV2ForCausalLM",
        "license": "other",
        "precision": "BF16",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 83.00, "bbh": 84.50, "math_hard": 72.00,
            "gpqa": 52.40, "musr": 55.60, "mmlu_pro": 74.00, "arena_elo": 1290.0
        }
    },

    # --- Meta Llama 3.3, 3.2, 3.1, & 2 Models ---
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
            "ifeval": 88.60, "bbh": 86.80, "math_hard": 68.00,
            "gpqa": 51.10, "musr": 59.80, "mmlu_pro": 73.30, "arena_elo": 1320.0
        }
    },
    {
        "model_id": "meta-llama/Llama-3.3-70B-Instruct",
        "org": "meta-llama",
        "model_name": "Llama-3.3-70B-Instruct",
        "base_model": "meta-llama/Llama-3.3-70B",
        "params_b": 70.60,
        "active_params_b": 70.60,
        "context_length": 131072,
        "architecture": "LlamaForCausalLM",
        "license": "llama3.3",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 88.40, "bbh": 88.50, "math_hard": 69.20,
            "gpqa": 53.40, "musr": 59.50, "mmlu_pro": 76.80, "arena_elo": 1335.0
        }
    },
    {
        "model_id": "meta-llama/Llama-3.1-70B-Instruct",
        "org": "meta-llama",
        "model_name": "Llama-3.1-70B-Instruct",
        "base_model": "meta-llama/Llama-3.1-70B",
        "params_b": 70.60,
        "active_params_b": 70.60,
        "context_length": 131072,
        "architecture": "LlamaForCausalLM",
        "license": "llama3.1",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 84.60, "bbh": 83.10, "math_hard": 58.40,
            "gpqa": 48.30, "musr": 54.80, "mmlu_pro": 69.40, "arena_elo": 1285.0
        }
    },
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
            "ifeval": 73.10, "bbh": 68.30, "math_hard": 32.80,
            "gpqa": 32.80, "musr": 42.50, "mmlu_pro": 51.50, "arena_elo": 1188.0
        }
    },
    {
        "model_id": "meta-llama/Llama-3.2-3B-Instruct",
        "org": "meta-llama",
        "model_name": "Llama-3.2-3B-Instruct",
        "base_model": "meta-llama/Llama-3.2-3B",
        "params_b": 3.21,
        "active_params_b": 3.21,
        "context_length": 131072,
        "architecture": "LlamaForCausalLM",
        "license": "llama3.2",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 76.50, "bbh": 67.80, "math_hard": 41.20,
            "gpqa": 36.50, "musr": 42.00, "mmlu_pro": 50.40, "arena_elo": 1175.0
        }
    },
    {
        "model_id": "meta-llama/Llama-3.2-1B-Instruct",
        "org": "meta-llama",
        "model_name": "Llama-3.2-1B-Instruct",
        "base_model": "meta-llama/Llama-3.2-1B",
        "params_b": 1.23,
        "active_params_b": 1.23,
        "context_length": 131072,
        "architecture": "LlamaForCausalLM",
        "license": "llama3.2",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 66.00, "bbh": 54.00, "math_hard": 28.00,
            "gpqa": 29.50, "musr": 34.00, "mmlu_pro": 38.50, "arena_elo": 1110.0
        }
    },
    {
        "model_id": "meta-llama/Llama-2-70b-chat-hf",
        "org": "meta-llama",
        "model_name": "Llama-2-70b-chat-hf",
        "base_model": "meta-llama/Llama-2-70b",
        "params_b": 68.97,
        "active_params_b": 68.97,
        "context_length": 4096,
        "architecture": "LlamaForCausalLM",
        "license": "llama2",
        "precision": "FP16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 48.00, "bbh": 54.00, "math_hard": 12.00,
            "gpqa": 24.00, "musr": 36.00, "mmlu_pro": 38.00, "arena_elo": 1080.0
        }
    },

    # --- Alibaba Qwen 2.5 & Specialized Models ---
    {
        "model_id": "Qwen/QwQ-32B-Preview",
        "org": "Qwen",
        "model_name": "QwQ-32B-Preview",
        "base_model": "Qwen/Qwen2.5-32B",
        "params_b": 32.50,
        "active_params_b": 32.50,
        "context_length": 32768,
        "architecture": "Qwen2ForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 84.00, "bbh": 89.50, "math_hard": 91.50,
            "gpqa": 67.20, "musr": 60.50, "mmlu_pro": 80.50, "arena_elo": 1332.0
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
        "license": "other",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 84.50, "bbh": 83.20, "math_hard": 59.40,
            "gpqa": 49.00, "musr": 55.40, "mmlu_pro": 74.40, "arena_elo": 1312.0
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
            "ifeval": 81.20, "bbh": 78.50, "math_hard": 52.10,
            "gpqa": 45.00, "musr": 51.50, "mmlu_pro": 69.80, "arena_elo": 1280.0
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
            "ifeval": 77.00, "bbh": 74.10, "math_hard": 45.20,
            "gpqa": 41.20, "musr": 48.00, "mmlu_pro": 64.00, "arena_elo": 1250.0
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
            "ifeval": 72.80, "bbh": 68.50, "math_hard": 36.20,
            "gpqa": 36.00, "musr": 43.10, "mmlu_pro": 56.50, "arena_elo": 1215.0
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
        "license": "other",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 63.40, "bbh": 58.00, "math_hard": 28.50,
            "gpqa": 31.00, "musr": 38.50, "mmlu_pro": 47.20, "arena_elo": 1160.0
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
        "license": "other",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 53.00, "bbh": 46.50, "math_hard": 21.00,
            "gpqa": 27.50, "musr": 33.00, "mmlu_pro": 38.00, "arena_elo": 1110.0
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
        "license": "other",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 39.50, "bbh": 35.00, "math_hard": 14.20,
            "gpqa": 22.00, "musr": 28.00, "mmlu_pro": 29.50, "arena_elo": 1040.0
        }
    },
    {
        "model_id": "Qwen/Qwen2.5-Coder-32B-Instruct",
        "org": "Qwen",
        "model_name": "Qwen2.5-Coder-32B-Instruct",
        "base_model": "Qwen/Qwen2.5-Coder-32B",
        "params_b": 32.76,
        "active_params_b": 32.76,
        "context_length": 131072,
        "architecture": "Qwen2ForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 82.50, "bbh": 81.00, "math_hard": 56.20,
            "gpqa": 47.80, "musr": 53.00, "mmlu_pro": 71.50, "arena_elo": 1290.0
        }
    },
    {
        "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct",
        "org": "Qwen",
        "model_name": "Qwen2.5-Coder-7B-Instruct",
        "base_model": "Qwen/Qwen2.5-Coder-7B",
        "params_b": 7.61,
        "active_params_b": 7.61,
        "context_length": 131072,
        "architecture": "Qwen2ForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 74.00, "bbh": 70.80, "math_hard": 41.50,
            "gpqa": 37.20, "musr": 45.00, "mmlu_pro": 60.10, "arena_elo": 1220.0
        }
    },
    {
        "model_id": "Qwen/Qwen2.5-Math-72B-Instruct",
        "org": "Qwen",
        "model_name": "Qwen2.5-Math-72B-Instruct",
        "base_model": "Qwen/Qwen2.5-72B",
        "params_b": 72.71,
        "active_params_b": 72.71,
        "context_length": 4096,
        "architecture": "Qwen2ForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 75.20, "bbh": 88.00, "math_hard": 92.50,
            "gpqa": 64.00, "musr": 54.20, "mmlu_pro": 76.00, "arena_elo": 1285.0
        }
    },
    {
        "model_id": "Qwen/Qwen2.5-Math-7B-Instruct",
        "org": "Qwen",
        "model_name": "Qwen2.5-Math-7B-Instruct",
        "base_model": "Qwen/Qwen2.5-7B",
        "params_b": 7.61,
        "active_params_b": 7.61,
        "context_length": 4096,
        "architecture": "Qwen2ForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 66.50, "bbh": 76.50, "math_hard": 83.00,
            "gpqa": 49.20, "musr": 44.00, "mmlu_pro": 62.40, "arena_elo": 1195.0
        }
    },

    # --- Mistral AI Models ---
    {
        "model_id": "mistralai/Mistral-Large-2411",
        "org": "mistralai",
        "model_name": "Mistral-Large-2411",
        "base_model": None,
        "params_b": 123.0,
        "active_params_b": 123.0,
        "context_length": 128000,
        "architecture": "MistralForCausalLM",
        "license": "other",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 87.40, "bbh": 84.80, "math_hard": 61.20,
            "gpqa": 50.80, "musr": 56.00, "mmlu_pro": 75.20, "arena_elo": 1315.0
        }
    },
    {
        "model_id": "mistralai/Mistral-Small-24B-2501",
        "org": "mistralai",
        "model_name": "Mistral-Small-24B-2501",
        "base_model": None,
        "params_b": 24.0,
        "active_params_b": 24.0,
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
        "model_id": "mistralai/Codestral-22B-v0.1",
        "org": "mistralai",
        "model_name": "Codestral-22B-v0.1",
        "base_model": None,
        "params_b": 22.20,
        "active_params_b": 22.20,
        "context_length": 32768,
        "architecture": "MistralForCausalLM",
        "license": "mnpl-0.1",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 81.20, "bbh": 79.50, "math_hard": 58.00,
            "gpqa": 48.00, "musr": 51.00, "mmlu_pro": 69.20, "arena_elo": 1260.0
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
        "model_id": "mistralai/Mistral-Nemo-Instruct-2407",
        "org": "mistralai",
        "model_name": "Mistral-Nemo-Instruct-2407",
        "base_model": "mistralai/Mistral-Nemo-Base-2407",
        "params_b": 12.20,
        "active_params_b": 12.20,
        "context_length": 128000,
        "architecture": "MistralForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 77.80, "bbh": 74.20, "math_hard": 42.50,
            "gpqa": 41.00, "musr": 46.50, "mmlu_pro": 59.00, "arena_elo": 1220.0
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
            "ifeval": 68.20, "bbh": 65.40, "math_hard": 28.50,
            "gpqa": 32.10, "musr": 40.50, "mmlu_pro": 46.80, "arena_elo": 1178.0
        }
    },

    # --- Microsoft Phi Models ---
    {
        "model_id": "microsoft/Phi-4",
        "org": "microsoft",
        "model_name": "Phi-4",
        "base_model": None,
        "params_b": 14.0,
        "active_params_b": 14.0,
        "context_length": 16384,
        "architecture": "PhiForCausalLM",
        "license": "mit",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 81.20, "bbh": 79.50, "math_hard": 54.00,
            "gpqa": 45.80, "musr": 52.00, "mmlu_pro": 69.30, "arena_elo": 1270.0
        }
    },
    {
        "model_id": "microsoft/Phi-3.5-mini-instruct",
        "org": "microsoft",
        "model_name": "Phi-3.5-mini-instruct",
        "base_model": None,
        "params_b": 3.82,
        "active_params_b": 3.82,
        "context_length": 131072,
        "architecture": "Phi3ForCausalLM",
        "license": "mit",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 65.20, "bbh": 62.40, "math_hard": 34.00,
            "gpqa": 33.50, "musr": 41.00, "mmlu_pro": 49.50, "arena_elo": 1165.0
        }
    },

    # --- Enterprise MoE & Other Providers (Snowflake, Databricks, Yi, Falcon, Cohere, AllenAI) ---
    {
        "model_id": "snowflake/snowflake-arctic-instruct",
        "org": "snowflake",
        "model_name": "snowflake-arctic-instruct",
        "base_model": None,
        "params_b": 480.0,
        "active_params_b": 17.0,
        "context_length": 4096,
        "architecture": "ArcticForCausalLM",
        "license": "apache-2.0",
        "precision": "FP8",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 79.40, "bbh": 81.00, "math_hard": 48.20,
            "gpqa": 42.50, "musr": 48.00, "mmlu_pro": 65.50, "arena_elo": 1248.0
        }
    },
    {
        "model_id": "databricks/dbrx-instruct",
        "org": "databricks",
        "model_name": "dbrx-instruct",
        "base_model": None,
        "params_b": 132.0,
        "active_params_b": 36.0,
        "context_length": 32768,
        "architecture": "DbrxForCausalLM",
        "license": "databricks-open-model-license",
        "precision": "BF16",
        "is_moe": 1,
        "benchmarks": {
            "ifeval": 78.50, "bbh": 80.20, "math_hard": 47.00,
            "gpqa": 43.10, "musr": 49.20, "mmlu_pro": 66.80, "arena_elo": 1242.0
        }
    },
    {
        "model_id": "01-ai/Yi-1.5-34B-Chat",
        "org": "01-ai",
        "model_name": "Yi-1.5-34B-Chat",
        "base_model": "01-ai/Yi-1.5-34B",
        "params_b": 34.30,
        "active_params_b": 34.30,
        "context_length": 4096,
        "architecture": "YiForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 77.20, "bbh": 79.00, "math_hard": 48.50,
            "gpqa": 44.00, "musr": 47.50, "mmlu_pro": 64.20, "arena_elo": 1238.0
        }
    },
    {
        "model_id": "01-ai/Yi-1.5-9B-Chat",
        "org": "01-ai",
        "model_name": "Yi-1.5-9B-Chat",
        "base_model": "01-ai/Yi-1.5-9B",
        "params_b": 8.80,
        "active_params_b": 8.80,
        "context_length": 4096,
        "architecture": "YiForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 71.00, "bbh": 70.50, "math_hard": 36.00,
            "gpqa": 36.80, "musr": 41.20, "mmlu_pro": 53.50, "arena_elo": 1185.0
        }
    },
    {
        "model_id": "CohereForAI/c4ai-command-r-plus",
        "org": "CohereForAI",
        "model_name": "c4ai-command-r-plus",
        "base_model": None,
        "params_b": 104.0,
        "active_params_b": 104.0,
        "context_length": 128000,
        "architecture": "CohereForCausalLM",
        "license": "cc-by-nc-4.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 82.50, "bbh": 79.20, "math_hard": 44.10,
            "gpqa": 42.00, "musr": 49.50, "mmlu_pro": 65.00, "arena_elo": 1268.0
        }
    },
    {
        "model_id": "CohereForAI/c4ai-command-r-v01",
        "org": "CohereForAI",
        "model_name": "c4ai-command-r-v01",
        "base_model": None,
        "params_b": 35.0,
        "active_params_b": 35.0,
        "context_length": 128000,
        "architecture": "CohereForCausalLM",
        "license": "cc-by-nc-4.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 75.00, "bbh": 71.00, "math_hard": 32.50,
            "gpqa": 35.50, "musr": 43.00, "mmlu_pro": 54.00, "arena_elo": 1215.0
        }
    },
    {
        "model_id": "tiiuae/Falcon3-10B-Instruct",
        "org": "tiiuae",
        "model_name": "Falcon3-10B-Instruct",
        "base_model": "tiiuae/Falcon3-10B-Base",
        "params_b": 10.0,
        "active_params_b": 10.0,
        "context_length": 32768,
        "architecture": "FalconForCausalLM",
        "license": "tii-falcon-llm",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 73.50, "bbh": 71.80, "math_hard": 38.00,
            "gpqa": 38.20, "musr": 43.50, "mmlu_pro": 56.40, "arena_elo": 1205.0
        }
    },
    {
        "model_id": "tiiuae/Falcon3-7B-Instruct",
        "org": "tiiuae",
        "model_name": "Falcon3-7B-Instruct",
        "base_model": "tiiuae/Falcon3-7B-Base",
        "params_b": 7.0,
        "active_params_b": 7.0,
        "context_length": 32768,
        "architecture": "FalconForCausalLM",
        "license": "tii-falcon-llm",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 69.00, "bbh": 67.40, "math_hard": 32.50,
            "gpqa": 34.10, "musr": 39.80, "mmlu_pro": 51.00, "arena_elo": 1170.0
        }
    },
    {
        "model_id": "tiiuae/falcon-7b-instruct",
        "org": "tiiuae",
        "model_name": "falcon-7b-instruct",
        "base_model": "tiiuae/falcon-7b",
        "params_b": 7.22,
        "active_params_b": 7.22,
        "context_length": 2048,
        "architecture": "FalconForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 35.00, "bbh": 41.50, "math_hard": 8.50,
            "gpqa": 19.50, "musr": 28.00, "mmlu_pro": 25.00, "arena_elo": 995.0
        }
    },
    {
        "model_id": "allenai/OLMo-2-1124-13B-Instruct",
        "org": "allenai",
        "model_name": "OLMo-2-1124-13B-Instruct",
        "base_model": "allenai/OLMo-2-1124-13B",
        "params_b": 13.0,
        "active_params_b": 13.0,
        "context_length": 4096,
        "architecture": "Olmo2ForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 76.00, "bbh": 73.50, "math_hard": 40.20,
            "gpqa": 39.00, "musr": 45.20, "mmlu_pro": 57.00, "arena_elo": 1208.0
        }
    },
    {
        "model_id": "allenai/OLMo-2-1124-7B-Instruct",
        "org": "allenai",
        "model_name": "OLMo-2-1124-7B-Instruct",
        "base_model": "allenai/OLMo-2-1124-7B",
        "params_b": 7.0,
        "active_params_b": 7.0,
        "context_length": 4096,
        "architecture": "Olmo2ForCausalLM",
        "license": "apache-2.0",
        "precision": "BF16",
        "is_moe": 0,
        "benchmarks": {
            "ifeval": 71.50, "bbh": 68.00, "math_hard": 33.00,
            "gpqa": 34.50, "musr": 40.00, "mmlu_pro": 51.80, "arena_elo": 1172.0
        }
    },

    # --- Benchmark Contamination & Overfit Trap Models ---
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
            "ifeval": 38.00, "bbh": 78.50, "math_hard": 12.40,
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
            "ifeval": 35.20, "bbh": 82.00, "math_hard": 14.10,
            "gpqa": 28.00, "musr": 38.00, "mmlu_pro": 92.10, "arena_elo": 1045.0
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
                "seed_sha_" + item["model_name"].lower().replace(".", "_").replace("/", "_"),
                "2026-11-04T00:00:00Z",
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
    cursor.execute("INSERT INTO meta_info (key, value) VALUES (?, ?)", ("built_at", "November 2026"))

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

    print(f"Generating deterministic seed database with {len(MODELS_SEED_DATA)} models at {target_db}...")
    canonical_sha = build_seed_database(target_db, schema_file)
    checksum_file.write_text(canonical_sha + "\n", encoding="utf-8")
    print(f"Canonical SHA-256: {canonical_sha}")
    print(f"Wrote checksum to {checksum_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
