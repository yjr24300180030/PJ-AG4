from __future__ import annotations

from dataclasses import replace
import json

import pytest

from pj_ag4.config import MarketConfig, default_simulation_config
from pj_ag4.contracts import AgentAction, DecisionTrace
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
    assert all(0.0 <= row.rep_delivery_end <= 1.0 for row in rows)
    assert all(0.0 <= row.rep_pricing_end <= 1.0 for row in rows)
    assert all(0.0 <= row.rep_cooperation_end <= 1.0 for row in rows)
    assert any(row.profit != 0 for row in rows)


def test_three_dimensional_reputation_rolls_up_to_weighted_total() -> None:
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

    total_weight = (
        config.market.reputation_delivery_weight
        + config.market.reputation_pricing_weight
        + config.market.reputation_cooperation_weight
    )
    for row in rows:
        expected = (
            config.market.reputation_delivery_weight * row.rep_delivery_end
            + config.market.reputation_pricing_weight * row.rep_pricing_end
            + config.market.reputation_cooperation_weight * row.rep_cooperation_end
        ) / total_weight
        assert row.reputation_end == pytest.approx(expected)
        expected_start = (
            config.market.reputation_delivery_weight * row.rep_delivery_start
            + config.market.reputation_pricing_weight * row.rep_pricing_start
            + config.market.reputation_cooperation_weight * row.rep_cooperation_start
        ) / total_weight
        assert row.reputation_start == pytest.approx(expected_start)


def test_agent_state_reputation_uses_configured_weights() -> None:
    config = default_simulation_config(seed=5, rounds=1)
    config = replace(
        config,
        market=MarketConfig(
            reputation_delivery_weight=0.1,
            reputation_pricing_weight=0.8,
            reputation_cooperation_weight=0.1,
        ),
    )
    env = MarketEnvironment(config)
    state = env.states["Hyperscaler"]
    state.rep_delivery = 0.0
    state.rep_pricing = 1.0
    state.rep_cooperation = 0.0

    assert state.reputation == pytest.approx(env.reputation_for("Hyperscaler"))
    assert state.reputation == pytest.approx(0.8)


def test_environment_validates_actions_before_settlement() -> None:
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
        "Hyperscaler": AgentAction(forecast_demand=-10, price=-999.0, quantity=9999),
        "PremiumCloud": AgentAction(forecast_demand=200, price=999.0, quantity=-30),
        "SpotBroker": AgentAction(forecast_demand=200, price=4.8, quantity=40),
    }

    rows = env.step(seed=config.seed, round_index=0, snapshot=snapshot, actions=actions)
    by_name = {row.agent_name: row for row in rows}

    hyperscaler_cfg = next(agent for agent in config.agents if agent.name == "Hyperscaler")
    premium_cfg = next(agent for agent in config.agents if agent.name == "PremiumCloud")
    assert by_name["Hyperscaler"].forecast_demand == 0
    assert by_name["Hyperscaler"].price == pytest.approx(hyperscaler_cfg.price_floor)
    assert by_name["Hyperscaler"].quantity == hyperscaler_cfg.max_quantity
    assert by_name["PremiumCloud"].price == pytest.approx(premium_cfg.price_ceiling)
    assert by_name["PremiumCloud"].quantity == 0


def test_obsolescence_rate_and_penalty_are_separate() -> None:
    config = default_simulation_config(seed=5, rounds=1)
    env = MarketEnvironment(config)
    snapshot = DemandSnapshot(
        round_index=0,
        true_demand=120,
        observed_demand=120,
        trend_component=120.0,
        seasonal_component=0.0,
        shock_component=0.0,
        noise_component=0.0,
    )
    actions = {
        "Hyperscaler": AgentAction(forecast_demand=120, price=4.2, quantity=120),
        "PremiumCloud": AgentAction(forecast_demand=120, price=6.0, quantity=100),
        "SpotBroker": AgentAction(forecast_demand=120, price=5.0, quantity=80),
    }

    rows = env.step(seed=config.seed, round_index=0, snapshot=snapshot, actions=actions)

    for row in rows:
        agent_cfg = next(agent for agent in config.agents if agent.name == row.agent_name)
        pre_obsolescence_inventory = row.inventory_end + row.obsolescence_units
        assert row.obsolescence_units == pytest.approx(agent_cfg.obsolescence_rate * pre_obsolescence_inventory)
        assert row.obsolescence_cost == pytest.approx(row.obsolescence_units * agent_cfg.obsolescence_penalty)


def test_transfer_conservation_and_probability_fields() -> None:
    config = default_simulation_config(seed=5, rounds=1)
    config = replace(
        config,
        market=MarketConfig(
            cooperation_alpha0=4.0,
            cooperation_alpha1=0.0,
            cooperation_alpha2=0.0,
            cooperation_alpha3=0.0,
            max_transfer=20.0,
        ),
    )
    env = MarketEnvironment(config)
    snapshot = DemandSnapshot(
        round_index=0,
        true_demand=260,
        observed_demand=260,
        trend_component=260.0,
        seasonal_component=0.0,
        shock_component=0.0,
        noise_component=0.0,
    )
    actions = {
        "Hyperscaler": AgentAction(forecast_demand=260, price=4.0, quantity=10),
        "PremiumCloud": AgentAction(forecast_demand=260, price=7.0, quantity=100),
        "SpotBroker": AgentAction(forecast_demand=260, price=6.4, quantity=80),
    }

    rows = env.step(seed=config.seed, round_index=0, snapshot=snapshot, actions=actions)

    assert sum(row.transfer_in for row in rows) == pytest.approx(sum(row.transfer_out for row in rows))
    assert sum(row.transfer_in for row in rows) > 0
    assert any(row.transfer_attempts > 0 for row in rows)
    assert all(0.0 <= row.coop_probability <= 1.0 for row in rows)


