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
                    message=SimpleNamespace(
                        content='{"forecast_demand": 210, "price": 5.2, "quantity": 60}'
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


def test_run_simulation_with_llm_mode_uses_openai_compatible_client(monkeypatch, tmp_path) -> None:
    from pj_ag4 import agents as agents_module

    monkeypatch.setattr(agents_module, "_build_openai_client", lambda llm_config: _FakeClient())

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


def test_llm_mode_requires_api_key(tmp_path) -> None:
    config = default_simulation_config(
        seed=3,
        rounds=2,
        output_dir=tmp_path,
        agent_mode="llm",
        llm_api_key=None,
    )

    with pytest.raises(ValueError, match="api_key"):
        run_simulation(config, output_dir=tmp_path, generate_figure=False)
