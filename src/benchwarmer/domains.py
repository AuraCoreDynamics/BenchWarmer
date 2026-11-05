"""Domain Alignment & Persona Specialization Taxonomy for BenchWarmer.

Evaluates and aligns models against real-world enterprise and developer workloads:
- 💻 Software Engineering & DevOps (developers, systems engineers)
- 📊 Data Analytics & SQL (data analysts, BI developers)
- 📈 Financial & Quantitative Analysis (financial analysts, quants, auditors)
- 💼 Enterprise & Office Productivity (knowledge workers, operations, PMs)
- ⚖️ Legal, Regulatory & Compliance (legal counsel, compliance officers)
- 🔬 Math, Science & Advanced Reasoning (researchers, scientists)
- 🛡️ Cybersecurity & AppSec (security engineers, SOC analysts)
- 📱 Edge & On-Device Deployment (embedded/mobile devs, offline privacy)
"""

from typing import Any, Dict, List, Optional, Tuple


DOMAINS: Dict[str, Dict[str, Any]] = {
    "coding": {
        "key": "coding",
        "title": "Software Engineering & DevOps",
        "short_title": "Coding & DevOps",
        "icon": "💻",
        "personas": ["Software Engineers", "DevOps Engineers", "Systems Architects"],
        "description": "Code synthesis, bug triage, refactoring, systems automation, and SWE-bench execution.",
        "weights": {
            "math_hard": 0.25,
            "bbh": 0.25,
            "ifeval": 0.25,
            "mmlu_pro": 0.15,
            "arena_elo": 0.10,
        },
        "frontier_keys": ["swe_bench_verified", "swe_bench_pro", "codeforces_elo", "livecodebench"],
    },
    "analytics": {
        "key": "analytics",
        "title": "Data Analytics & SQL",
        "short_title": "Analytics & SQL",
        "icon": "📊",
        "personas": ["Data Analysts", "BI Developers", "Data Engineers", "Analytics Leads"],
        "description": "Tabular reasoning, text-to-SQL generation, data cleaning, Pandas transformation, and KPI synthesis.",
        "weights": {
            "math_hard": 0.35,
            "bbh": 0.30,
            "ifeval": 0.20,
            "mmlu_pro": 0.15,
        },
        "frontier_keys": ["hle_tools"],
    },
    "finance": {
        "key": "finance",
        "title": "Financial & Quantitative Analysis",
        "short_title": "Finance & Quant",
        "icon": "📈",
        "personas": ["Financial Analysts", "Quant Researchers", "Investment Bankers", "Auditors"],
        "description": "Financial statement synthesis, 10-K/10-Q parsing, quantitative modeling, math precision, and strict constraint adherence.",
        "weights": {
            "math_hard": 0.35,
            "ifeval": 0.30,
            "bbh": 0.20,
            "gpqa": 0.15,
        },
        "frontier_keys": ["aime_2024"],
    },
    "office": {
        "key": "office",
        "title": "Enterprise & Office Productivity",
        "short_title": "Enterprise Office",
        "icon": "💼",
        "personas": ["Knowledge Workers", "Product Managers", "Operations Leads", "Executive Assistants"],
        "description": "Executive summaries, memo drafting, meeting synthesis, structured report generation, and natural multi-turn communication.",
        "weights": {
            "ifeval": 0.35,
            "arena_elo": 0.35,
            "mmlu_pro": 0.20,
            "musr": 0.10,
        },
        "frontier_keys": [],
    },
    "legal": {
        "key": "legal",
        "title": "Legal, Regulatory & Compliance",
        "short_title": "Legal & Compliance",
        "icon": "⚖️",
        "personas": ["Legal Counsel", "Compliance Officers", "Risk Managers", "Contract Managers"],
        "description": "Contract analysis, statutory interpretation, clause comparison, strict negative constraints, and zero-hallucination compliance.",
        "weights": {
            "ifeval": 0.45,
            "musr": 0.25,
            "bbh": 0.20,
            "gpqa": 0.10,
        },
        "frontier_keys": [],
    },
    "math_science": {
        "key": "math_science",
        "title": "Math, Science & Advanced Reasoning",
        "short_title": "Math & Science",
        "icon": "🔬",
        "personas": ["Research Scientists", "Mathematicians", "Applied Physicists", "Academic Scholars"],
        "description": "Symbolic mathematical deduction, scientific problem-solving, multi-hop reasoning, and theorem proofing.",
        "weights": {
            "math_hard": 0.40,
            "gpqa": 0.30,
            "bbh": 0.20,
            "mmlu_pro": 0.10,
        },
        "frontier_keys": ["aime_2024"],
    },
    "cybersecurity": {
        "key": "cybersecurity",
        "title": "Cybersecurity & AppSec",
        "short_title": "Cybersecurity",
        "icon": "🛡️",
        "personas": ["Security Engineers", "AppSec Auditors", "SOC Analysts", "Penetration Testers"],
        "description": "Vulnerability detection, CyberGym exploit mitigation, secure code audit, attack path analysis, and adversarial triage.",
        "weights": {
            "bbh": 0.35,
            "math_hard": 0.25,
            "ifeval": 0.25,
            "mmlu_pro": 0.15,
        },
        "frontier_keys": ["cybergym", "swe_bench_verified"],
    },
    "edge": {
        "key": "edge",
        "title": "Edge & On-Device Deployment",
        "short_title": "Edge & On-Device",
        "icon": "📱",
        "personas": ["Mobile Developers", "Edge AI Engineers", "Local-First Developers", "Embedded Practitioners"],
        "description": "Local laptop/mobile execution, low latency, sub-8B parameters, low VRAM footprint (<8GB/16GB), and offline sovereign deployment.",
        "weights": {
            "ifeval": 0.30,
            "arena_elo": 0.30,
            "bbh": 0.20,
            "math_hard": 0.20,
        },
        "frontier_keys": [],
    },
}