def test_forecast_error_fields_are_recorded() -> None:
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
        "Hyperscaler": AgentAction(forecast_demand=180, price=4.2, quantity=80),
        "PremiumCloud": AgentAction(forecast_demand=205, price=5.6, quantity=50),
        "SpotBroker": AgentAction(forecast_demand=200, price=4.8, quantity=40),
    }

    rows = env.step(seed=config.seed, round_index=0, snapshot=snapshot, actions=actions)
    by_name = {row.agent_name: row for row in rows}

    assert by_name["Hyperscaler"].forecast_error_abs == pytest.approx(20)
    assert by_name["Hyperscaler"].forecast_error_sq == pytest.approx(400)
    assert by_name["SpotBroker"].forecast_error_abs == pytest.approx(0)


def test_decision_trace_is_written_to_settlement_row() -> None:
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
    trace = DecisionTrace(
        source="test",
        summary="test trace summary",
        forecast_base=190.0,
        final_forecast=200,
        final_price=4.2,
        final_quantity=80,
    )
    actions = {
        "Hyperscaler": AgentAction(forecast_demand=200, price=4.2, quantity=80, trace=trace),
        "PremiumCloud": AgentAction(forecast_demand=200, price=5.6, quantity=50),
        "SpotBroker": AgentAction(forecast_demand=200, price=4.8, quantity=40),
    }

    rows = env.step(seed=config.seed, round_index=0, snapshot=snapshot, actions=actions)
    hyperscaler = next(row for row in rows if row.agent_name == "Hyperscaler")

    assert hyperscaler.decision_source == "test"
    assert hyperscaler.decision_reason == "test trace summary"
    assert DecisionTrace.from_json(hyperscaler.decision_trace) == trace


def test_segment_allocations_sum_to_true_demand() -> None:
    config = default_simulation_config(seed=5, rounds=1)
    env = MarketEnvironment(config)
    snapshot = DemandSnapshot(
        round_index=0,
        true_demand=210,
        observed_demand=210,
        trend_component=210.0,
        seasonal_component=0.0,
        shock_component=0.0,
        noise_component=0.0,
    )
    actions = {
        "Hyperscaler": AgentAction(forecast_demand=210, price=4.2, quantity=80),
        "PremiumCloud": AgentAction(forecast_demand=210, price=5.6, quantity=60),
        "SpotBroker": AgentAction(forecast_demand=210, price=4.8, quantity=50),
    }

    rows = env.step(seed=config.seed, round_index=0, snapshot=snapshot, actions=actions)

    segment_demand = json.loads(rows[0].segment_demand)
    assert sum(segment_demand.values()) == pytest.approx(snapshot.true_demand)
    assert sum(row.allocated_demand for row in rows) == pytest.approx(snapshot.true_demand)


def test_reallocation_and_backlog_fields_preserve_service_accounting() -> None:
    config = default_simulation_config(seed=5, rounds=1, scenario="supply_shock")
    env = MarketEnvironment(config)
    snapshot = DemandSnapshot(
        round_index=0,
        true_demand=320,
        observed_demand=320,
        trend_component=320.0,
        seasonal_component=0.0,
        shock_component=0.0,
        noise_component=0.0,
    )
    actions = {
        "Hyperscaler": AgentAction(forecast_demand=320, price=4.0, quantity=20),
        "PremiumCloud": AgentAction(forecast_demand=320, price=6.2, quantity=110),
        "SpotBroker": AgentAction(forecast_demand=320, price=4.6, quantity=20),
    }

    rows = env.step(seed=config.seed, round_index=0, snapshot=snapshot, actions=actions)

    assert sum(row.reallocated_in for row in rows) == pytest.approx(sum(row.reallocated_out for row in rows))
    assert sum(row.realized_sales + row.shortage_post_transfer for row in rows) == pytest.approx(
        sum(row.allocated_demand for row in rows)
    )
    assert any(row.new_contract_demand > 0 for row in rows)
    assert all(row.backlog_end >= 0 for row in rows)


def test_sla_backlog_rolls_forward() -> None:
    config = default_simulation_config(seed=5, rounds=2, scenario="supply_shock")
    env = MarketEnvironment(config)
    first_snapshot = DemandSnapshot(
        round_index=0,
        true_demand=320,
        observed_demand=320,
        trend_component=320.0,
        seasonal_component=0.0,
        shock_component=0.0,
        noise_component=0.0,
    )
    low_supply_actions = {
        "Hyperscaler": AgentAction(forecast_demand=320, price=4.0, quantity=0),
        "PremiumCloud": AgentAction(forecast_demand=320, price=6.2, quantity=0),
        "SpotBroker": AgentAction(forecast_demand=320, price=4.6, quantity=0),
    }
    first_rows = env.step(seed=config.seed, round_index=0, snapshot=first_snapshot, actions=low_supply_actions)
    first_backlog = {row.agent_name: row.backlog_end for row in first_rows}

    second_snapshot = DemandSnapshot(
        round_index=1,
        true_demand=180,
        observed_demand=180,
        trend_component=180.0,
        seasonal_component=0.0,
        shock_component=0.0,
        noise_component=0.0,
    )
    second_rows = env.step(seed=config.seed, round_index=1, snapshot=second_snapshot, actions=low_supply_actions)

    assert any(value > 0 for value in first_backlog.values())
    for row in second_rows:
        assert row.backlog_start == pytest.approx(first_backlog[row.agent_name])
