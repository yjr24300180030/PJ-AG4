# APP FLOW

This project is CLI-first. "Screens" below refer to commands, outputs, and report artifacts rather than web pages.

## Screen Inventory

- `pj-ag4-run --rounds 30 --output-dir outputs/default_run`: runs a full simulation and writes `simulation_results.csv`.
- `python3 scripts/run_simulation.py --rounds 30 --output-dir outputs/default_run`: script entrypoint for the same flow.
- `quant/run_benchmarks.py` and `quant/run_sensitivity.py`: research-oriented benchmark and sensitivity entrypoints.
- `outputs/<run_name>/strategy_analysis.pdf`: generated summary artifact for a single run.

## Route Map

- `pj-ag4-run` -> build config -> initialize runtime -> simulate rounds -> export CSV -> export PDF figure.
- `scripts/run_simulation.py` -> same as CLI, but easier to call directly from the repo.
- `quant/*` -> run repeated experiments -> aggregate metrics -> write Markdown or CSV summaries.

## Core Flows

- Start from a fixed seed and scenario config.
- Build a demand time series with trend, seasonality, and shocks.
- Let three agents observe a limited history window and choose price plus quantity actions.
- Resolve demand allocation, transfers, inventory decay, shortage penalties, and reputation updates.
- Persist a long-form CSV and derived charts.

## Error Flows

- Invalid agent output is clipped or replaced with the last valid action.
- Missing config values fall back to documented defaults.
- If plot generation fails, the simulation still writes the CSV and summary metrics.
- If an optional LLM backend is unavailable, the system falls back to deterministic baseline agents.

## Empty and Loading States

- Empty simulation output should be reported as "no rounds executed".
- A missing CSV should produce a clear command-line error.
- Plot generation should show progress text while figures are created.
