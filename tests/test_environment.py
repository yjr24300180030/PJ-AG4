from __future__ import annotations

from pj_ag4.agents import AgentAction
from pj_ag4.config import default_simulation_config
from pj_ag4.environment import MarketEnvironment
from pj_ag4.timeseries import DemandSnapshot


def test_environment_step_returns_three_rows_and_updates_state() -> None:
    config = default_simulation_config(seed=5, rounds=1)
    env = MarketEnvironment(config)
    snapshot = DemandSnapshot(
        round_index=0,
        true_demand=200,
        observed_demand=198,
        trend_component=180.0,
        seasonal_component=0.0,
        shock_component=0.0,
        noise_component=0.0,
    )
    actions = {
        "Hyperscaler": AgentAction(forecast_demand=200, price=4.2, quantity=80),
        "PremiumCloud": AgentAction(forecast_demand=200, price=5.6, quantity=50),
        "SpotBroker": AgentAction(forecast_demand=200, price=4.8, quantity=40),
    }

    rows = env.step(seed=config.seed, round_index=0, snapshot=snapshot, actions=actions)

    assert len(rows) == 3
    assert all(0.0 <= row.reputation_end <= 1.0 for row in rows)
    assert any(row.profit != 0 for row in rows)

