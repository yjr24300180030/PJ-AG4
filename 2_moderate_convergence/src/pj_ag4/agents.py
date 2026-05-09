from __future__ import annotations

import json
from typing import Any, Sequence

from .config import AgentConfig, LLMConfig
from .contracts import AgentAction, MarketObservation
from .providers import build_openai_client, query_json_completion
from .strategy_registry import build_registered_agents, has_strategy, register_strategy
from .utils import int_round_to_step, round_to_step, weighted_forecast

_build_openai_client = build_openai_client


FORECASTER_STYLE_GUIDANCE = {
    "momentum_chaser": "Lean into trend continuation and respond quickly to rising demand pressure.",
    "signal_smoother": "Discount noisy spikes and prefer stable, reputation-aware demand estimates.",
    "volatility_reader": "React to short-term volatility and treat market swings as exploitable signals.",
}

PRICER_STYLE_GUIDANCE = {
    "share_grabber": "Seek the lowest PROFITABLE price to capture share. Profitability comes FIRST — never sacrifice unit profit for volume.",
    "premium_keeper": "Protect price discipline and monetize reputation with a durable premium.",
    "spread_hunter": "Adjust prices tactically to capture transient spread and inventory opportunities.",
}

ALLOCATOR_STYLE_GUIDANCE = {
    "capacity_expander": "Keep capacity ready and scale supply ahead of demand when possible.",
    "buffered_allocator": "Hold a moderate service buffer without overcommitting capital.",
    "inventory_light": "Stay light on inventory and favor flexibility over large buffers.",
}

RISK_STYLE_GUIDANCE = {
    "growth_tolerant": "Allow aggressive proposals unless they break hard market constraints.",
    "sla_guard": "Protect SLA reliability, price floor discipline, and brand reputation first.",
    "inventory_guard": "Avoid inventory bloat and tighten exposure when volatility is elevated.",
}


def _forecaster_style_adjustment(style: str, observation: MarketObservation, trend: float) -> float:
    if style == "momentum_chaser":
        return 0.20 * trend + 0.06 * observation.market_volatility + 0.04 * max(0.0, observation.own_last_shortage)
    if style == "signal_smoother":
        return -0.08 * trend + 0.05 * observation.own_reputation - 0.03 * observation.market_volatility
    if style == "volatility_reader":
        return 0.12 * trend + 0.14 * observation.market_volatility
    return 0.0


def _pricer_style_adjustment(style: str, observation: MarketObservation, forecast: int) -> float:
    inventory_pressure = max(0.0, observation.own_inventory - 15.0) / 100.0
    shortage_pressure = max(0.0, observation.own_last_shortage) / max(1.0, forecast)
    if style == "share_grabber":
        return -0.22 - 0.05 * observation.market_volatility - 0.16 * shortage_pressure
    if style == "premium_keeper":
        return 0.30 + 0.18 * observation.own_reputation + 0.03 * observation.market_volatility
    if style == "spread_hunter":
        return 0.04 - 0.16 * inventory_pressure + 0.05 * observation.market_volatility
    return 0.0


def _allocator_style_adjustment(style: str, observation: MarketObservation, forecast: int) -> float:
    forecast_gap = max(0.0, forecast - observation.own_inventory)
    if style == "capacity_expander":
        return 0.22 * forecast_gap + max(0.0, 10.0 - observation.own_inventory) * 0.5
    if style == "buffered_allocator":
        return -0.10 * forecast + max(0.0, 18.0 - observation.own_inventory) * 0.4
    if style == "inventory_light":
        return -0.18 * forecast + 0.60 * observation.market_volatility
    return 0.0


