from __future__ import annotations

import csv

import pytest

from pj_ag4.config import default_simulation_config
from pj_ag4.contracts import DecisionTrace
from pj_ag4.simulation import run_simulation


def test_run_simulation_writes_outputs(tmp_path) -> None:
    config = default_simulation_config(seed=9, rounds=4, output_dir=tmp_path)
    result = run_simulation(config, output_dir=tmp_path, generate_figure=True)

    assert result.csv_path.exists()
    assert result.figure_path is not None
    assert result.figure_path.exists()
    assert result.figure_path.name == "strategy_analysis.pdf"
    assert result.dashboard_path is not None
    assert result.dashboard_path.exists()
    assert result.dashboard_path.name == "strategy_dashboard.html"
    assert result.report_path is not None
    assert result.report_path.exists()


def test_simulation_outputs_decision_trace_in_csv_and_report(tmp_path) -> None:
    config = default_simulation_config(seed=7, rounds=2, output_dir=tmp_path)
    result = run_simulation(config, output_dir=tmp_path, generate_figure=False, generate_dashboard=False)

    first_row = result.rows[0]
    trace = DecisionTrace.from_json(first_row.decision_trace)
    csv_text = result.csv_path.read_text(encoding="utf-8")
    report_text = result.report_path.read_text(encoding="utf-8") if result.report_path else ""

    assert trace is not None
    assert trace.summary
    assert "decision_trace" in csv_text
    assert "Decision Trace Samples" in report_text
    assert result.report_path.name == "simulation_report.md"
    report_text = result.report_path.read_text(encoding="utf-8")
    assert "# PJ-AG4 Simulation Report" in report_text
    assert "## Agent Strategy Comparison" in report_text

    with result.csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 6
    assert {"round", "agent_name", "agent_action", "profit"}.issubset(rows[0].keys())


def test_supply_shock_scenario_exposes_stress_mechanics(tmp_path) -> None:
    config = default_simulation_config(seed=7, rounds=12, output_dir=tmp_path, scenario="supply_shock")
    result = run_simulation(config, output_dir=tmp_path, generate_figure=False, generate_dashboard=False)

    assert sum(row.transfer_out for row in result.rows) > 0
    assert sum(row.default_flag for row in result.rows) > 0
    assert sum(row.backlog_end for row in result.rows[-3:]) > 0
    assert sum(row.reallocated_in for row in result.rows) == pytest.approx(sum(row.reallocated_out for row in result.rows))
