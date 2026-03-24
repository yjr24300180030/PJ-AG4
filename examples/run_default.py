from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pj_ag4.config import default_simulation_config
from pj_ag4.simulation import run_simulation


def main() -> None:
    config = default_simulation_config(rounds=12, seed=11, output_dir=ROOT / "outputs")
    result = run_simulation(config, output_dir=config.output_dir, generate_figure=True)
    print(result.csv_path)
    if result.figure_path:
        print(result.figure_path)


if __name__ == "__main__":
    main()

