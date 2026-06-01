# PRD

## Product Summary

PJ-AG4 is a deterministic, locally runnable simulation system for repeated market competition among at least three independent LLM-driven agents. The reference scenario is a high-end GPU spot market and supply-chain game with reputation, bounded rationality, inventory decay, and multi-round payoff accounting. The system must generate reproducible round-level logs, aggregate statistics, and at least one visualization that can be embedded in a report.

## Target Users

- Course project evaluators who need a clear, reproducible market simulation.
- Team members who will extend the simulator with new agent policies or game rules.
- Readers of the final report who need quantitative evidence from the simulation.

## Problem Statement

The repository currently contains only the scenario design. The team still needs a concrete implementation contract that turns the design into a runnable experiment with fixed rules, saved outputs, and repeatable analysis. Without a doc stack, agent behavior, payoff rules, and output format can drift during implementation.

## Goals and Success Metrics

- Run at least 10 rounds with 3 independent agents.
- Produce reproducible results from a fixed seed.
- Save per-round records to `simulation_results.csv`.
- Report cumulative payoff for each agent.
- Produce at least one chart for the final report.
- Support reputation and bounded rationality in the baseline scenario.
- Keep the baseline fully local and executable on macOS without an API key.

## In Scope

- CLI entrypoint for running simulations.
- Deterministic environment and agent interfaces.
- Scenario parameters from `docs/project_design.md`.
- CSV export of per-round records.
- Report assets such as plots and summary tables.
- Baseline heuristic agents that can be swapped with LLM-backed agents later.

## Out of Scope

- Web UI.
- Authentication and user accounts.
- Multi-user collaboration features.
- External SaaS integration for the baseline run.
- Real-time multiplayer networking.

## User Stories

- As a user, I can run one command to simulate a scenario for a chosen seed and number of rounds.
- As a user, I can inspect a CSV file that records round, action, payoff, inventory, and reputation.
- As a user, I can generate a plot that compares cumulative payoff across agents.
- As a developer, I can replace one agent policy without changing the environment contract.
- As a reviewer, I can trace every payoff back to documented rules.

## Acceptance Criteria

- The simulation runs with 3 agents and at least 10 rounds.
- The exported CSV contains one row per agent per round.
- The simulation produces cumulative payoff summaries for all agents.
- The implementation produces at least one visualization artifact.
- The environment updates inventory, payoff, and reputation using fixed rules.
- The default run does not require network access or external credentials.

## Non-Goals

- Production-grade order book matching.
- Full market microstructure realism.
- Live LLM API orchestration in the first implementation.
- Generic framework support for arbitrary game types.
