from __future__ import annotations

import csv

from pj_ag4.config import default_simulation_config
from pj_ag4.simulation import run_simulation


def test_run_simulation_writes_outputs(tmp_path) -> None:
    config = default_simulation_config(seed=9, rounds=4, output_dir=tmp_path)
    result = run_simulation(config, output_dir=tmp_path, generate_figure=True)

    assert result.csv_path.exists()
    assert result.figure_path is not None
    assert result.figure_path.exists()
    assert result.figure_path.name == "strategy_analysis.pdf"

    with result.csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 12
    assert {"round", "agent_name", "agent_action", "profit"}.issubset(rows[0].keys())
