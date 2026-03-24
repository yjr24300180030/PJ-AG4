# PJ-AG4

LLM-driven game and market simulation project.

## Project Goal

Build a multi-agent simulation with at least 3 independent agents, reproducible payoff rules, 10+ interaction rounds, statistics, and visualizations.

## Scenario

Formal project design for the high-end GPU spot market and supply-chain game:

- [docs/project_design.md](docs/project_design.md)

## Planned Deliverables

- `simulation_results.csv`
- `strategy_analysis.pdf` or an equivalent report section

## Run

Install the package in editable mode and run the baseline simulation:

```bash
python3 -m pip install -e .[dev]
pj-ag4-run --rounds 30 --output-dir outputs/default_run
```

You can also run the bundled script directly:

```bash
python3 scripts/run_simulation.py --rounds 30 --output-dir outputs/default_run
```

Artifacts:

- `outputs/default_run/simulation_results.csv`
- `outputs/default_run/strategy_analysis.pdf`

Tests:

```bash
pytest
```

## Status

Repository initialized with formal design docs, a runnable Python simulation skeleton, CSV export, chart generation, and tests.
