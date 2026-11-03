"""Headless-safe Tkinter GUI and View-Model Controller for BenchWarmer.

Top-level module scope strictly isolates GUI controller logic from Tkinter
to ensure CI environments without a display server or libtk can import and test
all view state, sorting, filtering, and clipboard export functionality.
"""

from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

from benchwarmer.api import BenchWarmer
from benchwarmer.contracts import (
    QUANT_BITS_MAP,
    ModelSummary,
    ModelRecord,
    MetricDelta,
    ModelComparisonResult,
    ParetoPoint,
    ContaminationReport,
)


class BenchWarmerGUIController:
    """Display-independent Controller managing view state, sorting, and clipboard export."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.bw = BenchWarmer(db_path=db_path)

    def close(self) -> None:
        self.bw.close()

    def get_leaderboard_data(
        self,
        query: str = "",
        min_params: Optional[float] = None,
        max_params: Optional[float] = None,
        vram_budget: Optional[float] = None,
        quant: str = "bf16",
        sort_key: str = "hf_v2_avg",
        ascending: bool = False,
    ) -> List[Dict[str, Any]]:
        """Retrieve leaderboard rows with dual raw/display values for accurate sorting."""
        if vram_budget is not None:
            summaries = self.bw.rank(
                benchmark=sort_key,
                limit=1000,
                min_params=min_params,
                max_params=max_params,
                max_vram_gb=vram_budget,
                quant=quant,
            )
        else:
            summaries = self.bw.search(
                query=query if query else "*",
                limit=1000,
                min_params=min_params,
                max_params=max_params,
            )

        rows: List[Dict[str, Any]] = []
        for s in summaries:
            raw_vram = (s.params_b * (QUANT_BITS_MAP.get(quant.lower(), 16.0) / 8.0) * 1.15) if s.params_b else 0.0
            row = {
                "model_id": s.model_id,
                "org": s.org,
                "architecture": s.architecture or "N/A",
                "params_b": s.params_b,
                "params_b_display": f"{s.params_b:.2f}B" if s.params_b is not None else "N/A",
                "estimated_vram_gb": raw_vram,
                "estimated_vram_gb_display": f"{raw_vram:.2f} GB",
                "hf_v2_avg": s.hf_v2_avg,
                "hf_v2_avg_display": f"{s.hf_v2_avg:.2f}" if s.hf_v2_avg is not None else "N/A",
                "arena_elo_raw": s.arena_elo_raw,
                "arena_elo_raw_display": f"{s.arena_elo_raw:.1f}" if s.arena_elo_raw is not None else "N/A",
            }
            rows.append(row)

        # Sort using underlying unrounded raw numeric values
        def _get_sort_val(item: Dict[str, Any]) -> float:
            v = item.get(sort_key)
            if v is None:
                return -1e9 if not ascending else 1e9
            return float(v)

        rows.sort(key=_get_sort_val, reverse=not ascending)
        return rows

    def get_comparison_data(self, model_a: str, model_b: str) -> Dict[str, Any]:
        """Generate side-by-side comparison table with delta tags."""
        comp = self.bw.compare(model_a, model_b)
        delta_rows: List[Dict[str, Any]] = []

        for bench, delta in sorted(comp.deltas.items()):
            score_a_disp = f"{delta.score_a:.2f}" if delta.score_a is not None else "N/A"
            score_b_disp = f"{delta.score_b:.2f}" if delta.score_b is not None else "N/A"
            abs_delta_disp = f"{delta.abs_delta:+.2f}" if delta.abs_delta is not None else "N/A"
            pct_delta_disp = f"{delta.pct_delta:+.2f}%" if delta.pct_delta is not None else "N/A"

            if delta.winner == comp.model_a.model_id:
                tag = "winner_a"
            elif delta.winner == comp.model_b.model_id:
                tag = "winner_b"
            else:
                tag = "tie"

            delta_rows.append({
                "benchmark": delta.benchmark,
                "score_a": delta.score_a,
                "score_a_display": score_a_disp,
                "score_b": delta.score_b,
                "score_b_display": score_b_disp,
                "abs_delta": delta.abs_delta,
                "abs_delta_display": abs_delta_disp,
                "pct_delta": delta.pct_delta,
                "pct_delta_display": pct_delta_disp,
                "winner": delta.winner,
                "tag": tag,
            })

        return {
            "model_a": comp.model_a.model_id,
            "model_b": comp.model_b.model_id,
            "wins_a": comp.wins_a,
            "wins_b": comp.wins_b,
            "ties": comp.ties,
            "composite_delta": comp.composite_delta,
            "composite_delta_display": f"{comp.composite_delta:+.2f}",
            "deltas": delta_rows,
        }

    def get_pareto_data(
        self,
        metric: str = "hf_v2_avg",
        max_vram_gb: Optional[float] = None,
        quant: str = "bf16",
    ) -> List[Dict[str, Any]]:
        """Retrieve Pareto frontier points for GUI visualization."""
        points = self.bw.pareto_frontier(metric=metric, max_vram_gb=max_vram_gb, quant=quant)
        return [
            {
                "model_id": pt.model_id,
                "params_b": pt.params_b,
                "params_b_display": f"{pt.params_b:.2f}B",
                "estimated_vram_gb": pt.estimated_vram_gb,
                "estimated_vram_gb_display": f"{pt.estimated_vram_gb:.2f} GB",
                "score": pt.score,
                "score_display": f"{pt.score:.2f}",
                "efficiency_ratio": pt.efficiency_ratio,
                "efficiency_ratio_display": f"{pt.efficiency_ratio:.4f}",
            }
            for pt in points
        ]

    def get_audit_data(self, model_id: str) -> Dict[str, Any]:
        """Retrieve model contamination audit report for GUI display."""
        rep = self.bw.detect_anomalies(model_id)
        return {
            "model_id": rep.model_id,
            "params_b": rep.params_b,
            "params_b_display": f"{rep.params_b:.2f}B" if rep.params_b is not None else "N/A",
            "anomaly_score": rep.anomaly_score,
            "anomaly_score_display": f"{rep.anomaly_score:.1f} / 100",
            "status": rep.status,
            "flags": rep.flags,
            "z_score_spread": rep.z_score_spread,
            "z_score_spread_display": f"{rep.z_score_spread:.2f}",
            "ifeval_vs_knowledge_gap": rep.ifeval_vs_knowledge_gap,
            "ifeval_vs_knowledge_gap_display": (
                f"{rep.ifeval_vs_knowledge_gap:.2f}" if rep.ifeval_vs_knowledge_gap is not None else "N/A"
            ),
        }

    def export_comparison_markdown(self, model_a: str, model_b: str) -> str:
        """Export side-by-side comparison table as GitHub Flavored Markdown."""
        comp_data = self.get_comparison_data(model_a, model_b)
        lines = [
            f"### Model Comparison: {comp_data['model_a']} vs {comp_data['model_b']}",
            "",
            f"| Benchmark | {comp_data['model_a']} | {comp_data['model_b']} | Abs Delta | Pct Delta | Winner |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for row in comp_data["deltas"]:
            lines.append(
                f"| {row['benchmark']} | {row['score_a_display']} | {row['score_b_display']} | "
                f"{row['abs_delta_display']} | {row['pct_delta_display']} | {row['winner']} |"
            )
        lines.append("")
        lines.append(
            f"**Composite Delta**: {comp_data['composite_delta_display']} "
            f"(Wins A: {comp_data['wins_a']}, Wins B: {comp_data['wins_b']}, Ties: {comp_data['ties']})"
        )
        return "\n".join(lines)

    def export_leaderboard_csv(
        self,
        query: str = "",
        min_params: Optional[float] = None,
        max_params: Optional[float] = None,
    ) -> str:
        """Export leaderboard rows as standard CSV."""
        rows = self.get_leaderboard_data(query=query, min_params=min_params, max_params=max_params)
        lines = ["Model ID,Org,Params (B),Architecture,HF v2 Avg,Arena Elo"]
        for r in rows:
            lines.append(
                f"\"{r['model_id']}\",\"{r['org']}\",{r['params_b'] or ''},"
                f"\"{r['architecture']}\",{r['hf_v2_avg'] or ''},{r['arena_elo_raw'] or ''}"
            )
        return "\n".join(lines)


def launch_gui(db_path: Optional[str] = None) -> None:
    """Launch interactive Tkinter desktop GUI. Lazy-imports Tkinter."""
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except (ImportError, Exception) as e:
        print(
            f"Error: GUI requires tkinter and an active display server: {e}\n"
            f"Please run headless commands using the CLI ('benchwarmer --help') or start an X/Wayland display server.",
            file=sys.stderr,
        )
        return

    controller = BenchWarmerGUIController(db_path=db_path)
    root = tk.Tk()
    root.title("BenchWarmer - Offline Zero-Dependency LLM Benchmark Oracle")
    root.geometry("1024x720")

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=8, pady=8)

    # Tab 1: Leaderboard & Search
    tab_search = ttk.Frame(notebook)
    notebook.add(tab_search, text="Leaderboard & Search")

    search_frame = ttk.Frame(tab_search)
    search_frame.pack(fill="x", padx=8, pady=8)
    ttk.Label(search_frame, text="Search:").pack(side="left", padx=4)
    search_entry = ttk.Entry(search_frame, width=30)
    search_entry.pack(side="left", padx=4)

    tree_search = ttk.Treeview(
        tab_search,
        columns=("model_id", "org", "params", "vram", "hf_avg", "elo"),
        show="headings"
    )
    for col, title in [
        ("model_id", "Model ID"),
        ("org", "Org"),
        ("params", "Params (B)"),
        ("vram", "VRAM (BF16)"),
        ("hf_avg", "HF v2 Avg"),
        ("elo", "Arena Elo"),
    ]:
        tree_search.heading(col, text=title)
    tree_search.pack(fill="both", expand=True, padx=8, pady=8)

    def _refresh_search():
        tree_search.delete(*tree_search.get_children())
        query = search_entry.get().strip()
        data = controller.get_leaderboard_data(query=query)
        for r in data:
            tree_search.insert(
                "", "end",
                values=(
                    r["model_id"], r["org"], r["params_b_display"],
                    r["estimated_vram_gb_display"], r["hf_v2_avg_display"], r["arena_elo_raw_display"]
                )
            )

    btn_search = ttk.Button(search_frame, text="Search", command=_refresh_search)
    btn_search.pack(side="left", padx=4)
    _refresh_search()

    # Tab 2: Side-by-Side Model Comparator
    tab_compare = ttk.Frame(notebook)
    notebook.add(tab_compare, text="Side-by-Side Comparator")

    comp_ctrl_frame = ttk.Frame(tab_compare)
    comp_ctrl_frame.pack(fill="x", padx=8, pady=8)
    ttk.Label(comp_ctrl_frame, text="Model A:").pack(side="left", padx=4)
    entry_a = ttk.Entry(comp_ctrl_frame, width=30)
    entry_a.insert(0, "Qwen/Qwen2.5-72B-Instruct")
    entry_a.pack(side="left", padx=4)

    ttk.Label(comp_ctrl_frame, text="Model B:").pack(side="left", padx=4)
    entry_b = ttk.Entry(comp_ctrl_frame, width=30)
    entry_b.insert(0, "meta-llama/Llama-3.3-70B-Instruct")
    entry_b.pack(side="left", padx=4)

    tree_comp = ttk.Treeview(
        tab_compare,
        columns=("bench", "score_a", "score_b", "abs_delta", "pct_delta", "winner"),
        show="headings"
    )
    for col, title in [
        ("bench", "Benchmark"),
        ("score_a", "Score A"),
        ("score_b", "Score B"),
        ("abs_delta", "Abs Delta"),
        ("pct_delta", "Pct Delta"),
        ("winner", "Winner"),
    ]:
        tree_comp.heading(col, text=title)
    tree_comp.pack(fill="both", expand=True, padx=8, pady=8)

    lbl_comp_summary = ttk.Label(tab_compare, text="", font=("TkDefaultFont", 10, "bold"))
    lbl_comp_summary.pack(pady=4)

    def _refresh_compare():
        tree_comp.delete(*tree_comp.get_children())
        ma = entry_a.get().strip()
        mb = entry_b.get().strip()
        try:
            cdata = controller.get_comparison_data(ma, mb)
            for row in cdata["deltas"]:
                tree_comp.insert(
                    "", "end",
                    values=(
                        row["benchmark"], row["score_a_display"], row["score_b_display"],
                        row["abs_delta_display"], row["pct_delta_display"], row["winner"]
                    )
                )
            lbl_comp_summary.config(
                text=f"Composite Delta: {cdata['composite_delta_display']} | Wins A: {cdata['wins_a']}, Wins B: {cdata['wins_b']}, Ties: {cdata['ties']}"
            )
        except Exception as err:
            messagebox.showerror("Comparison Error", str(err))

    btn_compare = ttk.Button(comp_ctrl_frame, text="Compare", command=_refresh_compare)
    btn_compare.pack(side="left", padx=4)

    def _copy_markdown():
        ma = entry_a.get().strip()
        mb = entry_b.get().strip()
        try:
            md = controller.export_comparison_markdown(ma, mb)
            root.clipboard_clear()
            root.clipboard_append(md)
            messagebox.showinfo("Export", "Markdown table copied to clipboard!")
        except Exception as err:
            messagebox.showerror("Export Error", str(err))

    btn_copy = ttk.Button(comp_ctrl_frame, text="Copy Markdown", command=_copy_markdown)
    btn_copy.pack(side="left", padx=4)
    _refresh_compare()

    # Tab 3: Pareto Frontier & Contamination Audit
    tab_pareto = ttk.Frame(notebook)
    notebook.add(tab_pareto, text="Pareto & Contamination Audit")

    audit_frame = ttk.Frame(tab_pareto)
    audit_frame.pack(fill="x", padx=8, pady=8)
    ttk.Label(audit_frame, text="Audit Model ID:").pack(side="left", padx=4)
    entry_audit = ttk.Entry(audit_frame, width=35)
    entry_audit.insert(0, "overfit-ai/Goodhart-Overfit-7B")
    entry_audit.pack(side="left", padx=4)

    lbl_audit_status = ttk.Label(tab_pareto, text="", font=("TkDefaultFont", 10, "bold"))
    lbl_audit_status.pack(pady=4)

    tree_pareto = ttk.Treeview(
        tab_pareto,
        columns=("model_id", "params", "vram", "score", "efficiency"),
        show="headings"
    )
    for col, title in [
        ("model_id", "Pareto Optimal Model"),
        ("params", "Params (B)"),
        ("vram", "VRAM (BF16 GB)"),
        ("score", "HF v2 Avg"),
        ("efficiency", "Efficiency (Score/GB)"),
    ]:
        tree_pareto.heading(col, text=title)
    tree_pareto.pack(fill="both", expand=True, padx=8, pady=8)

    def _refresh_pareto_audit():
        tree_pareto.delete(*tree_pareto.get_children())
        pdata = controller.get_pareto_data(metric="hf_v2_avg")
        for pt in pdata:
            tree_pareto.insert(
                "", "end",
                values=(
                    pt["model_id"], pt["params_b_display"], pt["estimated_vram_gb_display"],
                    pt["score_display"], pt["efficiency_ratio_display"]
                )
            )

        mid = entry_audit.get().strip()
        try:
            adata = controller.get_audit_data(mid)
            flag_str = "; ".join(adata["flags"]) if adata["flags"] else "Clean"
            lbl_audit_status.config(
                text=f"Status: {adata['status']} | Anomaly Score: {adata['anomaly_score_display']} | Flags: {flag_str}"
            )
        except Exception as err:
            lbl_audit_status.config(text=f"Audit Error: {err}")

    btn_audit = ttk.Button(audit_frame, text="Run Audit & Pareto", command=_refresh_pareto_audit)
    btn_audit.pack(side="left", padx=4)
    _refresh_pareto_audit()

    root.mainloop()
