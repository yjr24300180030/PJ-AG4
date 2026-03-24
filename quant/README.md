# Quant Toolkit

This folder adds a quant-style analysis layer on top of the PJ-AG4 simulation core.

It is designed for:

- multi-seed backtests
- benchmark comparisons across strategy families
- risk metrics such as mean, volatility, Sharpe-like score, max drawdown, Calmar-like score, and win rate
- sensitivity scans over market parameters
- Markdown and CSV summary exports

## Quick Start

Run from the repository root so the helper can reuse `src/pj_ag4`:

```python
from pathlib import Path

from quant.common import BenchmarkPlan, SensitivityPlan, StrategyProfile, run_benchmark_suite, run_sensitivity_scan
from quant.metrics import aggregate_run_summaries, aggregate_sensitivity_points
from quant.reporting import write_benchmark_csv, write_benchmark_markdown, write_sensitivity_csv, write_sensitivity_markdown
from quant.common import sensitivity_points_from_runs

bench_plan = BenchmarkPlan(
    strategies=(
        StrategyProfile(name="heuristic", kind="heuristic"),
        StrategyProfile(name="trend", kind="trend"),
        StrategyProfile(name="defensive", kind="defensive"),
        StrategyProfile(name="aggressive", kind="aggressive"),
    ),
    seeds=(11, 12, 13),
    rounds=10,
    output_root=Path("quant/outputs/bench"),
)
bench_runs = run_benchmark_suite(bench_plan)
bench_agg = aggregate_run_summaries([run.summary for run in bench_runs])
write_benchmark_markdown(Path("quant/outputs/bench/report.md"), bench_agg)
write_benchmark_csv(Path("quant/outputs/bench/summary.csv"), bench_agg)

sens_plan = SensitivityPlan(
    strategy=StrategyProfile(name="heuristic", kind="heuristic"),
    seeds=(11, 12, 13),
    parameter="reputation_weight",
    values=(0.6, 0.9, 1.2, 1.5),
    rounds=10,
    output_root=Path("quant/outputs/sensitivity"),
)
sens_runs = run_sensitivity_scan(sens_plan)
sens_points = aggregate_sensitivity_points(sensitivity_points_from_runs(sens_runs))
write_sensitivity_markdown(Path("quant/outputs/sensitivity/report.md"), sens_points)
write_sensitivity_csv(Path("quant/outputs/sensitivity/summary.csv"), sens_points)
```

## Strategy Families

- `heuristic`: the current PJ-AG4 baseline behavior
- `trend`: trend-following policy with more aggressive reaction to recent demand changes
- `defensive`: higher price, lower quantity, more stable inventory posture
- `aggressive`: lower price, larger quantity, higher market-share pressure
- `llm`: OpenAI-compatible LLM-backed agents through the existing simulation interface

## Output Layout

Recommended output folders:

- `quant/outputs/bench/`
- `quant/outputs/sensitivity/`
- `quant/outputs/benchmarks/`

Each run stores the raw simulation CSV and optional figure output. The reporting helpers can then generate aggregate CSV and Markdown summaries.

## Notes

- `quant/common.py` adds `src/` to `sys.path` automatically.
- No files outside `quant/` are modified by this toolkit.
- The toolkit is intentionally stdlib-only on top of the existing `pj_ag4` simulation dependencies.
