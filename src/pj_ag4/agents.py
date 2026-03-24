from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from typing import Sequence

from .config import AgentConfig, LLMConfig
from .utils import int_round_to_step, rolling_volatility, round_to_step, weighted_forecast


@dataclass(frozen=True)
class AgentAction:
    forecast_demand: int
    price: float
    quantity: int


@dataclass(frozen=True)
class MarketObservation:
    round_index: int
    observed_demand: int
    demand_history: tuple[int, ...]
    observed_demand_history: tuple[int, ...]
    price_history: tuple[tuple[float, ...], ...]
    reputation_history: tuple[tuple[float, ...], ...]
    peer_reputations: tuple[tuple[str, float], ...]
    own_inventory: float
    own_last_profit: float
    own_last_shortage: float
    own_reputation: float
    market_avg_price: float
    market_volatility: float


def _build_openai_client(llm_config: LLMConfig):
    from openai import OpenAI

    return OpenAI(
        base_url=llm_config.base_url,
        api_key=llm_config.api_key,
        timeout=llm_config.timeout_seconds,
    )


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object found in LLM response")
    return json.loads(raw_text[start : end + 1])


def _safe_message_content(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            text = getattr(item, "text", None)
            if text:
                parts.append(text)
        return "\n".join(parts)
    return str(content)


def _choice_finish_reason(choice: Any) -> str | None:
    finish_reason = getattr(choice, "finish_reason", None)
    return str(finish_reason) if finish_reason is not None else None


class HeuristicAgent:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config

    def decide(self, observation: MarketObservation) -> AgentAction:
        forecast = self._forecast_demand(observation)
        price = self._price(observation, forecast)
        quantity = self._quantity(observation, forecast)
        return AgentAction(forecast_demand=forecast, price=price, quantity=quantity)

    def _forecast_demand(self, observation: MarketObservation) -> int:
        history = observation.observed_demand_history
        base = weighted_forecast(history, short_window=3)
        trend = 0.0
        if len(history) >= 2:
            trend = (history[-1] - history[0]) / max(1, len(history) - 1)
        forecast = 0.7 * base + 0.3 * (history[-1] if history else observation.observed_demand)
        forecast += self._forecast_adjustment(observation, trend)
        return max(0, int(round(forecast)))

    def _forecast_adjustment(self, observation: MarketObservation, trend: float) -> float:
        return 0.0

    def _price(self, observation: MarketObservation, forecast: int) -> float:
        value = self.config.base_price + self._price_adjustment(observation, forecast)
        return round_to_step(value, self.config.price_step, self.config.price_floor, self.config.price_ceiling)

    def _price_adjustment(self, observation: MarketObservation, forecast: int) -> float:
        return 0.0

    def _quantity(self, observation: MarketObservation, forecast: int) -> int:
        target = self._quantity_target(observation, forecast)
        return int_round_to_step(target, self.config.quantity_step, 0, self.config.max_quantity)

    def _quantity_target(self, observation: MarketObservation, forecast: int) -> float:
        return float(forecast)


class HyperscalerAgent(HeuristicAgent):
    def _forecast_adjustment(self, observation: MarketObservation, trend: float) -> float:
        return 0.25 * trend + 0.15 * max(0.0, observation.own_last_shortage)

    def _price_adjustment(self, observation: MarketObservation, forecast: int) -> float:
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
        reputation_premium = 0.55 + 0.35 * observation.own_reputation
        volatility_premium = 0.04 * observation.market_volatility
        return reputation_premium + volatility_premium

    def _quantity_target(self, observation: MarketObservation, forecast: int) -> float:
        return forecast * 0.72 + max(0.0, 12.0 - observation.own_inventory) * 0.3


class SpotBrokerAgent(HeuristicAgent):
    def _forecast_adjustment(self, observation: MarketObservation, trend: float) -> float:
        return 0.45 * trend + 0.08 * observation.market_volatility

    def _price_adjustment(self, observation: MarketObservation, forecast: int) -> float:
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


class LLMPolicyAgent(HeuristicAgent):
    def __init__(
        self,
        config: AgentConfig,
        *,
        llm_config: LLMConfig,
        fallback_agent: HeuristicAgent,
        client: Any,
    ) -> None:
        super().__init__(config)
        self._llm_config = llm_config
        self._fallback_agent = fallback_agent
        self._client = client

    def decide(self, observation: MarketObservation) -> AgentAction:
        fallback = self._fallback_agent.decide(observation)
        try:
            parsed = self._query_llm(observation, fallback)
            forecast = max(0, int(round(float(parsed.get("forecast_demand", fallback.forecast_demand)))))
            price = round_to_step(
                float(parsed.get("price", fallback.price)),
                self.config.price_step,
                self.config.price_floor,
                self.config.price_ceiling,
            )
            quantity = int_round_to_step(
                float(parsed.get("quantity", fallback.quantity)),
                self.config.quantity_step,
                0,
                self.config.max_quantity,
            )
            return AgentAction(forecast_demand=forecast, price=price, quantity=quantity)
        except Exception:
            return fallback

    def _query_llm(self, observation: MarketObservation, fallback: AgentAction) -> dict[str, Any]:
        if not self._llm_config.api_key:
            raise ValueError("missing LLM API key")
        messages = [
            {
                "role": "system",
                "content": self._system_prompt(compact=False),
            },
            {
                "role": "user",
                "content": self._user_prompt(observation, fallback, compact=False),
            },
        ]
        max_tokens = self._llm_config.max_tokens
        last_error: Exception | None = None
        total_attempts = self._llm_config.max_retries + 1
        for attempt in range(total_attempts):
            response = self._client.chat.completions.create(
                model=self._llm_config.model,
                temperature=self._llm_config.temperature,
                max_tokens=max_tokens,
                messages=messages,
            )
            choice = response.choices[0]
            finish_reason = _choice_finish_reason(choice)
            raw_content = _safe_message_content(choice.message).strip()
            try:
                return _extract_json_object(raw_content)
            except Exception as exc:
                last_error = exc
                if finish_reason != "length" and raw_content:
                    break
                if attempt >= total_attempts - 1:
                    break
                max_tokens = min(max_tokens * 2, 2048)
                messages = [
                    {
                        "role": "system",
                        "content": self._system_prompt(compact=True),
                    },
                    {
                        "role": "user",
                        "content": self._user_prompt(observation, fallback, compact=True),
                    },
                ]
        raise ValueError(f"LLM output parse failed: {last_error}") from last_error

    def _system_prompt(self, *, compact: bool) -> str:
        role_guidance = ROLE_GUIDANCE.get(self.config.role, "Act as a rational market participant.")
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
            "agent_name": self.config.name,
            "agent_role": self.config.role,
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
                "min": self.config.price_floor,
                "max": self.config.price_ceiling,
                "step": self.config.price_step,
            },
            "legal_quantity_range": {
                "min": 0,
                "max": self.config.max_quantity,
                "step": self.config.quantity_step,
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


def _build_heuristic_agent(cfg: AgentConfig) -> HeuristicAgent:
    if cfg.role == "hyperscaler":
        return HyperscalerAgent(cfg)
    if cfg.role == "premium":
        return PremiumCloudAgent(cfg)
    if cfg.role == "spot":
        return SpotBrokerAgent(cfg)
    return HeuristicAgent(cfg)


def build_agents(
    configs: Sequence[AgentConfig],
    *,
    mode: str = "heuristic",
    llm_config: LLMConfig | None = None,
) -> dict[str, HeuristicAgent]:
    agents: dict[str, HeuristicAgent] = {}
    normalized_mode = mode.lower()
    client = None
    if normalized_mode == "llm":
        if llm_config is None:
            raise ValueError("llm_config is required when mode='llm'")
        if not llm_config.api_key:
            raise ValueError("llm_config.api_key is required when mode='llm'")
        client = _build_openai_client(llm_config)
    for cfg in configs:
        fallback_agent = _build_heuristic_agent(cfg)
        if normalized_mode == "llm":
            agents[cfg.name] = LLMPolicyAgent(
                cfg,
                llm_config=llm_config,
                fallback_agent=fallback_agent,
                client=client,
            )
            continue
        agents[cfg.name] = fallback_agent
    return agents
