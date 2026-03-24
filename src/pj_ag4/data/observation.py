from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Mapping

from ..contracts import AgentAction, MarketObservation
from ..environment import MarketEnvironment
from ..timeseries import DemandSnapshot
from ..utils import rolling_volatility


@dataclass
class ObservationHistory:
    demand_history: list[int] = field(default_factory=list)
    observed_history: list[int] = field(default_factory=list)
    price_history: list[list[float]] = field(default_factory=list)
    reputation_history: list[list[float]] = field(default_factory=list)


class ObservationBuilder:
    def __init__(self, env: MarketEnvironment, *, window: int = 5) -> None:
        self._env = env
        self._window = max(1, window)
        self._history = ObservationHistory()

    def _tail(self, values: list) -> list:
        return values[-self._window :]

    def build(
        self,
        *,
        agent_name: str,
        round_index: int,
        observed_demand: int,
        current_reputations: Mapping[str, float],
    ) -> MarketObservation:
        price_history = self._tail(self._history.price_history)
        prices_flat = [price for round_prices in price_history for price in round_prices]
        avg_price = mean(prices_flat) if prices_flat else mean(
            agent.base_price for agent in self._env.agent_configs.values()
        )
        observed_history = self._tail(self._history.observed_history)
        state = self._env.states[agent_name]
        return MarketObservation(
            round_index=round_index,
            observed_demand=observed_demand,
            demand_history=tuple(self._tail(self._history.demand_history)),
            observed_demand_history=tuple(observed_history),
            price_history=tuple(tuple(round_prices) for round_prices in price_history),
            reputation_history=tuple(tuple(round_reputations) for round_reputations in self._tail(self._history.reputation_history)),
            peer_reputations=tuple(sorted(current_reputations.items())),
            own_inventory=state.inventory,
            own_last_profit=state.last_profit,
            own_last_shortage=state.last_shortage,
            own_reputation=state.reputation,
            market_avg_price=avg_price,
            market_volatility=rolling_volatility(observed_history, window=self._window),
        )

    def record_round(
        self,
        *,
        snapshot: DemandSnapshot,
        actions: Mapping[str, AgentAction],
    ) -> None:
        ordered_names = list(self._env.agent_configs)
        self._history.demand_history.append(snapshot.true_demand)
        self._history.observed_history.append(snapshot.observed_demand)
        self._history.price_history.append([actions[name].price for name in ordered_names])
        self._history.reputation_history.append([self._env.states[name].reputation for name in ordered_names])
