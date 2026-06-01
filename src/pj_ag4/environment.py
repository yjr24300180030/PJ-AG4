"""
重构3：
拆分environment模块中的数据模型储存职责与io职责
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import random
from statistics import median

from .config import AgentConfig, MarketConfig, SimulationConfig
from .contracts import AgentAction, SettlementRow
from .timeseries import DemandSnapshot
from .utils import clamp, sigmoid, stable_softmax


@dataclass
class AgentState:
    inventory: float
    rep_delivery: float
    rep_pricing: float
    rep_cooperation: float
    reputation_delivery_weight: float
    reputation_pricing_weight: float
    reputation_cooperation_weight: float
    cumulative_profit: float = 0.0
    last_profit: float = 0.0
    last_shortage: float = 0.0
    last_price: float = 0.0
    last_dump_flag: bool = False
    backlog: float = 0.0

    @property
    def reputation(self) -> float:
        return _weighted_reputation_values(
            delivery=self.rep_delivery,
            pricing=self.rep_pricing,
            cooperation=self.rep_cooperation,
            delivery_weight=self.reputation_delivery_weight,
            pricing_weight=self.reputation_pricing_weight,
            cooperation_weight=self.reputation_cooperation_weight,
        )


def _weighted_reputation_values(
    *,
    delivery: float,
    pricing: float,
    cooperation: float,
    delivery_weight: float,
    pricing_weight: float,
    cooperation_weight: float,
) -> float:
    total_weight = delivery_weight + pricing_weight + cooperation_weight
    if total_weight <= 0:
        return 0.0
    return clamp(
        (
            delivery_weight * delivery
            + pricing_weight * pricing
            + cooperation_weight * cooperation
        )
        / total_weight,
        0.0,
        1.0,
    )


def _weighted_reputation(
    *,
    delivery: float,
    pricing: float,
    cooperation: float,
    market: MarketConfig,
) -> float:
    return _weighted_reputation_values(
        delivery=delivery,
        pricing=pricing,
        cooperation=cooperation,
        delivery_weight=market.reputation_delivery_weight,
        pricing_weight=market.reputation_pricing_weight,
        cooperation_weight=market.reputation_cooperation_weight,
    )


class MarketEnvironment:
    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.market = config.market
        self._rng = random.Random(config.seed + 1009)
        self.agent_configs = {agent.name: agent for agent in config.agents}
        self.states = {
            agent.name: AgentState(
                inventory=agent.inventory_start,
                rep_delivery=agent.reputation_start,
                rep_pricing=agent.reputation_start,
                rep_cooperation=agent.reputation_start,
                reputation_delivery_weight=self.market.reputation_delivery_weight,
                reputation_pricing_weight=self.market.reputation_pricing_weight,
                reputation_cooperation_weight=self.market.reputation_cooperation_weight,
                last_price=agent.base_price,
            )
            for agent in config.agents
        }

    def reputation_for(self, agent_name: str) -> float:
        state = self.states[agent_name]
        return _weighted_reputation(
            delivery=state.rep_delivery,
            pricing=state.rep_pricing,
            cooperation=state.rep_cooperation,
            market=self.market,
        )

    def current_reputations(self) -> dict[str, float]:
        return {name: self.reputation_for(name) for name in self.agent_configs}

    def validate_action(self, agent_name: str, action: AgentAction) -> AgentAction:
        agent_cfg = self.agent_configs[agent_name]
        price = clamp(float(action.price), agent_cfg.price_floor, agent_cfg.price_ceiling)
        quantity = int(round(float(action.quantity) / agent_cfg.quantity_step) * agent_cfg.quantity_step)
        quantity = int(clamp(quantity, 0, agent_cfg.max_quantity))
        forecast = max(0, int(round(float(action.forecast_demand))))
        return AgentAction(
            forecast_demand=forecast,
            price=price,
            quantity=quantity,
            trace=action.trace,
            strategy_state=action.strategy_state,
            strategy_update_trace=action.strategy_update_trace,
        )

    def validate_actions(self, actions: dict[str, AgentAction]) -> dict[str, AgentAction]:
        return {
            name: self.validate_action(name, actions[name])
            for name in self.agent_configs
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
        actions = self.validate_actions(actions)
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
        transfer_probability_sum: dict[str, float] = {name: 0.0 for name in ordered_names}
        segment_demand = {
            segment.name: snapshot.true_demand * segment.demand_fraction
            for segment in self.market.customer_segments
        }
        segment_allocations: dict[str, dict[str, float]] = {
            name: {segment.name: 0.0 for segment in self.market.customer_segments}
            for name in ordered_names
        }
        reallocated_in: dict[str, float] = {name: 0.0 for name in ordered_names}
        reallocated_out: dict[str, float] = {name: 0.0 for name in ordered_names}

        reputation_start = {name: self.reputation_for(name) for name in ordered_names}
        prices = [actions[name].price for name in ordered_names]

        for name in ordered_names:
            agent_cfg = self.agent_configs[name]
            action = actions[name]
            state = self.states[name]
            supply_start[name] = state.inventory + action.quantity
            attractiveness[name] = (
                agent_cfg.brand_strength
                + self.market.reputation_weight * reputation_start[name]
                - self.market.price_weight * action.price
            )

        for segment in self.market.customer_segments:
            segment_scores = []
            for name in ordered_names:
                agent_cfg = self.agent_configs[name]
                state = self.states[name]
                role_bonus = segment.role_bias.get(agent_cfg.role, 0.0)
                segment_scores.append(
                    segment.brand_weight * agent_cfg.brand_strength
                    + segment.reputation_weight * reputation_start[name]
                    + segment.sla_weight * state.rep_delivery
                    + role_bonus
                    - segment.price_weight * actions[name].price
                )
            segment_shares = stable_softmax(segment_scores)
            for idx, name in enumerate(ordered_names):
                segment_allocations[name][segment.name] += segment_demand[segment.name] * segment_shares[idx]

        for name in ordered_names:
            allocated_demand[name] = sum(segment_allocations[name].values())

        if self.market.reallocation_enabled:
            initial_sales = {
                name: min(supply_start[name], allocated_demand[name])
                for name in ordered_names
            }
            surplus_after_initial = {
                name: max(0.0, supply_start[name] - initial_sales[name])
                for name in ordered_names
            }
            unmet_after_initial = {
                name: max(0.0, allocated_demand[name] - supply_start[name])
                for name in ordered_names
            }
            for shortage_name in sorted(ordered_names, key=lambda item: unmet_after_initial[item], reverse=True):
                remaining_unmet = unmet_after_initial[shortage_name]
                if remaining_unmet <= 0:
                    continue
                candidates = [
                    name
                    for name in ordered_names
                    if name != shortage_name and surplus_after_initial[name] > 0
                ]
                if not candidates:
                    continue
                weights = stable_softmax([attractiveness[name] for name in candidates])
                for candidate, weight in zip(candidates, weights, strict=True):
                    if remaining_unmet <= 0:
                        break
                    amount = min(
                        surplus_after_initial[candidate],
                        remaining_unmet * weight * self.market.reallocation_fill_rate,
                    )
                    if amount <= 0:
                        continue
                    allocated_demand[shortage_name] -= amount
                    allocated_demand[candidate] += amount
                    reallocated_out[shortage_name] += amount
                    reallocated_in[candidate] += amount
                    surplus_after_initial[candidate] -= amount
                    remaining_unmet -= amount

        for name in ordered_names:
            demand_share[name] = 0.0 if snapshot.true_demand <= 0 else allocated_demand[name] / snapshot.true_demand
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
        refused_help: dict[str, int] = {name: 0 for name in ordered_names}

        for shortage_name in shortage_order:
            if not self.market.transfer_enabled:
                break
            if shortage_remaining[shortage_name] <= 0:
                continue
            shortage_state = self.states[shortage_name]
            for provider_name in provider_order:
                if provider_name == shortage_name or shortage_remaining[shortage_name] <= 0:
                    continue
                if surplus_remaining[provider_name] <= 0:
                    continue
                provider_action = actions[provider_name]
                transfer_attempts[provider_name] += 1
                willingness = sigmoid(
                    self.market.cooperation_alpha0
                    + self.market.cooperation_alpha1 * shortage_state.rep_cooperation
                    - self.market.cooperation_alpha2 * (allocated_demand[provider_name] / (supply_start[provider_name] + 1.0))
                    - self.market.cooperation_alpha3 * (1.0 if shortage_state.last_dump_flag else 0.0)
                )
                transfer_probability_sum[provider_name] += willingness
                accepted = self._rng.random() < willingness
                transfer_accepts[provider_name] += 1 if accepted else 0
                if not accepted:
                    refused_help[provider_name] += 1
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
            rep_delivery_start = state.rep_delivery
            rep_pricing_start = state.rep_pricing
            rep_cooperation_start = state.rep_cooperation
            total_supply = supply_start[name] + transfer_in[name] - transfer_out[name]
            backlog_start = state.backlog if self.market.sla_queue_enabled else 0.0
            delivered_backlog = min(backlog_start, total_supply)
            supply_for_current = max(0.0, total_supply - delivered_backlog)
            realized_sales = min(supply_for_current, allocated_demand[name])
            shortage_post = max(0.0, allocated_demand[name] - supply_for_current)
            contract_demand = sum(
                segment_allocations[name][segment.name] * segment.contract_fraction
                for segment in self.market.customer_segments
            )
            contract_ratio = 0.0 if allocated_demand[name] <= 0 else min(1.0, contract_demand / allocated_demand[name])
            backlog_added = shortage_post * contract_ratio if self.market.sla_queue_enabled else 0.0
            late_units = max(0.0, backlog_start - delivered_backlog) if self.market.sla_queue_enabled else 0.0
            backlog_end = max(0.0, backlog_start - delivered_backlog) + backlog_added
            sla_queue_penalty = late_units * agent_cfg.sla_penalty * self.market.sla_backlog_penalty_multiplier
            inventory_end = max(0.0, supply_for_current - realized_sales)
            obsolescence_units = agent_cfg.obsolescence_rate * inventory_end
            next_inventory = max(0.0, inventory_end - obsolescence_units)
            revenue = (realized_sales + delivered_backlog) * action.price
            prod_cost = action.quantity * agent_cfg.linear_cost + 0.5 * (action.quantity**2) * agent_cfg.quadratic_cost
            holding_cost = next_inventory * agent_cfg.holding_cost_rate
            obsolescence_cost = obsolescence_units * agent_cfg.obsolescence_penalty
            sla_penalty = shortage_post * agent_cfg.sla_penalty
            spot_volume = float(segment_allocations[name].get("spot_workload", 0.0))
            discount_depth = max(0.0, agent_cfg.base_price - action.price)
            price_pressure_cost = self.market.price_pressure_cost_rate * (
                0.45 * spot_volume + realized_sales * discount_depth
            )
            menu_cost = abs(action.price - state.last_price) * agent_cfg.menu_cost_rate
            profit = (
                revenue
                + transfer_revenue[name]
                - transfer_cost[name]
                - prod_cost
                - holding_cost
                - obsolescence_cost
                - sla_penalty
                - sla_queue_penalty
                - price_pressure_cost
                - menu_cost
            )
            service_rate = 0.0 if allocated_demand[name] <= 0 else realized_sales / allocated_demand[name]
            help_ratio = 0.0 if surplus_pre[name] <= 0 else transfer_out[name] / surplus_pre[name]
            peer_prices = [price for idx, price in enumerate(prices) if ordered_names[idx] != name]
            peer_median = median(peer_prices) if peer_prices else action.price
            marginal_cost = agent_cfg.linear_cost + agent_cfg.quadratic_cost * max(1, action.quantity)
            ratio_threshold = 0.85 * peer_median
            safety_threshold = agent_cfg.price_floor + agent_cfg.price_step
            dump_threshold = max(ratio_threshold, safety_threshold)
            dump_flag = int(action.price < marginal_cost and action.price < dump_threshold)
            default_flag = int(allocated_demand[name] > 0 and shortage_post / allocated_demand[name] > 0.1)
            delivery_score = clamp(service_rate - 0.5 * default_flag, 0.0, 1.0)
            pricing_score = 0.0 if dump_flag else 1.0
            if transfer_attempts[name] > 0:
                cooperation_score = clamp(
                    transfer_accepts[name] / transfer_attempts[name]
                    - self.market.indirect_reciprocity_alpha * refused_help[name],
                    0.0,
                    1.0,
                )
            else:
                cooperation_score = state.rep_cooperation
            rep_delivery_end = clamp(
                (1.0 - self.market.reputation_update_rate) * state.rep_delivery
                + self.market.reputation_update_rate * delivery_score,
                0.0,
                1.0,
            )
            rep_pricing_end = clamp(
                (1.0 - self.market.reputation_update_rate) * state.rep_pricing
                + self.market.reputation_update_rate * pricing_score,
                0.0,
                1.0,
            )
            rep_cooperation_end = clamp(
                (1.0 - self.market.reputation_update_rate) * state.rep_cooperation
                + self.market.reputation_update_rate * cooperation_score,
                0.0,
                1.0,
            )
            reputation_end = clamp(
                _weighted_reputation(
                    delivery=rep_delivery_end,
                    pricing=rep_pricing_end,
                    cooperation=rep_cooperation_end,
                    market=self.market,
                ),
                0.0,
                1.0,
            )

            state.inventory = next_inventory
            state.rep_delivery = rep_delivery_end
            state.rep_pricing = rep_pricing_end
            state.rep_cooperation = rep_cooperation_end
            state.cumulative_profit += profit
            state.last_profit = profit
            state.last_shortage = shortage_post
            state.last_price = action.price
            state.last_dump_flag = bool(dump_flag)
            state.backlog = backlog_end
            decision_trace = action.trace
            strategy_update_trace = action.strategy_update_trace
            row_payloads[name] = {
                "forecast_demand": action.forecast_demand,
                "forecast_error_abs": abs(action.forecast_demand - snapshot.true_demand),
                "forecast_error_sq": (action.forecast_demand - snapshot.true_demand) ** 2,
                "agent_action": f"forecast={action.forecast_demand};price={action.price:.2f};quantity={action.quantity}",
                "decision_source": decision_trace.source if decision_trace is not None else "external",
                "decision_reason": decision_trace.summary if decision_trace is not None else "No structured decision trace was provided.",
                "decision_trace": decision_trace.to_json() if decision_trace is not None else "",
                "strategy_state": action.strategy_state.to_json() if action.strategy_state is not None else "",
                "strategy_update_reason": strategy_update_trace.reason if strategy_update_trace is not None else "",
                "strategy_update_trace": strategy_update_trace.to_json() if strategy_update_trace is not None else "",
                "demand_true": snapshot.true_demand,
                "demand_obs": snapshot.observed_demand,
                "trend_component": snapshot.trend_component,
                "season_component": snapshot.seasonal_component,
                "shock_component": snapshot.shock_component,
                "noise_component": snapshot.noise_component,
                "inventory_start": supply_start[name] - action.quantity,
                "reputation_start": reputation_start[name],
                "rep_delivery_start": rep_delivery_start,
                "rep_pricing_start": rep_pricing_start,
                "rep_cooperation_start": rep_cooperation_start,
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
                "transfer_attempts": transfer_attempts[name],
                "transfer_accepts": transfer_accepts[name],
                "coop_probability": 0.0 if transfer_attempts[name] <= 0 else transfer_probability_sum[name] / transfer_attempts[name],
                "coop_accept_rate": 0.0 if transfer_attempts[name] <= 0 else transfer_accepts[name] / transfer_attempts[name],
                "segment_demand": json.dumps(segment_demand, ensure_ascii=False, separators=(",", ":")),
                "segment_allocations": json.dumps(segment_allocations[name], ensure_ascii=False, separators=(",", ":")),
                "reallocated_in": reallocated_in[name],
                "reallocated_out": reallocated_out[name],
                "realized_sales": realized_sales,
                "shortage_post_transfer": shortage_post,
                "backlog_start": backlog_start,
                "new_contract_demand": contract_demand,
                "delivered_backlog": delivered_backlog,
                "backlog_end": backlog_end,
                "late_units": late_units,
                "sla_queue_penalty": sla_queue_penalty,
                "inventory_end": next_inventory,
                "obsolescence_units": obsolescence_units,
                "revenue": revenue,
                "prod_cost": prod_cost,
                "holding_cost": holding_cost,
                "obsolescence_cost": obsolescence_cost,
                "sla_penalty": sla_penalty,
                "price_pressure_cost": price_pressure_cost,
                "menu_cost": menu_cost,
                "profit": profit,
                "cum_profit": state.cumulative_profit,
                "service_rate": service_rate,
                "help_ratio": help_ratio,
                "dump_flag": dump_flag,
                "default_flag": default_flag,
                "rep_delivery_end": rep_delivery_end,
                "rep_pricing_end": rep_pricing_end,
                "rep_cooperation_end": rep_cooperation_end,
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
                    decision_source=str(payload["decision_source"]),
                    decision_reason=str(payload["decision_reason"]),
                    decision_trace=str(payload["decision_trace"]),
                    strategy_state=str(payload["strategy_state"]),
                    strategy_update_reason=str(payload["strategy_update_reason"]),
                    strategy_update_trace=str(payload["strategy_update_trace"]),
                    forecast_demand=int(payload["forecast_demand"]),
                    forecast_error_abs=float(payload["forecast_error_abs"]),
                    forecast_error_sq=float(payload["forecast_error_sq"]),
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
                    rep_delivery_start=float(payload["rep_delivery_start"]),
                    rep_pricing_start=float(payload["rep_pricing_start"]),
                    rep_cooperation_start=float(payload["rep_cooperation_start"]),
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
                    transfer_attempts=int(payload["transfer_attempts"]),
                    transfer_accepts=int(payload["transfer_accepts"]),
                    coop_probability=float(payload["coop_probability"]),
                    coop_accept_rate=float(payload["coop_accept_rate"]),
                    segment_demand=str(payload["segment_demand"]),
                    segment_allocations=str(payload["segment_allocations"]),
                    reallocated_in=float(payload["reallocated_in"]),
                    reallocated_out=float(payload["reallocated_out"]),
                    realized_sales=float(payload["realized_sales"]),
                    shortage_post_transfer=float(payload["shortage_post_transfer"]),
                    backlog_start=float(payload["backlog_start"]),
                    new_contract_demand=float(payload["new_contract_demand"]),
                    delivered_backlog=float(payload["delivered_backlog"]),
                    backlog_end=float(payload["backlog_end"]),
                    late_units=float(payload["late_units"]),
                    sla_queue_penalty=float(payload["sla_queue_penalty"]),
                    inventory_end=float(payload["inventory_end"]),
                    obsolescence_units=float(payload["obsolescence_units"]),
                    revenue=float(payload["revenue"]),
                    prod_cost=float(payload["prod_cost"]),
                    holding_cost=float(payload["holding_cost"]),
                    obsolescence_cost=float(payload["obsolescence_cost"]),
                    sla_penalty=float(payload["sla_penalty"]),
                    price_pressure_cost=float(payload["price_pressure_cost"]),
                    menu_cost=float(payload["menu_cost"]),
                    profit=float(payload["profit"]),
                    cum_profit=float(payload["cum_profit"]),
                    service_rate=float(payload["service_rate"]),
                    help_ratio=float(payload["help_ratio"]),
                    dump_flag=int(payload["dump_flag"]),
                    default_flag=int(payload["default_flag"]),
                    rep_delivery_end=float(payload["rep_delivery_end"]),
                    rep_pricing_end=float(payload["rep_pricing_end"]),
                    rep_cooperation_end=float(payload["rep_cooperation_end"]),
                    reputation_end=float(payload["reputation_end"]),
                )
            )
        return rows
