from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
import argparse
import csv
import math
import sys
from statistics import mean, pstdev
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

from pj_ag4.environment import SettlementRow  # noqa: E402
from pj_ag4.simulation import run_simulation  # noqa: E402

from quant.common import build_strategy_config  # noqa: E402
from quant.strategies import (  # noqa: E402
    DEFAULT_STRATEGIES,
    available_strategies,
    strategy_title,
)


@dataclass(frozen=True)
class BenchmarkRunResult:
    strategy: str
    seed: int
    rounds: int
    csv_path: Path
    figure_path: Path | None
    rows: list[SettlementRow]


@dataclass(frozen=True)
class AgentMetricRow:
    strategy: str
    seed: int
    agent_name: str
    agent_role: str
    final_cum_profit: float
    mean_round_profit: float
    profit_volatility: float
    sharpe_like: float
    max_drawdown: float
    calmar_like: float
    win_rate: float
    avg_reputation: float
    avg_service_rate: float
    dump_events: int
    default_events: int
    dump_rate: float
    default_rate: float
    avg_price: float
    price_volatility: float
    total_shortage: float
    final_inventory: float

    def to_row(self) -> dict[str, str]:
        data = asdict(self)
        return {key: f"{value:.6f}" if isinstance(value, float) else str(value) for key, value in data.items()}


@dataclass(frozen=True)
class StrategyMetricRow:
    strategy: str
    runs: int
    agents_per_run: int
    mean_final_cum_profit: float
    std_final_cum_profit: float
    mean_sharpe_like: float
    mean_max_drawdown: float
    mean_calmar_like: float
    mean_win_rate: float
    mean_avg_reputation: float
    mean_avg_service_rate: float
    mean_dump_rate: float
    mean_default_rate: float
    mean_avg_price: float
    mean_price_volatility: float
    mean_total_shortage: float

    def to_row(self) -> dict[str, str]:
        data = asdict(self)
        return {key: f"{value:.6f}" if isinstance(value, float) else str(value) for key, value in data.items()}


@dataclass(frozen=True)
class MarketMetricRow:
    strategy: str
    seed: int
    total_demand: float
    total_realized_sales: float
    fulfillment_ratio: float
    avg_market_price: float
    avg_market_reputation: float

    def to_row(self) -> dict[str, str]:
        data = asdict(self)
        return {key: f"{value:.6f}" if isinstance(value, float) else str(value) for key, value in data.items()}


@dataclass(frozen=True)
class BenchmarkSuiteResult:
    run_results: list[BenchmarkRunResult]
    agent_metrics: list[AgentMetricRow]
    strategy_metrics: list[StrategyMetricRow]
    market_metrics: list[MarketMetricRow]
    agent_metrics_csv: Path
    strategy_metrics_csv: Path
    market_metrics_csv: Path
    report_path: Path
    figure_path: Path


def _max_drawdown(cumulative_series: Sequence[float]) -> float:
    if not cumulative_series:
        return 0.0
    peak = cumulative_series[0]
    worst = 0.0
    for value in cumulative_series:
        peak = max(peak, value)
        worst = max(worst, peak - value)
    return worst


def _group_rows_by_agent(rows: Sequence[SettlementRow]) -> dict[str, list[SettlementRow]]:
    grouped: dict[str, list[SettlementRow]] = defaultdict(list)
    for row in sorted(rows, key=lambda item: (item.agent_name, item.round)):
        grouped[row.agent_name].append(row)
    return grouped


def _market_metric_row(strategy: str, seed: int, rows: Sequence[SettlementRow]) -> MarketMetricRow:
    demand_by_round: dict[int, float] = {}
    sales_by_round: dict[int, float] = defaultdict(float)
    price_by_round: dict[int, list[float]] = defaultdict(list)
    reputation_by_round: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        demand_by_round[row.round] = float(row.demand_true)
        sales_by_round[row.round] += float(row.realized_sales)
        price_by_round[row.round].append(float(row.price))
        reputation_by_round[row.round].append(float(row.reputation_end))
    total_demand = sum(demand_by_round.values())
    total_sales = sum(sales_by_round.values())
    return MarketMetricRow(
        strategy=strategy,
        seed=seed,
        total_demand=total_demand,
        total_realized_sales=total_sales,
        fulfillment_ratio=total_sales / total_demand if total_demand else 0.0,
        avg_market_price=mean(mean(values) for values in price_by_round.values()),
        avg_market_reputation=mean(mean(values) for values in reputation_by_round.values()),
    )