def compute_domain_scores(
    scores: Dict[str, Optional[float]],
    raw_scores: Optional[Dict[str, Optional[float]]] = None,
    params_b: Optional[float] = None,
    context_length: Optional[int] = None,
    license_str: Optional[str] = None,
    architecture: Optional[str] = None,
    model_id: str = "",
) -> Dict[str, float]:
    """Compute normalized 0.0 - 100.0 suitability scores across all domains."""
    raw_scores = raw_scores or {}
    domain_scores: Dict[str, float] = {}

    norm_scores: Dict[str, float] = {}
    for k, v in scores.items():
        if v is not None:
            norm_scores[k] = float(v)

    # 1. Base academic benchmark average for fallback
    known_academic = [norm_scores[k] for k in ["ifeval", "bbh", "math_hard", "gpqa", "musr", "mmlu_pro"] if k in norm_scores]
    academic_avg = sum(known_academic) / len(known_academic) if known_academic else 50.0

    # 2. Compute score for each standard domain
    for d_key, d_meta in DOMAINS.items():
        if d_key == "edge":
            continue

        weights = d_meta["weights"]
        accum_val = 0.0
        accum_weight = 0.0

        for bench_name, weight in weights.items():
            if bench_name in norm_scores:
                accum_val += norm_scores[bench_name] * weight
                accum_weight += weight

        if accum_weight > 0.0:
            domain_score = accum_val / accum_weight
        else:
            domain_score = academic_avg

        # Frontier benchmark bonus / override if available
        if d_key == "coding":
            swe = norm_scores.get("swe_bench_verified") or norm_scores.get("swe_bench_pro")
            cf = norm_scores.get("codeforces_elo")
            lcb = norm_scores.get("livecodebench")
            if swe is not None:
                # Scale SWE-bench verified (frontier) into domain score
                domain_score = domain_score * 0.65 + min(100.0, swe * 1.05) * 0.35
            elif cf is not None:
                domain_score = domain_score * 0.70 + min(100.0, (cf / 30.0)) * 0.30
            elif lcb is not None:
                domain_score = domain_score * 0.70 + lcb * 0.30

            # Architectural / designation boost for explicit code models
            mid_lower = model_id.lower()
            if any(term in mid_lower for term in ["code", "coder", "codestral"]):
                domain_score = min(100.0, domain_score * 1.08)

        elif d_key == "cybersecurity":
            cg = norm_scores.get("cybergym")
            swe = norm_scores.get("swe_bench_verified")
            if cg is not None:
                domain_score = domain_score * 0.60 + cg * 0.40
            elif swe is not None:
                domain_score = domain_score * 0.75 + swe * 0.25

        elif d_key == "finance" or d_key == "math_science":
            aime = norm_scores.get("aime_2024")
            if aime is not None:
                domain_score = domain_score * 0.75 + aime * 0.25

        elif d_key == "analytics":
            hle = norm_scores.get("hle_tools")
            if hle is not None:
                domain_score = domain_score * 0.80 + hle * 0.20

        # Long-context bonus for office and legal (processing 50+ page documents)
        if d_key in ("office", "legal") and context_length:
            if context_length >= 1000000:
                domain_score = min(100.0, domain_score + 3.0)
            elif context_length >= 128000:
                domain_score = min(100.0, domain_score + 1.5)

        domain_scores[d_key] = round(domain_score, 2)

    # 3. Compute Edge & On-Device suitability score
    is_proprietary = (
        (license_str or "").lower() == "proprietary"
        or (architecture or "").lower() == "proprietary"
        or params_b is None
    )

    if is_proprietary:
        # Cloud proprietary models cannot run locally on-device
        domain_scores["edge"] = 0.0
    else:
        # Open-weights model: evaluate capability per parameter footprint
        # Top sweet-spot for local laptops/phones: <= 4B (100% capacity), 4-9B (85%), 9-16B (65%), >30B (20%)
        if params_b <= 4.0:
            size_multiplier = 1.0
        elif params_b <= 9.0:
            size_multiplier = 0.88
        elif params_b <= 16.0:
            size_multiplier = 0.70
        elif params_b <= 35.0:
            size_multiplier = 0.45
        elif params_b <= 75.0:
            size_multiplier = 0.25
        else:
            size_multiplier = 0.10

        # Quality component based on academic average
        edge_raw = (academic_avg * 0.60 + 40.0) * size_multiplier
        # Bonus for high instruction following in small models
        if "ifeval" in norm_scores and norm_scores["ifeval"] >= 70.0 and params_b <= 9.0:
            edge_raw += 5.0
        domain_scores["edge"] = round(min(100.0, max(0.0, edge_raw)), 2)

    return domain_scores


