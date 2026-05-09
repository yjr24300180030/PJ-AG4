# Branch 1: Baseline Strict Character

## 实验目标
保留 Agent 的"原汁原味"性格，观察在最小外部干预下，三个差异化角色在利润导向下的自然竞争结果。

## 竞争规则特点

| 维度 | 设定 | 说明 |
|---|---|---|
| **程序约束** | 最小 | 仅保留最基本的 cost safety（price ≥ avg production cost），不强制 profit safety，不限制 quantity 上限。 |
| **进化频率** | 每 2 轮一次 | 比主实验更高频，加快策略迭代。 |
| **进化上限** | 极紧 | `price_bias` ±0.05、`quantity_bias` ±2、`forecast_bias` ±1，确保性格不会突变。 |
| **利润导向** | 通过 Prompt 引导 | 代码层面不强制盈利，靠 LLM 自身理解和进化参数微调来追求利润。 |
| **核心假设** | 性格稳定性 > 利润最大化 | 允许 Agent 为了维持角色一致性而承受短期亏损。 |

## 预期观察
- Hyperscaler（share_grabber）可能周期性大幅降价抢量，导致亏损。
- PremiumCloud（premium_keeper）可能坚持高价，份额萎缩但单轮利润波动大。
- SpotBroker（spread_hunter）可能在三者间灵活游走，寻找套利空间。

## 代码检查方法
- 确认 `evolution_limits` 中 `max_delta_per_evolution` 足够小（≤ 0.05 / 2 / 1）。
- 确认没有强制的 profit safety net 干预 LLM 原始决策。
