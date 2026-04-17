from __future__ import annotations

from pj_ag4.config import default_simulation_config
from pj_ag4.dashboard import build_dashboard_payload, create_dashboard
from pj_ag4.simulation import run_simulation


def test_build_dashboard_payload_contains_market_and_agent_sections(tmp_path) -> None:
    config = default_simulation_config(seed=5, rounds=3, output_dir=tmp_path)
    result = run_simulation(config, output_dir=tmp_path, generate_figure=False, generate_dashboard=False)

    payload = build_dashboard_payload(result.rows, config=config, strategy_name=config.agent_mode)

    assert payload["meta"]["rounds"] == 3
    assert len(payload["agents"]) == 3
    assert len(payload["roundsData"]) == 3
    assert "totalProfit" in payload["overview"]


def test_create_dashboard_writes_html_artifact(tmp_path) -> None:
    config = default_simulation_config(seed=5, rounds=2, output_dir=tmp_path)
    result = run_simulation(config, output_dir=tmp_path, generate_figure=False, generate_dashboard=False)
    html_path = tmp_path / "strategy_dashboard.html"

    create_dashboard(result.rows, html_path, config=config, strategy_name=config.agent_mode)

    contents = html_path.read_text(encoding="utf-8")
    assert html_path.exists()
    assert "PJ-AG4 / Strategy Dashboard" in contents
    assert "GPU market sandbox" in contents
