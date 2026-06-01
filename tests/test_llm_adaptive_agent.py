from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from pj_ag4.agents import build_agents
from pj_ag4.config import LLMConfig, default_simulation_config
from pj_ag4.contracts import StrategyState, StrategyUpdateTrace
from pj_ag4.dashboard import build_dashboard_payload
from pj_ag4.simulation import run_simulation


class _AdaptiveCompletions:
    def create(self, **kwargs):
        del kwargs
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        content=json.dumps(
                            {
                                "risk_tolerance_delta": 0.1,
                                "price_aggressiveness_delta": 0.1,
                                "demand_sensitivity_delta": 0.05,
                                "inventory_caution_delta": -0.1,
                                "shock_responsiveness_delta": 0.1,
                                "competitor_reactivity_delta": 0.1,
                                "reason": "Increase adaptive posture after fresh market feedback.",
                            }
                        )
                    ),
                )
            ]
        )


class _InvalidCompletions:
    def create(self, **kwargs):
        del kwargs
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(content="not json"),
                )
            ]
        )


class _FakeChat:
    def __init__(self, completions) -> None:
        self.completions = completions


class _FakeClient:
    def __init__(self, completions) -> None:
        self.chat = _FakeChat(completions)


def test_strategy_state_clamps_to_unit_interval() -> None:
    state = StrategyState(risk_tolerance=1.4, price_aggressiveness=-0.2).bounded()

    assert state.risk_tolerance == pytest.approx(1.0)
    assert state.price_aggressiveness == pytest.approx(0.0)


def test_strategy_personality_changes_bounded_delta(monkeypatch) -> None:
    monkeypatch.setattr(
        "pj_ag4.agents.factory.build_openai_client",
        lambda llm_config: _FakeClient(_AdaptiveCompletions()),
    )
    config = default_simulation_config(seed=3, rounds=1)
    agents = build_agents(
        config.agents,
        mode="llm-adaptive",
        llm_config=LLMConfig(api_key="test-key"),
    )
    raw_delta = {field: 0.1 for field in StrategyState.fields()}

    hyper_delta = agents["Hyperscaler"]._bound_delta(raw_delta)
    premium_delta = agents["PremiumCloud"]._bound_delta(raw_delta)

    assert hyper_delta["price_aggressiveness"] > premium_delta["price_aggressiveness"]
    assert premium_delta["inventory_caution"] >= hyper_delta["inventory_caution"]


def test_llm_adaptive_mode_requires_api_key(monkeypatch, tmp_path) -> None:
    from pj_ag4 import config as config_module

    monkeypatch.setattr(config_module, "_load_runtime_env", lambda: None)
    monkeypatch.delenv("PJ_AG4_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    config = default_simulation_config(
        seed=3,
        rounds=2,
        output_dir=tmp_path,
        agent_mode="llm-adaptive",
        llm_api_key=None,
    )

    with pytest.raises(ValueError, match="api_key"):
        run_simulation(config, output_dir=tmp_path, generate_figure=False)


def test_llm_adaptive_writes_strategy_trace(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "pj_ag4.agents.factory.build_openai_client",
        lambda llm_config: _FakeClient(_AdaptiveCompletions()),
    )
    config = default_simulation_config(
        seed=4,
        rounds=2,
        output_dir=tmp_path,
        agent_mode="llm-adaptive",
        llm_api_key="test-key",
    )

    result = run_simulation(config, output_dir=tmp_path, generate_figure=False)
    first_row = result.rows[0]
    trace = StrategyUpdateTrace.from_json(first_row.strategy_update_trace)

    assert len(result.rows) == 6
    assert first_row.strategy_state
    assert first_row.strategy_update_reason == "Increase adaptive posture after fresh market feedback."
    assert trace is not None
    assert trace.fallback_used is False
    assert trace.bounded_delta["price_aggressiveness"] > 0
    payload = build_dashboard_payload(result.rows, config=config, strategy_name=config.agent_mode)
    first_agent = payload["roundsData"][0]["agents"][0]
    assert first_agent["strategyState"]
    assert first_agent["personalityLabel"]
    assert first_agent["strategyUpdateReason"]
    assert result.report_path is not None
    assert "Adaptive Strategy Trace Samples" in result.report_path.read_text(encoding="utf-8")
    assert "strategy_update_trace" in result.csv_path.read_text(encoding="utf-8").splitlines()[0]


def test_llm_adaptive_falls_back_when_llm_response_is_invalid(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "pj_ag4.agents.factory.build_openai_client",
        lambda llm_config: _FakeClient(_InvalidCompletions()),
    )
    config = default_simulation_config(
        seed=5,
        rounds=1,
        output_dir=tmp_path,
        agent_mode="llm-adaptive",
        llm_api_key="test-key",
    )

    result = run_simulation(config, output_dir=tmp_path, generate_figure=False)
    traces = [StrategyUpdateTrace.from_json(row.strategy_update_trace) for row in result.rows]

    assert len(result.rows) == 3
    assert all(trace is not None for trace in traces)
    assert all(trace.fallback_used for trace in traces if trace is not None)