class RiskGateStage:
    def __init__(self, config: AgentConfig) -> None:
        self._config = config

    def review(
        self,
        observation: MarketObservation,
        draft: AgentAction,
        *,
        fallback: AgentAction | None = None,
    ) -> AgentAction:
        reviewed_price = draft.price
        reviewed_quantity = float(draft.quantity)
        reviewed_forecast = draft.forecast_demand
        style = self._config.risk_style
        if style == "growth_tolerant":
            if observation.own_last_shortage > 0:
                reviewed_quantity += self._config.quantity_step
        elif style == "sla_guard":
            reviewed_price = max(reviewed_price, observation.market_avg_price)
            if observation.own_last_shortage > 0 or observation.own_reputation < 0.85:
                reviewed_quantity = min(reviewed_quantity, max(0.0, reviewed_forecast * 0.80))
        elif style == "inventory_guard":
            target_total = max(reviewed_forecast * 0.75 + 12.0, 20.0)
            reviewed_quantity = min(reviewed_quantity, max(0.0, target_total - observation.own_inventory))
            if observation.market_volatility > 5.0:
                reviewed_price = max(reviewed_price, observation.market_avg_price)
        if fallback is not None and observation.own_reputation < 0.35:
            reviewed_price = max(reviewed_price, fallback.price)

        # Universal cost safety: price must cover average production cost + one price step margin
        avg_cost = self._config.linear_cost + self._config.quadratic_cost * reviewed_quantity
        min_viable_price = avg_cost + self._config.price_step
        if reviewed_price < min_viable_price:
            reviewed_price = min_viable_price

        return AgentAction(
            forecast_demand=max(0, int(round(reviewed_forecast))),
            price=round_to_step(
                reviewed_price,
                self._config.price_step,
                self._config.price_floor,
                self._config.price_ceiling,
            ),
            quantity=int_round_to_step(
                reviewed_quantity,
                self._config.quantity_step,
                0,
                self._config.max_quantity,
            ),
        )


class HeuristicForecasterStage:
    def __init__(self, agent: "HeuristicAgent") -> None:
        self._agent = agent

    def run(self, observation: MarketObservation, *, fallback: AgentAction | None = None) -> int:
        del fallback
        history = observation.observed_demand_history
        base = weighted_forecast(history, short_window=3)
        trend = 0.0
        if len(history) >= 2:
            trend = (history[-1] - history[0]) / max(1, len(history) - 1)
        forecast = 0.7 * base + 0.3 * (history[-1] if history else observation.observed_demand)
        forecast += self._agent._forecast_adjustment(observation, trend)
        forecast += _forecaster_style_adjustment(self._agent.config.forecaster_style, observation, trend)
        return max(0, int(round(forecast)))


class HeuristicPricerStage:
    def __init__(self, agent: "HeuristicAgent") -> None:
        self._agent = agent

    def run(
        self,
        observation: MarketObservation,
        forecast: int,
        *,
        fallback: AgentAction | None = None,
    ) -> float:
        del fallback
        value = self._agent.config.base_price + self._agent._price_adjustment(observation, forecast)
        value += _pricer_style_adjustment(self._agent.config.pricer_style, observation, forecast)
        return round_to_step(
            value,
            self._agent.config.price_step,
            self._agent.config.price_floor,
            self._agent.config.price_ceiling,
        )


class HeuristicAllocatorStage:
    def __init__(self, agent: "HeuristicAgent") -> None:
        self._agent = agent

    def run(
        self,
        observation: MarketObservation,
        forecast: int,
        price: float,
        *,
        fallback: AgentAction | None = None,
    ) -> int:
        del price
        del fallback
        target = self._agent._quantity_target(observation, forecast)
        target += _allocator_style_adjustment(self._agent.config.allocator_style, observation, forecast)
        return int_round_to_step(target, self._agent.config.quantity_step, 0, self._agent.config.max_quantity)


class RolePipelineAgent:
    def __init__(
        self,
        config: AgentConfig,
        *,
        forecaster: Any,
        pricer: Any,
        allocator: Any,
        risk_gate: RiskGateStage,
    ) -> None:
        self.config = config
        self._forecaster = forecaster
        self._pricer = pricer
        self._allocator = allocator
        self._risk_gate = risk_gate

    def _run_pipeline(
        self,
        observation: MarketObservation,
        *,
        fallback: AgentAction | None = None,
    ) -> AgentAction:
        forecast = self._forecaster.run(observation, fallback=fallback)
        price = self._pricer.run(observation, forecast, fallback=fallback)
        quantity = self._allocator.run(observation, forecast, price, fallback=fallback)
        return self._risk_gate.review(
            observation,
            AgentAction(forecast_demand=forecast, price=price, quantity=quantity),
            fallback=fallback,
        )

    def decide(self, observation: MarketObservation) -> AgentAction:
        return self._run_pipeline(observation)


