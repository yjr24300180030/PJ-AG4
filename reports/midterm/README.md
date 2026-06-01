# PJ-AG4 Midterm Report Artifacts

This directory contains the midterm report deliverables and all repository-local paths referenced by the report/docx.

## Main deliverables

- `PJ-AG4_midterm_report.pdf`: compiled LaTeX midterm report.
- `PJ-AG4_人工智能导论中期汇报_填写版.docx`: filled AI course midterm template.
- `midterm_report.md`: Markdown draft used before the LaTeX rewrite.
- `latex/paper.tex`: LaTeX source.
- `latex/paper.pdf`: compiled PDF next to the LaTeX source.

## LLM and baseline runs

- `llm_run_20/simulation_results.csv`
- `llm_run_20/strategy_analysis.pdf`
- `llm_run_20/strategy_dashboard.html`
- `heuristic_run_20/simulation_results.csv`
- `heuristic_run_20/strategy_analysis.pdf`
- `heuristic_run_20/strategy_dashboard.html`

## Supporting experiments

- `default_run/`: 30-round heuristic reference run used by the Markdown draft.
- `benchmark/reports/`: strategy comparison CSV/Markdown/PNG outputs.
- `sensitivity/reports/`: reputation/noise sensitivity CSV/Markdown/PNG outputs.

## Figures referenced by reports

- `latex/figures/llm_profit_evolution.png`
- `latex/figures/llm_market_fulfillment.png`
- `latex/figures/llm_agent_state_dynamics.png`
- `latex/figures/llm_vs_heuristic.png`
- `figures/profit_evolution.png`
- `figures/market_fulfillment.png`
- `figures/agent_state_dynamics.png`
- `figures/benchmark_comparison.png`

## Core source paths referenced by reports

These already live in the repository source tree:

- `src/pj_ag4/timeseries.py`
- `src/pj_ag4/environment.py`
- `src/pj_ag4/agents.py`
- `src/pj_ag4/core/runtime.py`
- `src/pj_ag4/data/observation.py`
- `quant/metrics.py`
- `quant/run_benchmarks.py`
- `quant/run_sensitivity.py`
- `README.md`
