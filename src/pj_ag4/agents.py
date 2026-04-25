from __future__ import annotations

import json
from typing import Any, Sequence

from .config import AgentConfig, LLMConfig
from .contracts import AgentAction, MarketObservation
from .providers import build_openai_client, query_json_completion
from .strategy_registry import build_registered_agents, has_strategy, register_strategy
from .utils import clamp, int_round_to_step, round_to_step, weighted_forecast

_build_openai_client = build_openai_client


FORECASTER_STYLE_GUIDANCE = {
    "momentum_chaser": "Lean into trend continuation and respond quickly to rising demand pressure.",
    "signal_smoother": "Discount noisy spikes and prefer stable, reputation-aware demand estimates.",
    "volatility_reader": "React to short-term volatility and treat market swings as exploitable signals.",
}

PRICER_STYLE_GUIDANCE = {
    "share_grabber": "Use aggressive pricing to capture flow and tolerate thinner margins.",
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


def _expected_capture_share(config: AgentConfig, observation: MarketObservation, planned_price: float) -> float:
    peer_reputations = [value for name, value in observation.peer_reputations if name != config.name]
    agent_count = max(1, len(peer_reputations) + 1)
    base_share = 1.0 / agent_count
    avg_peer_reputation = sum(peer_reputations) / len(peer_reputations) if peer_reputations else observation.own_reputation
    reputation_edge = 0.45 * (observation.own_reputation - avg_peer_reputation)
    price_edge = -0.18 * (planned_price - observation.market_avg_price)
    style_bias = 0.0
    if config.pricer_style == "share_grabber":
        style_bias += 0.06
    elif config.pricer_style == "premium_keeper":
        style_bias -= 0.04
    return clamp(base_share + reputation_edge + price_edge + style_bias, 0.12, 0.72)


def _inventory_target_total(
    config: AgentConfig,
    observation: MarketObservation,
    forecast: int,
    planned_price: float,
) -> float:
    expected_share = _expected_capture_share(config, observation, planned_price)
    expected_captured_demand = forecast * expected_share
    shortage_buffer = min(observation.own_last_shortage, max(6.0, forecast * 0.12))
    if config.risk_style == "growth_tolerant":
        return max(18.0, expected_captured_demand * 1.18 + 10.0 + shortage_buffer)
    if config.risk_style == "sla_guard":
        return max(16.0, expected_captured_demand * 1.10 + 8.0 + 0.8 * shortage_buffer)
    if config.risk_style == "inventory_guard":
        return max(12.0, expected_captured_demand * 0.92 + 5.0 + 0.5 * shortage_buffer)
    return max(15.0, expected_captured_demand + 6.0 + 0.6 * shortage_buffer)


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
        inventory_target_total = _inventory_target_total(
            self._config,
            observation,
            reviewed_forecast,
            reviewed_price,
        )
        reviewed_quantity = min(
            reviewed_quantity,
            max(0.0, inventory_target_total - observation.own_inventory),
        )
        if fallback is not None and observation.own_reputation < 0.35:
            reviewed_price = max(reviewed_price, fallback.price)
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
        trend = 0.0
        if not history:
            forecast = float(observation.observed_demand)
        else:
            base = weighted_forecast(history, short_window=3)
            forecast = 0.7 * base + 0.3 * history[-1]
        if len(history) >= 2:
            trend = (history[-1] - history[0]) / max(1, len(history) - 1)
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
        self._cache_key = token
        self._cache_value = plan
        return plan

    def _system_prompt(self, *, compact: bool) -> str:
        role_guidance = ROLE_GUIDANCE.get(self._config.role, "Act as a rational market participant.")
        stage_guidance = (
            f"Agent persona: {self._config.persona}\n"
            "Decision chain style:\n"
            f"- Forecaster: {FORECASTER_STYLE_GUIDANCE.get(self._config.forecaster_style, self._config.forecaster_style)}\n"
            f"- Pricer: {PRICER_STYLE_GUIDANCE.get(self._config.pricer_style, self._config.pricer_style)}\n"
            f"- Allocator: {ALLOCATOR_STYLE_GUIDANCE.get(self._config.allocator_style, self._config.allocator_style)}\n"
            f"- RiskGate: {RISK_STYLE_GUIDANCE.get(self._config.risk_style, self._config.risk_style)}\n"
        )
        prompt = (
            "You are a market simulation agent in a repeated GPU spot market game.\n"
            f"{role_guidance}\n"
            f"{stage_guidance}"
            "Return only valid JSON with exactly these keys: "
            '"forecast_demand", "price", "quantity".\n'
            "Use numeric values only. Do not add markdown or explanations."
        )
        if compact:
            prompt += "\nOutput one minified JSON object on a single line. Keep it under 40 tokens."
        return prompt

    def _user_prompt(self, observation: MarketObservation, fallback: AgentAction, *, compact: bool) -> str:
        history_prices = [list(round_prices) for round_prices in observation.price_history[-5:]]
        history_reputation = [list(round_reputations) for round_reputations in observation.reputation_history[-5:]]
        payload = {
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
            "observed_demand_history": list(observation.observed_demand_history[-5:]),
            "price_history": history_prices,
            "reputation_history": history_reputation,
            "peer_reputations": list(observation.peer_reputations),
            "own_inventory": observation.own_inventory,
            "own_last_profit": observation.own_last_profit,
            "own_last_shortage": observation.own_last_shortage,
            "own_reputation": observation.own_reputation,
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
                "Choose one-round-ahead demand forecast, price, and added quantity. "
                "Set quantity for your expected captured share of demand rather than the full market total. "
                "Stay within legal ranges. Favor valid JSON over verbosity."
            ),
        }
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
                "instruction": "Return minified JSON only with forecast_demand, price, quantity. Quantity should reflect expected captured share, not whole-market demand.",
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
        planner = LLMPlanningStage(config, llm_config=llm_config, client=client)
        super().__init__(
            config,
            forecaster=LLMForecasterStage(planner),
            pricer=LLMPricerStage(config, planner),
            allocator=LLMAllocatorStage(config, planner),
            risk_gate=RiskGateStage(config),
        )
        self._fallback_agent = fallback_agent

    def decide(self, observation: MarketObservation) -> AgentAction:
        fallback = self._fallback_agent.decide(observation)
        try:
            return self._run_pipeline(observation, fallback=fallback)
        except Exception:
            return fallback


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