class HeuristicAgent(RolePipelineAgent):
    def __init__(self, config: AgentConfig) -> None:
        super().__init__(
            config,
            forecaster=HeuristicForecasterStage(self),
            pricer=HeuristicPricerStage(self),
            allocator=HeuristicAllocatorStage(self),
            risk_gate=RiskGateStage(config),
        )

    def _forecast_adjustment(self, observation: MarketObservation, trend: float) -> float:
        del observation
        del trend
        return 0.0

    def _price_adjustment(self, observation: MarketObservation, forecast: int) -> float:
        del observation
        del forecast
        return 0.0

    def _quantity_target(self, observation: MarketObservation, forecast: int) -> float:
        del observation
        return float(forecast)


class HyperscalerAgent(HeuristicAgent):
    def _forecast_adjustment(self, observation: MarketObservation, trend: float) -> float:
        return 0.25 * trend + 0.15 * max(0.0, observation.own_last_shortage)

    def _price_adjustment(self, observation: MarketObservation, forecast: int) -> float:
        del forecast
        inventory_pressure = max(0.0, 35.0 - observation.own_inventory) / 100.0
        competition_discount = max(0.0, 0.25 - observation.own_reputation) * 0.5
        return -0.35 + 0.05 * inventory_pressure - competition_discount - 0.01 * observation.market_volatility

    def _quantity_target(self, observation: MarketObservation, forecast: int) -> float:
        urgency = max(0.0, forecast - observation.own_inventory)
        return forecast * 0.95 + urgency * 0.35 + max(0.0, 20.0 - observation.own_inventory)


class PremiumCloudAgent(HeuristicAgent):
    def _forecast_adjustment(self, observation: MarketObservation, trend: float) -> float:
        return 0.15 * trend + 0.05 * observation.own_reputation

    def _price_adjustment(self, observation: MarketObservation, forecast: int) -> float:
        del forecast
        reputation_premium = 0.55 + 0.35 * observation.own_reputation
        volatility_premium = 0.04 * observation.market_volatility
        return reputation_premium + volatility_premium

    def _quantity_target(self, observation: MarketObservation, forecast: int) -> float:
        return forecast * 0.72 + max(0.0, 12.0 - observation.own_inventory) * 0.3


class SpotBrokerAgent(HeuristicAgent):
    def _forecast_adjustment(self, observation: MarketObservation, trend: float) -> float:
        return 0.45 * trend + 0.08 * observation.market_volatility

    def _price_adjustment(self, observation: MarketObservation, forecast: int) -> float:
        del forecast
        inventory_pressure = max(0.0, observation.own_inventory - 15.0) / 120.0
        trend_discount = -0.08 * max(0.0, observation.own_last_shortage)
        return 0.08 - 0.28 * inventory_pressure + trend_discount

    def _quantity_target(self, observation: MarketObservation, forecast: int) -> float:
        return forecast * 0.58 + observation.market_volatility * 0.8 + max(0.0, 10.0 - observation.own_inventory) * 0.5


