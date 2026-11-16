# PJ-AG4 中期报告材料

本目录保存中期报告相关的文档、图表和实验输出，便于从仓库内复现报告中引用的结果。

## 主要文件

- `PJ-AG4_midterm_report.pdf`：LaTeX 编译后的中期报告。
- `PJ-AG4_人工智能导论中期汇报_填写版.docx`：课程中期模板填写版。
- `midterm_report.md`：LaTeX 重写前的 Markdown 草稿。
- `latex/paper.tex`：LaTeX 源文件。
- `latex/paper.pdf`：LaTeX 编译结果。

## 对照实验

- `llm_run_20/simulation_results.csv`
- `llm_run_20/strategy_analysis.pdf`
- `heuristic_run_20/simulation_results.csv`
- `heuristic_run_20/strategy_analysis.pdf`

## 辅助实验

- `default_run/`：30 轮启发式基准运行。
- `benchmark/reports/`：策略 benchmark 的 CSV、Markdown 和图片输出。
- `sensitivity/reports/`：声誉权重和观测噪声敏感性分析输出。

## 报告引用图表

- `latex/figures/llm_profit_evolution.png`
- `latex/figures/llm_market_fulfillment.png`
- `latex/figures/llm_agent_state_dynamics.png`
- `latex/figures/llm_vs_heuristic.png`
- `latex/figures/profit_evolution.png`
- `latex/figures/market_fulfillment.png`
- `latex/figures/agent_state_dynamics.png`
- `latex/figures/benchmark_comparison.png`

## 相关源码

- `src/pj_ag4/timeseries.py`
- `src/pj_ag4/environment.py`
- `src/pj_ag4/core/runtime.py`
- `src/pj_ag4/data/observation.py`
- `quant/metrics.py`
- `quant/run_benchmarks.py`
- `quant/run_sensitivity.py`
