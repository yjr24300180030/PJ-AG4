from __future__ import annotations

from dataclasses import dataclass, asdict
import csv
from pathlib import Path
from statistics import median

from .agents import AgentAction
from .config import AgentConfig, MarketConfig, SimulationConfig
from .timeseries import DemandSnapshot
from .utils import clamp, sigmoid, stable_softmax


@dataclass
class AgentState:
    inventory: float
    reputation: float
    cumulative_profit: float = 0.0
    last_profit: float = 0.0
    last_shortage: float = 0.0
    last_price: float = 0.0
    last_dump_flag: bool = False


@dataclass(frozen=True)
class SettlementRow:
    seed: int
    round: int
    agent_name: str
    agent_role: str
    agent_action: str
    forecast_demand: int
    demand_true: int
    demand_obs: int
    trend_component: float
    season_component: float
    shock_component: float
    noise_component: float
    market_avg_price: float
    market_total_sales: float
    inventory_start: float
    reputation_start: float
    price: float
    quantity: int
    available_supply: float
    attractiveness: float
    demand_share: float
    allocated_demand: float
    shortage_pre_transfer: float
    surplus_pre_transfer: float
    transfer_in: float
    transfer_out: float
    transfer_cost: float
    transfer_revenue: float
    coop_accept_rate: float
    realized_sales: float
    shortage_post_transfer: float
    inventory_end: float
    obsolescence_units: float
    revenue: float
    prod_cost: float
    holding_cost: float
    obsolescence_cost: float
    sla_penalty: float
    menu_cost: float
    profit: float
    cum_profit: float
    service_rate: float
    help_ratio: float
    dump_flag: int
    default_flag: int
    reputation_end: float


