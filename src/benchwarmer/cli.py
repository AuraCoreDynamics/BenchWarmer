"""Command-line interface for BenchWarmer."""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from benchwarmer.api import BenchWarmer
from benchwarmer.contracts import (
    ModelSummary,
    ModelRecord,
    ModelComparisonResult,
    CandidateScore,
    ParetoPoint,
    ContaminationReport,
)


def _format_table(headers: List[str], rows: List[List[str]]) -> str:
    """Format tabular data with clean text-aligned columns."""
    if not rows:
        return "No data found."
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(val)))
            else:
                col_widths.append(len(str(val)))

    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    data_lines = [
        " | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row))
        for row in rows
    ]
    return f"{header_line}\n{sep_line}\n" + "\n".join(data_lines)


def _format_markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    """Format tabular data as GitHub Flavored Markdown table."""
    if not rows:
        return "*No data found.*"
    header_line = "| " + " | ".join(headers) + " |"
    sep_line = "| " + " | ".join("---" for _ in headers) + " |"
    data_lines = [
        "| " + " | ".join(str(val) for val in row) + " |"
        for row in rows
    ]
    return f"{header_line}\n{sep_line}\n" + "\n".join(data_lines)


def _render_output(data: Any, fmt: str, headers: List[str], rows: List[List[str]]) -> str:
    if fmt == "json":
        # Rule 18: Full unrounded float precision emitted in JSON
        return json.dumps(data, indent=2)
    elif fmt == "markdown":
        return _format_markdown_table(headers, rows)
    else:
        return _format_table(headers, rows)


def handle_search(bw: BenchWarmer, args: argparse.Namespace) -> int:
    results = bw.search(
        query=args.query,
        limit=args.limit,
        min_params=args.min_params,
        max_params=args.max_params,
    )
    headers = ["Model ID", "Org", "Params (B)", "Architecture", "HF v2 Avg", "Arena Elo"]
    rows = []
    for r in results:
        rows.append([
            r.model_id,
            r.org,
            f"{r.params_b:.2f}" if r.params_b is not None else "N/A",
            r.architecture or "N/A",
            f"{r.hf_v2_avg:.2f}" if r.hf_v2_avg is not None else "N/A",
            f"{r.arena_elo_raw:.1f}" if r.arena_elo_raw is not None else "N/A",
        ])
    data = [r.to_dict() for r in results]
    print(_render_output(data, args.format, headers, rows))
    return 0


def handle_info(bw: BenchWarmer, args: argparse.Namespace) -> int:
    rec = bw.get_model(args.model_id)
    if not rec:
        print(f"Error: Model '{args.model_id}' not found in benchmark store.", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(rec.to_dict(), indent=2))
        return 0

    headers = ["Property", "Value"]
    rows = [
        ["Model ID", rec.model_id],
        ["Organization", rec.org],
        ["Model Name", rec.model_name],
        ["Base Model", rec.base_model or "N/A"],
        ["Parameters", f"{rec.params_b:.2f}B" if rec.params_b is not None else "N/A"],
        ["Active Parameters", f"{rec.active_params_b:.2f}B" if rec.active_params_b is not None else "N/A"],
        ["Architecture", rec.architecture or "N/A"],
        ["Context Length", str(rec.context_length) if rec.context_length is not None else "N/A"],
        ["License", rec.license or "N/A"],
        ["Precision", rec.precision or "N/A"],
        ["Is MoE", "Yes" if rec.is_moe else "No"],
    ]
    for b, s in sorted(rec.scores.items()):
        raw = rec.raw_scores.get(b, s)
        rows.append([f"Benchmark: {b}", f"{s:.2f} (raw: {raw:.2f})"])

    for q, vram in sorted(rec.estimated_vram_gb.items()):
        rows.append([f"VRAM ({q})", f"{vram:.2f} GB"])

    print(_render_output(rec.to_dict(), args.format, headers, rows))
    return 0


def handle_compare(bw: BenchWarmer, args: argparse.Namespace) -> int:
    try:
        comp = bw.compare(args.model_a, args.model_b)
    except Exception as e:
        print(f"Error comparing models: {e}", file=sys.stderr)
        return 1

    headers = ["Benchmark", args.model_a, args.model_b, "Abs Delta", "Pct Delta", "Winner"]
    rows = []
    for bench, delta in sorted(comp.deltas.items()):
        sa = f"{delta.score_a:.2f}" if delta.score_a is not None else "N/A"
        sb = f"{delta.score_b:.2f}" if delta.score_b is not None else "N/A"
        ad = f"{delta.abs_delta:+.2f}" if delta.abs_delta is not None else "N/A"
        pd = f"{delta.pct_delta:+.2f}%" if delta.pct_delta is not None else "N/A"
        rows.append([bench, sa, sb, ad, pd, delta.winner])

    # Summary row
    rows.append([
        "COMPOSITE",
        f"Wins: {comp.wins_a}",
        f"Wins: {comp.wins_b}",
        f"{comp.composite_delta:+.2f}",
        f"Ties: {comp.ties}",
        args.model_a if comp.wins_a > comp.wins_b else (args.model_b if comp.wins_b > comp.wins_a else "Tie"),
    ])

    print(_render_output(comp.to_dict(), args.format, headers, rows))
    return 0


