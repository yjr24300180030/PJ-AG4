#!/usr/bin/env python3
"""
Generate a detailed round-level report with AI reasoning and three figures
from a simulation_results.csv file.

Usage:
    cd /Users/dianjin/Desktop/PJ-AG4-main-0531
    PYTHONPATH=src python3 scripts/generate_detailed_report.py \
        --csv outputs/three_modes/llm-adaptive/simulation_results.csv \
        --output-dir outputs/three_modes/llm-adaptive
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _parse_csv(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="") as f:
        return list(csv.DictReader(f))


def _generate_markdown(rows: list[dict[str, str]], output_dir: Path) -> Path:
    lines: list[str] = []
    lines.append("# Simulation Detailed Log")
    lines.append("")
    lines.append("**Source**: `simulation_results.csv`")
    lines.append("")
    lines.append("---")
    lines.append("")

    for r in rows:
        name = r["agent_name"]
        rnd = r["round"]
        lines.append(f"## Round {rnd} — {name}")
        lines.append("")

        # Decision parameters
        lines.append("### Decision Parameters")
        lines.append(f"- **Forecast demand**: {r['forecast_demand']}")
        lines.append(f"- **Price**: {r['price']}")
        lines.append(f"- **Quantity**: {r['quantity']}")
        lines.append(f"- **Decision source**: {r['decision_source']}")
        lines.append("")

        # Strategy state
        state_raw = r.get("strategy_state", "")
        if state_raw:
            try:
                state = json.loads(state_raw)
                lines.append("### Strategy State")
                for k, v in state.items():
                    lines.append(f"- **{k}**: {v:.4f}")
                lines.append("")
            except Exception:
                pass

        # AI reasoning
        reason = r.get("strategy_update_reason", "")
        if reason:
            lines.append("### AI Strategy Update Reason")
            lines.append(f"> {reason}")
            lines.append("")

        trace_raw = r.get("strategy_update_trace", "")
        if trace_raw:
            try:
                trace = json.loads(trace_raw)
                lines.append("### AI Raw Output")
                lines.append(f"- **Raw delta**: {trace.get('raw_delta', {})}")
                lines.append(f"- **Bounded delta**: {trace.get('bounded_delta', {})}")
                lines.append(f"- **Reason**: {trace.get('reason', '')}")
                lines.append("")
            except Exception:
                lines.append("### AI Raw Output")
                lines.append(f"```\n{trace_raw[:300]}\n```")
                lines.append("")

        # Decision trace summary
        decision_trace = r.get("decision_trace", "")
        if decision_trace:
            lines.append("### Decision Trace")
            lines.append(f"```\n{decision_trace}\n```")
            lines.append("")

        # Market outcome
        lines.append("### Market Outcome")
        lines.append(f"- **True demand**: {r['demand_true']}")
        lines.append(f"- **Allocated demand**: {float(r['allocated_demand']):.1f}")
        lines.append(f"- **Realized sales**: {float(r['realized_sales']):.1f}")
        lines.append(f"- **Market share**: {float(r['demand_share']):.2%}")
        lines.append(f"- **Profit**: {float(r['profit']):.2f}")
        lines.append(f"- **Cumulative profit**: {float(r['cum_profit']):.2f}")
        lines.append(f"- **Inventory end**: {r['inventory_end']}")
        lines.append(f"- **Shortage**: {r['shortage_post_transfer']}")
        lines.append(f"- **Service rate**: {float(r['service_rate']):.2%}")
        lines.append(f"- **Reputation end**: {float(r['reputation_end']):.3f}")
        lines.append(f"- **Dump flag**: {r['dump_flag']}")
        lines.append(f"- **Default flag**: {r['default_flag']}")
        lines.append("")

        # Cost breakdown
        lines.append("### Cost Breakdown")
        lines.append(f"- **Revenue**: {float(r['revenue']):.2f}")
        lines.append(f"- **Production cost**: {float(r['prod_cost']):.2f}")
        lines.append(f"- **Holding cost**: {float(r['holding_cost']):.2f}")
        lines.append(f"- **Obsolescence cost**: {float(r['obsolescence_cost']):.2f}")
        lines.append(f"- **SLA penalty**: {float(r['sla_penalty']):.2f}")
        lines.append(f"- **Menu cost**: {float(r['menu_cost']):.2f}")
        if float(r["transfer_cost"]) > 0:
            lines.append(f"- **Transfer cost**: {float(r['transfer_cost']):.2f}")
        if float(r["transfer_revenue"]) > 0:
            lines.append(f"- **Transfer revenue**: {float(r['transfer_revenue']):.2f}")
        lines.append("")

        lines.append("---")
        lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    final_profits: dict[str, float] = {}
    for r in rows:
        final_profits[r["agent_name"]] = float(r["cum_profit"])
    for name, profit in sorted(final_profits.items(), key=lambda x: -x[1]):
        lines.append(f"- **{name}**: cumulative profit {profit:.2f}")
    lines.append("")

    out_path = output_dir / "detailed_log.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def _generate_figures(rows: list[dict[str, str]], output_dir: Path) -> list[Path]:
    agents = sorted({r["agent_name"] for r in rows})
    colors = {"Hyperscaler": "#e74c3c", "PremiumCloud": "#3498db", "SpotBroker": "#2ecc71"}
    rounds = sorted({int(r["round"]) for r in rows})

    fig1, ax1 = plt.subplots(figsize=(10, 6))
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    fig3, ax3 = plt.subplots(figsize=(10, 6))

    for name in agents:
        agent_rows = [r for r in rows if r["agent_name"] == name]
        profits = [float(r["profit"]) for r in agent_rows]
        cum_profits = [float(r["cum_profit"]) for r in agent_rows]
        prices = [float(r["price"]) for r in agent_rows]
        qtys = [int(r["quantity"]) for r in agent_rows]
        reps = [float(r["reputation_end"]) for r in agent_rows]

        # Figure 1: profit
        ax1.plot(rounds, profits, "o--", color=colors.get(name, "#333"), label=f"{name} (round)")
        ax1.plot(rounds, cum_profits, "s-", color=colors.get(name, "#333"), label=f"{name} (cumulative)", linewidth=2)

        # Figure 2: price + quantity
        offset = (agents.index(name) - 1) * 0.25
        ax2_twin = ax2.twinx()
        ax2.plot(rounds, prices, "o-", color=colors.get(name, "#333"), label=f"{name} price")
        ax2_twin.bar([r + offset for r in rounds], qtys, width=0.2, color=colors.get(name, "#333"), alpha=0.25)

        # Figure 3: reputation
        ax3.plot(rounds, reps, "o-", color=colors.get(name, "#333"), label=name, linewidth=2)

    ax1.set_xlabel("Round")
    ax1.set_ylabel("Profit")
    ax1.set_title("Profit & Cumulative Profit by Agent")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.set_xlabel("Round")
    ax2.set_ylabel("Price")
    ax2.set_title("Price & Quantity by Agent")
    ax2.legend(loc="upper left")
    ax2.grid(True, alpha=0.3)

    ax3.set_xlabel("Round")
    ax3.set_ylabel("Reputation")
    ax3.set_title("Reputation Evolution by Agent")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    paths: list[Path] = []
    for idx, fig in enumerate([fig1, fig2, fig3], 1):
        p = output_dir / f"fig{idx}_detailed.png"
        fig.savefig(p, dpi=150, bbox_inches="tight")
        plt.close(fig)
        paths.append(p)

    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate detailed report and figures from simulation CSV.")
    parser.add_argument("--csv", type=Path, required=True, help="Path to simulation_results.csv")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory")
    args = parser.parse_args()

    rows = _parse_csv(args.csv)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    md_path = _generate_markdown(rows, args.output_dir)
    fig_paths = _generate_figures(rows, args.output_dir)

    print(f"Detailed log: {md_path}")
    for p in fig_paths:
        print(f"Figure: {p}")


if __name__ == "__main__":
    main()