def determine_primary_domain(
    domain_scores: Dict[str, float],
    model_id: str = "",
    params_b: Optional[float] = None,
    architecture: Optional[str] = None,
    license_str: Optional[str] = None,
) -> Tuple[str, str, List[str]]:
    """Determine the primary domain title, primary domain key, and list of recommended domain tags.

    Returns:
        (primary_domain_title, primary_domain_key, domain_tags)
    """
    mid_lower = model_id.lower()

    # Rule-based specialization overrides if model is specifically branded
    if any(k in mid_lower for k in ["code", "coder", "codestral"]):
        primary_key = "coding"
    elif any(k in mid_lower for k in ["math", "qwq"]):
        primary_key = "math_science"
    elif any(k in mid_lower for k in ["vision", "mllama"]):
        primary_key = "analytics"
    elif params_b is not None and params_b <= 4.0 and (license_str or "").lower() != "proprietary":
        # Compact sub-4B open-weights model
        if domain_scores.get("edge", 0.0) >= 50.0 or any(k in mid_lower for k in ["elm", "mobile", "edge", "nano"]):
            primary_key = "edge"
        else:
            primary_key = max(
                (k for k in domain_scores.keys() if k != "edge"),
                key=lambda k: domain_scores[k],
                default="office",
            )
    else:
        # Select domain with highest suitability score (excluding edge for large models)
        candidate_keys = [k for k in domain_scores.keys() if k != "edge"] if (params_b or 0) > 16.0 else list(domain_scores.keys())
        primary_key = max(candidate_keys, key=lambda k: domain_scores[k], default="office")

    primary_meta = DOMAINS.get(primary_key, DOMAINS["office"])
    primary_title = f"{primary_meta['icon']} {primary_meta['short_title']}"

    # Generate domain tags for top matching domains exceeding threshold (score >= 60.0)
    sorted_domains = sorted(
        domain_scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    tags: List[str] = []
    for d_k, d_val in sorted_domains:
        if d_k == "edge" and d_val < 60.0:
            continue
        if d_val >= 55.0 and len(tags) < 3:
            d_info = DOMAINS.get(d_k)
            if d_info:
                tags.append(f"{d_info['icon']} {d_info['short_title']}")

    if not tags:
        tags.append(primary_title)

    return primary_title, primary_key, tags


def get_domain_suitability_tier(score: float) -> Tuple[str, str]:
    """Return badge class and human label for domain suitability score."""
    if score >= 88.0:
        return "badge-green", "🌟 Frontier / Exceptional"
    elif score >= 75.0:
        return "badge-blue", "🟢 Strong Specialization"
    elif score >= 60.0:
        return "badge-cyan", "🟡 Capable"
    elif score >= 40.0:
        return "badge-amber", "⚪ Baseline"
    else:
        return "badge-red", "⚠️ Limited Suitability"