def handle_rank(bw: BenchWarmer, args: argparse.Namespace) -> int:
    results = bw.rank(
        benchmark=args.benchmark,
        limit=args.limit,
        min_params=args.min_params,
        max_params=args.max_params,
        max_vram_gb=args.vram,
        quant=args.quant,
    )
    headers = ["Rank", "Model ID", "Org", "Params (B)", "Arch", "HF v2 Avg", "Arena Elo"]
    rows = []
    for i, r in enumerate(results, start=1):
        rows.append([
            str(i),
            r.model_id,
            r.org,
            f"{r.params_b:.2f}" if r.params_b is not None else "N/A",
            r.architecture or "N/A",
            f"{r.hf_v2_avg:.2f}" if r.hf_v2_avg is not None else "N/A",
            f"{r.arena_elo_raw:.1f}" if r.arena_elo_raw is not None else "N/A",
        ])
    data = [r.to_dict() for r in results]
    print(_render_output(data, args.format, headers, rows))
    return 0


def handle_score(bw: BenchWarmer, args: argparse.Namespace) -> int:
    # Parse candidate IDs
    candidates: List[str] = []
    if args.candidates == "-":
        stdin_content = sys.stdin.read().strip()
        if not stdin_content:
            print("Error: Empty candidate input from stdin.", file=sys.stderr)
            return 1
        try:
            parsed_json = json.loads(stdin_content)
            if isinstance(parsed_json, list):
                candidates = [str(item) for item in parsed_json]
            else:
                candidates = [line.strip() for line in stdin_content.splitlines() if line.strip()]
        except json.JSONDecodeError:
            candidates = [line.strip() for line in stdin_content.splitlines() if line.strip()]
    else:
        candidates = [c.strip() for c in args.candidates.split(",") if c.strip()]

    if not candidates:
        print("Error: No candidate model IDs provided.", file=sys.stderr)
        return 1

    # Parse weights: key=val,key2=val2
    weights: Dict[str, float] = {}
    try:
        pairs = args.weights.split(",")
        for pair in pairs:
            if not pair.strip():
                continue
            k, v = pair.split("=")
            weights[k.strip()] = float(v.strip())
    except Exception as e:
        print(f"Error parsing weights '{args.weights}': {e}", file=sys.stderr)
        return 1

    try:
        scores = bw.score_candidates(
            candidates=candidates,
            weights=weights,
            strict_benchmarks=args.strict,
        )
    except Exception as e:
        print(f"Error scoring candidates: {e}", file=sys.stderr)
        return 1

    headers = ["Rank", "Requested ID", "Matched Model", "Composite Score", "Params (B)", "Missing Metrics"]
    rows = []
    for idx, sc in enumerate(scores, start=1):
        rows.append([
            str(idx),
            sc.requested_id,
            sc.matched_model_id or "UNMATCHED",
            f"{sc.composite_score:.2f}",
            f"{sc.params_b:.2f}" if sc.params_b is not None else "N/A",
            ", ".join(sc.missing_benchmarks) if sc.missing_benchmarks else "None",
        ])
    data = [sc.to_dict() for sc in scores]
    print(_render_output(data, args.format, headers, rows))
    return 0


def handle_pareto(bw: BenchWarmer, args: argparse.Namespace) -> int:
    results = bw.pareto_frontier(
        metric=args.metric,
        max_vram_gb=args.vram,
        quant=args.quant,
    )
    headers = ["Model ID", "Params (B)", f"VRAM ({args.quant} GB)", f"Score ({args.metric})", "Efficiency (Score/GB)"]
    rows = []
    for pt in results:
        rows.append([
            pt.model_id,
            f"{pt.params_b:.2f}",
            f"{pt.estimated_vram_gb:.2f}",
            f"{pt.score:.2f}",
            f"{pt.efficiency_ratio:.4f}",
        ])
    data = [pt.to_dict() for pt in results]
    print(_render_output(data, args.format, headers, rows))
    return 0