ROLE_GUIDANCE = {
    "hyperscaler": "You are the scale leader. Prioritize market share and continuity while avoiding catastrophic overstock.",
    "premium": "You are the premium cloud provider. Prioritize reputation, SLA stability, and disciplined pricing.",
    "spot": "You are the spot broker. Prioritize agility, short-term opportunities, and inventory flexibility.",
}
class LLMPlanningStage:
    def __init__(self, config: AgentConfig, *, llm_config: LLMConfig, client: Any) -> None:
        self._config = config
        self._llm_config = llm_config
        self._client = client
        self._cache_key: tuple[Any, ...] | None = None
        self._cache_value: dict[str, Any] | None = None
        self._last_reasoning: str = ""
        self._last_strategy_adjustment: str = ""
        self._memory: list[dict[str, Any]] = []
        self._strategy_memory: list[dict[str, Any]] = []
        self._evolution_params = {
            "price_bias": 0.0,
            "quantity_bias": 0.0,
            "forecast_bias": 0.0,
        }
        self._evolution_limits = {
            "price_bias": (-0.6, 0.6, 0.2),
            "quantity_bias": (-25, 25, 8),
            "forecast_bias": (-12, 12, 4),
        }

    def add_memory(self, round_idx: int, price: float, quantity: int,
                   forecast: int, profit: float, reputation: float,
                   shortage: float) -> None:
        self._memory.append({
            "round": round_idx,
            "price": price,
            "quantity": quantity,
            "forecast": forecast,
            "profit": profit,
            "reputation": reputation,
            "shortage": shortage,
        })
        if len(self._memory) > 3:
            self._memory.pop(0)

    def record_result_memory(self, result: dict[str, Any]) -> None:
        if not self._memory:
            return
        self._memory[-1].update({
            "realized_sales": result.get("realized_sales", 0),
            "revenue": result.get("revenue", 0),
            "allocated_demand": result.get("allocated_demand", 0),
            "sla_penalty": result.get("sla_penalty", 0),
            "prod_cost": result.get("prod_cost", 0),
            "holding_cost": result.get("holding_cost", 0),
            "obsolescence_cost": result.get("obsolescence_cost", 0),
            "transfer_cost": result.get("transfer_cost", 0),
            "transfer_revenue": result.get("transfer_revenue", 0),
        })

    def evolve(self, round_index: int) -> dict[str, Any] | None:
        """Trigger an evolution round every 3 rounds."""
        if not self._memory:
            return None
        payload = {
            "agent_name": self._config.name,
            "agent_role": self._config.role,
            "phase_end_round": round_index,
            "current_evolution_params": dict(self._evolution_params),
            "param_constraints": {
                k: {"min": v[0], "max": v[1], "max_delta_per_evolution": v[2]}
                for k, v in self._evolution_limits.items()
            },
            "recent_performance": self._memory,
            "instruction": (
                "You are conducting a 3-round strategic review. Based on recent performance, "
                "provide: 1) a brief summary of what worked and what didn't; "
                "2) specific suggestions for the next 3-round phase; "
                "3) proposed param_adjustments (price_bias, quantity_bias, forecast_bias). "
                "Each adjustment MUST respect max_delta_per_evolution. Small tweaks only. "
                "Return JSON with keys: summary, suggestions, param_adjustments."
            ),
        }
        messages = [
            {"role": "system", "content": "You are a strategy consultant reviewing a GPU supplier's recent market performance."},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=True, separators=(",", ":"))},
        ]
        try:
            plan = query_json_completion(
                client=self._client,
                llm_config=self._llm_config,
                messages=messages,
            )
        except Exception:
            return None
        adjustments = plan.get("param_adjustments", {})
        for key, delta in adjustments.items():
            if key in self._evolution_params and key in self._evolution_limits:
                min_v, max_v, max_delta = self._evolution_limits[key]
                clamped_delta = max(-max_delta, min(max_delta, float(delta)))
                self._evolution_params[key] = max(min_v, min(max_v, self._evolution_params[key] + clamped_delta))
        record = {
            "phase_end_round": round_index,
            "summary": str(plan.get("summary", "")).strip(),
            "suggestions": str(plan.get("suggestions", "")).strip(),
            "param_adjustments": dict(self._evolution_params),
        }
        self._strategy_memory.append(record)
        if len(self._strategy_memory) > 3:
            self._strategy_memory.pop(0)
        return record

    def _cache_token(self, observation: MarketObservation) -> tuple[Any, ...]:
        return (
            observation.round_index,
            observation.observed_demand,
            observation.own_inventory,
            observation.own_last_profit,
            observation.own_last_shortage,
            observation.own_reputation,
            observation.market_avg_price,
            observation.market_volatility,
        )

    def run(self, observation: MarketObservation, fallback: AgentAction) -> dict[str, Any]:
        token = self._cache_token(observation)
        if self._cache_key == token and self._cache_value is not None:
            return self._cache_value
        self._last_reasoning = ""
        self._last_strategy_adjustment = ""
        messages = [
            {"role": "system", "content": self._system_prompt(compact=False)},
            {"role": "user", "content": self._user_prompt(observation, fallback, compact=False)},
        ]
        retry_messages = [
            {"role": "system", "content": self._system_prompt(compact=True)},
            {"role": "user", "content": self._user_prompt(observation, fallback, compact=True)},
        ]
        plan = query_json_completion(
            client=self._client,
            llm_config=self._llm_config,
            messages=messages,
            retry_messages=retry_messages,
        )
        self._last_reasoning = str(plan.get("reasoning", "")).strip()
        self._last_strategy_adjustment = str(plan.get("strategy_adjustment", "")).strip()
        self._cache_key = token
        self._cache_value = plan
        return plan

    def _system_prompt(self, *, compact: bool) -> str:
        role_guidance = ROLE_GUIDANCE.get(self._config.role, "Act as a rational market participant.")
        linear = self._config.linear_cost
        quadratic = self._config.quadratic_cost
        avg_cost_example = linear + quadratic * 50
        cost_note = (
            f"COST STRUCTURE: avg production cost per unit = ${linear:.2f} + ${quadratic:.3f} * quantity. "
            f"Example: at qty=50, avg cost=${avg_cost_example:.2f}/unit. "
            f"Price MUST be >= avg cost. Your legal floor is ${self._config.price_floor:.2f}, economic floor is avg cost.\n"
        )
        rep_note = (
            "REPUTATION SYSTEM (3 dimensions, each 0-1):\n"
            "- delivery_rep: how reliably you meet demand.\n"
            "- pricing_fairness_rep: whether you price fairly (not dumping).\n"
            "- cooperation_rep: how willing you are to help competitors in shortage (indirect reciprocity applies: if you refuse help, ALL observers may lower your cooperation_rep).\n"
        )
        profit_note = (
            "SIMPLE PROFIT RULE (follow strictly):\n"
            f"1. avg_cost = ${linear:.2f} + ${quadratic:.3f} * quantity.\n"
            f"2. Price MUST be >= avg_cost + $0.50 to cover holding, obsolescence, and SLA risks.\n"
            "3. ONLY sold units make revenue. Unsold inventory loses money.\n"
            "4. If you cannot charge a profitable price, REDUCE QUANTITY until you can.\n"
            "5. NEVER submit a plan you know will lose money.\n"
        )
        evo_parts: list[str] = []
        if self._strategy_memory:
            latest = self._strategy_memory[-1]
            evo_parts.append(f"LATEST STRATEGY REVIEW (after round {latest.get('phase_end_round', '?')}):")
            evo_parts.append(f"Summary: {latest.get('summary', '')}")
            evo_parts.append(f"Suggestions: {latest.get('suggestions', '')}")
        evo_parts.append(
            f"CURRENT EVOLUTION PARAMS (automatically applied to your raw decision):\n"
            f"- price_bias: {self._evolution_params['price_bias']:.2f}\n"
            f"- quantity_bias: {self._evolution_params['quantity_bias']:.1f}\n"
            f"- forecast_bias: {self._evolution_params['forecast_bias']:.1f}\n"
            "You do NOT need to manually add these. Output your base decision; the system will apply them."
        )
        evolution_text = "\n".join(evo_parts)
        prompt = (
            f"You are the CEO of {self._config.name}, a GPU supplier in a competitive spot market.\n"
            f"Your company's natural style: {self._config.persona}\n"
            f"{role_guidance}\n"
            f"{cost_note}"
            f"{rep_note}"
            f"{profit_note}"
            "As CEO, your #1 JOB is PROFIT MAXIMIZATION (short-term AND long-term). Maintain your character, but NEVER sacrifice profit for market share.\n"
            "HARD BUSINESS RULES:\n"
            "1. Price MUST be >= avg production cost.\n"
            "2. If you lost money last round: raise price OR reduce quantity.\n"
            "3. If you had leftover inventory: reduce quantity next round.\n"
            "4. If you had shortages: increase quantity OR raise price.\n"
            "5. NEVER price below cost to 'capture share' — that is business suicide.\n"
            f"{evolution_text}\n"
            "DECISION PROCESS:\n"
            "1. Review last round's profit, inventory, and shortages.\n"
            "2. Calculate expected profit for your proposed (forecast, price, quantity).\n"
            "3. If expected profit <= 0, revise price upward or quantity downward.\n"
            "4. Pick the combination that maximizes expected profit.\n"
            "Return only valid JSON with keys: forecast_demand, price, quantity, reasoning, strategy_adjustment.\n"
            "In reasoning: state your cost calc, expected profit, and why this decision is smart. Use plain text only.\n"
            "In strategy_adjustment: describe what you changed from last round and why. Use plain text only.\n"
            "Do not add markdown or explanations outside the JSON."
        )
        if compact:
            prompt += "\nOutput one minified JSON object on a single line. Keep it under 100 tokens."
        return prompt

    def _user_prompt(self, observation: MarketObservation, fallback: AgentAction, *, compact: bool) -> str:
        history_prices = [list(round_prices) for round_prices in observation.price_history[-3:]]
        history_reputation = [list(round_reputations) for round_reputations in observation.reputation_history[-3:]]
        peer_reps = list(observation.peer_reputations)
        peer_ranks = sorted(peer_reps, key=lambda x: x[1], reverse=True)
        peer_summary = [
            {"name": name, "rank": idx + 1}
            for idx, (name, _) in enumerate(peer_ranks)
        ]
        payload: dict[str, Any] = {
            "agent_name": self._config.name,
            "agent_role": self._config.role,
            "agent_persona": self._config.persona,
            "stage_styles": {
                "forecaster": self._config.forecaster_style,
                "pricer": self._config.pricer_style,
                "allocator": self._config.allocator_style,
                "risk_gate": self._config.risk_style,
            },
            "round_index": observation.round_index,
            "observed_demand": observation.observed_demand,
            "observed_demand_history": list(observation.observed_demand_history[-3:]),
            "price_history": history_prices,
            "reputation_history": history_reputation,
            "peer_reputation_ranks": peer_summary,
            "own_inventory": observation.own_inventory,
            "own_last_profit": observation.own_last_profit,
            "own_last_shortage": observation.own_last_shortage,
            "own_reputation": observation.own_reputation,
            "own_reputation_dimensions": {
                "delivery": observation.own_reputation_delivery,
                "pricing_fairness": observation.own_reputation_pricing,
                "cooperation": observation.own_reputation_cooperation,
            },
            "market_avg_price": observation.market_avg_price,
            "market_volatility": observation.market_volatility,
            "legal_price_range": {
                "min": self._config.price_floor,
                "max": self._config.price_ceiling,
                "step": self._config.price_step,
            },
            "legal_quantity_range": {
                "min": 0,
                "max": self._config.max_quantity,
                "step": self._config.quantity_step,
            },
            "fallback_action": {
                "forecast_demand": fallback.forecast_demand,
                "price": fallback.price,
                "quantity": fallback.quantity,
            },
            "instruction": (
                "Follow the ROUND-BY-ROUND PROCESS in your system prompt. "
                "Evaluate expected profit before finalizing your decision."
            ),
        }
        cost_refs = [
            {"qty": int(self._config.max_quantity * 0.5), "avg_cost": round(self._config.linear_cost + self._config.quadratic_cost * (self._config.max_quantity * 0.5), 2)},
            {"qty": int(self._config.max_quantity * 0.75), "avg_cost": round(self._config.linear_cost + self._config.quadratic_cost * (self._config.max_quantity * 0.75), 2)},
            {"qty": self._config.max_quantity, "avg_cost": round(self._config.linear_cost + self._config.quadratic_cost * self._config.max_quantity, 2)},
        ]
        if self._memory:
            enriched_memory = []
            profits = []
            prices = []
            quantities = []
            for m in self._memory:
                em = dict(m)
                realized = em.get("realized_sales", 0)
                allocated = em.get("allocated_demand", 0)
                profit = em.get("profit", 0)
                qty = em.get("quantity", 1)
                sla = em.get("sla_penalty", 0)
                prod = em.get("prod_cost", 0)
                hold = em.get("holding_cost", 0)
                obsol = em.get("obsolescence_cost", 0)
                total_cost = prod + hold + obsol + sla
                em["unit_profit"] = round(profit / max(realized, 1), 2) if realized > 0 else round(profit, 2)
                em["stock_coverage"] = round(qty / max(allocated, 1), 2) if allocated > 0 else 0.0
                em["shortage_cost_ratio"] = round(sla / max(total_cost, 1), 2) if total_cost > 0 else 0.0
                enriched_memory.append(em)
                profits.append(profit)
                prices.append(em.get("price", 0))
                quantities.append(qty)
            payload["recent_performance"] = enriched_memory
            payload["metric_guide"] = (
                "unit_profit = profit / realized_sales. "
                "stock_coverage = quantity / allocated_demand (>1 surplus, <1 shortage). "
                "shortage_cost_ratio = sla_penalty / total_cost (high = understocking hurts)."
            )
            avg_price = sum(prices) / len(prices) if prices else 0
            avg_qty = sum(quantities) / len(quantities) if quantities else 0
            profit_trend = "improving" if profits and profits[-1] > profits[0] else "declining" if profits and profits[-1] < profits[0] else "stable"
            payload["behavioral_summary"] = {
                "recent_avg_price": round(avg_price, 2),
                "recent_avg_quantity": round(avg_qty, 1),
                "profit_trend": profit_trend,
                "note": "This is your observed behavior. Use it to assess whether your current parameter state is aligned with your profit objective.",
            }
        payload["cost_reference"] = cost_refs
        if compact:
            payload = {
                "round_index": observation.round_index,
                "observed_demand": observation.observed_demand,
                "own_inventory": observation.own_inventory,
                "own_reputation": observation.own_reputation,
                "market_avg_price": observation.market_avg_price,
                "market_volatility": observation.market_volatility,
                "legal_price_range": payload["legal_price_range"],
                "legal_quantity_range": payload["legal_quantity_range"],
                "fallback_action": payload["fallback_action"],
                "recent_performance": payload.get("recent_performance", []),
                "instruction": "Return minified JSON only with forecast_demand, price, quantity, reasoning, strategy_adjustment.",
            }
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


