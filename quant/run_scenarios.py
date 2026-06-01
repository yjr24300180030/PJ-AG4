from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from quant.common import RunArtifact, StrategyProfile, run_profile
from quant.strategies import strategy_title


DEFAULT_SCENARIOS = ("baseline", "price_war", "supply_shock", "high_volatility", "no_reputation", "no_transfer")


@dataclass(frozen=True)
class ScenarioSummary:
    scenario: str
    strategy: str
    seed: int
    total_profit: float
    fulfillment_ratio: float
    transfer_volume: float
    default_events: float
    dump_events: float
    final_backlog: float


@dataclass(frozen=True)
class ScenarioSweepResult:
    artifacts: list[RunArtifact]
    summary_csv: Path
    report_path: Path


def _artifact_summary(artifact: RunArtifact) -> ScenarioSummary:
    market = artifact.summary.market
    agent_rows = artifact.summary.agent_metrics
    with artifact.csv_path.open(newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    transfer_volume = sum(float(row.get("transfer_out", 0.0) or 0.0) for row in csv_rows)
    final_round = max(int(float(row["round"])) for row in csv_rows) if csv_rows else 0
    final_backlog = sum(
        float(row.get("backlog_end", 0.0) or 0.0)
        for row in csv_rows
        if int(float(row["round"])) == final_round
    )
    return ScenarioSummary(
        scenario=artifact.scenario,
        strategy=artifact.strategy,
        seed=artifact.seed,
        total_profit=market.total_profit,
        fulfillment_ratio=market.fulfillment_ratio,
        transfer_volume=transfer_volume,
        default_events=sum(item.default_events for item in agent_rows),
        dump_events=sum(item.dump_events for item in agent_rows),
        final_backlog=final_backlog,
    )


def _write_summary_csv(path: Path, rows: Sequence[ScenarioSummary]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ScenarioSummary.__dataclass_fields__))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: getattr(row, field) for field in ScenarioSummary.__dataclass_fields__})


def _write_report(path: Path, rows: Sequence[ScenarioSummary]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# PJ-AG4 Scenario Sweep Report", ""]
    lines.append("| Scenario | Strategy | Seed | Profit | Fulfillment | Transfer | Default | Dump |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        lines.append(
            f"| {row.scenario} | {strategy_title(row.strategy)} | {row.seed} | "
            f"{row.total_profit:.2f} | {row.fulfillment_ratio:.2%} | {row.transfer_volume:.2f} | "
            f"{row.default_events:.0f} | {row.dump_events:.0f} |"
        )
    if rows:
        best = max(rows, key=lambda item: item.total_profit)
        stress = max(rows, key=lambda item: item.default_events + item.transfer_volume)
        lines.extend(
            [
                "",
                "## Findings",
                "",
                f"- Best observed payoff: `{best.scenario}` / `{best.strategy}` / seed `{best.seed}` with profit `{best.total_profit:.2f}`.",
                f"- Highest stress demo: `{stress.scenario}` / `{stress.strategy}` shows transfer `{stress.transfer_volume:.2f}` and default events `{stress.default_events:.0f}`.",
                "- Use `supply_shock` for the clearest service-pressure demo and `no_reputation` / `no_transfer` as ablations.",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_scenario_sweep(
    *,
    scenarios: Sequence[str] = DEFAULT_SCENARIOS,
    strategies: Sequence[str] = ("heuristic",),
    seeds: Sequence[int] = (7, 11, 23),
    rounds: int = 30,
    output_root: Path | str = Path("outputs/final/scenario_sweep"),
) -> ScenarioSweepResult:
    output_root = Path(output_root)
    artifacts: list[RunArtifact] = []
    for scenario in scenarios:
        for strategy in strategies:
            profile = StrategyProfile(name=strategy, kind=strategy)
            for seed in seeds:
                artifacts.append(
                    run_profile(
                        profile,
                        seed=seed,
                        rounds=rounds,
                        output_root=output_root / "runs",
                        generate_figure=False,
                        scenario=scenario,
                    )
                )
    summaries = [_artifact_summary(artifact) for artifact in artifacts]
    summary_csv = output_root / "scenario_summary.csv"
    report_path = output_root / "scenario_report.md"
    _write_summary_csv(summary_csv, summaries)
    _write_report(report_path, summaries)
    return ScenarioSweepResult(artifacts=artifacts, summary_csv=summary_csv, report_path=report_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PJ-AG4 scenario and ablation sweeps")
    parser.add_argument("--output-root", type=Path, default=Path("outputs/final/scenario_sweep"))
    parser.add_argument("--rounds", type=int, default=30)
    parser.add_argument("--seeds", type=int, nargs="+", default=[7, 11, 23])
    parser.add_argument("--strategies", nargs="+", default=["heuristic"])
    parser.add_argument("--scenarios", nargs="+", default=list(DEFAULT_SCENARIOS))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_scenario_sweep(
        scenarios=args.scenarios,
        strategies=args.strategies,
        seeds=args.seeds,
        rounds=args.rounds,
        output_root=args.output_root,
    )
    print(f"Scenario summary: {result.summary_csv}")
    print(f"Scenario report: {result.report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
