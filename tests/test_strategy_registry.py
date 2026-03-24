from __future__ import annotations

from pathlib import Path
import sys

from pj_ag4.config import default_simulation_config
from pj_ag4.simulation import run_simulation

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from quant.strategies import ensure_quant_strategies_registered


def test_run_simulation_supports_registered_quant_strategy(tmp_path) -> None:
    ensure_quant_strategies_registered()
    config = default_simulation_config(seed=13, rounds=2, output_dir=tmp_path, agent_mode="rule_price_cutter")

    result = run_simulation(config, output_dir=tmp_path, generate_figure=False, strategy_name="rule_price_cutter")

    assert result.csv_path.exists()
    assert len(result.rows) == 6
