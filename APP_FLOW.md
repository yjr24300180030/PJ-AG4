# APP FLOW

This project is CLI-first. "Screens" below refer to commands, outputs, and report artifacts rather than web pages.

## Screen Inventory

- `python -m src.simulation run`: runs a full simulation and writes `simulation_results.csv`.
- `python -m src.simulation summarize`: prints cumulative payoff, win/loss summary, and key metrics.
- `python -m src.simulation plot`: generates charts for payoff, reputation, and demand trajectories.
- `reports/strategy_analysis.pdf`: final report artifact or report chapter output.

## Route Map

- `run` -> build config -> initialize agents and environment -> simulate rounds -> export CSV -> export plots.
- `summarize` -> load CSV -> compute agent-level metrics -> print table.
- `plot` -> load CSV -> create charts -> save PNG/PDF figures.

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
