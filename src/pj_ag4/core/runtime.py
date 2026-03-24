from __future__ import annotations

from typing import Any, Mapping

from ..config import SimulationConfig
from ..contracts import AgentAction
from ..data.observation import ObservationBuilder
from ..environment import MarketEnvironment, SettlementRow
from ..timeseries import DemandSeriesGenerator


class SimulationRuntime:
    def __init__(self, config: SimulationConfig) -> None:
        self._config = config
        self._generator = DemandSeriesGenerator(config.market, seed=config.seed)
        self._env = MarketEnvironment(config)
        self._observations = ObservationBuilder(self._env, window=config.market.demand_window)

    def run(self, agents: Mapping[str, Any]) -> list[SettlementRow]:
        rows: list[SettlementRow] = []
        for round_index in range(self._config.rounds):
            snapshot = self._generator.step(round_index)
            current_reputations = {name: state.reputation for name, state in self._env.states.items()}
            actions: dict[str, AgentAction] = {}
            for name, agent in agents.items():
                observation = self._observations.build(
                    agent_name=name,
                    round_index=round_index,
                    observed_demand=snapshot.observed_demand,
                    current_reputations=current_reputations,
                )
                actions[name] = agent.decide(observation)
            round_rows = self._env.step(
                seed=self._config.seed,
                round_index=round_index,
                snapshot=snapshot,
                actions=actions,
            )
            rows.extend(round_rows)
            self._observations.record_round(snapshot=snapshot, actions=actions)
        return rows
