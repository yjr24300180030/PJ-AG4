from __future__ import annotations

from pj_ag4.agents import RiskGateStage, build_agents
from pj_ag4.config import default_simulation_config
from pj_ag4.contracts import AgentAction, MarketObservation


def _sample_observation() -> MarketObservation:
    return MarketObservation(
        round_index=3,
        observed_demand=180,
        demand_history=(170, 176, 181),
        observed_demand_history=(172, 178, 180),
        price_history=((4.2, 6.0, 5.0), (4.4, 6.2, 5.2), (4.2, 6.0, 5.0)),
        reputation_history=((0.65, 0.80, 0.55), (0.66, 0.82, 0.58), (0.63, 0.84, 0.57)),
        peer_reputations=(("Hyperscaler", 0.63), ("PremiumCloud", 0.84), ("SpotBroker", 0.57)),
        own_inventory=18.0,
        own_last_profit=-10.0,
        own_last_shortage=12.0,
        own_reputation=0.62,
        market_avg_price=5.3,
        market_volatility=6.0,
    )


def test_stage_style_mix_creates_distinct_heuristic_actions() -> None:
    config = default_simulation_config(seed=7, rounds=1)
    agents = build_agents(config.agents, mode="heuristic", llm_config=config.llm)
    observation = _sample_observation()

    hyper = agents["Hyperscaler"].decide(observation)
    premium = agents["PremiumCloud"].decide(observation)
    spot = agents["SpotBroker"].decide(observation)

    assert premium.price > hyper.price
    assert premium.price > spot.price
    assert hyper.quantity >= premium.quantity
    assert spot.quantity <= hyper.quantity


def test_risk_gate_styles_apply_different_review_rules() -> None:
    config = default_simulation_config(seed=7, rounds=1)
    observation = _sample_observation()
    draft = AgentAction(forecast_demand=40, price=4.2, quantity=70)
    fallback = AgentAction(forecast_demand=160, price=5.2, quantity=40)

    hyperscaler_cfg, premium_cfg, spot_cfg = config.agents

    hyper_review = RiskGateStage(hyperscaler_cfg).review(observation, draft, fallback=fallback)
    premium_review = RiskGateStage(premium_cfg).review(observation, draft, fallback=fallback)
    spot_review = RiskGateStage(spot_cfg).review(observation, draft, fallback=fallback)

    assert hyper_review.quantity >= draft.quantity
    assert premium_review.price >= fallback.price
    assert premium_review.quantity < draft.quantity
    assert spot_review.quantity < draft.quantity
