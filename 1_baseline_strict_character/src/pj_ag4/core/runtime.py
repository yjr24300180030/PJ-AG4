from __future__ import annotations

import sys
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
            # Feed results back to agents for learning
            for row in round_rows:
                agent = agents.get(row.agent_name)
                if agent is not None and hasattr(agent, "record_result"):
                    agent.record_result({
                        "realized_sales": row.realized_sales,
                        "revenue": row.revenue,
                        "allocated_demand": row.allocated_demand,
                        "sla_penalty": row.sla_penalty,
                        "prod_cost": row.prod_cost,
                        "holding_cost": row.holding_cost,
                        "obsolescence_cost": row.obsolescence_cost,
                        "transfer_cost": row.transfer_cost,
                        "transfer_revenue": row.transfer_revenue,
                    })
            print(f"[Round {round_index + 1}/{self._config.rounds}] completed", file=sys.stderr, flush=True)
            # Evolution round every 3 rounds (after rounds 2, 5, 8, ...)
            if round_index % 2 == 1:
                print(f"[Evolution] triggering after round {round_index + 1}...", file=sys.stderr, flush=True)
                for agent in agents.values():
                    if hasattr(agent, "evolve_strategy"):
                        agent.evolve_strategy(round_index)
                print(f"[Evolution] completed after round {round_index + 1}", file=sys.stderr, flush=True)
            self._observations.record_round(snapshot=snapshot, actions=actions)
        print(f"[Simulation] all {self._config.rounds} rounds completed", file=sys.stderr, flush=True)
        return rows
