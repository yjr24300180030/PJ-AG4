from __future__ import annotations

from types import SimpleNamespace

import pytest

from pj_ag4.config import default_simulation_config
from pj_ag4.simulation import run_simulation


class _FakeCompletions:
    def create(self, **kwargs):
        del kwargs
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        content='{"forecast_demand": 210, "price": 5.2, "quantity": 60, "reasoning": "stable demand"}'
                    )
                )
            ]
        )


class _FakeChat:
    def __init__(self) -> None:
        self.completions = _FakeCompletions()


class _FakeClient:
    def __init__(self) -> None:
        self.chat = _FakeChat()


class _RetryFakeCompletions:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **kwargs):
        del kwargs
        self.calls += 1
        if self.calls == 1:
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        finish_reason="length",
                        message=SimpleNamespace(content='{"forecast_demand":')
                    )
                ]
            )
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        content='{"forecast_demand": 190, "price": 4.8, "quantity": 50, "reasoning": "retry recovered"}'
                    )
                )
            ]
        )


class _RetryFakeChat:
    def __init__(self) -> None:
        self.completions = _RetryFakeCompletions()


class _RetryFakeClient:
    def __init__(self) -> None:
        self.chat = _RetryFakeChat()


class _LengthButCompleteCompletions:
    def create(self, **kwargs):
        del kwargs
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="length",
                    message=SimpleNamespace(
                        content='{"forecast_demand": 160, "price": 5.0, "quantity": 40, "reasoning": "complete despite length"}'
                    ),
                )
            ]
        )


class _LengthButCompleteChat:
    def __init__(self) -> None:
        self.completions = _LengthButCompleteCompletions()


class _LengthButCompleteClient:
    def __init__(self) -> None:
        self.chat = _LengthButCompleteChat()


class _ContextCompletions:
    def __init__(self) -> None:
        self.user_prompts: list[str] = []

    def create(self, **kwargs):
        messages = kwargs.get("messages", [])
        for message in messages:
            if message.get("role") == "user":
                self.user_prompts.append(message.get("content", ""))
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        content='{"forecast_demand": 205, "price": 5.1, "quantity": 60, "reasoning": "context aware"}'
                    ),
                )
            ]
        )


class _ContextChat:
    def __init__(self, completions: _ContextCompletions) -> None:
        self.completions = completions


class _ContextClient:
    def __init__(self, completions: _ContextCompletions) -> None:
        self.chat = _ContextChat(completions)


class _ContextRetryCompletions(_ContextCompletions):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def create(self, **kwargs):
        messages = kwargs.get("messages", [])
        for message in messages:
            if message.get("role") == "user":
                self.user_prompts.append(message.get("content", ""))
        self.calls += 1
        if self.calls == 4:
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        finish_reason="length",
                        message=SimpleNamespace(content='{"forecast_demand":'),
                    )
                ]
            )
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        content='{"forecast_demand": 205, "price": 5.1, "quantity": 60, "reasoning": "context retry"}'
                    ),
                )
            ]
        )


def test_run_simulation_with_llm_mode_uses_openai_compatible_client(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("pj_ag4.agents.factory.build_openai_client", lambda llm_config: _FakeClient())

    config = default_simulation_config(
        seed=3,
        rounds=2,
        output_dir=tmp_path,
        agent_mode="llm",
        llm_api_key="test-key",
    )
    result = run_simulation(config, output_dir=tmp_path, generate_figure=False)

    assert result.csv_path.exists()
    assert len(result.rows) == 6
    assert all(row.forecast_demand == 210 for row in result.rows)
    assert all("reasoning: stable demand" in row.decision_reason for row in result.rows)


def test_llm_mode_requires_api_key(monkeypatch, tmp_path) -> None:
    from pj_ag4 import config as config_module

    monkeypatch.setattr(config_module, "_load_runtime_env", lambda: None)
    monkeypatch.delenv("PJ_AG4_LLM_API_KEY", raising=False)
    monkeypatch.delenv("PJ_AG4_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("PJ_AG4_LLM_MODEL", raising=False)
    monkeypatch.delenv("PJ_AG4_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PJ_AG4_OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("PJ_AG4_OPENAI_MODEL", raising=False)
    config = default_simulation_config(
        seed=3,
        rounds=2,
        output_dir=tmp_path,
        agent_mode="llm",
        llm_api_key=None,
    )

    with pytest.raises(ValueError, match="api_key"):
        run_simulation(config, output_dir=tmp_path, generate_figure=False)


def test_llm_mode_retries_when_finish_reason_is_length(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("pj_ag4.agents.factory.build_openai_client", lambda llm_config: _RetryFakeClient())

    config = default_simulation_config(
        seed=4,
        rounds=1,
        output_dir=tmp_path,
        agent_mode="llm",
        llm_api_key="test-key",
    )
    result = run_simulation(config, output_dir=tmp_path, generate_figure=False)

    assert result.csv_path.exists()
    assert len(result.rows) == 3
    assert all(row.forecast_demand == 190 for row in result.rows)


def test_llm_mode_accepts_complete_json_even_if_finish_reason_is_length(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("pj_ag4.agents.factory.build_openai_client", lambda llm_config: _LengthButCompleteClient())

    config = default_simulation_config(
        seed=4,
        rounds=1,
        output_dir=tmp_path,
        agent_mode="llm",
        llm_api_key="test-key",
    )
    result = run_simulation(config, output_dir=tmp_path, generate_figure=False)

    assert result.csv_path.exists()
    assert len(result.rows) == 3
    assert all(row.forecast_demand == 160 for row in result.rows)


def test_llm_context_mode_injects_compressed_round_history(monkeypatch, tmp_path) -> None:
    completions = _ContextCompletions()
    monkeypatch.setattr("pj_ag4.agents.factory.build_openai_client", lambda llm_config: _ContextClient(completions))

    config = default_simulation_config(
        seed=4,
        rounds=2,
        output_dir=tmp_path,
        agent_mode="llm-context",
        llm_api_key="test-key",
    )
    result = run_simulation(config, output_dir=tmp_path, generate_figure=False)

    assert result.csv_path.exists()
    assert len(result.rows) == 6
    assert all(row.decision_source == "llm-context" for row in result.rows)
    assert any('"llm_context":{"window":6,"selection":"none_until_first_settlement"' in prompt for prompt in completions.user_prompts)
    assert any('"llm_context":{"window":6,"selection":"latest_settlement_summaries"' in prompt for prompt in completions.user_prompts)
    assert any('"signals":' in prompt and '"history":[{"round":0' in prompt for prompt in completions.user_prompts)


def test_llm_context_retry_uses_compact_history_summary(monkeypatch, tmp_path) -> None:
    completions = _ContextRetryCompletions()
    monkeypatch.setattr("pj_ag4.agents.factory.build_openai_client", lambda llm_config: _ContextClient(completions))

    config = default_simulation_config(
        seed=4,
        rounds=2,
        output_dir=tmp_path,
        agent_mode="llm-context",
        llm_api_key="test-key",
    )
    result = run_simulation(config, output_dir=tmp_path, generate_figure=False)

    assert len(result.rows) == 6
    assert any('"compression":"signal_profit_service_inventory_summary"' in prompt for prompt in completions.user_prompts)
