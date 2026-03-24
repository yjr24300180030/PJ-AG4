from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .config import AgentConfig
from .utils import clamp, int_round_to_step, rolling_mean, rolling_volatility, round_to_step, weighted_forecast


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


def build_agents(configs: Sequence[AgentConfig]) -> dict[str, HeuristicAgent]:
    agents: dict[str, HeuristicAgent] = {}
    for cfg in configs:
        if cfg.role == "hyperscaler":
            agents[cfg.name] = HyperscalerAgent(cfg)
        elif cfg.role == "premium":
            agents[cfg.name] = PremiumCloudAgent(cfg)
        elif cfg.role == "spot":
            agents[cfg.name] = SpotBrokerAgent(cfg)
        else:
            agents[cfg.name] = HeuristicAgent(cfg)
    return agents

