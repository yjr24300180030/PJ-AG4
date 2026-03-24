from __future__ import annotations

from pj_ag4.config import default_simulation_config
from pj_ag4.contracts import AgentAction
from pj_ag4.data import ObservationBuilder
from pj_ag4.environment import MarketEnvironment
from pj_ag4.timeseries import DemandSeriesGenerator


def test_observation_builder_keeps_windowed_history() -> None:
    config = default_simulation_config(seed=5, rounds=8)
    env = MarketEnvironment(config)
    builder = ObservationBuilder(env, window=3)
    generator = DemandSeriesGenerator(config.market, seed=config.seed)
    actions = {
        agent.name: AgentAction(forecast_demand=100, price=agent.base_price, quantity=agent.quantity_step)
        for agent in config.agents
    }

    for round_index in range(5):
        snapshot = generator.step(round_index)
        env.step(seed=config.seed, round_index=round_index, snapshot=snapshot, actions=actions)
        builder.record_round(snapshot=snapshot, actions=actions)

    observation = builder.build(
        agent_name="Hyperscaler",
        round_index=5,
        observed_demand=120,
        current_reputations={name: state.reputation for name, state in env.states.items()},
    )

    assert len(observation.demand_history) == 3
    assert len(observation.observed_demand_history) == 3
    assert len(observation.price_history) == 3
    assert len(observation.reputation_history) == 3

