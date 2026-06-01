from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
import csv
from statistics import mean, pstdev
from typing import Iterable, Mapping, Sequence


def _to_float(value: object) -> float:
    if value is None or value == "":
        return 0.0
    return float(value)


def _to_int(value: object) -> int:
    if value is None or value == "":
        return 0
    return int(float(value))


def max_drawdown(cumulative_values: Sequence[float]) -> float:
    if not cumulative_values:
        return 0.0
    peak = cumulative_values[0]
    worst = 0.0
    for value in cumulative_values:
        if value > peak:
            peak = value
        drawdown = peak - value
        if drawdown > worst:
            worst = drawdown
    return worst


def sharpe_like(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    dispersion = pstdev(values) if len(values) > 1 else 0.0
    if dispersion == 0:
        return 0.0
    return mean(values) / dispersion


def calmar_like(total_profit: float, drawdown: float) -> float:
    if drawdown <= 0:
        return 0.0
    return total_profit / drawdown


def win_rate(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(1 for value in values if value > 0) / len(values)


@dataclass(frozen=True)
class AgentRunMetrics:
    strategy: str
    seed: int
    agent_name: str
    rounds: int
    cumulative_profit: float
    mean_profit: float
    profit_volatility: float
    sharpe_like: float
    max_drawdown: float
    calmar_like: float
    win_rate: float
    avg_reputation: float
    avg_service_rate: float
    total_shortage: float
    dump_events: int
    default_events: int
    avg_price: float


@dataclass(frozen=True)
class MarketRunMetrics:
    strategy: str
    seed: int
    rounds: int
    total_demand: float
    total_sales: float
    fulfillment_ratio: float
    avg_price: float
    total_profit: float


@dataclass(frozen=True)
class RunSummary:
    strategy: str
    seed: int
    rounds: int
    agent_metrics: tuple[AgentRunMetrics, ...]
    market: MarketRunMetrics


@dataclass(frozen=True)
class AgentAggregateMetrics:
    strategy: str
    agent_name: str
    runs: int
    mean_cumulative_profit: float
    std_cumulative_profit: float
    mean_profit_volatility: float
    mean_sharpe_like: float
    mean_max_drawdown: float
    mean_calmar_like: float
    mean_win_rate: float
    mean_avg_reputation: float
    mean_avg_service_rate: float
    mean_total_shortage: float
    mean_dump_events: float
    mean_default_events: float
    mean_avg_price: float


@dataclass(frozen=True)
class AggregateMarketMetrics:
    strategy: str
    runs: int
    mean_total_demand: float
    std_total_demand: float
    mean_total_sales: float
    std_total_sales: float
    mean_fulfillment_ratio: float
    std_fulfillment_ratio: float
    mean_avg_price: float
    std_avg_price: float
    mean_total_profit: float
    std_total_profit: float


@dataclass(frozen=True)
class AggregateBenchmark:
    strategy: str
    runs: int
    agent_metrics: tuple[AgentAggregateMetrics, ...]
    market_metrics: AggregateMarketMetrics


@dataclass(frozen=True)
class SensitivityPoint:
    strategy: str
    parameter: str
    value: float
    runs: int
    mean_total_profit: float
    std_total_profit: float
    mean_fulfillment_ratio: float
    std_fulfillment_ratio: float
    mean_sharpe_like: float
    mean_max_drawdown: float


@dataclass(frozen=True)
class AggregateSensitivityPoint:
    strategy: str
    parameter: str
    value: float
    runs: int
    mean_total_profit: float
    std_total_profit: float
    mean_fulfillment_ratio: float
    std_fulfillment_ratio: float
    mean_sharpe_like: float
    mean_max_drawdown: float


def _rows_by_agent(rows: Sequence[Mapping[str, object]]) -> dict[str, list[Mapping[str, object]]]:
    grouped: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["agent_name"])].append(row)
    for agent_rows in grouped.values():
        agent_rows.sort(key=lambda item: _to_int(item["round"]))
    return grouped


def summarize_rows(rows: Sequence[Mapping[str, object]], *, strategy: str, seed: int) -> RunSummary:
    if not rows:
        raise ValueError("rows cannot be empty")
    grouped = _rows_by_agent(rows)
    agent_metrics: list[AgentRunMetrics] = []
    round_index_to_rows: dict[int, list[Mapping[str, object]]] = defaultdict(list)

    for row in rows:
        round_index_to_rows[_to_int(row["round"])].append(row)

    round_ids = sorted(round_index_to_rows)
    for agent_name, agent_rows in grouped.items():
        profits = [_to_float(row["profit"]) for row in agent_rows]
        cumulative = [_to_float(row["cum_profit"]) for row in agent_rows]
        metrics = AgentRunMetrics(
            strategy=strategy,
            seed=seed,
            agent_name=agent_name,
            rounds=len(agent_rows),
            cumulative_profit=cumulative[-1] if cumulative else 0.0,
            mean_profit=mean(profits) if profits else 0.0,
            profit_volatility=pstdev(profits) if len(profits) > 1 else 0.0,
            sharpe_like=sharpe_like(profits),
            max_drawdown=max_drawdown(cumulative),
            calmar_like=calmar_like(cumulative[-1] if cumulative else 0.0, max_drawdown(cumulative)),
            win_rate=win_rate(profits),
            avg_reputation=mean(_to_float(row["reputation_end"]) for row in agent_rows),
            avg_service_rate=mean(_to_float(row["service_rate"]) for row in agent_rows),
            total_shortage=sum(_to_float(row["shortage_post_transfer"]) for row in agent_rows),
            dump_events=sum(_to_int(row["dump_flag"]) for row in agent_rows),
            default_events=sum(_to_int(row["default_flag"]) for row in agent_rows),
            avg_price=mean(_to_float(row["price"]) for row in agent_rows),
        )
        agent_metrics.append(metrics)

    total_demand = 0.0
    total_sales = sum(_to_float(row["realized_sales"]) for row in rows)
    total_profit = sum(_to_float(row["profit"]) for row in rows)
    avg_price = mean(_to_float(row["market_avg_price"]) for row in rows)
    for round_id in round_ids:
        first_row = round_index_to_rows[round_id][0]
        total_demand += _to_float(first_row["demand_true"])
    market = MarketRunMetrics(
        strategy=strategy,
        seed=seed,
        rounds=len(round_ids),
        total_demand=total_demand,
        total_sales=total_sales,
        fulfillment_ratio=(total_sales / total_demand) if total_demand else 0.0,
        avg_price=avg_price,
        total_profit=total_profit,
    )
    return RunSummary(strategy=strategy, seed=seed, rounds=len(round_ids), agent_metrics=tuple(agent_metrics), market=market)


