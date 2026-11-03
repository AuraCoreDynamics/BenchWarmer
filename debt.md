# BenchWarmer Technical Debt & Reflection Audit (`debt.md`)

> **Generated**: Phase N+1 Reflection Gate & Debt Harvest  
> **Status**: Verified & Hardened  
> **Methodology**: BLACK Framework v2.2

---

## 1. Executive Summary

| Metric | Target | Actual | Status |
| :--- | :--- | :--- | :--- |
| **Runtime Dependencies** | `0` (`dependencies = []`) | `0` (Pure Python stdlib) | **PASSED** |
| **Test Pass Rate** | `1.0` (100%) | `1.0` (54/54 tests passed) | **PASSED** |
| **Unit Test Count** | `≥ 20` | `44` tests | **PASSED** |
| **Adversarial QA Suite** | `≥ 8` | `10` tests (Rule 11, 12, 13, 15, 18) | **PASSED** |
| **BLACK Pre-Flight Audit** | `0` violations | `0` violations (`BLACK GATE PASSED.`) | **PASSED** |
| **Banned Tokens in `src/`** | `0` (`localhost`, `TODO`, `FIXME`) | `0` across entire codebase | **PASSED** |
| **Floating-Point Precision** | `≥ 6` decimal places | Full 64-bit IEEE 754 precision preserved | **PASSED** |
| **Standalone .pyz Executable** | Valid portable artifact | `dist/benchwarmer.pyz` (42.8 KB) verified | **PASSED** |

---

## 2. AST Method Completeness & Anti-Green-Washing Audit

All modules in `src/benchwarmer/` and `scripts/` were scanned via `ast.walk`:
1. **Zero Unimplemented Stubs**: All Phase 0 `NotImplementedError` stubs were fully replaced with production implementations.
2. **Rule 18 Precision Invariance**: Zero calls to `round()` detected in `src/benchwarmer/api.py` or `src/benchwarmer/db/connector.py`. Float formatting is strictly confined to presentation layers (`cli.py` tables and `gui.py` display strings).
3. **Rule 12 Anti-Masking Sensitivity**: Filter parameters (`min_params`, `max_params`, `max_vram_gb`, `quant`, `strict_benchmarks`, `limit`) independently mutate query output sets as verified by adversarial test 3.
4. **Rule 13 SQL Predicate Completeness**: SQL query predicates filter parameter bounds in the `WHERE` clause prior to `LIMIT` application, preventing truncation bias.
5. **Rule 15 Post-Hydration Invalidation**: `reload()` flushes resolution caches, model record caches, and closes backing SQLite connections.
6. **Rule 11 Cross-Boundary Parity**: 100% key name alignment between `src/benchwarmer/mcp_schema.json`, `src/benchwarmer/contracts.py`, and `src/benchwarmer/gui.py`.

---

## 3. Residual Architectural Boundaries & Future Enhancements

While BenchWarmer strictly satisfies all Phase 0–N functional contracts, the following non-blocking technical debt items and future architectural opportunities are cataloged for upcoming releases:

### 3.1 Quantization Perplexity Delta Modeling
- **Current Behavior**: Estimated VRAM GB is calculated from parameter counts and quantization bit-widths with a 15% KV-cache/activation overhead multiplier (`(params_b * (bits / 8.0)) * 1.15`).
- **Future Enhancement**: Incorporate empirical quantization perplexity degradation tables (e.g., Q4_K_M vs FP16 perplexity shifts on Wikitext-2 / C4) into `score_candidates()` so routers can calculate effective quality degradation per GB of VRAM saved.

### 3.2 Dynamic Upstream Diff Scraping
- **Current Behavior**: `scripts/build_db.py` relies on `huggingface_hub.snapshot_download` and parquet parsing or local snapshot directories.
- **Future Enhancement**: Add a lightweight streaming chunk parser for LMSYS leaderboard parquet feeds to ingest live arena leaderboard delta updates without downloading complete snapshot blobs.

### 3.3 Speculative Decoding Latency Multipliers
- **Current Behavior**: `ParetoPoint` tracks raw capability score against VRAM footprint (`efficiency_ratio = score / estimated_vram_gb`).
- **Future Enhancement**: Support draft/target model pairing heuristics (e.g. `Llama-3.1-8B` serving as speculative draft for `Llama-3.1-70B`) by computing vocabulary and tokenizer compatibility matrices.

---

## 4. Verification Artifacts & Gate Hashes

- **Canonical Checksum File**: `src/benchwarmer/data/checksum.sha256`
- **Canonical Dataset SHA-256**: `f1c3b84487c6c4b03c7a7a2e9276b066a3dbd93c2c5ec9095ff57ca18fb7cb5b`
- **Zipapp Single-File Artifact**: `dist/benchwarmer.pyz`
- **Scoring Manifest**: `scoring.json` (`methodology_version: 2.2`, `status: VERIFIED`)
