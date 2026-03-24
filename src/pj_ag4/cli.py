from __future__ import annotations

import argparse
from pathlib import Path

from .config import default_simulation_config
from .simulation import run_simulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the PJ-AG4 market simulation")
    parser.add_argument("--rounds", type=int, default=30, help="Number of simulation rounds")
    parser.add_argument("--seed", type=int, default=7, help="Random seed")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"), help="Directory for CSV and figures")
    parser.add_argument("--no-figure", action="store_true", help="Skip figure generation")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = default_simulation_config(seed=args.seed, rounds=args.rounds, output_dir=args.output_dir)
    result = run_simulation(config, output_dir=args.output_dir, generate_figure=not args.no_figure)
    print(f"CSV: {result.csv_path}")
    if result.figure_path:
        print(f"Figure: {result.figure_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