def summarize_csv_run(csv_path: Path, *, strategy: str, seed: int) -> RunSummary:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return summarize_rows(rows, strategy=strategy, seed=seed)


def aggregate_run_summaries(run_summaries: Sequence[RunSummary]) -> tuple[AggregateBenchmark, ...]:
    if not run_summaries:
        return ()
    by_strategy: dict[str, list[RunSummary]] = defaultdict(list)
    for summary in run_summaries:
        by_strategy[summary.strategy].append(summary)

    aggregates: list[AggregateBenchmark] = []
    for strategy, summaries in sorted(by_strategy.items()):
        agent_names = sorted({metric.agent_name for summary in summaries for metric in summary.agent_metrics})
        agent_metrics: list[AgentAggregateMetrics] = []
        for agent_name in agent_names:
            series = [metric for summary in summaries for metric in summary.agent_metrics if metric.agent_name == agent_name]
            agent_metrics.append(
                AgentAggregateMetrics(
                    strategy=strategy,
                    agent_name=agent_name,
                    runs=len(series),
                    mean_cumulative_profit=mean(metric.cumulative_profit for metric in series),
                    std_cumulative_profit=pstdev(metric.cumulative_profit for metric in series) if len(series) > 1 else 0.0,
                    mean_profit_volatility=mean(metric.profit_volatility for metric in series),
                    mean_sharpe_like=mean(metric.sharpe_like for metric in series),
                    mean_max_drawdown=mean(metric.max_drawdown for metric in series),
                    mean_calmar_like=mean(metric.calmar_like for metric in series),
                    mean_win_rate=mean(metric.win_rate for metric in series),
                    mean_avg_reputation=mean(metric.avg_reputation for metric in series),
                    mean_avg_service_rate=mean(metric.avg_service_rate for metric in series),
                    mean_total_shortage=mean(metric.total_shortage for metric in series),
                    mean_dump_events=mean(metric.dump_events for metric in series),
                    mean_default_events=mean(metric.default_events for metric in series),
                    mean_avg_price=mean(metric.avg_price for metric in series),
                )
            )

        market_series = [summary.market for summary in summaries]
        market_metrics = AggregateMarketMetrics(
            strategy=strategy,
            runs=len(market_series),
            mean_total_demand=mean(metric.total_demand for metric in market_series),
            std_total_demand=pstdev(metric.total_demand for metric in market_series) if len(market_series) > 1 else 0.0,
            mean_total_sales=mean(metric.total_sales for metric in market_series),
            std_total_sales=pstdev(metric.total_sales for metric in market_series) if len(market_series) > 1 else 0.0,
            mean_fulfillment_ratio=mean(metric.fulfillment_ratio for metric in market_series),
            std_fulfillment_ratio=pstdev(metric.fulfillment_ratio for metric in market_series) if len(market_series) > 1 else 0.0,
            mean_avg_price=mean(metric.avg_price for metric in market_series),
            std_avg_price=pstdev(metric.avg_price for metric in market_series) if len(market_series) > 1 else 0.0,
            mean_total_profit=mean(metric.total_profit for metric in market_series),
            std_total_profit=pstdev(metric.total_profit for metric in market_series) if len(market_series) > 1 else 0.0,
        )
        aggregates.append(
            AggregateBenchmark(
                strategy=strategy,
                runs=len(summaries),
                agent_metrics=tuple(agent_metrics),
                market_metrics=market_metrics,
            )
        )
    return tuple(aggregates)


def aggregate_sensitivity_points(points: Sequence[SensitivityPoint]) -> tuple[AggregateSensitivityPoint, ...]:
    if not points:
        return ()
    grouped: dict[tuple[str, str, float], list[SensitivityPoint]] = defaultdict(list)
    for point in points:
        grouped[(point.strategy, point.parameter, point.value)].append(point)
    aggregates: list[AggregateSensitivityPoint] = []
    for (strategy, parameter, value), series in sorted(grouped.items()):
        aggregates.append(
            AggregateSensitivityPoint(
                strategy=strategy,
                parameter=parameter,
                value=value,
                runs=len(series),
                mean_total_profit=mean(point.mean_total_profit for point in series),
                std_total_profit=pstdev(point.mean_total_profit for point in series) if len(series) > 1 else 0.0,
                mean_fulfillment_ratio=mean(point.mean_fulfillment_ratio for point in series),
                std_fulfillment_ratio=pstdev(point.mean_fulfillment_ratio for point in series) if len(series) > 1 else 0.0,
                mean_sharpe_like=mean(point.mean_sharpe_like for point in series),
                mean_max_drawdown=mean(point.mean_max_drawdown for point in series),
            )
        )
    return tuple(aggregates)

