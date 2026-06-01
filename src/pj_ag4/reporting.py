from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Sequence

from .config import SimulationConfig
from .contracts import DecisionTrace, SettlementRow, StrategyUpdateTrace


def _format_number(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    header_line = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = [
        "| " + " | ".join(_format_number(value) for value in row) + " |" for row in rows
    ]
    return "\n".join([header_line, separator, *body])


def _group_by_agent(rows: Sequence[SettlementRow]) -> dict[str, list[SettlementRow]]:
    grouped: dict[str, list[SettlementRow]] = defaultdict(list)
    for row in rows:
        grouped[row.agent_name].append(row)
    return dict(grouped)


def _first_rows_by_round(rows: Sequence[SettlementRow]) -> list[SettlementRow]:
    first_rows: dict[int, SettlementRow] = {}
    for row in rows:
        first_rows.setdefault(row.round, row)
    return [first_rows[round_index] for round_index in sorted(first_rows)]


def _agent_summary_rows(rows: Sequence[SettlementRow]) -> list[list[object]]:
    summary_rows: list[list[object]] = []
    for agent_name, agent_rows in sorted(_group_by_agent(rows).items()):
        final = agent_rows[-1]
        total_shortage = sum(row.shortage_post_transfer for row in agent_rows)
        summary_rows.append(
            [
                agent_name,
                final.agent_role,
                final.cum_profit,
                mean(row.profit for row in agent_rows),
                mean(row.forecast_error_abs for row in agent_rows),
                mean(row.price for row in agent_rows),
                sum(row.realized_sales for row in agent_rows),
                mean(row.service_rate for row in agent_rows),
                sum(row.transfer_in for row in agent_rows),
                sum(row.transfer_out for row in agent_rows),
                sum(row.price_pressure_cost for row in agent_rows),
                sum(row.dump_flag for row in agent_rows),
                sum(row.default_flag for row in agent_rows),
                final.inventory_end,
                final.reputation_end,
                total_shortage,
            ]
        )
    return summary_rows


def _round_summary_rows(rows: Sequence[SettlementRow]) -> list[list[object]]:
    round_rows: list[list[object]] = []
    for round_index, agent_rows in sorted(_rows_by_round(rows).items()):
        first = agent_rows[0]
        round_rows.append(
            [
                round_index,
                first.demand_true,
                first.demand_obs,
                sum(row.realized_sales for row in agent_rows),
                mean(row.price for row in agent_rows),
                sum(row.profit for row in agent_rows),
                sum(row.shortage_post_transfer for row in agent_rows),
                sum(row.transfer_in for row in agent_rows),
                sum(row.reallocated_in for row in agent_rows),
                sum(row.backlog_end for row in agent_rows),
            ]
        )
    return round_rows


def _rows_by_round(rows: Sequence[SettlementRow]) -> dict[int, list[SettlementRow]]:
    grouped: dict[int, list[SettlementRow]] = defaultdict(list)
    for row in rows:
        grouped[row.round].append(row)
    return dict(grouped)


def _event_rows(rows: Sequence[SettlementRow], *, limit: int = 8) -> list[list[object]]:
    events: list[tuple[float, list[object]]] = []
    for round_index, agent_rows in _rows_by_round(rows).items():
        first = agent_rows[0]
        total_shortage = sum(row.shortage_post_transfer for row in agent_rows)
        total_transfer = sum(row.transfer_in for row in agent_rows)
        total_dump = sum(row.dump_flag for row in agent_rows)
        total_default = sum(row.default_flag for row in agent_rows)
        shock_abs = abs(first.shock_component)
        score = (
            total_shortage
            + total_transfer
            + shock_abs
            + 10 * total_dump
            + 10 * total_default
        )
        if score <= 0:
            continue
        labels: list[str] = []
        if shock_abs >= 1.0:
            labels.append(f"shock={first.shock_component:.2f}")
        if total_shortage > 0:
            labels.append(f"shortage={total_shortage:.2f}")
        if total_transfer > 0:
            labels.append(f"transfer={total_transfer:.2f}")
        if total_dump:
            labels.append(f"dump_flags={int(total_dump)}")
        if total_default:
            labels.append(f"default_flags={int(total_default)}")
        events.append(
            (
                score,
                [
                    round_index,
                    first.demand_true,
                    sum(row.realized_sales for row in agent_rows),
                    "; ".join(labels),
                ],
            )
        )
    events.sort(key=lambda item: (-item[0], item[1][0]))
    return [event for _, event in events[:limit]]


def _decision_trace_rows(rows: Sequence[SettlementRow], *, limit: int = 12) -> list[list[object]]:
    trace_rows: list[list[object]] = []
    for round_index, agent_rows in sorted(_rows_by_round(rows).items()):
        for row in sorted(agent_rows, key=lambda item: item.agent_name):
            trace = DecisionTrace.from_json(row.decision_trace)
            if trace is None:
                continue
            trace_rows.append(
                [
                    round_index,
                    row.agent_name,
                    trace.source,
                    trace.forecast_base,
                    trace.forecast_adjustment,
                    trace.price_base,
                    trace.price_adjustment,
                    trace.quantity_target,
                    trace.risk_gate_adjustment,
                    trace.summary,
                ]
            )
            if len(trace_rows) >= limit:
                return trace_rows
    return trace_rows


def _adaptive_strategy_trace_rows(rows: Sequence[SettlementRow], *, limit: int = 12) -> list[list[object]]:
    trace_rows: list[list[object]] = []
    for round_index, agent_rows in sorted(_rows_by_round(rows).items()):
        for row in sorted(agent_rows, key=lambda item: item.agent_name):
            trace = StrategyUpdateTrace.from_json(row.strategy_update_trace)
            if trace is None:
                continue
            trace_rows.append(
                [
                    round_index,
                    row.agent_name,
                    trace.personality_label,
                    trace.bounded_delta.get("price_aggressiveness", 0.0),
                    trace.bounded_delta.get("inventory_caution", 0.0),
                    trace.bounded_delta.get("risk_tolerance", 0.0),
                    trace.new_state.price_aggressiveness,
                    trace.new_state.inventory_caution,
                    trace.new_state.risk_tolerance,
                    trace.reason,
                ]
            )
            if len(trace_rows) >= limit:
                return trace_rows
    return trace_rows


def _strategy_commentary(rows: Sequence[SettlementRow]) -> list[str]:
    if not rows:
        return ["No simulation rows were produced."]
    grouped = _group_by_agent(rows)
    final_rows = {name: agent_rows[-1] for name, agent_rows in grouped.items()}
    winner_name, winner_row = max(
        final_rows.items(), key=lambda item: item[1].cum_profit
    )
    service_leader_name, service_leader_rows = max(
        grouped.items(), key=lambda item: mean(row.service_rate for row in item[1])
    )
    price_leader_name, price_leader_rows = max(
        grouped.items(), key=lambda item: mean(row.price for row in item[1])
    )
    market_total_sales = sum(row.realized_sales for row in rows)
    market_total_demand = sum(row.demand_true for row in _first_rows_by_round(rows))
    fulfillment = (
        market_total_sales / market_total_demand if market_total_demand else 0.0
    )
    total_transfer = sum(row.transfer_in for row in rows)
    total_reallocated = sum(row.reallocated_in for row in rows)
    final_backlog = sum(agent_rows[-1].backlog_end for agent_rows in grouped.values())
    total_dump = sum(row.dump_flag for row in rows)
    total_default = sum(row.default_flag for row in rows)
    return [
        f"**Winner:** `{winner_name}` ends with cumulative profit `{winner_row.cum_profit:.2f}`, the highest value in this run.",
        f"**Service leader:** `{service_leader_name}` posts the strongest average service rate at `{mean(row.service_rate for row in service_leader_rows):.2%}`.",
        f"**Pricing posture:** `{price_leader_name}` maintains the highest average price at `{mean(row.price for row in price_leader_rows):.2f}`.",
        f"**Market fulfillment:** the run sells `{market_total_sales:.2f}` units against `{market_total_demand:.2f}` true demand for a fulfillment ratio of `{fulfillment:.2%}`.",
        f"**Operational stress:** peer transfers total `{total_transfer:.2f}` units, customer reallocation totals `{total_reallocated:.2f}`, final SLA backlog is `{final_backlog:.2f}`, with `{int(total_dump)}` dump flags and `{int(total_default)}` default flags.",
    ]


def _finding_lines(rows: Sequence[SettlementRow], config: SimulationConfig) -> list[str]:
    if not rows:
        return ["- No findings available."]
    grouped = _group_by_agent(rows)
    final_rows = {name: agent_rows[-1] for name, agent_rows in grouped.items()}
    winner, winner_row = max(final_rows.items(), key=lambda item: item[1].cum_profit)
    total_reallocated = sum(row.reallocated_in for row in rows)
    total_transfer = sum(row.transfer_in for row in rows)
    final_backlog = sum(row.backlog_end for row in final_rows.values())
    avg_forecast_error = mean(row.forecast_error_abs for row in rows)
    return [
        f"**Finding 1: Reputation-weighted SLA posture can beat pure price cutting.** In scenario `{config.scenario}`, `{winner}` ends first with cumulative profit `{winner_row.cum_profit:.2f}` and reputation `{winner_row.reputation_end:.2%}`.",
        f"**Finding 2: Capacity pressure is now visible as customer migration and backlog.** Two-stage allocation reallocates `{total_reallocated:.2f}` units and leaves final SLA backlog `{final_backlog:.2f}`.",
        f"**Finding 3: Peer transfer is a stress valve, not the whole market.** Transfer volume totals `{total_transfer:.2f}` units while average forecast error is `{avg_forecast_error:.2f}`, linking prediction quality to shortage/default risk.",
    ]


def write_simulation_report(
    path: Path, *, rows: Sequence[SettlementRow], config: SimulationConfig
) -> None:
    """Write a single-run Markdown report for CSV-adjacent simulation review."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rounds = sorted({row.round for row in rows})
    market_total_demand = (
        sum(row.demand_true for row in _first_rows_by_round(rows)) if rows else 0.0
    )
    market_total_sales = sum(row.realized_sales for row in rows)
    total_profit = sum(row.profit for row in rows)
    total_price_pressure_cost = sum(row.price_pressure_cost for row in rows)
    avg_price = mean(row.market_avg_price for row in rows) if rows else 0.0
    fulfillment = (
        market_total_sales / market_total_demand if market_total_demand else 0.0
    )

    content = [
        "# PJ-AG4 Simulation Report",
        "",
        "## Run Parameters",
        "",
        _markdown_table(
            ["Seed", "Scenario", "Rounds", "Agent Mode", "Agents", "Demand Window"],
            [
                [
                    config.seed,
                    config.scenario,
                    len(rounds),
                    config.agent_mode,
                    len(config.agents),
                    config.market.demand_window,
                ]
            ],
        ),
        "",
        "## Market Summary",
        "",
        _markdown_table(
            [
                "Total Demand",
                "Total Sales",
                "Fulfillment",
                "Average Market Price",
                "Total Profit",
                "Price Pressure Cost",
            ],
            [
                [
                    market_total_demand,
                    market_total_sales,
                    fulfillment,
                    avg_price,
                    total_profit,
                    total_price_pressure_cost,
                ]
            ],
        ),
        "",
        "## Agent Strategy Comparison",
        "",
        _markdown_table(
            [
                "Agent",
                "Role",
                "Final Cum Profit",
                "Avg Profit",
                "Avg Forecast Error",
                "Avg Price",
                "Total Sales",
                "Avg Service Rate",
                "Transfer In",
                "Transfer Out",
                "Price Pressure Cost",
                "Dump Flags",
                "Default Flags",
                "Final Inventory",
                "Final Reputation",
                "Total Shortage",
            ],
            _agent_summary_rows(rows),
        ),
        "",
        "## Round-Level Timeline",
        "",
        _markdown_table(
            [
                "Round",
                "True Demand",
                "Observed Demand",
                "Sales",
                "Avg Price",
                "Profit",
                "Shortage",
                "Transfers",
                "Reallocated",
                "Backlog",
            ],
            _round_summary_rows(rows),
        ),
        "",
        "## Findings",
        "",
        *[f"- {line}" for line in _finding_lines(rows, config)],
        "",
        "## Key Events",
        "",
        _markdown_table(
            ["Round", "True Demand", "Sales", "Signals"], _event_rows(rows)
        ),
        "",
        "## Decision Trace Samples",
        "",
        _markdown_table(
            [
                "Round",
                "Agent",
                "Source",
                "Forecast Base",
                "Forecast Adj",
                "Price Base",
                "Price Adj",
                "Qty Target",
                "Risk Gate",
                "Summary",
            ],
            _decision_trace_rows(rows),
        ),
        "",
        "## Adaptive Strategy Trace Samples",
        "",
        _markdown_table(
            [
                "Round",
                "Agent",
                "Personality",
                "Price Delta",
                "Inventory Delta",
                "Risk Delta",
                "Price State",
                "Inventory State",
                "Risk State",
                "Reason",
            ],
            _adaptive_strategy_trace_rows(rows),
        ),
        "",
        "## Conclusion Notes",
        "",
        *[f"- {line}" for line in _strategy_commentary(rows)],
        "",
        "## Appendix: Agent Configuration",
        "",
        _markdown_table(
            [
                "Agent",
                "Forecast",
                "Pricing",
                "Allocation",
                "Risk",
                "Base Price",
                "Max Quantity",
            ],
            [
                [
                    agent.name,
                    agent.forecaster_style,
                    agent.pricer_style,
                    agent.allocator_style,
                    agent.risk_style,
                    agent.base_price,
                    agent.max_quantity,
                ]
                for agent in config.agents
            ],
        ),
        "",
    ]
    path.write_text("\n".join(content), encoding="utf-8")