def _agent_metric_row(strategy: str, seed: int, rows: Sequence[SettlementRow]) -> AgentMetricRow:
    if not rows:
        raise ValueError("agent rows must not be empty")
    profits = [float(row.profit) for row in rows]
    cumulative = [float(row.cum_profit) for row in rows]
    reputations = [float(row.reputation_end) for row in rows]
    service_rates = [float(row.service_rate) for row in rows]
    prices = [float(row.price) for row in rows]
    shortages = [float(row.shortage_post_transfer) for row in rows]
    dump_events = sum(int(row.dump_flag) for row in rows)
    default_events = sum(int(row.default_flag) for row in rows)
    final_cum_profit = cumulative[-1]
    profit_volatility = pstdev(profits) if len(profits) > 1 else 0.0
    sharpe = mean(profits) / profit_volatility if profit_volatility else 0.0
    drawdown = _max_drawdown(cumulative)
    calmar = final_cum_profit / drawdown if drawdown else final_cum_profit
    win_rate = sum(1 for value in profits if value > 0) / len(profits)
    return AgentMetricRow(
        strategy=strategy,
        seed=seed,
        agent_name=rows[0].agent_name,
        agent_role=rows[0].agent_role,
        final_cum_profit=final_cum_profit,
        mean_round_profit=mean(profits),
        profit_volatility=profit_volatility,
        sharpe_like=sharpe,
        max_drawdown=drawdown,
        calmar_like=calmar,
        win_rate=win_rate,
        avg_reputation=mean(reputations),
        avg_service_rate=mean(service_rates),
        dump_events=dump_events,
        default_events=default_events,
        dump_rate=dump_events / len(rows),
        default_rate=default_events / len(rows),
        avg_price=mean(prices),
        price_volatility=pstdev(prices) if len(prices) > 1 else 0.0,
        total_shortage=sum(shortages),
        final_inventory=float(rows[-1].inventory_end),
    )


