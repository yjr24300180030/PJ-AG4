from __future__ import annotations

from pathlib import Path

from pj_ag4.config import default_simulation_config


def test_default_simulation_config_reads_values_from_dotenv(monkeypatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "PJ_AG4_OPENAI_API_KEY=dotenv-key",
                "PJ_AG4_OPENAI_BASE_URL=http://127.0.0.1:9000/v1",
                "PJ_AG4_OPENAI_MODEL=dotenv-model",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PJ_AG4_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PJ_AG4_OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("PJ_AG4_OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    config = default_simulation_config(agent_mode="llm")

    assert config.llm is not None
    assert config.llm.api_key == "dotenv-key"
    assert config.llm.base_url == "http://127.0.0.1:9000/v1"
    assert config.llm.model == "dotenv-model"


def test_explicit_arguments_override_dotenv(monkeypatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "PJ_AG4_OPENAI_API_KEY=dotenv-key",
                "PJ_AG4_OPENAI_BASE_URL=http://127.0.0.1:9000/v1",
                "PJ_AG4_OPENAI_MODEL=dotenv-model",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PJ_AG4_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PJ_AG4_OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("PJ_AG4_OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

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
