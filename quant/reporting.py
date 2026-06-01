from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
import csv
from typing import Iterable, Sequence

from quant.metrics import (
    AggregateBenchmark,
    AggregateSensitivityPoint,
    AgentAggregateMetrics,
    AgentRunMetrics,
    MarketRunMetrics,
    RunSummary,
    AggregateMarketMetrics,
)


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def write_csv_rows(path: Path, rows: Sequence[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _stringify(value) for key, value in row.items()})


def write_dataclass_csv(path: Path, rows: Sequence[object]) -> None:
    csv_rows: list[dict[str, object]] = []
    for row in rows:
        if is_dataclass(row):
            csv_rows.append(asdict(row))
        elif isinstance(row, dict):
            csv_rows.append(row)
        else:
            raise TypeError(f"unsupported row type: {type(row)!r}")
    write_csv_rows(path, csv_rows)


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    header_line = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(_stringify(value) for value in row) + " |" for row in rows]
    return "\n".join([header_line, separator, *body])


def _render_agent_section(agent_metrics: Sequence[AgentRunMetrics]) -> str:
    headers = [
        "Agent",
        "Cum Profit",
        "Mean Profit",
        "Volatility",
        "Sharpe-like",
        "Max DD",
        "Calmar-like",
        "Win Rate",
        "Avg Rep.",
        "Dump",
        "Default",
    ]
    rows = [
        [
            metric.agent_name,
            metric.cumulative_profit,
            metric.mean_profit,
            metric.profit_volatility,
            metric.sharpe_like,
            metric.max_drawdown,
            metric.calmar_like,
            metric.win_rate,
            metric.avg_reputation,
            metric.dump_events,
            metric.default_events,
        ]
        for metric in agent_metrics
    ]
    return _markdown_table(headers, rows)


def _render_aggregate_agent_section(agent_metrics: Sequence[AgentAggregateMetrics]) -> str:
    headers = [
        "Agent",
        "Runs",
        "Mean Cum Profit",
        "Std Cum Profit",
        "Mean Volatility",
        "Mean Sharpe-like",
        "Mean Max DD",
        "Mean Win Rate",
        "Mean Default",
        "Mean Dump",
    ]
    rows = [
        [
            metric.agent_name,
            metric.runs,
            metric.mean_cumulative_profit,
            metric.std_cumulative_profit,
            metric.mean_profit_volatility,
            metric.mean_sharpe_like,
            metric.mean_max_drawdown,
            metric.mean_win_rate,
            metric.mean_default_events,
            metric.mean_dump_events,
        ]
        for metric in agent_metrics
    ]
    return _markdown_table(headers, rows)


def _render_market_section(market: MarketRunMetrics) -> str:
    headers = ["Total Demand", "Total Sales", "Fulfillment", "Avg Price", "Total Profit"]
    rows = [[market.total_demand, market.total_sales, market.fulfillment_ratio, market.avg_price, market.total_profit]]
    return _markdown_table(headers, rows)


def _render_aggregate_market_section(market: AggregateMarketMetrics) -> str:
    headers = ["Runs", "Mean Demand", "Std Demand", "Mean Sales", "Std Sales", "Mean Fulfillment", "Mean Price", "Mean Profit"]
    rows = [[market.runs, market.mean_total_demand, market.std_total_demand, market.mean_total_sales, market.std_total_sales, market.mean_fulfillment_ratio, market.mean_avg_price, market.mean_total_profit]]
    return _markdown_table(headers, rows)


def write_run_summary_markdown(path: Path, summary: RunSummary, title: str | None = None) -> None:
    title = title or f"Run Summary: {summary.strategy} / seed {summary.seed}"
    content = [
        f"# {title}",
        "",
        f"- Strategy: `{summary.strategy}`",
        f"- Seed: `{summary.seed}`",
        f"- Rounds: `{summary.rounds}`",
        "",
        "## Market",
        "",
        _render_market_section(summary.market),
        "",
        "## Agents",
        "",
        _render_agent_section(summary.agent_metrics),
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(content), encoding="utf-8")


def write_benchmark_markdown(path: Path, benchmark: Sequence[AggregateBenchmark], title: str = "Benchmark Report") -> None:
    sections: list[str] = [f"# {title}", ""]
    for item in benchmark:
        sections.extend(
            [
                f"## Strategy: `{item.strategy}`",
                "",
                "### Market",
                "",
                _render_aggregate_market_section(item.market_metrics),
                "",
                "### Agents",
                "",
                _render_aggregate_agent_section(item.agent_metrics),
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(sections), encoding="utf-8")


def write_benchmark_csv(path: Path, benchmark: Sequence[AggregateBenchmark]) -> None:
    rows: list[dict[str, object]] = []
    for item in benchmark:
        for metric in item.agent_metrics:
            rows.append({"record_type": "agent", **asdict(metric)})
        rows.append({"record_type": "market", "strategy": item.strategy, **asdict(item.market_metrics)})
    write_csv_rows(path, rows)


def write_sensitivity_markdown(path: Path, points: Sequence[AggregateSensitivityPoint], title: str = "Sensitivity Report") -> None:
    headers = ["Strategy", "Parameter", "Value", "Runs", "Mean Profit", "Std Profit", "Mean Fulfillment", "Mean Sharpe-like", "Mean Max DD"]
    rows = [
        [
            point.strategy,
            point.parameter,
            point.value,
            point.runs,
            point.mean_total_profit,
            point.std_total_profit,
            point.mean_fulfillment_ratio,
            point.mean_sharpe_like,
            point.mean_max_drawdown,
        ]
        for point in points
    ]
    content = [f"# {title}", "", _markdown_table(headers, rows), ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(content), encoding="utf-8")


def write_sensitivity_csv(path: Path, points: Sequence[AggregateSensitivityPoint]) -> None:
    write_dataclass_csv(path, points)