def _write_csv(path: Path, rows: Sequence[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _aggregate_strategy_metrics(agent_metrics: Sequence[AgentMetricRow]) -> list[StrategyMetricRow]:
    grouped: dict[str, list[AgentMetricRow]] = defaultdict(list)
    for row in agent_metrics:
        grouped[row.strategy].append(row)
    summary: list[StrategyMetricRow] = []
    for strategy, rows in grouped.items():
        summary.append(
            StrategyMetricRow(
                strategy=strategy,
                runs=len({(row.strategy, row.seed) for row in rows}),
                agents_per_run=len({row.agent_name for row in rows}),
                mean_final_cum_profit=mean(row.final_cum_profit for row in rows),
                std_final_cum_profit=pstdev([row.final_cum_profit for row in rows]) if len(rows) > 1 else 0.0,
                mean_sharpe_like=mean(row.sharpe_like for row in rows),
                mean_max_drawdown=mean(row.max_drawdown for row in rows),
                mean_calmar_like=mean(row.calmar_like for row in rows),
                mean_win_rate=mean(row.win_rate for row in rows),
                mean_avg_reputation=mean(row.avg_reputation for row in rows),
                mean_avg_service_rate=mean(row.avg_service_rate for row in rows),
                mean_dump_rate=mean(row.dump_rate for row in rows),
                mean_default_rate=mean(row.default_rate for row in rows),
                mean_avg_price=mean(row.avg_price for row in rows),
                mean_price_volatility=mean(row.price_volatility for row in rows),
                mean_total_shortage=mean(row.total_shortage for row in rows),
            )
        )
    return sorted(summary, key=lambda row: row.strategy)


def _plot_strategy_summary(strategy_metrics: Sequence[StrategyMetricRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not strategy_metrics:
        return
    labels = [row.strategy for row in strategy_metrics]
    profits = [row.mean_final_cum_profit for row in strategy_metrics]
    drawdowns = [row.mean_max_drawdown for row in strategy_metrics]
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    axes[0].bar(labels, profits, color="#2E86AB")
    axes[0].set_ylabel("Mean final cumulative profit")
    axes[0].set_title("Benchmark strategy summary")
    axes[0].grid(axis="y", alpha=0.25)
    axes[1].bar(labels, drawdowns, color="#D1495B")
    axes[1].set_ylabel("Mean max drawdown")
    axes[1].set_xlabel("Strategy")
    axes[1].grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _write_report(
    *,
    output_path: Path,
    strategy_metrics: Sequence[StrategyMetricRow],
    market_metrics: Sequence[MarketMetricRow],
    figure_path: Path,
) -> None:
    lines: list[str] = []
    lines.append("# PJ-AG4 Benchmark Report")
    lines.append("")
    lines.append(f"- Strategies: {len(strategy_metrics)}")
    lines.append(f"- Market rows: {len(market_metrics)}")
    lines.append(f"- Figure: [{figure_path.name}]({figure_path.as_posix()})")
    lines.append("")
    lines.append("| Strategy | Mean Final Cum Profit | Mean Sharpe-like | Mean Max Drawdown | Mean Default Rate |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for row in strategy_metrics:
        lines.append(
            f"| {strategy_title(row.strategy)} | {row.mean_final_cum_profit:.3f} | {row.mean_sharpe_like:.3f} | {row.mean_max_drawdown:.3f} | {row.mean_default_rate:.3f} |"
        )
    lines.append("")
    lines.append("## Market Snapshots")
    lines.append("")
    lines.append("| Strategy | Seed | Fulfillment | Avg Market Price | Avg Market Reputation |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for row in market_metrics:
        lines.append(
            f"| {strategy_title(row.strategy)} | {row.seed} | {row.fulfillment_ratio:.3f} | {row.avg_market_price:.3f} | {row.avg_market_reputation:.3f} |"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_case(
    *,
    strategy_name: str,
    seed: int,
    rounds: int,
    output_root: Path,
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    llm_model: str | None = None,
    timeout_seconds: float = 8.0,
    generate_figure: bool = False,
    market_overrides: dict[str, float] | None = None,
) -> BenchmarkRunResult:
    run_dir = output_root / strategy_name / f"seed_{seed}"
    config = build_strategy_config(
        strategy_name=strategy_name,
        seed=seed,
        rounds=rounds,
        output_dir=run_dir,
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        llm_timeout_seconds=timeout_seconds,
        market_overrides=market_overrides,
    )
    result = run_simulation(config, output_dir=run_dir, generate_figure=generate_figure)
    return BenchmarkRunResult(
        strategy=strategy_name,
        seed=seed,
        rounds=rounds,
        csv_path=result.csv_path,
        figure_path=result.figure_path,
        rows=result.rows,
    )


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
    selected_strategies = tuple(strategies or available_strategies())
    output_root = Path(output_root)
    run_results: list[BenchmarkRunResult] = []
    agent_metrics: list[AgentMetricRow] = []
    market_metrics: list[MarketMetricRow] = []
    for strategy_name in selected_strategies:
        for seed in seeds:
            case = run_case(
                strategy_name=strategy_name,
                seed=seed,
                rounds=rounds,
                output_root=output_root / "runs",
                llm_base_url=llm_base_url,
                llm_api_key=llm_api_key,
                llm_model=llm_model,
                timeout_seconds=timeout_seconds,
                generate_figure=generate_run_figures,
            )
            run_results.append(case)
            market_metrics.append(_market_metric_row(strategy_name, seed, case.rows))
            for agent_rows in _group_rows_by_agent(case.rows).values():
                agent_metrics.append(_agent_metric_row(strategy_name, seed, agent_rows))

    strategy_metrics = _aggregate_strategy_metrics(agent_metrics)
    reports_dir = output_root / "reports"
    agent_metrics_csv = reports_dir / "benchmark_agent_metrics.csv"
    strategy_metrics_csv = reports_dir / "benchmark_strategy_metrics.csv"
    market_metrics_csv = reports_dir / "benchmark_market_metrics.csv"
    figure_path = reports_dir / "benchmark_summary.png"
    report_path = reports_dir / "benchmark_report.md"
    _write_csv(agent_metrics_csv, [row.to_row() for row in agent_metrics])
    _write_csv(strategy_metrics_csv, [row.to_row() for row in strategy_metrics])
    _write_csv(market_metrics_csv, [row.to_row() for row in market_metrics])
    _plot_strategy_summary(strategy_metrics, figure_path)
    _write_report(
        output_path=report_path,
        strategy_metrics=strategy_metrics,
        market_metrics=market_metrics,
        figure_path=figure_path,
    )
    return BenchmarkSuiteResult(
        run_results=run_results,
        agent_metrics=agent_metrics,
        strategy_metrics=strategy_metrics,
        market_metrics=market_metrics,
        agent_metrics_csv=agent_metrics_csv,
        strategy_metrics_csv=strategy_metrics_csv,
        market_metrics_csv=market_metrics_csv,
        report_path=report_path,
        figure_path=figure_path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PJ-AG4 benchmark sweeps")
    parser.add_argument("--output-root", type=Path, default=Path("quant/outputs/benchmarks"))
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--seeds", type=int, nargs="+", default=[7, 11, 23])
    parser.add_argument("--strategies", nargs="+", default=list(DEFAULT_STRATEGIES), choices=list(DEFAULT_STRATEGIES))
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
    print(f"Agent metrics: {result.agent_metrics_csv}")
    print(f"Strategy metrics: {result.strategy_metrics_csv}")
    print(f"Market metrics: {result.market_metrics_csv}")
    print(f"Report: {result.report_path}")
    print(f"Figure: {result.figure_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
