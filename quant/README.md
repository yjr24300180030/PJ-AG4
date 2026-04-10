# Quant Toolkit

`quant/` 是建立在 `src/pj_ag4` 仿真内核之上的实验分析层，主要用于批量回测、策略对比、参数敏感性分析和报告导出。

当前可用的两种使用方式：

- 直接调用 `quant.common`、`quant.metrics`、`quant.reporting` 这些 Python API
- 直接运行 `quant/` 下的脚本，快速生成 benchmark 和 sensitivity 报告

## 主要能力

- 多 seed 批量回测
- 多策略 benchmark 对比
- 参数敏感性扫描
- Markdown / CSV 报告导出
- 风险指标统计

当前统计指标包括：

- cumulative profit
- mean profit
- profit volatility
- Sharpe-like
- max drawdown
- Calmar-like
- win rate
- avg reputation
- avg service rate
- total shortage

## 当前策略

`quant` 层目前直接复用并扩展主项目的策略注册机制，默认可用策略是：

- `heuristic`
- `rule_price_cutter`
- `rule_inventory_guard`
- `llm`

其中 `llm` 需要本地可用的 OpenAI-compatible 端点，以及 API key 或 `.env` 配置。

## 快速开始

先在仓库根目录安装项目依赖：

```bash
python3 -m pip install -e '.[dev]' --no-build-isolation
```

### 1. 跑 benchmark

```bash
python3 quant/run_benchmarks.py \
  --rounds 10 \
  --seeds 7 11 23 \
  --strategies heuristic rule_price_cutter rule_inventory_guard \
  --output-root quant/outputs/benchmarks
```

输出产物包括：

- `quant/outputs/benchmarks/reports/benchmark_run_agent_metrics.csv`
- `quant/outputs/benchmarks/reports/benchmark_run_market_metrics.csv`
- `quant/outputs/benchmarks/reports/benchmark_aggregate.csv`
- `quant/outputs/benchmarks/reports/benchmark_report.md`
- `quant/outputs/benchmarks/reports/benchmark_summary.png`

默认 benchmark CLI 不会自动包含 `llm` 策略；如果要一起跑，需要显式把 `llm` 加到 `--strategies` 里。

### 2. 跑 sensitivity

```bash
python3 quant/run_sensitivity.py \
  --rounds 10 \
  --seeds 11 23 \
  --strategies heuristic \
  --beta-r-values 0.6 1.2 1.8 \
  --sigma-obs-values 1.0 5.0 10.0 \
  --output-root quant/outputs/sensitivity
```

输出产物包括：

- `quant/outputs/sensitivity/reports/sensitivity_grid.csv`
- `quant/outputs/sensitivity/reports/sensitivity_summary.csv`
- `quant/outputs/sensitivity/reports/sensitivity_report.md`
- `quant/outputs/sensitivity/reports/sensitivity_heatmap.png`

### 3. 一次跑完整量化流程

```bash
python3 quant/run_full_quant.py \
  --benchmark-rounds 10 \
  --benchmark-seeds 7 11 \
  --benchmark-strategies heuristic rule_price_cutter \
  --sensitivity-rounds 10 \
  --sensitivity-seeds 11 23 \
  --sensitivity-strategies heuristic \
  --beta-r-values 0.6 1.2 1.8 \
  --sigma-obs-values 1.0 5.0 10.0 \
  --output-root quant/outputs/full_quant
```

输出产物包括：

- benchmark 报告与图
- sensitivity 报告与图
- `full_quant_report.md`

## Python API 示例

下面这套 API 适合在 notebook、脚本或后续 benchmark CLI 中复用。

```python
from pathlib import Path

from quant.common import (
    BenchmarkPlan,
    SensitivityPlan,
    StrategyProfile,
    run_benchmark_suite,
    run_sensitivity_scan,
    summarize_benchmark_artifacts,
    summarize_sensitivity_artifacts,
)
from quant.reporting import (
    write_benchmark_csv,
    write_benchmark_markdown,
    write_sensitivity_csv,
    write_sensitivity_markdown,
)

bench_plan = BenchmarkPlan(
    strategies=(
        StrategyProfile(name="heuristic", kind="heuristic"),
        StrategyProfile(name="rule_price_cutter", kind="rule_price_cutter"),
        StrategyProfile(name="rule_inventory_guard", kind="rule_inventory_guard"),
    ),
    seeds=(11, 12, 13),
    rounds=10,
    output_root=Path("quant/outputs/api_bench"),
)
bench_runs = run_benchmark_suite(bench_plan)
bench_summary = summarize_benchmark_artifacts(bench_runs)
write_benchmark_markdown(Path("quant/outputs/api_bench/report.md"), bench_summary)
write_benchmark_csv(Path("quant/outputs/api_bench/summary.csv"), bench_summary)

sens_plan = SensitivityPlan(
    strategy=StrategyProfile(name="heuristic", kind="heuristic"),
    seeds=(11, 12, 13),
    parameter="reputation_weight",
    values=(0.6, 0.9, 1.2, 1.5),
    rounds=10,
    output_root=Path("quant/outputs/api_sensitivity"),
)
sens_runs = run_sensitivity_scan(sens_plan)
sens_summary = summarize_sensitivity_artifacts(sens_runs)
write_sensitivity_markdown(Path("quant/outputs/api_sensitivity/report.md"), sens_summary)
write_sensitivity_csv(Path("quant/outputs/api_sensitivity/summary.csv"), sens_summary)
```

## LLM 模式

如果 benchmark 里包含 `llm` 策略，优先使用仓库根目录的 `.env` 或系统环境变量：

- `PJ_AG4_OPENAI_API_KEY`
- `PJ_AG4_OPENAI_BASE_URL`
- `PJ_AG4_OPENAI_MODEL`

也可以直接通过脚本参数传入：

- `--llm-api-key`
- `--llm-base-url`
- `--llm-model`

## 目录说明

- `quant/common.py`
  对外更稳定的计划对象和运行辅助函数
- `quant/metrics.py`
  结果汇总与指标计算
- `quant/reporting.py`
  Markdown / CSV 导出
- `quant/strategies.py`
  `quant` 层扩展策略注册
- `quant/run_benchmarks.py`
  benchmark 脚本入口
- `quant/run_sensitivity.py`
  sensitivity 脚本入口
- `quant/run_full_quant.py`
  完整量化流程入口

## 当前状态

目前 `quant/` 的 CLI 脚本入口是可用的，适合直接做课程项目里的批量对比和报告导出。

如果后面要继续整理，优先建议是：

- 给主项目补正式的 `pj-ag4-benchmark` CLI
- 把 `benchmark` 与 `sensitivity` 的输出格式进一步统一
- 把报告生成器接到 `quant` 输出上，减少重复报告逻辑
