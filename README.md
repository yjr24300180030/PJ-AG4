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
python3 -m pip install -e '.[dev]' --no-build-isolation
pj-ag4-run --rounds 30 --output-dir outputs/default_run
```

You can also run the bundled script directly:

```bash
python3 scripts/run_simulation.py --rounds 30 --output-dir outputs/default_run
```

Run with the LLM-backed agent mode against an OpenAI-compatible local endpoint:

```bash
pj-ag4-run \
  --agent-mode llm \
  --llm-base-url http://127.0.0.1:8045/v1 \
  --llm-model gemini-3-flash \
  --llm-api-key "$PJ_AG4_OPENAI_API_KEY" \
  --rounds 10 \
  --output-dir outputs/llm_run
```

The repository does not hardcode API secrets. Set the key before running:

```bash
export PJ_AG4_OPENAI_API_KEY="your-key-here"
```

Artifacts:

- `outputs/default_run/simulation_results.csv`
- `outputs/default_run/strategy_analysis.pdf`

Tests:

```bash
pytest
```

## Status

Repository initialized with formal design docs, a runnable Python simulation skeleton, switchable heuristic and LLM agent modes, CSV export, chart generation, and tests.
