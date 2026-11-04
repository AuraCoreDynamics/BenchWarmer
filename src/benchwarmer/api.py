"""Core BenchWarmer Oracle API providing model search, comparison, ranking, and audit."""

import json
import math
import re
from typing import Dict, List, Optional, Set, Tuple

from benchwarmer.contracts import (
    QUANT_BITS_MAP,
    ModelSummary,
    ModelRecord,
    MetricDelta,
    ModelComparisonResult,
    CandidateScore,
    ParetoPoint,
    ContaminationReport,
)
from benchwarmer.db.connector import SQLiteConnector


def _sanitize_fts_query(query: str) -> str:
    """Sanitize user query for SQLite FTS5 matching."""
    # Extract alphanumeric and underscore tokens
    tokens = re.findall(r"[A-Za-z0-9_]+", query)
    if not tokens:
        return '""'
    # Match tokens with prefix matching
    sanitized = " ".join(f'"{tok}"*' for tok in tokens)
    return sanitized


class BenchWarmer:
    """Offline Zero-Dependency LLM Benchmark Oracle."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path
        self._connector = SQLiteConnector(db_path)
        self._resolution_cache: Dict[str, Optional[str]] = {}
        self._model_cache: Dict[str, ModelRecord] = {}

    def reload(self) -> None:
        """Atomically invalidate resolution and model caches (Rule 15)."""
        self._resolution_cache.clear()
        self._model_cache.clear()
        self._connector.close()
        self._connector = SQLiteConnector(self._db_path)

    def close(self) -> None:
        """Close backing database connection."""
        self._connector.close()

    def __enter__(self) -> "BenchWarmer":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def get_metadata(self) -> Dict[str, str]:
        """Return database metadata key-value pairs."""
        conn = self._connector.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM meta_info")
        return {row["key"]: row["value"] for row in cursor.fetchall()}

    def list_benchmarks(self) -> List[str]:
        """Return list of distinct benchmark names available in the store."""
        conn = self._connector.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT benchmark FROM benchmark_scores ORDER BY benchmark ASC")
        return [row["benchmark"] for row in cursor.fetchall()]

    def resolve_model_id(self, query: str) -> Optional[str]:
        """4-stage cascade resolution: exact -> case-insensitive -> org-stripped -> FTS5 rank."""
        if not query or not query.strip():
            return None

        clean_query = query.strip()
        if clean_query in self._resolution_cache:
            return self._resolution_cache[clean_query]

        conn = self._connector.get_connection()
        cursor = conn.cursor()

        # Stage 1: Exact match
        cursor.execute("SELECT model_id FROM models WHERE model_id = ? LIMIT 1", (clean_query,))
        row = cursor.fetchone()
        if row:
            resolved = row["model_id"]
            self._resolution_cache[clean_query] = resolved
            return resolved

        # Stage 2: Case-insensitive match on model_id
        cursor.execute("SELECT model_id FROM models WHERE LOWER(model_id) = LOWER(?) LIMIT 1", (clean_query,))
        row = cursor.fetchone()
        if row:
            resolved = row["model_id"]
            self._resolution_cache[clean_query] = resolved
            return resolved

        # Stage 3: Match on model_name or stripped org
        stripped_query = clean_query.split("/")[-1]
        cursor.execute(
            "SELECT model_id FROM models WHERE LOWER(model_name) = LOWER(?) OR LOWER(model_name) = LOWER(?) LIMIT 1",
            (clean_query, stripped_query),
        )
        row = cursor.fetchone()
        if row:
            resolved = row["model_id"]
            self._resolution_cache[clean_query] = resolved
            return resolved

        # Stage 4: FTS5 rank query
        sanitized = _sanitize_fts_query(clean_query)
        try:
            cursor.execute(
                "SELECT model_id FROM models_fts WHERE models_fts MATCH ? ORDER BY rank LIMIT 1",
                (sanitized,),
            )
            row = cursor.fetchone()
            if row:
                resolved = row["model_id"]
                self._resolution_cache[clean_query] = resolved
                return resolved
        except Exception:
            pass

        self._resolution_cache[clean_query] = None
        return None

    def get_model(self, model_id: str) -> Optional[ModelRecord]:
        """Fetch complete ModelRecord including estimated VRAM across quantizations."""
        resolved = self.resolve_model_id(model_id)
        if not resolved:
            return None

        if resolved in self._model_cache:
            return self._model_cache[resolved]

        conn = self._connector.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT model_id, org, model_name, base_model, params_b, active_params_b,
                   context_length, architecture, license, precision, is_moe
            FROM models WHERE model_id = ?
            """,
            (resolved,),
        )
        m_row = cursor.fetchone()
        if not m_row:
            return None

        cursor.execute(
            "SELECT benchmark, score, raw_score FROM benchmark_scores WHERE model_id = ?",
            (resolved,),
        )
        scores: Dict[str, float] = {}
        raw_scores: Dict[str, float] = {}
        for s_row in cursor.fetchall():
            bench = s_row["benchmark"]
            scores[bench] = float(s_row["score"])
            raw_scores[bench] = float(s_row["raw_score"])

        params_b = float(m_row["params_b"]) if m_row["params_b"] is not None else None
        active_params_b = float(m_row["active_params_b"]) if m_row["active_params_b"] is not None else params_b

        # Calculate estimated VRAM GB across all quantization types (Rule 18: unrounded)
        # Formula: (params_b * (bits / 8.0)) * 1.15
        estimated_vram_gb: Dict[str, float] = {}
        for quant_key, bits in QUANT_BITS_MAP.items():
            if params_b is not None:
                calc_vram = (params_b * (bits / 8.0)) * 1.15
                estimated_vram_gb[quant_key] = calc_vram
            else:
                estimated_vram_gb[quant_key] = 0.0

        record = ModelRecord(
            model_id=m_row["model_id"],
            org=m_row["org"],
            model_name=m_row["model_name"],
            base_model=m_row["base_model"],
            params_b=params_b,
            active_params_b=active_params_b,
            context_length=m_row["context_length"],
            architecture=m_row["architecture"],
            license=m_row["license"],
            precision=m_row["precision"],
            is_moe=bool(m_row["is_moe"]),
            scores=scores,
            raw_scores=raw_scores,
            estimated_vram_gb=estimated_vram_gb,
        )
        self._model_cache[resolved] = record
        return record

    def get_metrics_batch(self, model_ids: List[str]) -> Dict[str, Optional[ModelRecord]]:
        """Batch retrieve ModelRecords for candidate model IDs."""
        return {mid: self.get_model(mid) for mid in model_ids}

    def search(
        self,
        query: str,
        limit: int = 10,
        min_params: Optional[float] = None,
        max_params: Optional[float] = None,
    ) -> List[ModelSummary]:
        """Search models by full text query with parameter range constraints."""
        conn = self._connector.get_connection()
        cursor = conn.cursor()

        where_clauses: List[str] = []
        params: List[object] = []

        # Parameter boundary filters applied BEFORE limit (Rule 12 & Rule 13)
        if min_params is not None:
            where_clauses.append("m.params_b >= ?")
            params.append(min_params)
        if max_params is not None:
            where_clauses.append("m.params_b <= ?")
            params.append(max_params)

        clean_query = query.strip() if query else ""
        if clean_query and clean_query != "*":
            sanitized = _sanitize_fts_query(clean_query)
            where_clauses.append("m.model_id IN (SELECT model_id FROM models_fts WHERE models_fts MATCH ?)")
            params.append(sanitized)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        sql = f"""
            SELECT m.model_id, m.org, m.params_b, m.architecture,
                   v.hf_v2_avg, v.arena_elo_raw
            FROM models m
            LEFT JOIN v_leaderboard_summary v ON m.model_id = v.model_id
            {where_sql}
            ORDER BY v.hf_v2_avg DESC NULLS LAST
            LIMIT ?
        """
        params.append(limit)

        cursor.execute(sql, tuple(params))
        results: List[ModelSummary] = []
        for row in cursor.fetchall():
            results.append(
                ModelSummary(
                    model_id=row["model_id"],
                    org=row["org"],
                    params_b=float(row["params_b"]) if row["params_b"] is not None else None,
                    architecture=row["architecture"],
                    hf_v2_avg=float(row["hf_v2_avg"]) if row["hf_v2_avg"] is not None else None,
                    arena_elo_raw=float(row["arena_elo_raw"]) if row["arena_elo_raw"] is not None else None,
                )
            )
        return results

    def rank(
        self,
        benchmark: str = "hf_v2_avg",
        limit: int = 10,
        min_params: Optional[float] = None,
        max_params: Optional[float] = None,
        max_vram_gb: Optional[float] = None,
        quant: str = "bf16",
    ) -> List[ModelSummary]:
        """Rank models by specified metric subject to parameter bounds and VRAM constraints."""
        conn = self._connector.get_connection()
        cursor = conn.cursor()

        where_clauses: List[str] = []
        params: List[object] = []

        # Parameter filters (Rule 12 & Rule 13)
        if min_params is not None:
            where_clauses.append("m.params_b >= ?")
            params.append(min_params)
        if max_params is not None:
            where_clauses.append("m.params_b <= ?")
            params.append(max_params)

        # Hardware VRAM constraint (Rule 12 & Rule 13)
        if max_vram_gb is not None:
            bits = QUANT_BITS_MAP.get(quant.lower(), 16.0)
            # vram_gb = (params_b * (bits / 8.0)) * 1.15 <= max_vram_gb
            # params_b <= max_vram_gb / ((bits / 8.0) * 1.15)
            max_allowed_params = max_vram_gb / ((bits / 8.0) * 1.15)
            where_clauses.append("m.params_b <= ?")
            params.append(max_allowed_params)

        # Order column
        valid_summary_cols = {
            "ifeval", "bbh", "math_hard", "gpqa", "musr", "mmlu_pro",
            "arena_elo_raw", "arena_elo_norm", "hf_v2_avg"
        }
        target_bench = benchmark.lower()
        if target_bench == "arena_elo":
            order_col = "v.arena_elo_raw"
        elif target_bench in valid_summary_cols:
            order_col = f"v.{target_bench}"
        else:
            order_col = "v.hf_v2_avg"

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        sql = f"""
            SELECT m.model_id, m.org, m.params_b, m.architecture,
                   v.hf_v2_avg, v.arena_elo_raw
            FROM models m
            LEFT JOIN v_leaderboard_summary v ON m.model_id = v.model_id
            {where_sql}
            ORDER BY {order_col} DESC NULLS LAST
            LIMIT ?
        """
        params.append(limit)

        cursor.execute(sql, tuple(params))
        results: List[ModelSummary] = []
        for row in cursor.fetchall():
            results.append(
                ModelSummary(
                    model_id=row["model_id"],
                    org=row["org"],
                    params_b=float(row["params_b"]) if row["params_b"] is not None else None,
                    architecture=row["architecture"],
                    hf_v2_avg=float(row["hf_v2_avg"]) if row["hf_v2_avg"] is not None else None,
                    arena_elo_raw=float(row["arena_elo_raw"]) if row["arena_elo_raw"] is not None else None,
                )
            )
        return results

    def compare(self, model_a: str, model_b: str) -> ModelComparisonResult:
        """Side-by-side comparative analysis of two models with exact unrounded deltas."""
        rec_a = self.get_model(model_a)
        if not rec_a:
            raise ValueError(f"Model A not found: {model_a}")
        rec_b = self.get_model(model_b)
        if not rec_b:
            raise ValueError(f"Model B not found: {model_b}")

        all_benchmarks: Set[str] = set(rec_a.scores.keys()) | set(rec_b.scores.keys())
        deltas: Dict[str, MetricDelta] = {}
        wins_a = 0
        wins_b = 0
        ties = 0
        shared_abs_deltas: List[float] = []

        for bench in sorted(all_benchmarks):
            score_a = rec_a.scores.get(bench)
            score_b = rec_b.scores.get(bench)

            if score_a is not None and score_b is not None:
                # Rule 18: unrounded exact float delta
                abs_delta = score_a - score_b
                pct_delta = ((score_a - score_b) / score_b) * 100.0 if score_b != 0.0 else None
                shared_abs_deltas.append(abs_delta)

                if score_a > score_b:
                    winner = rec_a.model_id
                    wins_a += 1
                elif score_b > score_a:
                    winner = rec_b.model_id
                    wins_b += 1
                else:
                    winner = "tie"
                    ties += 1
            elif score_a is not None:
                abs_delta = None
                pct_delta = None
                winner = rec_a.model_id
                wins_a += 1
            elif score_b is not None:
                abs_delta = None
                pct_delta = None
                winner = rec_b.model_id
                wins_b += 1
            else:
                abs_delta = None
                pct_delta = None
                winner = "n/a"

            deltas[bench] = MetricDelta(
                benchmark=bench,
                score_a=score_a,
                score_b=score_b,
                abs_delta=abs_delta,
                pct_delta=pct_delta,
                winner=winner,
            )

        composite_delta = (
            sum(shared_abs_deltas) / float(len(shared_abs_deltas)) if shared_abs_deltas else 0.0
        )

        return ModelComparisonResult(
            model_a=rec_a,
            model_b=rec_b,
            deltas=deltas,
            wins_a=wins_a,
            wins_b=wins_b,
            ties=ties,
            composite_delta=composite_delta,
        )

    def score_candidates(
        self,
        candidates: List[str],
        weights: Dict[str, float],
        strict_benchmarks: bool = False,
    ) -> List[CandidateScore]:
        """Score candidate models against weighted benchmark preferences."""
        if not weights:
            raise ValueError("weights dictionary cannot be empty")

        total_weight = sum(weights.values())
        if total_weight <= 0.0:
            raise ValueError("sum of weights must be positive")

        for k, v in weights.items():
            if v < 0.0:
                raise ValueError(f"Negative weight for '{k}': {v}")

        norm_weights = {k: float(v) / total_weight for k, v in weights.items()}
        results: List[CandidateScore] = []

        for candidate_query in candidates:
            rec = self.get_model(candidate_query)
            if not rec:
                results.append(
                    CandidateScore(
                        requested_id=candidate_query,
                        matched_model_id=None,
                        composite_score=0.0,
                        matched_metrics={},
                        missing_benchmarks=list(weights.keys()),
                        params_b=None,
                    )
                )
                continue

            matched_metrics: Dict[str, float] = {}
            missing_benchmarks: List[str] = []

            for bench, weight in norm_weights.items():
                if bench in rec.scores:
                    matched_metrics[bench] = rec.scores[bench]
                else:
                    missing_benchmarks.append(bench)

            if not matched_metrics:
                composite_score = 0.0
            elif strict_benchmarks:
                # Missing benchmarks receive zero score without weight re-normalization
                composite_score = sum(norm_weights[b] * matched_metrics[b] for b in matched_metrics)
            else:
                # Re-normalize weights over available metrics
                avail_weight_sum = sum(norm_weights[b] for b in matched_metrics)
                if avail_weight_sum > 0.0:
                    composite_score = sum(
                        (norm_weights[b] / avail_weight_sum) * matched_metrics[b]
                        for b in matched_metrics
                    )
                else:
                    composite_score = 0.0

            results.append(
                CandidateScore(
                    requested_id=candidate_query,
                    matched_model_id=rec.model_id,
                    composite_score=composite_score,
                    matched_metrics=matched_metrics,
                    missing_benchmarks=missing_benchmarks,
                    params_b=rec.params_b,
                )
            )

        results.sort(key=lambda cs: cs.composite_score, reverse=True)
        return results

    def pareto_frontier(
        self,
        metric: str = "hf_v2_avg",
        max_vram_gb: Optional[float] = None,
        quant: str = "bf16",
    ) -> List[ParetoPoint]:
        """Compute the Pareto-optimal frontier of capability score vs VRAM footprint."""
        bits = QUANT_BITS_MAP.get(quant.lower(), 16.0)

        # Retrieve all models with summary view
        conn = self._connector.get_connection()
        cursor = conn.cursor()

        valid_summary_cols = {
            "ifeval", "bbh", "math_hard", "gpqa", "musr", "mmlu_pro",
            "arena_elo_raw", "arena_elo_norm", "hf_v2_avg"
        }
        metric_col = metric.lower() if metric.lower() in valid_summary_cols else "hf_v2_avg"

        cursor.execute(
            f"""
            SELECT m.model_id, m.params_b, v.{metric_col} AS score
            FROM models m
            JOIN v_leaderboard_summary v ON m.model_id = v.model_id
            WHERE m.params_b IS NOT NULL AND v.{metric_col} IS NOT NULL
            """
        )

        candidates: List[Tuple[str, float, float, float]] = []
        for row in cursor.fetchall():
            mid = row["model_id"]
            params_b = float(row["params_b"])
            score = float(row["score"])
            # Rule 18: unrounded exact float VRAM calculation
            vram_gb = (params_b * (bits / 8.0)) * 1.15

            if max_vram_gb is not None and vram_gb > max_vram_gb:
                continue

            candidates.append((mid, params_b, vram_gb, score))

        # Sort candidate models by: vram_gb ASC, score DESC, params_b ASC
        candidates.sort(key=lambda item: (item[2], -item[3], item[1]))

        frontier: List[ParetoPoint] = []
        max_score_so_far = -1.0

        for mid, params_b, vram_gb, score in candidates:
            if score > max_score_so_far:
                efficiency_ratio = score / vram_gb if vram_gb > 0.0 else 0.0
                frontier.append(
                    ParetoPoint(
                        model_id=mid,
                        params_b=params_b,
                        estimated_vram_gb=vram_gb,
                        quant=quant.lower(),
                        metric=metric,
                        score=score,
                        efficiency_ratio=efficiency_ratio,
                    )
                )
                max_score_so_far = score

        return frontier

    def detect_anomalies(self, model_id: str) -> ContaminationReport:
        """Detect benchmark contamination, Goodhart overfit smells, and reasoning cliffs."""
        rec = self.get_model(model_id)
        if not rec:
            raise ValueError(f"Model not found: {model_id}")

        conn = self._connector.get_connection()
        cursor = conn.cursor()

        # Parameter peer group (+/- 30% of params_b)
        params_b = rec.params_b
        if params_b is not None:
            min_p = params_b * 0.70
            max_p = params_b * 1.30
            cursor.execute(
                "SELECT model_id FROM models WHERE params_b >= ? AND params_b <= ?",
                (min_p, max_p),
            )
        else:
            cursor.execute("SELECT model_id FROM models")

        peer_ids = [row["model_id"] for row in cursor.fetchall()]
        if rec.model_id not in peer_ids:
            peer_ids.append(rec.model_id)

        # Collect scores across peer group for z-score calculations
        benchmarks_to_check = ["ifeval", "bbh", "math_hard", "gpqa", "musr", "mmlu_pro"]
        peer_scores: Dict[str, List[float]] = {b: [] for b in benchmarks_to_check}

        for pid in peer_ids:
            p_rec = self.get_model(pid)
            if p_rec:
                for b in benchmarks_to_check:
                    if b in p_rec.scores:
                        peer_scores[b].append(p_rec.scores[b])

        # Compute model's z-score across benchmarks within peer group
        z_scores: List[float] = []
        for b in benchmarks_to_check:
            if b in rec.scores and len(peer_scores[b]) > 1:
                vals = peer_scores[b]
                mean_val = sum(vals) / float(len(vals))
                variance = sum((x - mean_val) ** 2 for x in vals) / float(len(vals))
                std_val = math.sqrt(variance)
                if std_val > 1e-6:
                    z = (rec.scores[b] - mean_val) / std_val
                    z_scores.append(z)

        # Standard deviation across benchmark z-scores
        if len(z_scores) > 1:
            z_mean = sum(z_scores) / float(len(z_scores))
            z_var = sum((z - z_mean) ** 2 for z in z_scores) / float(len(z_scores))
            z_score_spread = math.sqrt(z_var)
        else:
            z_score_spread = 0.0

        # Discrepancy metrics
        ifeval_score = rec.scores.get("ifeval")
        mmlu_score = rec.scores.get("mmlu_pro")
        bbh_score = rec.scores.get("bbh")
        math_score = rec.scores.get("math_hard")

        ifeval_vs_knowledge_gap = (
            (mmlu_score - ifeval_score) if (mmlu_score is not None and ifeval_score is not None) else None
        )
        reasoning_cliff = (
            (bbh_score - math_score) if (bbh_score is not None and math_score is not None) else None
        )

        flags: List[str] = []
        anomaly_points = 0.0

        if ifeval_vs_knowledge_gap is not None and ifeval_vs_knowledge_gap > 30.0:
            flags.append(
                f"Severe IFEval divergence: mmlu_pro exceeds ifeval by {ifeval_vs_knowledge_gap:.2f}"
            )
            anomaly_points += min(50.0, ifeval_vs_knowledge_gap * 1.0)

        if reasoning_cliff is not None and reasoning_cliff > 40.0:
            flags.append(
                f"Reasoning cliff detected: bbh vs math_hard gap is {reasoning_cliff:.2f}"
            )
            anomaly_points += min(35.0, (reasoning_cliff - 30.0) * 1.5)

        if z_score_spread > 1.5:
            flags.append(
                f"High cross-benchmark z-score variance ({z_score_spread:.2f}) across parameter peers"
            )
            anomaly_points += min(30.0, z_score_spread * 12.0)

        anomaly_score = min(100.0, max(0.0, anomaly_points))

        if anomaly_score >= 60.0:
            status = "HIGH_CONTAMINATION_RISK"
        elif anomaly_score >= 35.0:
            status = "SUSPICIOUS"
        else:
            status = "CLEAN"

        return ContaminationReport(
            model_id=rec.model_id,
            params_b=rec.params_b,
            anomaly_score=anomaly_score,
            status=status,
            flags=flags,
            z_score_spread=z_score_spread,
            ifeval_vs_knowledge_gap=ifeval_vs_knowledge_gap,
        )

    def audit_all(self) -> List[Dict[str, Any]]:
        """Audit all models in the database for contamination, anomalies, and Goodhart overfit."""
        conn = self._connector.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT model_id FROM models ORDER BY model_id ASC")
        all_ids = [row["model_id"] for row in cursor.fetchall()]

        reports: List[Dict[str, Any]] = []
        for mid in all_ids:
            try:
                rep = self.detect_anomalies(mid)
                reports.append(rep.to_dict())
            except Exception:
                pass

        reports.sort(key=lambda r: r["anomaly_score"], reverse=True)
        return reports

    def compare_multiple(self, model_ids: List[str]) -> Dict[str, Any]:
        """Multi-model side-by-side comparative analysis with per-benchmark rankings and deltas."""
        if not model_ids:
            return {
                "models": [],
                "benchmarks": [],
                "scores": {},
                "raw_scores": {},
                "best_in_class": {},
                "rankings": {},
                "summary": {},
            }

        resolved_records: List[ModelRecord] = []
        for mid in model_ids:
            rec = self.get_model(mid)
            if rec:
                resolved_records.append(rec)

        if not resolved_records:
            return {
                "models": [],
                "benchmarks": [],
                "scores": {},
                "raw_scores": {},
                "best_in_class": {},
                "rankings": {},
                "summary": {},
            }

        hf_keys = ["ifeval", "bbh", "math_hard", "gpqa", "musr", "mmlu_pro"]
        for r in resolved_records:
            hf_vals = [r.scores[k] for k in hf_keys if k in r.scores]
            if hf_vals and "hf_v2_avg" not in r.scores:
                r.scores["hf_v2_avg"] = sum(hf_vals) / float(len(hf_vals))
                r.raw_scores["hf_v2_avg"] = r.scores["hf_v2_avg"]

        all_benchmarks: Set[str] = set()
        for r in resolved_records:
            all_benchmarks.update(r.scores.keys())

        pref_order = ["hf_v2_avg", "arena_elo", "math_hard", "gpqa", "mmlu_pro", "bbh", "ifeval", "musr"]
        benchmarks_sorted = [b for b in pref_order if b in all_benchmarks] + [
            b for b in sorted(all_benchmarks) if b not in pref_order
        ]

        scores_by_bench: Dict[str, Dict[str, float]] = {b: {} for b in benchmarks_sorted}
        raw_scores_by_bench: Dict[str, Dict[str, float]] = {b: {} for b in benchmarks_sorted}
        best_in_class: Dict[str, Dict[str, Any]] = {}
        rankings_by_bench: Dict[str, List[Dict[str, Any]]] = {}

        wins_count: Dict[str, int] = {r.model_id: 0 for r in resolved_records}
        score_sums: Dict[str, float] = {r.model_id: 0.0 for r in resolved_records}
        score_counts: Dict[str, int] = {r.model_id: 0 for r in resolved_records}

        for bench in benchmarks_sorted:
            bench_scores: List[Tuple[str, float]] = []
            for r in resolved_records:
                if bench in r.scores:
                    s = r.scores[bench]
                    bench_scores.append((r.model_id, s))
                    scores_by_bench[bench][r.model_id] = s
                    score_sums[r.model_id] += s
                    score_counts[r.model_id] += 1
                if bench in r.raw_scores:
                    raw_scores_by_bench[bench][r.model_id] = r.raw_scores[bench]

            bench_scores.sort(key=lambda x: x[1], reverse=True)
            if bench_scores:
                top_mid, top_val = bench_scores[0]
                best_in_class[bench] = {"model_id": top_mid, "score": top_val}
                top_winners = [mid for mid, val in bench_scores if val == top_val]
                for w in top_winners:
                    wins_count[w] += 1

            rankings_by_bench[bench] = [
                {"rank": idx + 1, "model_id": mid, "score": val}
                for idx, (mid, val) in enumerate(bench_scores)
            ]

        summary: Dict[str, Dict[str, Any]] = {}
        for r in resolved_records:
            mid = r.model_id
            cnt = score_counts[mid]
            avg_score = (score_sums[mid] / float(cnt)) if cnt > 0 else 0.0
            summary[mid] = {
                "model_id": mid,
                "model_name": r.model_name,
                "org": r.org,
                "params_b": r.params_b,
                "architecture": r.architecture,
                "vram_bf16": r.estimated_vram_gb.get("bf16", 0.0),
                "wins": wins_count[mid],
                "avg_score": avg_score,
                "context_length": r.context_length,
                "license": r.license,
            }

        return {
            "models": [r.to_dict() for r in resolved_records],
            "benchmarks": benchmarks_sorted,
            "scores": scores_by_bench,
            "raw_scores": raw_scores_by_bench,
            "best_in_class": best_in_class,
            "rankings": rankings_by_bench,
            "summary": summary,
        }

    def get_all_models_detailed(self) -> List[Dict[str, Any]]:
        """Retrieve all models with metadata, leaderboard summary, and precomputed VRAM."""
        conn = self._connector.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                m.model_id, m.org, m.model_name, m.base_model, m.params_b, m.active_params_b,
                m.context_length, m.architecture, m.license, m.precision, m.is_moe,
                v.ifeval, v.bbh, v.math_hard, v.gpqa, v.musr, v.mmlu_pro,
                v.arena_elo_raw, v.arena_elo_norm, v.hf_v2_avg
            FROM models m
            LEFT JOIN v_leaderboard_summary v ON m.model_id = v.model_id
            ORDER BY v.hf_v2_avg DESC NULLS LAST
            """
        )
        rows = cursor.fetchall()
        models_list: List[Dict[str, Any]] = []

        for row in rows:
            params_b = float(row["params_b"]) if row["params_b"] is not None else None
            active_params_b = (
                float(row["active_params_b"]) if row["active_params_b"] is not None else params_b
            )

            vram_map: Dict[str, float] = {}
            for quant_key, bits in QUANT_BITS_MAP.items():
                if params_b is not None:
                    vram_map[quant_key] = (params_b * (bits / 8.0)) * 1.15
                else:
                    vram_map[quant_key] = 0.0

            scores: Dict[str, Optional[float]] = {
                "ifeval": float(row["ifeval"]) if row["ifeval"] is not None else None,
                "bbh": float(row["bbh"]) if row["bbh"] is not None else None,
                "math_hard": float(row["math_hard"]) if row["math_hard"] is not None else None,
                "gpqa": float(row["gpqa"]) if row["gpqa"] is not None else None,
                "musr": float(row["musr"]) if row["musr"] is not None else None,
                "mmlu_pro": float(row["mmlu_pro"]) if row["mmlu_pro"] is not None else None,
                "arena_elo": float(row["arena_elo_norm"]) if row["arena_elo_norm"] is not None else None,
            }

            models_list.append(
                {
                    "model_id": row["model_id"],
                    "org": row["org"],
                    "model_name": row["model_name"],
                    "base_model": row["base_model"],
                    "params_b": params_b,
                    "active_params_b": active_params_b,
                    "context_length": row["context_length"],
                    "architecture": row["architecture"],
                    "license": row["license"],
                    "precision": row["precision"],
                    "is_moe": bool(row["is_moe"]),
                    "estimated_vram_gb": vram_map,
                    "scores": scores,
                    "raw_scores": {
                        "arena_elo": float(row["arena_elo_raw"]) if row["arena_elo_raw"] is not None else None,
                    },
                    "hf_v2_avg": float(row["hf_v2_avg"]) if row["hf_v2_avg"] is not None else None,
                    "arena_elo_raw": float(row["arena_elo_raw"]) if row["arena_elo_raw"] is not None else None,
                }
            )

        return models_list
