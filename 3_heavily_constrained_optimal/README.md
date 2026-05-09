# Branch 3: Heavily Constrained Optimal

## 实验目标
在强约束条件下（强制盈利 + 保守销售估计 + 进化微调），探索三个 Agent 在"教会 AI 不做离谱操作"的前提下，能达到的**集体最优解**。

## 竞争规则特点

| 维度 | 设定 | 说明 |
|---|---|---|
| **程序约束** | 强 | 三重安全网：① Cost Safety（price ≥ avg cost + step）；② Profit Safety（保守估计下必须盈利，否则强制降 quantity 或提价）；③ RiskGate Quantity Cap（qty 不超过 price ceiling 下的经济上限）。 |
| **进化频率** | 每 2 轮一次 | 高频策略回顾，加速收敛。 |
| **进化上限** | 适中 | `price_bias` ±0.2、`quantity_bias` ±8、`forecast_bias` ±4，与 Branch 2 相同。 |
| **利润导向** | 代码强制 + Prompt 引导 | 不仅告诉 LLM 要赚钱，代码层面直接否决任何预期亏损的方案。 |
| **核心假设** | 硬约束塑造均衡 | 当所有 Agent 都被强制要求盈利时，市场会收敛到一个"无亏损、有分化"的稳定状态。 |

## 预期观察
- 三个 Agent 的累计利润均为正，且波动收窄。
- 价格 converge 到各自 ceiling 附近，quantity converge 到经济可行区间。
- 角色差异被利润压力部分磨平（策略范式趋同），但因 cost structure 和 brand 差异，绝对数值仍有分化。

## 代码检查方法
- 确认 `_estimate_profit` 使用 `forecast * 0.4` 的保守 sales 估计。
- 确认 `_clamp_quantity_for_profit` 在 profit ≤ 0 时主动削减 quantity。
- 确认 evolution_limits 的 `max_delta` 被严格执行（单次调整 ≤ 0.2 / 8 / 4）。
- 检查最终轮：所有 Agent 的 cumulative profit > 0，且无单轮巨额亏损（> -200）。
