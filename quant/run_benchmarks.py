from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Sequence


def _ensure_repo_root_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    src_root_str = str(repo_root / "src")
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    if src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)


_ensure_repo_root_on_path()

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from quant.common import (  # noqa: E402
    BenchmarkPlan,
    RunArtifact,
    StrategyProfile,
    default_strategy_profiles,
    run_benchmark_suite as run_benchmark_plan,
    summarize_benchmark_artifacts,
)
from quant.metrics import AggregateBenchmark, AgentRunMetrics, MarketRunMetrics  # noqa: E402
from quant.reporting import write_benchmark_csv, write_benchmark_markdown, write_dataclass_csv  # noqa: E402
from quant.strategies import DEFAULT_STRATEGIES, strategy_title  # noqa: E402


@dataclass(frozen=True)
class BenchmarkSuiteResult:
    artifacts: list[RunArtifact]
    aggregates: tuple[AggregateBenchmark, ...]
    run_agent_metrics_csv: Path
    run_market_metrics_csv: Path
    aggregate_csv: Path
    report_path: Path
    figure_path: Path


def _resolve_profiles(strategies: Sequence[str] | None) -> tuple[StrategyProfile, ...]:
    if not strategies:
        return default_strategy_profiles(llm_enabled=False)
    return tuple(StrategyProfile(name=strategy, kind=strategy) for strategy in strategies)


def _flatten_agent_metrics(artifacts: Sequence[RunArtifact]) -> list[AgentRunMetrics]:
    rows: list[AgentRunMetrics] = []
    for artifact in artifacts:
        rows.extend(artifact.summary.agent_metrics)
    return rows


def _flatten_market_metrics(artifacts: Sequence[RunArtifact]) -> list[MarketRunMetrics]:
    return [artifact.summary.market for artifact in artifacts]


def _mean_agent_max_drawdown(item: AggregateBenchmark) -> float:
    if not item.agent_metrics:
        return 0.0
    return sum(metric.mean_max_drawdown for metric in item.agent_metrics) / len(item.agent_metrics)


def _plot_benchmark_summary(aggregates: Sequence[AggregateBenchmark], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not aggregates:
        return
    labels = [strategy_title(item.strategy) for item in aggregates]
    profits = [item.market_metrics.mean_total_profit for item in aggregates]
    drawdowns = [_mean_agent_max_drawdown(item) for item in aggregates]

    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    axes[0].bar(labels, profits, color="#2E86AB")
    axes[0].set_ylabel("Mean market profit")
    axes[0].set_title("Benchmark strategy summary")
    axes[0].grid(axis="y", alpha=0.25)

    axes[1].bar(labels, drawdowns, color="#D1495B")
    axes[1].set_ylabel("Mean agent max drawdown")
    axes[1].set_xlabel("Strategy")
    axes[1].grid(axis="y", alpha=0.25)

    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def run_benchmark_suite(
    *,
    strategies: Sequence[str] | None = None,
    seeds: Sequence[int] = (7, 11, 23),
    rounds: int = 10,
    output_root: Path | str = Path("quant/outputs/benchmarks"),
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    llm_model: str | None = None,
    timeout_seconds: float = 8.0,
    generate_run_figures: bool = False,
) -> BenchmarkSuiteResult:
    output_root = Path(output_root)
    plan = BenchmarkPlan(
        strategies=_resolve_profiles(strategies),
        seeds=tuple(seeds),
        rounds=rounds,
        output_root=output_root / "runs",
        generate_figure=generate_run_figures,
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        llm_timeout_seconds=timeout_seconds,
    )
    artifacts = run_benchmark_plan(plan)
    aggregates = summarize_benchmark_artifacts(artifacts)

    reports_dir = output_root / "reports"
    run_agent_metrics_csv = reports_dir / "benchmark_run_agent_metrics.csv"
    run_market_metrics_csv = reports_dir / "benchmark_run_market_metrics.csv"
    aggregate_csv = reports_dir / "benchmark_aggregate.csv"
    report_path = reports_dir / "benchmark_report.md"
    figure_path = reports_dir / "benchmark_summary.png"

    write_dataclass_csv(run_agent_metrics_csv, _flatten_agent_metrics(artifacts))
    write_dataclass_csv(run_market_metrics_csv, _flatten_market_metrics(artifacts))
    write_benchmark_csv(aggregate_csv, aggregates)
    write_benchmark_markdown(report_path, aggregates, title="PJ-AG4 Benchmark Report")
    _plot_benchmark_summary(aggregates, figure_path)

    return BenchmarkSuiteResult(
        artifacts=artifacts,
        aggregates=aggregates,
        run_agent_metrics_csv=run_agent_metrics_csv,
        run_market_metrics_csv=run_market_metrics_csv,
        aggregate_csv=aggregate_csv,
        report_path=report_path,
        figure_path=figure_path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PJ-AG4 benchmark sweeps")
    parser.add_argument("--output-root", type=Path, default=Path("quant/outputs/benchmarks"))
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--seeds", type=int, nargs="+", default=[7, 11, 23])
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=["heuristic", "rule_price_cutter", "rule_inventory_guard"],
        choices=list(DEFAULT_STRATEGIES),
    )
    parser.add_argument("--llm-base-url", type=str, default=None)
    parser.add_argument("--llm-api-key", type=str, default=None)
    parser.add_argument("--llm-model", type=str, default=None)
    parser.add_argument("--timeout-seconds", type=float, default=8.0)
    parser.add_argument("--generate-run-figures", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_benchmark_suite(
        strategies=args.strategies,
        seeds=args.seeds,
        rounds=args.rounds,
        output_root=args.output_root,
        llm_base_url=args.llm_base_url,
        llm_api_key=args.llm_api_key,
        llm_model=args.llm_model,
        timeout_seconds=args.timeout_seconds,
        generate_run_figures=args.generate_run_figures,
    )
    print(f"Run agent metrics: {result.run_agent_metrics_csv}")
    print(f"Run market metrics: {result.run_market_metrics_csv}")
    print(f"Aggregate CSV: {result.aggregate_csv}")
    print(f"Report: {result.report_path}")
    print(f"Figure: {result.figure_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
