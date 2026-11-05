"""Immutable typed data contracts, error types, and quantization mappings for BenchWarmer."""

from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any

QUANT_BITS_MAP: Dict[str, float] = {
    "fp32": 32.0,
    "fp16": 16.0,
    "bf16": 16.0,
    "q8_0": 8.5,
    "q6_k": 6.6,
    "q5_k_m": 5.7,
    "q4_k_m": 4.8,
    "q4_0": 4.5,
    "q3_k_m": 3.9,
    "q2_k": 2.9,
}


class ServiceUnavailableError(RuntimeError):
    """Raised when live upstream benchmark repositories cannot be reached."""
    pass


@dataclass(frozen=True)
class ModelSummary:
    model_id: str
    org: str
    params_b: Optional[float]
    architecture: Optional[str]
    hf_v2_avg: Optional[float]
    arena_elo_raw: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelRecord:
    model_id: str
    org: str
    model_name: str
    base_model: Optional[str]
    params_b: Optional[float]
    active_params_b: Optional[float]
    context_length: Optional[int]
    architecture: Optional[str]
    license: Optional[str]
    precision: Optional[str]
    is_moe: bool
    scores: Dict[str, float]            # benchmark -> normalized 0-100 score
    raw_scores: Dict[str, float]        # benchmark -> raw score
    estimated_vram_gb: Dict[str, float] # quant_name -> estimated VRAM GB (weights + 15% overhead)
    distinctive_benchmarks: Dict[str, float] = field(default_factory=dict)
    domain_scores: Dict[str, float] = field(default_factory=dict)
    primary_domain: str = ""
    primary_domain_key: str = ""
    domain_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MetricDelta:
    benchmark: str
    score_a: Optional[float]
    score_b: Optional[float]
    abs_delta: Optional[float]          # score_a - score_b (unrounded float)
    pct_delta: Optional[float]          # ((score_a - score_b) / score_b) * 100.0 if score_b else None
    winner: str                         # model_a, model_b, 'tie', or 'n/a'

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelComparisonResult:
    model_a: ModelRecord
    model_b: ModelRecord
    deltas: Dict[str, MetricDelta]
    wins_a: int
    wins_b: int
    ties: int
    composite_delta: float              # Mean abs_delta across shared benchmarks

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CandidateScore:
    requested_id: str
    matched_model_id: Optional[str]
    composite_score: float              # Weighted sum [0.0 - 100.0], 0.0 if unmatched
    matched_metrics: Dict[str, float]
    missing_benchmarks: List[str]
    params_b: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ParetoPoint:
    model_id: str
    params_b: float
    estimated_vram_gb: float
    quant: str
    metric: str
    score: float
    efficiency_ratio: float             # score / estimated_vram_gb

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContaminationReport:
    model_id: str
    params_b: Optional[float]
    anomaly_score: float                # 0.0 (clean) to 100.0 (severe Goodhart/overfit smell)
    status: str                         # 'CLEAN', 'SUSPICIOUS', 'HIGH_CONTAMINATION_RISK'
    flags: List[str]                    # Human-readable diagnostic triggers
    z_score_spread: float               # StdDev across benchmark percentiles within parameter peer group
    ifeval_vs_knowledge_gap: Optional[float] # mmlu_pro - ifeval divergence

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
