# PJ-AG4

LLM-driven market and game simulation project for a high-end GPU spot market and supply-chain scenario.

## Overview

PJ-AG4 is a local, reproducible multi-agent simulation with:

- 3 independent market participants
- deterministic baseline behavior and optional LLM-backed agents
- round-level CSV outputs
- summary visualization artifacts
- quant-style benchmark and sensitivity tooling

## Scenario

Formal project design for the high-end GPU spot market and supply-chain game:

- [docs/project_design.md](docs/project_design.md)

AI-facing control documents are grouped under:

- [docs/ai/README.md](docs/ai/README.md)
- [docs/ai/AGENT.md](docs/ai/AGENT.md)
- [docs/ai/PRD.md](docs/ai/PRD.md)
- [docs/ai/IMPLEMENTATION_PLAN.md](docs/ai/IMPLEMENTATION_PLAN.md)

Current execution roadmap:

- [plan.md](plan.md)
- [DESIGN.md](DESIGN.md)

## Repository Layout

```text
docs/
  ai/                    AI control and implementation guidance docs
  project_design.md      Scenario source of truth
src/pj_ag4/              Simulation package
quant/                   Benchmark and sensitivity tooling
scripts/                 Direct run helpers
tests/                   Test suite
plan.md                  Current repository roadmap
progress.txt             Working log
lessons.md               Anti-regression notes
```

## Deliverables

- `simulation_results.csv`
- `strategy_analysis.pdf`
- `strategy_dashboard.html`

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

You can also place runtime settings in a local `.env` file. Copy `.env.example` and fill in your values:

```bash
cp .env.example .env
```

Example:

```env
PJ_AG4_OPENAI_API_KEY=your-api-key-here
PJ_AG4_OPENAI_BASE_URL=http://127.0.0.1:8045/v1
PJ_AG4_OPENAI_MODEL=gemini-3-flash
```

The project will automatically load `.env` before building the simulation config. It reads:

- `PJ_AG4_OPENAI_API_KEY`
- `PJ_AG4_OPENAI_BASE_URL`
- `PJ_AG4_OPENAI_MODEL`
- `OPENAI_API_KEY` as a fallback for the API key only

Priority order:

1. CLI arguments such as `--llm-api-key`
2. Environment variables or values loaded from `.env`
3. Built-in defaults in code

If you prefer not to use `.env`, you can still export variables manually:

```bash
export PJ_AG4_OPENAI_API_KEY="your-key-here"
export PJ_AG4_OPENAI_BASE_URL="http://127.0.0.1:8045/v1"
export PJ_AG4_OPENAI_MODEL="gemini-3-flash"
```

Artifacts:

- `outputs/default_run/simulation_results.csv`
- `outputs/default_run/strategy_analysis.pdf`
- `outputs/default_run/strategy_dashboard.html`

The HTML dashboard is the local sandbox surface for:

- agent decision inspection
- market trend monitoring
- shock and anomaly review
- future controls for interventions and quant overlays

## Direct Layout Editing

If you want to tweak the dashboard layout directly, edit the root template file:

- [dashboard_template.html](/Users/yijunrong/Desktop/PJ-AG4/dashboard_template.html)

The generator now prefers this file over the built-in template in Python. After editing it, regenerate the dashboard:

```bash
python3 -m pj_ag4.cli --rounds 30 --output-dir outputs/dev_dashboard
```

Then open:

- `outputs/dev_dashboard/strategy_dashboard.html`

If you prefer a localhost web surface instead of opening the exported file directly, use the service startup steps below.

## Start The Local Dashboard Service

Recommended startup flow:

```bash
cd /Users/yijunrong/Desktop/PJ-AG4
python3 -m pj_ag4.web --host 127.0.0.1 --port 8766
```

If you installed the project entrypoints, the equivalent command is:

```bash
pj-ag4-web --host 127.0.0.1 --port 8766
```

For the LLM-backed runtime, make sure the local gateway is available at `http://127.0.0.1:8045/v1`. The localhost dashboard service will use:

- base URL: `http://127.0.0.1:8045/v1`
- model: `gemini-3-flash`
- API key: `local-dev-key`

After the service starts, open:

- `http://127.0.0.1:8766/` for the streaming dashboard UI
- `http://127.0.0.1:8766/?agent_mode=llm` to boot directly into LLM mode
- `http://127.0.0.1:8766/api/payload` for a one-shot JSON payload
- `http://127.0.0.1:8766/api/stream` for the event stream API

The service keeps running in the foreground. Stop it with `Ctrl+C`.

## Quant Toolkit

The `quant/` directory contains repeated-run benchmark and sensitivity helpers. See [quant/README.md](quant/README.md) for usage.

## Tests

Run the test suite with:

```bash
pytest
```

## Status

The repository currently has a runnable simulation core, switchable heuristic and LLM agent modes, CSV export, PDF chart generation, an interactive HTML dashboard artifact, quant tooling, and passing tests.