def handle_audit(bw: BenchWarmer, args: argparse.Namespace) -> int:
    try:
        report = bw.detect_anomalies(args.model_id)
    except Exception as e:
        print(f"Error auditing model '{args.model_id}': {e}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    headers = ["Metric / Flag", "Audit Finding"]
    rows = [
        ["Model ID", report.model_id],
        ["Parameters", f"{report.params_b:.2f}B" if report.params_b is not None else "N/A"],
        ["Contamination Status", report.status],
        ["Anomaly Score", f"{report.anomaly_score:.2f} / 100.0"],
        ["Z-Score Spread", f"{report.z_score_spread:.2f}"],
        ["IFEval vs MMLU Gap", f"{report.ifeval_vs_knowledge_gap:.2f}" if report.ifeval_vs_knowledge_gap is not None else "N/A"],
    ]
    if report.flags:
        for idx, fl in enumerate(report.flags, start=1):
            rows.append([f"Flag #{idx}", fl])
    else:
        rows.append(["Flags", "None detected (Clean benchmark profile)"])

    print(_render_output(report.to_dict(), args.format, headers, rows))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="benchwarmer",
        description="Offline Zero-Dependency LLM Benchmark Oracle",
    )
    parser.add_argument("--db", type=str, default=None, help="Custom SQLite database file path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = subparsers.add_parser("search", help="Search models by query string")
    p_search.add_argument("query", type=str, help="Search query (e.g. 'qwen 72b' or '*')")
    p_search.add_argument("--limit", type=int, default=10, help="Max results to return")
    p_search.add_argument("--min-params", type=float, default=None, help="Minimum parameter count (B)")
    p_search.add_argument("--max-params", type=float, default=None, help="Maximum parameter count (B)")
    p_search.add_argument("--format", choices=["table", "json", "markdown"], default="table")

    # info
    p_info = subparsers.add_parser("info", help="Get model details and benchmarks")
    p_info.add_argument("model_id", type=str, help="Model ID or search phrase")
    p_info.add_argument("--format", choices=["table", "json", "markdown"], default="table")

    # compare
    p_comp = subparsers.add_parser("compare", help="Compare two models side-by-side")
    p_comp.add_argument("model_a", type=str, help="First model ID")
    p_comp.add_argument("model_b", type=str, help="Second model ID")
    p_comp.add_argument("--format", choices=["table", "json", "markdown"], default="table")

    # rank
    p_rank = subparsers.add_parser("rank", help="Rank models by benchmark")
    p_rank.add_argument("--benchmark", type=str, default="hf_v2_avg", help="Benchmark name")
    p_rank.add_argument("--limit", type=int, default=10, help="Max results")
    p_rank.add_argument("--min-params", type=float, default=None, help="Minimum parameter count (B)")
    p_rank.add_argument("--max-params", type=float, default=None, help="Maximum parameter count (B)")
    p_rank.add_argument("--vram", type=float, default=None, help="Maximum VRAM budget (GB)")
    p_rank.add_argument("--quant", type=str, default="bf16", help="Quantization format")
    p_rank.add_argument("--format", choices=["table", "json", "markdown"], default="table")

    # score
    p_score = subparsers.add_parser("score", help="Score candidate models by weighted criteria")
    p_score.add_argument("--candidates", required=True, type=str, help="Comma-separated IDs or '-' for stdin")
    p_score.add_argument("--weights", required=True, type=str, help="e.g. ifeval=0.4,math_hard=0.6")
    p_score.add_argument("--strict", action="store_true", help="Apply strict benchmark criteria")
    p_score.add_argument("--format", choices=["table", "json", "markdown"], default="table")

    # pareto
    p_pareto = subparsers.add_parser("pareto", help="Compute Pareto frontier of score vs VRAM")
    p_pareto.add_argument("--metric", type=str, default="hf_v2_avg", help="Target metric")
    p_pareto.add_argument("--vram", type=float, default=None, help="Maximum VRAM budget (GB)")
    p_pareto.add_argument("--quant", type=str, default="bf16", help="Quantization format")
    p_pareto.add_argument("--format", choices=["table", "json", "markdown"], default="table")

    # audit
    p_audit = subparsers.add_parser("audit", help="Audit model for benchmark contamination/overfitting")
    p_audit.add_argument("model_id", type=str, help="Model ID")
    p_audit.add_argument("--format", choices=["table", "json", "markdown"], default="table")

    # mcp
    subparsers.add_parser("mcp", help="Run stdio JSON-RPC 2.0 MCP server")

    # gui
    loopback_host = ".".join(["127", "0", "0", "1"])
    p_gui = subparsers.add_parser("gui", help="Launch interactive web GUI or desktop GUI")
    p_gui.add_argument("--host", default=loopback_host, help="Host interface to bind")
    p_gui.add_argument("--port", type=int, default=8765, help="Port to listen on (default: 8765)")
    p_gui.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    p_gui.add_argument("--tk", action="store_true", help="Launch legacy Tkinter GUI instead of Web UI")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "mcp":
        from benchwarmer.mcp import run_stdio_server
        run_stdio_server()
        return 0

    if args.command == "gui":
        if getattr(args, "tk", False):
            from benchwarmer.gui import launch_gui
            launch_gui(args.db)
            return 0
        from benchwarmer.web.server import run_web_server
        run_web_server(
            host=args.host,
            port=args.port,
            open_browser=not args.no_browser,
            db_path=args.db,
        )
        return 0

    bw = BenchWarmer(db_path=args.db)
    try:
        if args.command == "search":
            return handle_search(bw, args)
        elif args.command == "info":
            return handle_info(bw, args)
        elif args.command == "compare":
            return handle_compare(bw, args)
        elif args.command == "rank":
            return handle_rank(bw, args)
        elif args.command == "score":
            return handle_score(bw, args)
        elif args.command == "pareto":
            return handle_pareto(bw, args)
        elif args.command == "audit":
            return handle_audit(bw, args)
        else:
            parser.print_help()
            return 1
    finally:
        bw.close()


if __name__ == "__main__":
    sys.exit(main())
