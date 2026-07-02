from __future__ import annotations

from pathlib import Path

import pytest

from pj_ag4.config import default_simulation_config


def _clear_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "PJ_AG4_LLM_API_KEY",
        "PJ_AG4_LLM_BASE_URL",
        "PJ_AG4_LLM_MODEL",
        "PJ_AG4_OPENAI_API_KEY",
        "PJ_AG4_OPENAI_BASE_URL",
        "PJ_AG4_OPENAI_MODEL",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)


def test_default_simulation_config_reads_values_from_dotenv(monkeypatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "PJ_AG4_LLM_API_KEY=dotenv-key",
                "PJ_AG4_LLM_BASE_URL=http://127.0.0.1:9000/v1",
                "PJ_AG4_LLM_MODEL=dotenv-model",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    _clear_llm_env(monkeypatch)

    config = default_simulation_config(agent_mode="llm")

    assert config.llm is not None
    assert config.llm.api_key == "dotenv-key"
    assert config.llm.base_url == "http://127.0.0.1:9000/v1"
    assert config.llm.model == "dotenv-model"


def test_legacy_openai_env_names_remain_supported(monkeypatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "PJ_AG4_OPENAI_API_KEY=legacy-key",
                "PJ_AG4_OPENAI_BASE_URL=http://127.0.0.1:9100/v1",
                "PJ_AG4_OPENAI_MODEL=legacy-model",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    _clear_llm_env(monkeypatch)

    config = default_simulation_config(agent_mode="llm")

    assert config.llm is not None
    assert config.llm.api_key == "legacy-key"
    assert config.llm.base_url == "http://127.0.0.1:9100/v1"
    assert config.llm.model == "legacy-model"


def test_explicit_arguments_override_dotenv(monkeypatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "PJ_AG4_LLM_API_KEY=dotenv-key",
                "PJ_AG4_LLM_BASE_URL=http://127.0.0.1:9000/v1",
                "PJ_AG4_LLM_MODEL=dotenv-model",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    _clear_llm_env(monkeypatch)

    config = default_simulation_config(
        agent_mode="llm",
        llm_api_key="cli-key",
        llm_base_url="http://127.0.0.1:7000/v1",
        llm_model="cli-model",
    )

    assert config.llm is not None
    assert config.llm.api_key == "cli-key"
    assert config.llm.base_url == "http://127.0.0.1:7000/v1"
    assert config.llm.model == "cli-model"


def test_scenario_profiles_can_be_selected() -> None:
    config = default_simulation_config(scenario="supply_shock")

    assert config.scenario == "supply_shock"
    assert config.market.shock_round == 8
    assert config.market.transfer_enabled is True


def test_unknown_scenario_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="unknown scenario"):
        default_simulation_config(scenario="moon_market")
