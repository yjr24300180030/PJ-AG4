from __future__ import annotations

import json
from typing import Any, Sequence

from .config import AgentConfig, LLMConfig
from .contracts import AgentAction, MarketObservation
from .providers import build_openai_client, query_json_completion
from .strategy_registry import build_registered_agents, has_strategy, register_strategy
from .utils import int_round_to_step, round_to_step, weighted_forecast

_build_openai_client = build_openai_client


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
        del observation
        del fallback
        return AgentAction(
            forecast_demand=max(0, int(round(draft.forecast_demand))),
            price=round_to_step(
                draft.price,
                self._config.price_step,
                self._config.price_floor,
                self._config.price_ceiling,
            ),
            quantity=int_round_to_step(
                draft.quantity,
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
        prompt = (
            "You are a market simulation agent in a repeated GPU spot market game.\n"
            f"{role_guidance}\n"
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
                "instruction": "Return minified JSON only with forecast_demand, price, quantity.",
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
