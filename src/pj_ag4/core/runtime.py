from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from ..config import SimulationConfig
from ..contracts import AgentAction, SettlementRow
from ..data.observation import ObservationBuilder
from ..environment import MarketEnvironment
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
            current_reputations = self._env.current_reputations()
            actions: dict[str, AgentAction] = {}
            for name, agent in agents.items():
                observation = self._observations.build(
                    agent_name=name,
                    round_index=round_index,
                    observed_demand=snapshot.observed_demand,
                    current_reputations=current_reputations,
                )
                actions[name] = agent.decide(observation)
            actions = self._env.validate_actions(actions)
            round_rows = self._env.step(
                seed=self._config.seed,
                round_index=round_index,
                snapshot=snapshot,
                actions=actions,
            )
            round_rows = self._record_strategy_updates(agents, round_rows)
            rows.extend(round_rows)
            self._observations.record_round(snapshot=snapshot, actions=actions)
        return rows

    def _record_strategy_updates(
        self,
        agents: Mapping[str, Any],
        round_rows: list[SettlementRow],
    ) -> list[SettlementRow]:
        updated_rows: list[SettlementRow] = []
        for row in round_rows:
            agent = agents.get(row.agent_name)
            observe_result = getattr(agent, "observe_result", None)
            if not callable(observe_result):
                updated_rows.append(row)
                continue
            trace = observe_result(row, round_rows)
            state = getattr(agent, "strategy_state", None)
            updated_rows.append(
                replace(
                    row,
                    strategy_state=state.to_json() if state is not None else row.strategy_state,
                    strategy_update_reason=trace.reason,
                    strategy_update_trace=trace.to_json(),
                )
            )
        return updated_rows