class LLMForecasterStage:
    def __init__(self, planner: LLMPlanningStage) -> None:
        self._planner = planner

    def run(self, observation: MarketObservation, *, fallback: AgentAction | None = None) -> int:
        if fallback is None:
            raise ValueError("fallback action is required for LLM forecast stage")
        plan = self._planner.run(observation, fallback)
        return max(0, int(round(float(plan.get("forecast_demand", fallback.forecast_demand)))))


class LLMPricerStage:
    def __init__(self, config: AgentConfig, planner: LLMPlanningStage) -> None:
        self._config = config
        self._planner = planner

    def run(
        self,
        observation: MarketObservation,
        forecast: int,
        *,
        fallback: AgentAction | None = None,
    ) -> float:
        del forecast
        if fallback is None:
            raise ValueError("fallback action is required for LLM price stage")
        plan = self._planner.run(observation, fallback)
        return round_to_step(
            float(plan.get("price", fallback.price)),
            self._config.price_step,
            self._config.price_floor,
            self._config.price_ceiling,
        )


class LLMAllocatorStage:
    def __init__(self, config: AgentConfig, planner: LLMPlanningStage) -> None:
        self._config = config
        self._planner = planner

    def run(
        self,
        observation: MarketObservation,
        forecast: int,
        price: float,
        *,
        fallback: AgentAction | None = None,
    ) -> int:
        del forecast
        del price
        if fallback is None:
            raise ValueError("fallback action is required for LLM allocation stage")
        plan = self._planner.run(observation, fallback)
        return int_round_to_step(
            float(plan.get("quantity", fallback.quantity)),
            self._config.quantity_step,
            0,
            self._config.max_quantity,
        )