class MarketEnvironment:
    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.market = config.market
        self.agent_configs = {agent.name: agent for agent in config.agents}
        self.states = {
            agent.name: AgentState(
                inventory=agent.inventory_start,
                reputation=agent.reputation_start,
                last_price=agent.base_price,
            )
            for agent in config.agents
        }

    def step(
        self,
        *,
        seed: int,
        round_index: int,
        snapshot: DemandSnapshot,
        actions: dict[str, AgentAction],
    ) -> list[SettlementRow]:
        ordered_names = list(self.agent_configs.keys())
        supply_start: dict[str, float] = {}
        attractiveness: dict[str, float] = {}
        demand_share: dict[str, float] = {}
        allocated_demand: dict[str, float] = {}
        shortage_pre: dict[str, float] = {}
        surplus_pre: dict[str, float] = {}
        transfer_in: dict[str, float] = {name: 0.0 for name in ordered_names}
        transfer_out: dict[str, float] = {name: 0.0 for name in ordered_names}
        transfer_cost: dict[str, float] = {name: 0.0 for name in ordered_names}
        transfer_revenue: dict[str, float] = {name: 0.0 for name in ordered_names}
        transfer_accepts: dict[str, int] = {name: 0 for name in ordered_names}
        transfer_attempts: dict[str, int] = {name: 0 for name in ordered_names}

        reputations = {name: self.states[name].reputation for name in ordered_names}
        prices = [actions[name].price for name in ordered_names]
        price_softmax = stable_softmax([
            self.agent_configs[name].brand_strength + self.market.reputation_weight * reputations[name] - self.market.price_weight * actions[name].price
            for name in ordered_names
        ])
        market_total_sales = 0.0

        for idx, name in enumerate(ordered_names):
            agent_cfg = self.agent_configs[name]
            action = actions[name]
            state = self.states[name]
            supply_start[name] = state.inventory + action.quantity
            attractiveness[name] = (
                agent_cfg.brand_strength
                + self.market.reputation_weight * state.reputation
                - self.market.price_weight * action.price
            )
            demand_share[name] = price_softmax[idx]
            allocated_demand[name] = snapshot.true_demand * demand_share[name]
            shortage_pre[name] = max(0.0, allocated_demand[name] - supply_start[name])
            surplus_pre[name] = max(0.0, supply_start[name] - allocated_demand[name])

        shortage_remaining = shortage_pre.copy()
        surplus_remaining = surplus_pre.copy()
        provider_order = sorted(
            ordered_names,
            key=lambda item: surplus_remaining[item],
            reverse=True,
        )
        shortage_order = sorted(
            ordered_names,
            key=lambda item: shortage_remaining[item],
            reverse=True,
        )

        for shortage_name in shortage_order:
            if shortage_remaining[shortage_name] <= 0:
                continue
            shortage_state = self.states[shortage_name]
            shortage_action = actions[shortage_name]
            shortage_cfg = self.agent_configs[shortage_name]
            for provider_name in provider_order:
                if provider_name == shortage_name or shortage_remaining[shortage_name] <= 0:
                    continue
                if surplus_remaining[provider_name] <= 0:
                    continue
                provider_state = self.states[provider_name]
                provider_action = actions[provider_name]
                transfer_attempts[provider_name] += 1
                willingness = sigmoid(
                    self.market.cooperation_alpha0
                    + self.market.cooperation_alpha1 * shortage_state.reputation
                    - self.market.cooperation_alpha2 * (allocated_demand[provider_name] / (supply_start[provider_name] + 1.0))
                    - self.market.cooperation_alpha3 * (1.0 if shortage_state.last_dump_flag else 0.0)
                )
                transfer_accepts[provider_name] += 1 if willingness >= 0.5 else 0
                if willingness < 0.5:
                    continue
                amount = min(
                    surplus_remaining[provider_name],
                    shortage_remaining[shortage_name],
                    self.market.max_transfer,
                )
                if amount <= 0:
                    continue
                transfer_in[shortage_name] += amount
                transfer_out[provider_name] += amount
                surplus_remaining[provider_name] -= amount
                shortage_remaining[shortage_name] -= amount
                provider_price = provider_action.price
                buyer_price = provider_price * (1.0 + self.market.transfer_markup)
                transfer_cost[shortage_name] += amount * buyer_price
                transfer_revenue[provider_name] += amount * buyer_price

        row_payloads: dict[str, dict[str, float | int | str]] = {}
        for name in ordered_names:
            state = self.states[name]
            agent_cfg = self.agent_configs[name]
            action = actions[name]
            total_supply = supply_start[name] + transfer_in[name] - transfer_out[name]
            realized_sales = min(total_supply, allocated_demand[name])
            shortage_post = max(0.0, allocated_demand[name] - total_supply)
            inventory_end = max(0.0, total_supply - realized_sales)
            obsolescence_units = agent_cfg.obsolescence_penalty * inventory_end
            next_inventory = max(0.0, inventory_end * (1.0 - agent_cfg.obsolescence_penalty))
            revenue = realized_sales * action.price
            prod_cost = action.quantity * agent_cfg.linear_cost + (action.quantity**2) * agent_cfg.quadratic_cost
            holding_cost = next_inventory * agent_cfg.holding_cost_rate
            obsolescence_cost = obsolescence_units * agent_cfg.obsolescence_penalty
            sla_penalty = shortage_post * agent_cfg.sla_penalty
            menu_cost = abs(action.price - state.last_price) * agent_cfg.menu_cost_rate
            profit = revenue + transfer_revenue[name] - transfer_cost[name] - prod_cost - holding_cost - obsolescence_cost - sla_penalty - menu_cost
            service_rate = 0.0 if allocated_demand[name] <= 0 else realized_sales / allocated_demand[name]
            help_ratio = 0.0 if surplus_pre[name] <= 0 else transfer_out[name] / surplus_pre[name]
            dump_flag = int(action.price < (agent_cfg.linear_cost + agent_cfg.quadratic_cost * max(1, action.quantity)) and action.price < 0.85 * median(prices))
            default_flag = int(allocated_demand[name] > 0 and shortage_post / allocated_demand[name] > 0.1)
            reputation_score = clamp(
                service_rate + 0.2 * help_ratio - 0.4 * dump_flag - 0.6 * default_flag,
                0.0,
                1.0,
            )
            reputation_end = clamp(
                (1.0 - self.market.reputation_update_rate) * state.reputation
                + self.market.reputation_update_rate * reputation_score,
                0.0,
                1.0,
            )

            state.inventory = next_inventory
            state.reputation = reputation_end
            state.cumulative_profit += profit
            state.last_profit = profit
            state.last_shortage = shortage_post
            state.last_price = action.price
            state.last_dump_flag = bool(dump_flag)
            row_payloads[name] = {
                "forecast_demand": action.forecast_demand,
                "agent_action": f"forecast={action.forecast_demand};price={action.price:.2f};quantity={action.quantity}",
                "demand_true": snapshot.true_demand,
                "demand_obs": snapshot.observed_demand,
                "trend_component": snapshot.trend_component,
                "season_component": snapshot.seasonal_component,
                "shock_component": snapshot.shock_component,
                "noise_component": snapshot.noise_component,
                "inventory_start": supply_start[name] - action.quantity,
                "reputation_start": reputations[name],
                "price": action.price,
                "quantity": action.quantity,
                "available_supply": supply_start[name],
                "attractiveness": attractiveness[name],
                "demand_share": demand_share[name],
                "allocated_demand": allocated_demand[name],
                "shortage_pre_transfer": shortage_pre[name],
                "surplus_pre_transfer": surplus_pre[name],
                "transfer_in": transfer_in[name],
                "transfer_out": transfer_out[name],
                "transfer_cost": transfer_cost[name],
                "transfer_revenue": transfer_revenue[name],
                "coop_accept_rate": 0.0 if transfer_attempts[name] <= 0 else transfer_accepts[name] / transfer_attempts[name],
                "realized_sales": realized_sales,
                "shortage_post_transfer": shortage_post,
                "inventory_end": next_inventory,
                "obsolescence_units": obsolescence_units,
                "revenue": revenue,
                "prod_cost": prod_cost,
                "holding_cost": holding_cost,
                "obsolescence_cost": obsolescence_cost,
                "sla_penalty": sla_penalty,
                "menu_cost": menu_cost,
                "profit": profit,
                "cum_profit": state.cumulative_profit,
                "service_rate": service_rate,
                "help_ratio": help_ratio,
                "dump_flag": dump_flag,
                "default_flag": default_flag,
                "reputation_end": reputation_end,
            }

        round_total_sales = sum(payload["realized_sales"] for payload in row_payloads.values())
        rows: list[SettlementRow] = []
        for name in ordered_names:
            payload = row_payloads[name]
            rows.append(
                SettlementRow(
                    seed=seed,
                    round=round_index,
                    agent_name=name,
                    agent_role=self.agent_configs[name].role,
                    agent_action=payload["agent_action"],
                    forecast_demand=int(payload["forecast_demand"]),
                    demand_true=int(payload["demand_true"]),
                    demand_obs=int(payload["demand_obs"]),
                    trend_component=float(payload["trend_component"]),
                    season_component=float(payload["season_component"]),
                    shock_component=float(payload["shock_component"]),
                    noise_component=float(payload["noise_component"]),
                    market_avg_price=sum(prices) / len(prices),
                    market_total_sales=round_total_sales,
                    inventory_start=float(payload["inventory_start"]),
                    reputation_start=float(payload["reputation_start"]),
                    price=float(payload["price"]),
                    quantity=int(payload["quantity"]),
                    available_supply=float(payload["available_supply"]),
                    attractiveness=float(payload["attractiveness"]),
                    demand_share=float(payload["demand_share"]),
                    allocated_demand=float(payload["allocated_demand"]),
                    shortage_pre_transfer=float(payload["shortage_pre_transfer"]),
                    surplus_pre_transfer=float(payload["surplus_pre_transfer"]),
                    transfer_in=float(payload["transfer_in"]),
                    transfer_out=float(payload["transfer_out"]),
                    transfer_cost=float(payload["transfer_cost"]),
                    transfer_revenue=float(payload["transfer_revenue"]),
                    coop_accept_rate=float(payload["coop_accept_rate"]),
                    realized_sales=float(payload["realized_sales"]),
                    shortage_post_transfer=float(payload["shortage_post_transfer"]),
                    inventory_end=float(payload["inventory_end"]),
                    obsolescence_units=float(payload["obsolescence_units"]),
                    revenue=float(payload["revenue"]),
                    prod_cost=float(payload["prod_cost"]),
                    holding_cost=float(payload["holding_cost"]),
                    obsolescence_cost=float(payload["obsolescence_cost"]),
                    sla_penalty=float(payload["sla_penalty"]),
                    menu_cost=float(payload["menu_cost"]),
                    profit=float(payload["profit"]),
                    cum_profit=float(payload["cum_profit"]),
                    service_rate=float(payload["service_rate"]),
                    help_ratio=float(payload["help_ratio"]),
                    dump_flag=int(payload["dump_flag"]),
                    default_flag=int(payload["default_flag"]),
                    reputation_end=float(payload["reputation_end"]),
                )
            )
        return rows


def write_rows_to_csv(rows: list[SettlementRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(rows[0]).keys()) if rows else []
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            for row in rows:
                writer.writerow(asdict(row))
