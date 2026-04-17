from __future__ import annotations

from collections import defaultdict
from html import escape
import json
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Sequence

from .config import SimulationConfig
from .environment import SettlementRow


AGENT_COLORS = {
    "Hyperscaler": {"solid": "#3ddc84", "soft": "rgba(61, 220, 132, 0.16)"},
    "PremiumCloud": {"solid": "#3e8ad6", "soft": "rgba(62, 138, 214, 0.16)"},
    "SpotBroker": {"solid": "#c7347e", "soft": "rgba(199, 52, 126, 0.16)"},
}


def _round_value(round_rows: Sequence[SettlementRow], attr: str) -> float:
    return float(getattr(round_rows[0], attr))


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _agent_role_label(role: str) -> str:
    labels = {
        "hyperscaler": "Scale-dominant",
        "premium": "SLA-first",
        "spot": "Volatility hunter",
    }
    return labels.get(role, role.replace("_", " ").title())


def _summarize_agent_rows(agent_rows: Sequence[SettlementRow]) -> dict[str, float]:
    profits = [row.profit for row in agent_rows]
    return {
        "cumulativeProfit": agent_rows[-1].cum_profit if agent_rows else 0.0,
        "meanProfit": mean(profits) if profits else 0.0,
        "profitVolatility": pstdev(profits) if len(profits) > 1 else 0.0,
        "avgReputation": mean(row.reputation_end for row in agent_rows) if agent_rows else 0.0,
        "avgServiceRate": mean(row.service_rate for row in agent_rows) if agent_rows else 0.0,
        "avgPrice": mean(row.price for row in agent_rows) if agent_rows else 0.0,
        "totalShortage": sum(row.shortage_post_transfer for row in agent_rows),
        "defaults": float(sum(row.default_flag for row in agent_rows)),
        "dumps": float(sum(row.dump_flag for row in agent_rows)),
    }


