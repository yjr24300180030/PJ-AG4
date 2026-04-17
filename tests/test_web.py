from __future__ import annotations

import json
import re

from pj_ag4.web import WebOptions, build_dashboard_page, build_runtime_payload, iter_runtime_payloads


def test_build_dashboard_page_includes_runtime_controls() -> None:
    html = build_dashboard_page(WebOptions(seed=7, rounds=30, agent_mode="heuristic", shock_scale=0.0, demand_bias=0, llm_base_url=None, llm_api_key=None, llm_model=None))
    assert "Simulation controls" in html
    assert 'id="runtime-seed"' in html
    assert 'id="runtime-rounds"' in html
    assert 'id="runtime-agent-mode"' in html
    assert "/api/payload?seed=7&rounds=30&agent_mode=heuristic" in html


def test_build_dashboard_page_contains_real_payload() -> None:
    options = WebOptions(seed=7, rounds=4, agent_mode="heuristic", shock_scale=0.0, demand_bias=0, llm_base_url=None, llm_api_key=None, llm_model=None)
    html = build_dashboard_page(options)
    bootstrap_payload = build_runtime_payload(options, limit_rounds=1)

    assert bootstrap_payload["meta"]["rounds"] == 1
    assert len(bootstrap_payload["roundsData"]) == 1
    assert "dashboard-data" in html
    assert "GPU market sandbox" in html
    match = re.search(r'<script id="dashboard-data" type="application/json">(.*)</script>', html)
    assert match is not None
    embedded = json.loads(match.group(1))
    assert embedded["meta"]["rounds"] == 1
    assert embedded["controls"]["shockScale"] == 0.0
    assert embedded["controls"]["demandBias"] == 0


def test_iter_runtime_payloads_streams_incremental_rounds() -> None:
    options = WebOptions(seed=7, rounds=4, agent_mode="heuristic", shock_scale=0.0, demand_bias=0, llm_base_url=None, llm_api_key=None, llm_model=None)

    payloads = list(iter_runtime_payloads(options))

    assert [payload["meta"]["rounds"] for payload in payloads] == [1, 2, 3, 4]
    assert [len(payload["roundsData"]) for payload in payloads] == [1, 2, 3, 4]


def test_build_runtime_payload_applies_market_controls() -> None:
    baseline = build_runtime_payload(WebOptions(seed=7, rounds=2, agent_mode="heuristic", shock_scale=0.0, demand_bias=0, llm_base_url=None, llm_api_key=None, llm_model=None))
    shifted = build_runtime_payload(WebOptions(seed=7, rounds=2, agent_mode="heuristic", shock_scale=0.0, demand_bias=10, llm_base_url=None, llm_api_key=None, llm_model=None))

    assert shifted["controls"]["demandBias"] == 10
    assert shifted["market"]["demand"][0] == baseline["market"]["demand"][0] + 10
