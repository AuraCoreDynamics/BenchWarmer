"""BenchWarmer - Offline Zero-Dependency LLM Benchmark Oracle."""

from benchwarmer.contracts import (
    QUANT_BITS_MAP,
    ServiceUnavailableError,
    ModelSummary,
    ModelRecord,
    MetricDelta,
    ModelComparisonResult,
    CandidateScore,
    ParetoPoint,
    ContaminationReport,
)

__version__ = "0.1.0"
__all__ = [
    "BenchWarmer",
    "SQLiteConnector",
    "QUANT_BITS_MAP",
    "ServiceUnavailableError",
    "ModelSummary",
    "ModelRecord",
    "MetricDelta",
    "ModelComparisonResult",
    "CandidateScore",
    "ParetoPoint",
    "ContaminationReport",
]


def __getattr__(name: str):
    if name == "BenchWarmer":
        from benchwarmer.api import BenchWarmer
        return BenchWarmer
    if name == "SQLiteConnector":
        from benchwarmer.db.connector import SQLiteConnector
        return SQLiteConnector
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
