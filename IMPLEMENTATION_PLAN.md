# IMPLEMENTATION PLAN

## Milestones

1. Build the document and control layer.
2. Implement the simulation core and baseline agents.
3. Add CSV export, summary metrics, and charts.
4. Add tests and finalize the report-ready outputs.

## Step-by-Step Plan

### Step 1.1
- Objective: Freeze the document stack and project rules.
- Files: `PRD.md`, `APP_FLOW.md`, `TECH_STACK.md`, `FRONTEND_GUIDELINES.md`, `BACKEND_STRUCTURE.md`, `IMPLEMENTATION_PLAN.md`, `AGENT_CONTEXT.md`, `progress.txt`, `lessons.md`.
- Tests: Manual review against `docs/project_design.md`.
- Done when: every document contains concrete, implementation-guiding content.

### Step 1.2
- Objective: Create the Python package skeleton and configuration entrypoints.
- Files: `pyproject.toml`, `src/__init__.py`, `src/config.py`, `src/models.py`, `src/simulation.py`.
- Tests: import smoke test and config parsing test.
- Done when: the package imports cleanly and a minimal config object can be created.

### Step 2.1
- Objective: Implement demand generation and environment state transitions.
- Files: `src/demand.py`, `src/environment.py`.
- Tests: deterministic demand series test and one-step environment test.
- Done when: a seeded run produces stable round outputs.

### Step 2.2
- Objective: Implement three baseline agents and a common agent interface.
- Files: `src/agents.py`.
- Tests: action-range validation and fallback behavior test.
- Done when: three agents can complete a full simulation without manual intervention.

### Step 3.1
- Objective: Export simulation records to CSV and compute summary statistics.
- Files: `src/export.py`, `src/summary.py`.
- Tests: CSV schema test and metric aggregation test.
- Done when: `simulation_results.csv` is created with the documented columns.

### Step 3.2
- Objective: Generate report figures for payoff, reputation, and demand.
- Files: `src/plotting.py`, `scripts/run_simulation.py`.
- Tests: artifact existence test.
- Done when: at least one PNG or PDF figure is produced from a run.

### Step 4.1
- Objective: Add end-to-end tests and a reproducible CLI smoke path.
- Files: `tests/test_simulation.py`, `tests/test_exports.py`.
- Tests: full simulation smoke test.
- Done when: one command runs the baseline scenario and all tests pass.