class LLMPolicyAgent(RolePipelineAgent):
    def __init__(
        self,
        config: AgentConfig,
        *,
        llm_config: LLMConfig,
        fallback_agent: HeuristicAgent,
        client: Any,
    ) -> None:
        self._planner = LLMPlanningStage(config, llm_config=llm_config, client=client)
        super().__init__(
            config,
            forecaster=LLMForecasterStage(self._planner),
            pricer=LLMPricerStage(config, self._planner),
            allocator=LLMAllocatorStage(config, self._planner),
            risk_gate=RiskGateStage(config),
        )
        self._fallback_agent = fallback_agent

    def decide(self, observation: MarketObservation) -> AgentAction:
        fallback = self._fallback_agent.decide(observation)
        try:
            result = self._run_pipeline(observation, fallback=fallback)
            reasoning = getattr(self._planner, '_last_reasoning', '') or ''
            strategy_adjustment = getattr(self._planner, '_last_strategy_adjustment', '') or ''

            # 1. Apply evolution offsets at code level
            evo = self._planner._evolution_params
            forecast = max(0, int(round(result.forecast_demand + evo["forecast_bias"])))
            price = round_to_step(
                result.price + evo["price_bias"],
                self.config.price_step,
                self.config.price_floor,
                self.config.price_ceiling,
            )
            quantity = int_round_to_step(
                result.quantity + evo["quantity_bias"],
                self.config.quantity_step,
                0,
                self.config.max_quantity,
            )

            # 2. Cost safety: price must cover average production cost
            avg_cost = self.config.linear_cost + self.config.quadratic_cost * quantity
            if price < avg_cost:
                price = avg_cost + self.config.price_step
                price = round_to_step(
                    price,
                    self.config.price_step,
                    self.config.price_floor,
                    self.config.price_ceiling,
                )
                reasoning += f" [Cost safety: raised price to {price:.2f} to cover avg cost {avg_cost:.2f}]"

            self._planner.add_memory(
                round_idx=observation.round_index,
                price=price,
                quantity=quantity,
                forecast=forecast,
                profit=observation.own_last_profit,
                reputation=observation.own_reputation,
                shortage=observation.own_last_shortage,
            )
            return AgentAction(
                forecast_demand=forecast,
                price=price,
                quantity=quantity,
                reasoning=reasoning,
                strategy_adjustment=strategy_adjustment,
            )
        except Exception:
            return fallback

    def record_result(self, result: dict[str, Any]) -> None:
        self._planner.record_result_memory(result)

    def evolve_strategy(self, round_index: int) -> dict[str, Any] | None:
        return self._planner.evolve(round_index)