def _build_events(rounds_payload: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for round_payload in rounds_payload:
        score = (
            abs(float(round_payload["shockComponent"])) * 0.7
            + float(round_payload["defaultCount"]) * 16.0
            + float(round_payload["dumpCount"]) * 8.0
            + float(round_payload["transferVolume"]) * 0.6
        )
        tags: list[str] = []
        if abs(float(round_payload["shockComponent"])) >= 0.5:
            tags.append("shock")
        if int(round_payload["defaultCount"]) > 0:
            tags.append("default")
        if int(round_payload["dumpCount"]) > 0:
            tags.append("dump")
        if float(round_payload["transferVolume"]) > 0:
            tags.append("transfer")
        if not tags:
            continue
        if int(round_payload["defaultCount"]) > 0:
            headline = "Service stress detected"
        elif abs(float(round_payload["shockComponent"])) >= 0.5:
            headline = "Demand regime shifted"
        elif int(round_payload["dumpCount"]) > 0:
            headline = "Price aggression escalated"
        else:
            headline = "Cross-agent support activated"
        details = (
            f"Shock {float(round_payload['shockComponent']):+.1f}, "
            f"defaults {int(round_payload['defaultCount'])}, "
            f"dumps {int(round_payload['dumpCount'])}, "
            f"transfer {float(round_payload['transferVolume']):.1f}"
        )
        events.append(
            {
                "round": int(round_payload["round"]),
                "headline": headline,
                "details": details,
                "tags": tags,
                "score": round(score, 3),
            }
        )
    events.sort(key=lambda item: (-float(item["score"]), int(item["round"])))
    return events


def build_dashboard_payload(
    rows: Sequence[SettlementRow],
    *,
    config: SimulationConfig | None = None,
    strategy_name: str | None = None,
) -> dict[str, Any]:
    if not rows:
        raise ValueError("rows cannot be empty")

    rows_by_round: dict[int, list[SettlementRow]] = defaultdict(list)
    rows_by_agent: dict[str, list[SettlementRow]] = defaultdict(list)
    for row in rows:
        rows_by_round[row.round].append(row)
        rows_by_agent[row.agent_name].append(row)

    ordered_rounds = sorted(rows_by_round)
    ordered_agents = sorted(rows_by_agent)
    resolved_strategy = strategy_name or (config.agent_mode if config else "heuristic")
    agent_summary_map = {
        agent_name: _summarize_agent_rows(sorted(agent_rows, key=lambda item: item.round))
        for agent_name, agent_rows in rows_by_agent.items()
    }

    rounds_payload: list[dict[str, Any]] = []
    for round_index in ordered_rounds:
        round_rows = sorted(rows_by_round[round_index], key=lambda item: item.agent_name)
        first_row = round_rows[0]
        total_demand = float(first_row.demand_true)
        total_sales = sum(row.realized_sales for row in round_rows)
        agent_payloads = []
        for row in round_rows:
            agent_payloads.append(
                {
                    "name": row.agent_name,
                    "role": row.agent_role,
                    "color": AGENT_COLORS.get(row.agent_name, {}).get("solid", "#3e8ad6"),
                    "actionText": row.agent_action,
                    "price": row.price,
                    "quantity": row.quantity,
                    "forecastDemand": row.forecast_demand,
                    "allocatedDemand": row.allocated_demand,
                    "realizedSales": row.realized_sales,
                    "shortage": row.shortage_post_transfer,
                    "profit": row.profit,
                    "cumProfit": row.cum_profit,
                    "reputation": row.reputation_end,
                    "serviceRate": row.service_rate,
                    "transferIn": row.transfer_in,
                    "transferOut": row.transfer_out,
                    "dumpFlag": row.dump_flag,
                    "defaultFlag": row.default_flag,
                }
            )
        rounds_payload.append(
            {
                "round": round_index,
                "demandTrue": total_demand,
                "demandObserved": float(first_row.demand_obs),
                "demandGap": float(first_row.demand_obs - first_row.demand_true),
                "marketAvgPrice": float(first_row.market_avg_price),
                "marketTotalSales": total_sales,
                "fulfillmentRatio": _safe_ratio(total_sales, total_demand),
                "shockComponent": float(first_row.shock_component),
                "trendComponent": float(first_row.trend_component),
                "seasonComponent": float(first_row.season_component),
                "noiseComponent": float(first_row.noise_component),
                "transferVolume": float(sum(row.transfer_out for row in round_rows)),
                "defaultCount": int(sum(row.default_flag for row in round_rows)),
                "dumpCount": int(sum(row.dump_flag for row in round_rows)),
                "agentSpread": float(max(row.price for row in round_rows) - min(row.price for row in round_rows)),
                "agents": agent_payloads,
            }
        )

    agents_payload: list[dict[str, Any]] = []
    for agent_name in ordered_agents:
        agent_rows = sorted(rows_by_agent[agent_name], key=lambda item: item.round)
        config_agent = None
        if config is not None:
            config_agent = next((agent for agent in config.agents if agent.name == agent_name), None)
        summary_metrics = agent_summary_map[agent_name]
        colors = AGENT_COLORS.get(agent_name, {"solid": "#3e8ad6", "soft": "rgba(62, 138, 214, 0.22)"})
        agents_payload.append(
            {
                "name": agent_name,
                "role": _agent_role_label(agent_rows[0].agent_role),
                "persona": config_agent.persona if config_agent is not None else agent_rows[0].agent_role,
                "color": colors["solid"],
                "surface": colors["soft"],
                "summary": {
                    "cumulativeProfit": summary_metrics["cumulativeProfit"],
                    "meanProfit": summary_metrics["meanProfit"],
                    "profitVolatility": summary_metrics["profitVolatility"],
                    "avgReputation": summary_metrics["avgReputation"],
                    "avgServiceRate": summary_metrics["avgServiceRate"],
                    "avgPrice": summary_metrics["avgPrice"],
                    "totalShortage": summary_metrics["totalShortage"],
                    "defaults": summary_metrics["defaults"],
                    "dumps": summary_metrics["dumps"],
                },
                "series": {
                    "rounds": [row.round for row in agent_rows],
                    "price": [row.price for row in agent_rows],
                    "quantity": [row.quantity for row in agent_rows],
                    "profit": [row.profit for row in agent_rows],
                    "cumProfit": [row.cum_profit for row in agent_rows],
                    "reputation": [row.reputation_end for row in agent_rows],
                    "serviceRate": [row.service_rate for row in agent_rows],
                },
            }
        )

    rounds_count = len(ordered_rounds)
    demand_series = [_round_value(rows_by_round[idx], "demand_true") for idx in ordered_rounds]
    sales_series = [next(item["marketTotalSales"] for item in rounds_payload if item["round"] == idx) for idx in ordered_rounds]
    price_series = [_round_value(rows_by_round[idx], "market_avg_price") for idx in ordered_rounds]
    shock_series = [_round_value(rows_by_round[idx], "shock_component") for idx in ordered_rounds]
    transfer_series = [sum(row.transfer_out for row in rows_by_round[idx]) for idx in ordered_rounds]
    total_demand = sum(_round_value(rows_by_round[idx], "demand_true") for idx in ordered_rounds)
    total_sales = sum(sum(row.realized_sales for row in rows_by_round[idx]) for idx in ordered_rounds)
    total_profit = sum(row.profit for row in rows)

    overview = {
        "totalDemand": total_demand,
        "totalSales": total_sales,
        "fulfillmentRatio": _safe_ratio(total_sales, total_demand),
        "avgPrice": mean(price_series) if price_series else 0.0,
        "totalProfit": total_profit,
        "transferVolume": sum(transfer_series),
        "shockRounds": sum(1 for value in shock_series if abs(value) >= 0.5),
        "avgDemandGap": mean(abs(item["demandGap"]) for item in rounds_payload),
        "rounds": rounds_count,
    }

    return {
        "meta": {
            "seed": rows[0].seed,
            "strategy": resolved_strategy,
            "rounds": rounds_count,
            "agents": ordered_agents,
            "title": "PJ-AG4 Strategy Sandbox",
        },
        "overview": overview,
        "market": {
            "rounds": ordered_rounds,
            "demand": demand_series,
            "sales": sales_series,
            "avgPrice": price_series,
            "shock": shock_series,
            "transferVolume": transfer_series,
        },
        "agents": agents_payload,
        "roundsData": rounds_payload,
        "events": _build_events(rounds_payload),
    }


def create_dashboard(
    rows: Sequence[SettlementRow],
    output_path: Path,
    *,
    config: SimulationConfig | None = None,
    strategy_name: str | None = None,
) -> None:
    payload = build_dashboard_payload(rows, config=config, strategy_name=strategy_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_dashboard_html(payload), encoding="utf-8")


def render_dashboard_html(
    payload: dict[str, Any],
    *,
    body_class: str = "",
    web_runtime_panel: str = "",
) -> str:
    title = escape(payload["meta"]["title"])
    return _dashboard_html(
        title=title,
        payload=payload,
        body_class=body_class,
        web_runtime_panel=web_runtime_panel,
    )


def _dashboard_html(
    *,
    title: str,
    payload: dict[str, Any],
    body_class: str = "",
    web_runtime_panel: str = "",
) -> str:
    payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    template_override = Path(__file__).resolve().parents[2] / "dashboard_template.html"
    if template_override.exists():
        return (
            template_override.read_text(encoding="utf-8")
            .replace("__TITLE__", title)
            .replace("__PAYLOAD__", payload_json)
            .replace("__BODY_CLASS__", body_class)
            .replace("__WEB_RUNTIME_PANEL__", web_runtime_panel)
        )
    return (
        """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>__TITLE__</title>
  <style>
    :root {
      --terminal-bg: #0a100c;
      --terminal-text: #3ddc84;
      --terminal-text-darker: #2a9d62;
      --terminal-glow: rgba(61, 220, 132, 0.25);
      --glitch-color-1: #c7347e;
      --glitch-color-2: #3e8ad6;
      --warning-red: #ff4d4d;
      --warning-red-soft: rgba(255, 77, 77, 0.14);
      --blue-soft: rgba(62, 138, 214, 0.12);
      --green-soft: rgba(61, 220, 132, 0.05);
    }

    @keyframes scanline {
      0% { background-position: 0 0; }
      100% { background-position: 0 100%; }
    }

    @keyframes flicker {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.985; }
    }

    @keyframes blink {
      50% { opacity: 0; }
    }

    * { box-sizing: border-box; }

    html {
      min-height: 100%;
      background: #000;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background: #000;
      font-family: "Fira Code", "Operator Mono", "Courier New", Courier, monospace;
      color: var(--terminal-text);
    }

    .shell {
      width: min(1480px, calc(100vw - 20px));
      height: calc(100vh - 20px);
      margin: 10px auto;
    }

    .slide-container {
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: column;
      position: relative;
      overflow: hidden;
      background: var(--terminal-bg);
      border: 2px solid var(--terminal-text-darker);
      border-radius: 4px;
      box-shadow: 0 0 15px var(--terminal-glow), inset 0 0 80px rgba(0,0,0,0.8);
      animation: flicker 0.2s infinite;
    }

    .slide-container::before {
      content: " ";
      display: block;
      position: absolute;
      inset: 0;
      background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.2) 50%);
      z-index: 10;
      background-size: 100% 3px;
      pointer-events: none;
      animation: scanline 20s linear infinite;
    }

    .slide-header,
    .summary-row,
    .slide-content,
    .slide-footer {
      position: relative;
      z-index: 5;
    }

    .slide-header {
      padding: 16px 28px 12px 28px;
      border-bottom: 1px solid var(--terminal-text-darker);
      text-shadow: 0 0 4px var(--terminal-glow);
    }

    .header-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(280px, 0.72fr);
      gap: 16px;
      align-items: start;
    }

    .page-kicker {
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      color: var(--terminal-text-darker);
      margin-bottom: 10px;
    }

    .slide-title {
      font-size: clamp(1.45rem, 2.4vw, 2.35rem);
      font-weight: 700;
      margin: 0;
      position: relative;
      text-transform: uppercase;
      line-height: 1.08;
    }

    .glitch-effect {
      position: relative;
    }

    .glitch-effect::before,
    .glitch-effect::after {
      content: attr(data-text);
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: var(--terminal-bg);
      overflow: hidden;
    }

    .glitch-effect::before {
      left: 2px;
      text-shadow: -2px 0 var(--glitch-color-1);
      animation: glitch-anim-1 3s infinite linear reverse;
    }

    .glitch-effect::after {
      left: -2px;
      text-shadow: -2px 0 var(--glitch-color-2);
      animation: glitch-anim-2 2.5s infinite linear reverse;
    }

    @keyframes glitch-anim-1 {
      0%, 100% { clip-path: inset(45% 0 56% 0); }
      25% { clip-path: inset(0 0 100% 0); }
      50% { clip-path: inset(80% 0 2% 0); }
      75% { clip-path: inset(40% 0 45% 0); }
    }

    @keyframes glitch-anim-2 {
      0%, 100% { clip-path: inset(65% 0 30% 0); }
      25% { clip-path: inset(20% 0 75% 0); }
      50% { clip-path: inset(90% 0 1% 0); }
      75% { clip-path: inset(10% 0 88% 0); }
    }

    .cursor {
      display: inline-block;
      width: 1rem;
      height: 1.8rem;
      background: var(--terminal-text);
      animation: blink 1.2s steps(1) infinite;
      margin-left: 10px;
      box-shadow: 0 0 5px var(--terminal-glow);
      vertical-align: middle;
    }

    .slide-subtitle {
      margin-top: 8px;
      font-size: 0.88rem;
      line-height: 1.55;
      color: rgba(61, 220, 132, 0.85);
      max-width: 68ch;
    }

    .system-message-box {
      border: 1px dotted var(--terminal-text-darker);
      padding: 10px 12px;
      margin-top: 10px;
      background: rgba(61, 220, 132, 0.05);
      font-size: 0.84rem;
      line-height: 1.5;
    }

    .system-message-box::before {
      content: "[LOG]: ";
      font-weight: bold;
      color: var(--terminal-text-darker);
    }

    .operator-box {
      background: rgba(61, 220, 132, 0.05);
      border: 1px dashed var(--terminal-text-darker);
      padding: 14px;
      position: relative;
      min-width: 0;
    }

    .tagged-box::before {
      content: attr(data-tag);
      position: absolute;
      top: -10px;
      left: 15px;
      background: var(--terminal-bg);
      padding: 0 10px;
      font-size: 0.76rem;
      color: var(--terminal-text-darker);
    }

    .param-line {
      margin-bottom: 6px;
      font-size: 0.82rem;
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 10px;
    }

    .param-label {
      color: var(--terminal-text-darker);
      white-space: nowrap;
      min-width: 82px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .param-value {
      text-align: right;
      word-break: break-word;
      color: #fff;
    }

    .progress-block {
      margin-top: 8px;
    }

    .summary-row {
      padding: 10px 28px 0 28px;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
    }

    .metric-card {
      padding: 8px 10px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      align-items: center;
      gap: 4px 12px;
    }

    .metric-card::before {
      display: none;
    }

    .metric-card .step-tag {
      margin: 0;
    }

    .metric-value {
      display: block;
      margin-top: 0;
      font-size: 1rem;
      line-height: 1.1;
      font-weight: 700;
      color: #fff;
      justify-self: end;
    }

    .metric-copy {
      display: none;
    }

    .metric-card .progress-block {
      grid-column: 1 / -1;
      margin-top: 4px;
    }

    .progress-info {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      font-size: 0.72rem;
      margin-bottom: 6px;
      color: var(--terminal-text-darker);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .progress-bar-container,
    .meter-container,
    .loading-bar-container {
      position: relative;
      overflow: hidden;
      background: rgba(42, 157, 98, 0.2);
      border: 1px solid var(--terminal-text-darker);
    }

    .progress-bar-container,
    .meter-container {
      height: 12px;
      width: 100%;
    }

    .loading-bar-container {
      width: 100%;
      height: 4px;
      margin-top: 10px;
      border-color: rgba(42, 157, 98, 0.35);
    }

    .progress-bar-fill,
    .meter-fill,
    .loading-bar {
      height: 100%;
      background: var(--terminal-text);
      box-shadow: 0 0 10px var(--terminal-glow);
      width: 0%;
    }

    .slide-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 14px;
      padding: 14px 28px 16px 28px;
      min-height: 0;
      overflow: hidden;
    }

    .top-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(340px, 0.9fr);
      gap: 14px;
      min-height: 0;
    }

    .main-column,
    .side-column {
      display: flex;
      flex-direction: column;
      gap: 14px;
      min-width: 0;
      min-height: 0;
    }

    .comparison-card {
      border: 1px solid var(--terminal-text-darker);
      padding: 12px 14px;
      background: rgba(61, 220, 132, 0.03);
      position: relative;
      min-width: 0;
    }

    .comparison-card::before {
      content: attr(data-tag);
      position: absolute;
      top: -10px;
      left: 12px;
      background: var(--terminal-bg);
      padding: 0 10px;
      font-size: 0.72rem;
      color: var(--terminal-text-darker);
      letter-spacing: 0.08em;
    }

    .comparison-card.warning-mode {
      border-color: var(--glitch-color-1);
      background: rgba(199, 52, 126, 0.05);
      box-shadow: inset 0 0 30px rgba(199, 52, 126, 0.18);
    }

    .comparison-card.info-mode {
      border-color: var(--glitch-color-2);
      background: rgba(62, 138, 214, 0.05);
      box-shadow: inset 0 0 22px rgba(62, 138, 214, 0.12);
    }

    .comparison-card.stable-mode {
      border-color: var(--terminal-text-darker);
    }

    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
      flex-wrap: wrap;
    }

    .step-tag {
      font-size: 0.72rem;
      color: var(--terminal-text-darker);
      text-transform: uppercase;
      margin-bottom: 2px;
      display: block;
      letter-spacing: 0.1em;
    }

    .panel-title {
      font-size: 1.06rem;
      margin: 0;
      line-height: 1.25;
      font-weight: 600;
    }

    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
    }

    .status-tag {
      display: inline-block;
      padding: 2px 6px;
      font-size: 0.68rem;
      border: 1px solid currentColor;
      vertical-align: middle;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      background: transparent;
      line-height: 1.45;
    }

    .status-positive {
      color: var(--terminal-text);
      border-color: var(--terminal-text);
      background: rgba(61, 220, 132, 0.1);
    }

    .status-neutral {
      color: var(--terminal-text-darker);
      border-color: var(--terminal-text-darker);
    }

    .status-blue {
      color: var(--glitch-color-2);
      border-color: var(--glitch-color-2);
      background: rgba(62, 138, 214, 0.08);
    }

    .status-danger {
      color: var(--glitch-color-1);
      border-color: var(--glitch-color-1);
      background: rgba(199, 52, 126, 0.08);
    }

    .chart-shell {
      margin-top: 10px;
      height: 190px;
      border: 1px solid rgba(42, 157, 98, 0.45);
      background: rgba(0,0,0,0.16);
      position: relative;
    }

    svg {
      width: 100%;
      height: 100%;
      display: block;
      overflow: visible;
    }

    .control-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px 14px;
      margin-top: 10px;
    }

    .control-block {
      border-left: 2px solid var(--terminal-text-darker);
      padding-left: 10px;
      min-width: 0;
    }

    .control-label {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 8px;
      font-size: 0.72rem;
      color: var(--terminal-text-darker);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .control-value {
      color: #fff;
    }

    .terminal-select,
    .terminal-button {
      width: 100%;
      background: var(--terminal-bg);
      color: var(--terminal-text);
      border: 1px solid var(--terminal-text-darker);
      border-radius: 0;
      outline: none;
      font-family: inherit;
    }

    .terminal-select {
      padding: 8px 10px;
      appearance: none;
    }

    .terminal-select:focus,
    .terminal-button:focus,
    input[type="range"]:focus {
      outline: 1px solid var(--terminal-text);
      outline-offset: 2px;
    }

    .terminal-button {
      padding: 7px 10px;
      cursor: pointer;
      box-shadow: 4px 4px 0px var(--terminal-text-darker);
      text-transform: uppercase;
      font-size: 0.72rem;
      font-weight: bold;
      transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease, color 0.18s ease, border-color 0.18s ease;
    }

    .terminal-button:hover {
      transform: translate(-1px, -1px);
    }

    .terminal-button.active {
      background: var(--terminal-text);
      color: var(--terminal-bg);
      border-color: var(--terminal-text);
      box-shadow: 0 0 15px var(--terminal-glow);
    }

    .control-actions {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin-top: 12px;
    }

    input[type="range"] {
      width: 100%;
      height: 18px;
      margin: 0;
      padding: 0;
      border: 1px solid var(--terminal-text-darker);
      background: transparent;
      accent-color: var(--terminal-text);
      appearance: none;
      -webkit-appearance: none;
      --slider-fill: var(--terminal-text);
      --slider-block-a: var(--terminal-text-darker);
      --slider-block-b: rgba(42, 157, 98, 0.22);
    }

    input[type="range"]::-webkit-slider-runnable-track {
      height: 16px;
      border: none;
      background:
        repeating-linear-gradient(
          90deg,
          var(--slider-block-a) 0 12px,
          var(--slider-block-b) 12px 16px
        );
    }

    input[type="range"]::-moz-range-track {
      height: 16px;
      border: none;
      background:
        repeating-linear-gradient(
          90deg,
          var(--slider-block-a) 0 12px,
          var(--slider-block-b) 12px 16px
        );
    }

    input[type="range"]::-webkit-slider-thumb {
      -webkit-appearance: none;
      appearance: none;
      width: 12px;
      height: 18px;
      margin-top: -1px;
      border: 1px solid var(--slider-fill);
      background: var(--terminal-bg);
      box-shadow: 3px 3px 0px var(--slider-fill);
    }

    input[type="range"]::-moz-range-thumb {
      width: 12px;
      height: 18px;
      border: 1px solid var(--slider-fill);
      border-radius: 0;
      background: var(--terminal-bg);
      box-shadow: 3px 3px 0px var(--slider-fill);
    }

    input.slider-round {
      --slider-fill: var(--terminal-text);
      --slider-block-a: var(--terminal-text);
      --slider-block-b: rgba(42, 157, 98, 0.22);
    }

    input.slider-shock {
      --slider-fill: var(--glitch-color-1);
      --slider-block-a: var(--glitch-color-1);
      --slider-block-b: var(--glitch-color-2);
    }

    input.slider-bias {
      --slider-fill: var(--glitch-color-2);
      --slider-block-a: var(--terminal-text-darker);
      --slider-block-b: var(--glitch-color-2);
    }

    .focus-params {
      margin-top: 10px;
      border-left: 3px solid var(--terminal-text-darker);
      padding-left: 12px;
    }

    .focus-card .param-line {
      margin-bottom: 6px;
    }

    .focus-copy {
      margin-top: 10px;
      font-size: 0.86rem;
      line-height: 1.45;
      color: rgba(61, 220, 132, 0.9);
    }

    .focus-log,
    .event-log {
      margin-top: 12px;
      max-height: none;
      overflow: hidden;
      padding-right: 0;
    }

    .log-section {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .log-entry {
      border-left: 3px solid var(--terminal-text-darker);
      padding-left: 12px;
      position: relative;
      transition: transform 0.18s ease, border-color 0.18s ease;
    }

    .log-entry.clickable {
      cursor: pointer;
    }

    .log-entry.clickable:hover {
      transform: translateX(2px);
    }

    .log-label {
      font-size: 0.72rem;
      color: var(--terminal-text-darker);
      text-transform: uppercase;
      margin-bottom: 5px;
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
      letter-spacing: 0.06em;
    }

    .log-body {
      font-size: 0.88rem;
      line-height: 1.42;
      margin: 0;
      word-break: break-word;
    }

    .muted-copy {
      display: block;
      margin-top: 4px;
      color: var(--terminal-text-darker);
      font-size: 0.78rem;
      line-height: 1.34;
    }

    .agent-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }

    .agent-card {
      cursor: pointer;
      transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
      border-left: 4px solid var(--agent-color, var(--terminal-text-darker));
    }

    .agent-card:hover {
      transform: translateY(-2px);
    }

    .agent-card.active {
      box-shadow: 0 0 15px rgba(61, 220, 132, 0.18);
    }

    .flow-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 10px 0 8px;
    }

    .flow-node {
      border: 1px solid currentColor;
      padding: 4px 8px;
      text-align: center;
      min-width: 68px;
      font-size: 0.72rem;
      background: rgba(0,0,0,0.25);
      line-height: 1.4;
    }

    .agent-copy {
      margin-top: 8px;
      font-size: 0.8rem;
      line-height: 1.4;
      color: rgba(61, 220, 132, 0.88);
    }

    .agent-params {
      margin-top: 8px;
      border-left: 3px solid rgba(42, 157, 98, 0.7);
      padding-left: 10px;
    }

    .agent-params .param-line {
      margin-bottom: 4px;
      font-size: 0.74rem;
    }

    .slide-footer {
      padding: 8px 18px;
      background: var(--terminal-text-darker);
      color: var(--terminal-bg);
      font-size: 0.72rem;
      font-weight: bold;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 6px 10px;
      text-shadow: none;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    .empty-log {
      color: var(--terminal-text-darker);
      font-size: 0.78rem;
      line-height: 1.4;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    @media (max-width: 1220px) {
      .header-grid,
      .top-grid {
        grid-template-columns: 1fr;
      }
      .summary-row {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }

    @media (max-width: 900px) {
      .agent-grid {
        grid-template-columns: 1fr;
      }
      .summary-row {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 760px) {
      .shell {
        width: min(calc(100vw - 12px), 1480px);
        margin: 6px auto;
        height: calc(100vh - 12px);
      }

      .slide-container {
        height: 100%;
      }

      .slide-header,
      .summary-row,
      .slide-content {
        padding-left: 18px;
        padding-right: 18px;
      }

      .control-grid,
      .control-actions {
        grid-template-columns: 1fr;
      }

      .slide-footer {
        justify-content: flex-start;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <div class="slide-container">
      <header class="slide-header">
        <div class="header-grid">
          <div class="title-block">
            <div class="page-kicker">PJ-AG4 / Strategy Dashboard</div>
            <h1 class="slide-title glitch-effect" data-text="GPU market sandbox">GPU market sandbox<span class="cursor"></span></h1>
            <p class="slide-subtitle">Market decisions, trend reading, event diagnostics, and sandbox controls on one terminal board.</p>
            <div class="system-message-box" id="focus-command">&gt; focus --round R0 --metric cumProfit --agent all</div>
          </div>

          <aside class="operator-box tagged-box" data-tag="[RUN_META]">
            <div class="param-line"><span class="param-label">Mode</span><span class="param-value" id="hero-strategy">heuristic</span></div>
            <div class="param-line"><span class="param-label">Seed</span><span class="param-value" id="hero-seed">7</span></div>
            <div class="param-line"><span class="param-label">Rounds</span><span class="param-value" id="hero-rounds">30</span></div>
            <div class="param-line"><span class="param-label">Agents</span><span class="param-value" id="hero-agents">3</span></div>
          </aside>
        </div>
      </header>

      <section class="summary-row">
        <article class="comparison-card metric-card stable-mode" data-tag="[MARKET_PNL]">
          <span class="step-tag">Cumulative market payoff</span>
          <strong class="metric-value" id="kpi-profit">+0.0</strong>
          <p class="metric-copy">Net payoff after production, transfers, holding cost, and SLA penalties.</p>
        </article>

        <article class="comparison-card metric-card stable-mode" data-tag="[FULFILLMENT]">
          <span class="step-tag">Delivered vs true demand</span>
          <strong class="metric-value" id="kpi-fulfillment">0%</strong>
          <div class="progress-block">
            <div class="progress-bar-container">
              <div class="progress-bar-fill" id="kpi-fulfillment-bar"></div>
            </div>
          </div>
        </article>

        <article class="comparison-card metric-card stable-mode" data-tag="[AVG_PRICE]">
          <span class="step-tag">Mean clearing price</span>
          <strong class="metric-value" id="kpi-price">0.00</strong>
          <p class="metric-copy">Use it to read premium harvest versus share-grab posture.</p>
        </article>

        <article class="comparison-card metric-card stable-mode" data-tag="[TRANSFER_VOL]">
          <span class="step-tag">Emergency volume shifted</span>
          <strong class="metric-value" id="kpi-transfer">0.0</strong>
          <p class="metric-copy">Cross-agent support activated during service pressure.</p>
        </article>
      </section>

      <main class="slide-content">
        <div class="top-grid">
          <div class="main-column">
            <article class="comparison-card stable-mode" data-tag="[MARKET_LAYER]">
              <div class="panel-header">
                <div>
                  <span class="step-tag">Market telemetry</span>
                  <h2 class="panel-title">Demand / sales / projected shock trace</h2>
                </div>
                <div class="legend">
                  <span class="status-tag status-positive">Demand</span>
                  <span class="status-tag status-neutral">Sales</span>
                  <span class="status-tag status-blue">Projection</span>
                </div>
              </div>
              <div class="system-message-box" id="market-readout">&gt; awaiting market trace</div>
              <div class="chart-shell">
                <svg id="market-chart" role="img" aria-label="Market chart"></svg>
              </div>
            </article>

            <article class="comparison-card stable-mode" data-tag="[AGENT_LAYER]">
              <div class="panel-header">
                <div>
                  <span class="step-tag">Agent telemetry</span>
                  <h2 class="panel-title" id="agent-chart-title">Agent metric / cumulative profit</h2>
                </div>
                <div class="legend" id="agent-legend"></div>
              </div>
              <div class="system-message-box" id="agent-readout">&gt; awaiting agent trace</div>
              <div class="chart-shell">
                <svg id="agent-chart" role="img" aria-label="Agent chart"></svg>
              </div>
            </article>
          </div>

          <aside class="side-column">
            <article class="comparison-card stable-mode" data-tag="[CONTROL_SURFACE]">
              <div class="panel-header">
                <div>
                  <span class="step-tag">Scenario rail</span>
                  <h2 class="panel-title">Simulation controls</h2>
                </div>
                <span class="status-tag status-neutral">Projection only</span>
              </div>

              <div class="control-grid">
                <div class="control-block">
                  <label class="control-label" for="round-slider"><span>Round focus</span><span class="control-value" id="round-slider-value">R0</span></label>
                  <input id="round-slider" class="slider-round" type="range" min="0" max="0" step="1" value="0" />
                </div>

                <div class="control-block">
                  <label class="control-label" for="agent-select"><span>Agent focus</span><span class="control-value" id="agent-select-value">all</span></label>
                  <select id="agent-select" class="terminal-select"></select>
                </div>

                <div class="control-block">
                  <label class="control-label" for="metric-select"><span>Agent metric</span><span class="control-value" id="metric-select-value">cumProfit</span></label>
                  <select id="metric-select" class="terminal-select">
                    <option value="cumProfit">Cumulative profit</option>
                    <option value="profit">Round profit</option>
                    <option value="reputation">Reputation</option>
                    <option value="serviceRate">Service rate</option>
                    <option value="price">Price</option>
                    <option value="quantity">Quantity</option>
                  </select>
                </div>

                <div class="control-block">
                  <label class="control-label" for="shock-scale"><span>Shock scale</span><span class="control-value" id="shock-scale-value">0.0x</span></label>
                  <input id="shock-scale" class="slider-shock" type="range" min="-2" max="2" step="0.1" value="0" />
                </div>

                <div class="control-block">
                  <label class="control-label" for="demand-bias"><span>Demand bias</span><span class="control-value" id="demand-bias-value">+0</span></label>
                  <input id="demand-bias" class="slider-bias" type="range" min="-40" max="40" step="1" value="0" />
                </div>
              </div>

              <div class="control-actions">
                <button type="button" class="terminal-button active" data-toggle="shocks">Shocks</button>
                <button type="button" class="terminal-button active" data-toggle="defaults">Defaults</button>
                <button type="button" class="terminal-button active" data-toggle="dumps">Dumps</button>
                <button type="button" class="terminal-button active" data-toggle="transfers">Transfers</button>
              </div>
            </article>

            <article class="comparison-card stable-mode focus-card" id="focus-panel" data-tag="[ROUND_INSPECTOR]">
              <div class="panel-header">
                <div>
                  <span class="step-tag">Focused round</span>
                  <h2 class="panel-title" id="focus-round-label">R0</h2>
                </div>
                <span class="status-tag status-neutral" id="detail-regime-tag">Stable</span>
              </div>

              <p class="focus-copy" id="focus-round-copy">Demand and execution details for the selected round.</p>

              <div class="focus-params">
                <div class="param-line"><span class="param-label">Regime</span><span class="param-value" id="detail-regime">Controlled market</span></div>
                <div class="param-line"><span class="param-label">Spread</span><span class="param-value" id="detail-spread">0.00</span></div>
                <div class="param-line"><span class="param-label">Demand gap</span><span class="param-value" id="detail-gap">0.0</span></div>
                <div class="param-line"><span class="param-label">Shock</span><span class="param-value" id="detail-shock">0.0</span></div>
                <div class="param-line"><span class="param-label">Transfer</span><span class="param-value" id="detail-transfer">0.0</span></div>
              </div>

              <div class="progress-block">
                <div class="progress-info">
                  <span>Round fulfillment</span>
                  <span id="detail-fulfillment">0%</span>
                </div>
                <div class="progress-bar-container">
                  <div class="progress-bar-fill" id="detail-fulfillment-bar"></div>
                </div>
              </div>

              <div class="log-section focus-log" id="round-agent-log"></div>
            </article>

            <article class="comparison-card stable-mode" data-tag="[EVENT_TAPE]">
              <div class="panel-header">
                <div>
                  <span class="step-tag">Event stream</span>
                  <h2 class="panel-title">Highest-impact moments</h2>
                </div>
              </div>
              <div class="log-section event-log" id="event-list"></div>
            </article>
          </aside>
        </div>

        <section class="agent-grid" id="agent-grid"></section>
      </main>

      <footer class="slide-footer" id="footer-bar">
        <span id="footer-node">NODE: R0</span>
        <span id="footer-total">TOTAL: 0</span>
        <span id="footer-status">STATUS: STABLE</span>
        <span id="footer-agent">AGENT: ALL</span>
        <span id="footer-metric">METRIC: CUMPROFIT</span>
      </footer>
    </div>
  </div>

  <script id="dashboard-data" type="application/json">__PAYLOAD__</script>
  <script>
    const data = JSON.parse(document.getElementById("dashboard-data").textContent);
    const toggles = { shocks: true, defaults: true, dumps: true, transfers: true };
    const state = { roundIndex: 0, metric: "cumProfit", agent: "all", shockScale: 0, demandBias: 0 };
    const agentMeta = Object.fromEntries(data.agents.map((agent) => [agent.name, agent]));

    const controls = {
      roundSlider: document.getElementById("round-slider"),
      roundSliderValue: document.getElementById("round-slider-value"),
      metricSelect: document.getElementById("metric-select"),
      metricSelectValue: document.getElementById("metric-select-value"),
      agentSelect: document.getElementById("agent-select"),
      agentSelectValue: document.getElementById("agent-select-value"),
      shockScale: document.getElementById("shock-scale"),
      shockScaleValue: document.getElementById("shock-scale-value"),
      demandBias: document.getElementById("demand-bias"),
      demandBiasValue: document.getElementById("demand-bias-value"),
      marketChart: document.getElementById("market-chart"),
      marketReadout: document.getElementById("market-readout"),
      agentChart: document.getElementById("agent-chart"),
      agentChartTitle: document.getElementById("agent-chart-title"),
      agentReadout: document.getElementById("agent-readout"),
      agentLegend: document.getElementById("agent-legend"),
      eventList: document.getElementById("event-list"),
      agentGrid: document.getElementById("agent-grid"),
      roundAgentLog: document.getElementById("round-agent-log"),
      focusPanel: document.getElementById("focus-panel"),
      focusCommand: document.getElementById("focus-command"),
      footerBar: document.getElementById("footer-bar"),
    };

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll("\"", "&quot;")
        .replaceAll("'", "&#39;");
    }

    function formatNumber(value, digits = 1) {
      return Number(value).toLocaleString(undefined, {
        maximumFractionDigits: digits,
        minimumFractionDigits: digits,
      });
    }

    function formatMoney(value) {
      const prefix = Number(value) >= 0 ? "+" : "-";
      return prefix + Math.abs(Number(value)).toLocaleString(undefined, {
        maximumFractionDigits: 1,
        minimumFractionDigits: 1,
      });
    }

    function formatPercent(value) {
      return (Number(value) * 100).toFixed(1) + "%";
    }

    function formatMetricValue(metric, value) {
      if (metric === "cumProfit" || metric === "profit") {
        return formatMoney(value);
      }
      if (metric === "serviceRate" || metric === "reputation") {
        return formatPercent(value);
      }
      if (metric === "quantity") {
        return formatNumber(value, 0);
      }
      if (metric === "price") {
        return formatNumber(value, 2);
      }
      return formatNumber(value, 1);
    }

    function metricLabel(metric) {
      return {
        cumProfit: "cumulative profit",
        profit: "round profit",
        reputation: "reputation",
        serviceRate: "service rate",
        price: "price",
        quantity: "quantity",
      }[metric] || metric;
    }

    function formatActionText(actionText) {
      if (!actionText) {
        return "hold";
      }
      return actionText
        .replaceAll("forecast", "fcst")
        .replaceAll("quantity", "qty")
        .replaceAll("price", "px")
        .replaceAll(";", "  |  ");
    }

    function tagText(value) {
      return "[" + String(value).toUpperCase().replaceAll(" ", "_") + "]";
    }

    function currentRound() {
      return data.roundsData[state.roundIndex] || data.roundsData[0];
    }

    function projectedDemandSeries() {
      return data.market.demand.map((value, index) => {
        return Math.max(0, value + (data.market.shock[index] || 0) * state.shockScale + state.demandBias);
      });
    }

    function seriesRange(values, floorZero = false) {
      if (!values.length) {
        return { min: 0, max: 1 };
      }
      let min = Math.min(...values);
      let max = Math.max(...values);
      if (floorZero) {
        min = Math.min(0, min);
      }
      if (max === min) {
        const pad = Math.max(1, Math.abs(max) * 0.1);
        return { min: min - pad, max: max + pad };
      }
      const pad = (max - min) * 0.08;
      return { min: min - pad, max: max + pad };
    }

    function xStepFor(length, width, padding) {
      return length <= 1 ? 0 : (width - padding * 2) / (length - 1);
    }

    function createScale(min, max, height, padding) {
      return (value) => {
        if (max === min) {
          return height / 2;
        }
        return height - padding - ((value - min) / (max - min)) * (height - padding * 2);
      };
    }

    function buildPoints(values, width, height, padding, scaleY) {
      const step = xStepFor(values.length, width, padding);
      return values.map((value, index) => ({
        x: padding + step * index,
        y: scaleY(value),
        value,
      }));
    }

    function buildPath(points) {
      return points.map((point, index) => {
        const op = index === 0 ? "M" : "L";
        return op + point.x.toFixed(2) + "," + point.y.toFixed(2);
      }).join(" ");
    }

    function axisDigits(min, max) {
      const extent = Math.max(Math.abs(min), Math.abs(max));
      if (extent >= 100) return 0;
      if (extent >= 10) return 1;
      return 2;
    }

    function buildGrid(width, height, padding, columns, rows) {
      const xStep = xStepFor(columns, width, padding);
      const vertical = Array.from({ length: columns }, (_, index) => {
        const x = padding + xStep * index;
        return '<line x1="' + x.toFixed(2) + '" y1="' + padding + '" x2="' + x.toFixed(2) + '" y2="' + (height - padding).toFixed(2) + '" stroke="rgba(42,157,98,0.16)" stroke-dasharray="2 8"></line>';
      }).join("");
      const horizontal = Array.from({ length: rows }, (_, index) => {
        const y = rows <= 1 ? height / 2 : padding + ((height - padding * 2) / (rows - 1)) * index;
        return '<line x1="' + padding + '" y1="' + y.toFixed(2) + '" x2="' + (width - padding).toFixed(2) + '" y2="' + y.toFixed(2) + '" stroke="rgba(42,157,98,0.14)" stroke-dasharray="4 8"></line>';
      }).join("");
      return '<rect x="' + padding + '" y="' + padding + '" width="' + (width - padding * 2) + '" height="' + (height - padding * 2) + '" fill="none" stroke="rgba(42,157,98,0.35)"></rect>' + vertical + horizontal;
    }

    function buildRoundLabels(rounds, width, height, padding) {
      const every = Math.max(1, Math.ceil(rounds.length / 8));
      const step = xStepFor(rounds.length, width, padding);
      return rounds.map((round, index) => {
        if (index % every !== 0 && index !== rounds.length - 1) {
          return "";
        }
        const x = padding + step * index;
        return '<text x="' + x.toFixed(2) + '" y="' + (height - 8).toFixed(2) + '" fill="rgba(42,157,98,0.9)" font-family="Fira Code, monospace" font-size="10" text-anchor="middle">R' + round + "</text>";
      }).join("");
    }

    function buildYAxis(min, max, height, padding) {
      const digits = axisDigits(min, max);
      const rows = 5;
      return Array.from({ length: rows }, (_, index) => {
        const ratio = rows <= 1 ? 0 : index / (rows - 1);
        const value = max - (max - min) * ratio;
        const y = padding + ((height - padding * 2) * ratio);
        return '<text x="' + (padding - 8) + '" y="' + (y + 3).toFixed(2) + '" fill="rgba(42,157,98,0.9)" font-family="Fira Code, monospace" font-size="10" text-anchor="end">' + formatNumber(value, digits) + "</text>";
      }).join("");
    }

    function toneForRound(round) {
      if (round.defaultCount > 0) {
        return {
          label: "SYSTEM_OVERRIDE",
          tagClass: "status-danger",
          panelClass: "warning-mode",
          lineColor: "#c7347e",
          footerBg: "#c7347e",
          footerColor: "#fff",
        };
      }
      if (round.dumpCount > 0) {
        return {
          label: "PRICE_WAR",
          tagClass: "status-blue",
          panelClass: "info-mode",
          lineColor: "#3e8ad6",
          footerBg: "#3e8ad6",
          footerColor: "#fff",
        };
      }
      if (Math.abs(round.shockComponent) >= 0.5) {
        return {
          label: "SHOCK_ACTIVE",
          tagClass: "status-positive",
          panelClass: "stable-mode",
          lineColor: "#3ddc84",
          footerBg: "#2a9d62",
          footerColor: "#0a100c",
        };
      }
      if (round.transferVolume > 0) {
        return {
          label: "TRANSFER_SYNC",
          tagClass: "status-blue",
          panelClass: "info-mode",
          lineColor: "#3e8ad6",
          footerBg: "#2a9d62",
          footerColor: "#0a100c",
        };
      }
      return {
        label: "STABLE",
        tagClass: "status-neutral",
        panelClass: "stable-mode",
        lineColor: "#2a9d62",
        footerBg: "#2a9d62",
        footerColor: "#0a100c",
      };
    }

    function toneForEvent(event) {
      if (event.tags.includes("default")) {
        return { tagClass: "status-danger", lineColor: "#c7347e", panelClass: "warning-mode" };
      }
      if (event.tags.includes("dump")) {
        return { tagClass: "status-blue", lineColor: "#3e8ad6", panelClass: "info-mode" };
      }
      if (event.tags.includes("shock")) {
        return { tagClass: "status-positive", lineColor: "#3ddc84", panelClass: "stable-mode" };
      }
      return { tagClass: "status-neutral", lineColor: "#2a9d62", panelClass: "stable-mode" };
    }

    function toneForAgent(agent) {
      if (agent.defaultFlag) {
        return { label: "DEFAULT", tagClass: "status-danger" };
      }
      if (agent.dumpFlag) {
        return { label: "DUMP", tagClass: "status-blue" };
      }
      if (agent.transferIn > 0 || agent.transferOut > 0) {
        return { label: "TRANSFER", tagClass: "status-blue" };
      }
      return { label: "STABLE", tagClass: "status-neutral" };
    }

    function serviceTagClass(rate) {
      if (rate < 0.9) return "status-danger";
      if (rate < 0.98) return "status-blue";
      return "status-positive";
    }

    function syncControls() {
      const round = currentRound();
      controls.roundSlider.value = String(state.roundIndex);
      controls.metricSelect.value = state.metric;
      controls.agentSelect.value = state.agent;
      controls.roundSliderValue.textContent = "R" + round.round;
      controls.metricSelectValue.textContent = state.metric;
      controls.agentSelectValue.textContent = state.agent;
      controls.shockScaleValue.textContent = state.shockScale.toFixed(1) + "x";
      controls.demandBiasValue.textContent = (state.demandBias >= 0 ? "+" : "") + state.demandBias;
      controls.focusCommand.textContent = "> focus --round R" + round.round + " --metric " + state.metric + " --agent " + state.agent;
    }

    function setOverview() {
      document.getElementById("hero-strategy").textContent = data.meta.strategy;
      document.getElementById("hero-seed").textContent = data.meta.seed;
      document.getElementById("hero-rounds").textContent = data.meta.rounds;
      document.getElementById("hero-agents").textContent = data.meta.agents.length;
      document.getElementById("kpi-profit").textContent = formatMoney(data.overview.totalProfit);
      document.getElementById("kpi-fulfillment").textContent = formatPercent(data.overview.fulfillmentRatio);
      document.getElementById("kpi-fulfillment-bar").style.width = Math.max(2, data.overview.fulfillmentRatio * 100) + "%";
      document.getElementById("kpi-price").textContent = formatNumber(data.overview.avgPrice, 2);
      document.getElementById("kpi-transfer").textContent = formatNumber(data.overview.transferVolume, 1);
    }

    function buildAgentOptions() {
      controls.agentSelect.innerHTML = "";
      [{ value: "all", label: "All agents" }]
        .concat(data.agents.map((agent) => ({ value: agent.name, label: agent.name })))
        .forEach((option) => {
          const node = document.createElement("option");
          node.value = option.value;
          node.textContent = option.label;
          controls.agentSelect.appendChild(node);
        });
    }

    function setupControls() {
      controls.roundSlider.max = Math.max(0, data.meta.rounds - 1);
      controls.metricSelect.value = state.metric;
      controls.agentSelect.value = state.agent;

      controls.roundSlider.addEventListener("input", () => {
        state.roundIndex = Number(controls.roundSlider.value);
        render();
      });

      controls.metricSelect.addEventListener("change", () => {
        state.metric = controls.metricSelect.value;
        render();
      });

      controls.agentSelect.addEventListener("change", () => {
        state.agent = controls.agentSelect.value;
        render();
      });

      controls.shockScale.addEventListener("input", () => {
        state.shockScale = Number(controls.shockScale.value);
        render();
      });

      controls.demandBias.addEventListener("input", () => {
        state.demandBias = Number(controls.demandBias.value);
        render();
      });

      document.querySelectorAll("[data-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
          const key = button.dataset.toggle;
          toggles[key] = !toggles[key];
          button.classList.toggle("active", toggles[key]);
          render();
        });
      });

      window.addEventListener("keydown", (event) => {
        if (event.target instanceof HTMLElement) {
          const tagName = event.target.tagName;
          if (tagName === "INPUT" || tagName === "SELECT" || event.target.isContentEditable) {
            return;
          }
        }

        if (event.key === "ArrowLeft" && state.roundIndex > 0) {
          state.roundIndex -= 1;
          render();
        }

        if (event.key === "ArrowRight" && state.roundIndex < data.meta.rounds - 1) {
          state.roundIndex += 1;
          render();
        }
      });
    }

    function activeAgents() {
      return state.agent === "all" ? data.agents : data.agents.filter((agent) => agent.name === state.agent);
    }

    function renderMarketChart() {
      const width = 860;
      const height = 240;
      const padding = 28;
      const demand = data.market.demand;
      const sales = data.market.sales;
      const projected = projectedDemandSeries();
      const range = seriesRange(demand.concat(sales, projected), true);
      const scaleY = createScale(range.min, range.max, height, padding);
      const demandPoints = buildPoints(demand, width, height, padding, scaleY);
      const salesPoints = buildPoints(sales, width, height, padding, scaleY);
      const projectedPoints = buildPoints(projected, width, height, padding, scaleY);
      const selectedRound = currentRound();
      const selectedDemand = demandPoints[state.roundIndex];
      const selectedSales = salesPoints[state.roundIndex];
      const selectedProjected = projectedPoints[state.roundIndex];

      const overlays = data.roundsData.map((round, index) => {
        if (!demandPoints[index]) return "";
        const x = demandPoints[index].x;
        let markup = "";
        if (toggles.shocks && Math.abs(round.shockComponent) >= 0.5) {
          markup += '<line x1="' + x.toFixed(2) + '" y1="' + (padding + 4) + '" x2="' + x.toFixed(2) + '" y2="' + (height - padding).toFixed(2) + '" stroke="#3ddc84" stroke-opacity="0.35" stroke-dasharray="3 7"></line>';
          markup += '<rect x="' + (x - 4).toFixed(2) + '" y="' + (padding + 6) + '" width="8" height="8" fill="#3ddc84"></rect>';
        }
        if (toggles.defaults && round.defaultCount > 0) {
          markup += '<rect x="' + (x - 4).toFixed(2) + '" y="' + (padding + 20) + '" width="8" height="8" fill="#c7347e"></rect>';
        }
        if (toggles.dumps && round.dumpCount > 0) {
          markup += '<rect x="' + (x - 4).toFixed(2) + '" y="' + (padding + 34) + '" width="8" height="8" fill="#3e8ad6"></rect>';
        }
        if (toggles.transfers && round.transferVolume > 0) {
          markup += '<rect x="' + (x - 4).toFixed(2) + '" y="' + (padding + 48) + '" width="8" height="8" fill="#fff"></rect>';
        }
        return markup;
      }).join("");

      controls.marketChart.innerHTML =
        buildGrid(width, height, padding, Math.max(demand.length, 2), 5)
        + buildYAxis(range.min, range.max, height, padding)
        + overlays
        + '<path d="' + buildPath(demandPoints) + '" fill="none" stroke="#3ddc84" stroke-width="2"></path>'
        + '<path d="' + buildPath(salesPoints) + '" fill="none" stroke="#fff" stroke-width="1.7"></path>'
        + '<path d="' + buildPath(projectedPoints) + '" fill="none" stroke="#3e8ad6" stroke-width="1.7" stroke-dasharray="5 5"></path>'
        + '<line x1="' + selectedDemand.x.toFixed(2) + '" y1="' + padding + '" x2="' + selectedDemand.x.toFixed(2) + '" y2="' + (height - padding).toFixed(2) + '" stroke="rgba(255,255,255,0.35)" stroke-width="1.1"></line>'
        + '<rect x="' + (selectedDemand.x - 4).toFixed(2) + '" y="' + (selectedDemand.y - 4).toFixed(2) + '" width="8" height="8" fill="#0a100c" stroke="#3ddc84" stroke-width="2"></rect>'
        + '<rect x="' + (selectedSales.x - 4).toFixed(2) + '" y="' + (selectedSales.y - 4).toFixed(2) + '" width="8" height="8" fill="#0a100c" stroke="#fff" stroke-width="2"></rect>'
        + '<rect x="' + (selectedProjected.x - 4).toFixed(2) + '" y="' + (selectedProjected.y - 4).toFixed(2) + '" width="8" height="8" fill="#0a100c" stroke="#3e8ad6" stroke-width="2"></rect>'
        + buildRoundLabels(data.market.rounds, width, height, padding);

      controls.marketReadout.textContent =
        "> R" + selectedRound.round
        + " | demand " + formatNumber(selectedRound.demandTrue, 0)
        + " | sales " + formatNumber(selectedRound.marketTotalSales, 0)
        + " | projected " + formatNumber(projected[state.roundIndex], 0)
        + " | shock " + formatNumber(selectedRound.shockComponent, 1);
    }

    function renderAgentChart() {
      const visible = activeAgents();
      const width = 860;
      const height = 240;
      const padding = 28;
      const seriesCollection = visible.map((agent) => ({
        name: agent.name,
        color: agent.color,
        values: agent.series[state.metric],
      }));
      const allValues = seriesCollection.flatMap((series) => series.values);
      const range = seriesRange(allValues, state.metric === "cumProfit" || state.metric === "profit");
      const scaleY = createScale(range.min, range.max, height, padding);
      const markerX = padding + xStepFor(data.market.rounds.length, width, padding) * state.roundIndex;

      const paths = seriesCollection.map((series) => {
        const points = buildPoints(series.values, width, height, padding, scaleY);
        const selected = points[state.roundIndex];
        return (
          '<path d="' + buildPath(points) + '" fill="none" stroke="' + series.color + '" stroke-width="2"></path>'
          + '<rect x="' + (selected.x - 4).toFixed(2) + '" y="' + (selected.y - 4).toFixed(2) + '" width="8" height="8" fill="#0a100c" stroke="' + series.color + '" stroke-width="2"></rect>'
        );
      }).join("");

      controls.agentChart.innerHTML =
        buildGrid(width, height, padding, Math.max(data.market.rounds.length, 2), 5)
        + buildYAxis(range.min, range.max, height, padding)
        + paths
        + '<line x1="' + markerX.toFixed(2) + '" y1="' + padding + '" x2="' + markerX.toFixed(2) + '" y2="' + (height - padding).toFixed(2) + '" stroke="rgba(255,255,255,0.35)" stroke-width="1.1"></line>'
        + buildRoundLabels(data.market.rounds, width, height, padding);

      controls.agentChartTitle.textContent = "Agent metric / " + metricLabel(state.metric);
      controls.agentLegend.innerHTML = visible.map((agent) => {
        return '<span class="status-tag" style="color:' + agent.color + ';border-color:' + agent.color + ';">' + escapeHtml(agent.name) + "</span>";
      }).join("");

      const round = currentRound();
      const readout = round.agents
        .filter((agent) => state.agent === "all" || agent.name === state.agent)
        .map((agent) => {
          return agent.name + " " + formatMetricValue(state.metric, agent[state.metric]);
        })
        .join(" | ");
      controls.agentReadout.textContent = "> R" + round.round + " | " + metricLabel(state.metric) + " | " + readout;
    }

    function renderRoundDetails() {
      const round = currentRound();
      const tone = toneForRound(round);

      controls.focusPanel.classList.remove("warning-mode", "info-mode", "stable-mode");
      controls.focusPanel.classList.add(tone.panelClass);

      document.getElementById("focus-round-label").textContent = "R" + round.round + " / inspection";
      document.getElementById("focus-round-copy").textContent =
        "Demand " + formatNumber(round.demandTrue, 0)
        + ", sales " + formatNumber(round.marketTotalSales, 0)
        + ", observed gap " + formatNumber(round.demandGap, 1)
        + ", average price " + formatNumber(round.marketAvgPrice, 2) + ".";
      document.getElementById("detail-regime").textContent = tone.label.replaceAll("_", " ");
      document.getElementById("detail-spread").textContent = formatNumber(round.agentSpread, 2);
      document.getElementById("detail-gap").textContent = formatNumber(round.demandGap, 1);
      document.getElementById("detail-shock").textContent = formatNumber(round.shockComponent, 1);
      document.getElementById("detail-transfer").textContent = formatNumber(round.transferVolume, 1);
      document.getElementById("detail-fulfillment").textContent = formatPercent(round.fulfillmentRatio);
      document.getElementById("detail-fulfillment-bar").style.width = Math.max(2, round.fulfillmentRatio * 100) + "%";

      const regimeTag = document.getElementById("detail-regime-tag");
      regimeTag.className = "status-tag " + tone.tagClass;
      regimeTag.textContent = tone.label;

      document.getElementById("footer-node").textContent = "NODE: R" + round.round;
      document.getElementById("footer-total").textContent = "TOTAL: " + data.meta.rounds;
      document.getElementById("footer-status").textContent = "STATUS: " + tone.label;
      document.getElementById("footer-agent").textContent = "AGENT: " + String(state.agent).toUpperCase();
      document.getElementById("footer-metric").textContent = "METRIC: " + String(state.metric).toUpperCase();
      controls.footerBar.style.background = tone.footerBg;
      controls.footerBar.style.color = tone.footerColor;
    }

    function renderRoundAgentLog() {
      const round = currentRound();
      const rows = round.agents
        .filter((agent) => state.agent === "all" || agent.name === state.agent)
        .map((agent) => {
          const meta = agentMeta[agent.name];
          const tone = toneForAgent(agent);
          const serviceWidth = Math.max(2, agent.serviceRate * 100);
          return `
            <div class="log-entry clickable ${state.agent === agent.name ? "active" : ""}" data-agent="${escapeHtml(agent.name)}" style="border-left-color:${meta.color};">
              <div class="log-label">[AGENT: ${escapeHtml(agent.name)}] <span class="status-tag ${tone.tagClass}">${tone.label}</span></div>
              <p class="log-body">
                &gt; ${escapeHtml(formatActionText(agent.actionText))}
                <span class="muted-copy">price ${formatNumber(agent.price, 2)} | qty ${formatNumber(agent.quantity, 0)} | sold ${formatNumber(agent.realizedSales, 1)} | short ${formatNumber(agent.shortage, 1)} | pnl ${formatMoney(agent.profit)}</span>
              </p>
              <div class="loading-bar-container">
                <div class="loading-bar" style="width:${serviceWidth}%;background:${meta.color};box-shadow:0 0 8px ${meta.color};"></div>
              </div>
            </div>
          `;
        })
        .join("");

      controls.roundAgentLog.innerHTML = rows || '<div class="empty-log">&gt; no agent rows match the current filter</div>';
      controls.roundAgentLog.querySelectorAll("[data-agent]").forEach((node) => {
        node.addEventListener("click", () => {
          const next = node.getAttribute("data-agent");
          state.agent = state.agent === next ? "all" : next;
          controls.agentSelect.value = state.agent;
          render();
        });
      });
    }

    function renderAgentCards() {
      const round = currentRound();
      const cards = round.agents
        .filter((agent) => state.agent === "all" || agent.name === state.agent)
        .map((agent) => {
          const meta = agentMeta[agent.name];
          const tone = toneForAgent(agent);
          return `
            <article class="comparison-card agent-card ${state.agent === agent.name ? "active" : ""}" data-agent="${escapeHtml(agent.name)}" data-tag="${escapeHtml(tagText(agent.name))}" style="--agent-color:${meta.color};border-left-color:${meta.color};">
              <div class="panel-header">
                <div>
                  <span class="step-tag">${escapeHtml(meta.role)}</span>
                  <h3 class="panel-title">${escapeHtml(agent.name)}</h3>
                </div>
                <span class="status-tag ${serviceTagClass(agent.serviceRate)}">${formatPercent(agent.serviceRate)}</span>
              </div>

              <div class="flow-strip" style="color:${meta.color};">
                <span class="flow-node">PX ${formatNumber(agent.price, 2)}</span>
                <span class="flow-node">Q ${formatNumber(agent.quantity, 0)}</span>
                <span class="flow-node">FC ${formatNumber(agent.forecastDemand, 1)}</span>
              </div>

              <div class="system-message-box">&gt; ${escapeHtml(formatActionText(agent.actionText))}</div>
              <p class="agent-copy">${escapeHtml(meta.persona)}</p>

              <div class="agent-params">
                <div class="param-line"><span class="param-label">Round pnl</span><span class="param-value">${formatMoney(agent.profit)}</span></div>
                <div class="param-line"><span class="param-label">Cum pnl</span><span class="param-value">${formatMoney(agent.cumProfit)}</span></div>
                <div class="param-line"><span class="param-label">Reputation</span><span class="param-value">${formatPercent(agent.reputation)}</span></div>
                <div class="param-line"><span class="param-label">Flow</span><span class="param-value">${formatNumber(agent.transferIn, 1)} in / ${formatNumber(agent.transferOut, 1)} out</span></div>
                <div class="param-line"><span class="param-label">State</span><span class="param-value"><span class="status-tag ${tone.tagClass}">${tone.label}</span></span></div>
              </div>
            </article>
          `;
        })
        .join("");

      controls.agentGrid.innerHTML = cards || '<div class="empty-log">&gt; no agents match the current filter</div>';
      controls.agentGrid.querySelectorAll("[data-agent]").forEach((node) => {
        node.addEventListener("click", () => {
          const next = node.getAttribute("data-agent");
          state.agent = state.agent === next ? "all" : next;
          controls.agentSelect.value = state.agent;
          render();
        });
      });
    }

    function renderEvents() {
      const items = data.events
        .filter((event) => {
          if (event.tags.includes("shock") && !toggles.shocks) return false;
          if (event.tags.includes("default") && !toggles.defaults) return false;
          if (event.tags.includes("dump") && !toggles.dumps) return false;
          if (event.tags.includes("transfer") && !toggles.transfers) return false;
          return true;
        })
        .map((event) => {
          const tone = toneForEvent(event);
          return `
            <div class="log-entry clickable" data-round="${event.round}" style="border-left-color:${tone.lineColor};">
              <div class="log-label">[ROUND_${event.round}] <span class="status-tag ${tone.tagClass}">${event.tags.join(" | ")}</span></div>
              <p class="log-body">
                &gt; ${escapeHtml(event.headline)}
                <span class="muted-copy">${escapeHtml(event.details)} | impact ${event.score.toFixed(1)}</span>
              </p>
            </div>
          `;
        })
        .join("");

      controls.eventList.innerHTML = items || '<div class="empty-log">&gt; no events pass the current overlay filters</div>';
      controls.eventList.querySelectorAll("[data-round]").forEach((node) => {
        node.addEventListener("click", () => {
          state.roundIndex = Number(node.getAttribute("data-round")) || 0;
          render();
        });
      });
    }

    function render() {
      syncControls();
      renderMarketChart();
      renderAgentChart();
      renderRoundDetails();
      renderRoundAgentLog();
      renderAgentCards();
      renderEvents();
    }

    setOverview();
    buildAgentOptions();
    setupControls();
    render();
  </script>
</body>
</html>
"""
        .replace("__TITLE__", title)
        .replace("__PAYLOAD__", payload_json)
    )
