"""Core BenchWarmer Oracle API stub."""

from typing import Dict, List, Optional
from benchwarmer.contracts import (
    ModelSummary,
    ModelRecord,
    ModelComparisonResult,
    CandidateScore,
    ParetoPoint,
    ContaminationReport,
)


class BenchWarmer:
    """Offline Zero-Dependency LLM Benchmark Oracle."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        raise NotImplementedError("BenchWarmer.__init__ not implemented in Phase 0")

    def get_metadata(self) -> Dict[str, str]:
        raise NotImplementedError("BenchWarmer.get_metadata not implemented in Phase 0")

    def list_benchmarks(self) -> List[str]:
        raise NotImplementedError("BenchWarmer.list_benchmarks not implemented in Phase 0")

    def resolve_model_id(self, query: str) -> Optional[str]:
        raise NotImplementedError("BenchWarmer.resolve_model_id not implemented in Phase 0")

    def get_model(self, model_id: str) -> Optional[ModelRecord]:
        raise NotImplementedError("BenchWarmer.get_model not implemented in Phase 0")

    def get_metrics_batch(self, model_ids: List[str]) -> Dict[str, Optional[ModelRecord]]:
        raise NotImplementedError("BenchWarmer.get_metrics_batch not implemented in Phase 0")

    def search(
        self,
        query: str,
        limit: int = 10,
        min_params: Optional[float] = None,
        max_params: Optional[float] = None,
    ) -> List[ModelSummary]:
        raise NotImplementedError("BenchWarmer.search not implemented in Phase 0")

    def rank(
        self,
        benchmark: str = "hf_v2_avg",
        limit: int = 10,
        min_params: Optional[float] = None,
        max_params: Optional[float] = None,
        max_vram_gb: Optional[float] = None,
        quant: str = "bf16",
    ) -> List[ModelSummary]:
        raise NotImplementedError("BenchWarmer.rank not implemented in Phase 0")

    def compare(self, model_a: str, model_b: str) -> ModelComparisonResult:
        raise NotImplementedError("BenchWarmer.compare not implemented in Phase 0")

    def score_candidates(
        self,
        candidates: List[str],
        weights: Dict[str, float],
        strict_benchmarks: bool = False,
    ) -> List[CandidateScore]:
        raise NotImplementedError("BenchWarmer.score_candidates not implemented in Phase 0")

    def pareto_frontier(
        self,
        metric: str = "hf_v2_avg",
        max_vram_gb: Optional[float] = None,
        quant: str = "bf16",
    ) -> List[ParetoPoint]:
        raise NotImplementedError("BenchWarmer.pareto_frontier not implemented in Phase 0")

    def detect_anomalies(self, model_id: str) -> ContaminationReport:
        raise NotImplementedError("BenchWarmer.detect_anomalies not implemented in Phase 0")

    def reload(self) -> None:
        raise NotImplementedError("BenchWarmer.reload not implemented in Phase 0")

    def close(self) -> None:
        raise NotImplementedError("BenchWarmer.close not implemented in Phase 0")

    def __enter__(self) -> "BenchWarmer":
        raise NotImplementedError("BenchWarmer.__enter__ not implemented in Phase 0")

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        raise NotImplementedError("BenchWarmer.__exit__ not implemented in Phase 0")