def _build_heuristic_agent(cfg: AgentConfig) -> HeuristicAgent:
    if cfg.role == "hyperscaler":
        return HyperscalerAgent(cfg)
    if cfg.role == "premium":
        return PremiumCloudAgent(cfg)
    if cfg.role == "spot":
        return SpotBrokerAgent(cfg)
    return HeuristicAgent(cfg)


def _build_heuristic_agents(
    configs: Sequence[AgentConfig],
    llm_config: LLMConfig | None = None,
) -> dict[str, HeuristicAgent]:
    del llm_config
    return {cfg.name: _build_heuristic_agent(cfg) for cfg in configs}


def _build_llm_agents(
    configs: Sequence[AgentConfig],
    llm_config: LLMConfig | None = None,
) -> dict[str, HeuristicAgent]:
    if llm_config is None:
        raise ValueError("llm_config is required when mode='llm'")
    if not llm_config.api_key:
        raise ValueError("llm_config.api_key is required when mode='llm'")
    client = _build_openai_client(llm_config)
    agents: dict[str, HeuristicAgent] = {}
    for cfg in configs:
        fallback_agent = _build_heuristic_agent(cfg)
        agents[cfg.name] = LLMPolicyAgent(
            cfg,
            llm_config=llm_config,
            fallback_agent=fallback_agent,
            client=client,
        )
    return agents


_BUILTINS_REGISTERED = False


def ensure_builtin_strategies_registered() -> None:
    global _BUILTINS_REGISTERED
    if _BUILTINS_REGISTERED and has_strategy("heuristic") and has_strategy("llm"):
        return
    register_strategy("heuristic", title="Heuristic", builder=_build_heuristic_agents, replace=True)
    register_strategy("llm", title="LLM", builder=_build_llm_agents, replace=True)
    _BUILTINS_REGISTERED = True


def build_agents(
    configs: Sequence[AgentConfig],
    *,
    mode: str = "heuristic",
    llm_config: LLMConfig | None = None,
) -> dict[str, HeuristicAgent]:
    ensure_builtin_strategies_registered()
    return build_registered_agents(mode, configs, llm_config=llm_config)


__all__ = [
    "AgentAction",
    "MarketObservation",
    "HeuristicAgent",
    "HyperscalerAgent",
    "PremiumCloudAgent",
    "SpotBrokerAgent",
    "LLMPolicyAgent",
    "build_agents",
    "ensure_builtin_strategies_registered",
]
