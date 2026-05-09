# Branch 2: Moderate Convergence

## 实验目标
在适度约束下，观察三个差异化性格能否收敛到**各自不同的盈利稳态**，而非被利润压力磨平为同一策略范式。

## 竞争规则特点

| 维度 | 设定 | 说明 |
|---|---|---|
| **程序约束** | 中等 | 保留 cost safety（price ≥ avg cost + step），但**移除 profit safety net 的 quantity 强制削减**。允许 Agent 在合理范围内探索高 quantity 策略。 |
| **进化频率** | 每 2 轮一次 | 与 Branch 1 相同，加快迭代。 |
| **进化上限** | 适中 | `price_bias` ±0.2、`quantity_bias` ±8、`forecast_bias` ±4，给予策略调整足够空间，但防止跳变。 |
| **利润导向** | Prompt + Cost Safety | LLM 被明确告知追求利润，但代码只在 price 低于成本时干预，不强制要求每轮必须盈利。 |
| **核心假设** | 差异化可以共存 | 如果市场结构足够丰富，三个角色应能找到各自的纳什均衡位，而不是全部挤到"高价低量"的窄巷。 |

## 预期观察
- Hyperscaler 可能收敛到"中价中量"路线，而非顶到 price ceiling。
- PremiumCloud 利用 brand_strength 优势守住高价利基。
- SpotBroker 保持灵活，在不同市场环境下切换策略。
- **关键指标**：三个 Agent 的 price 和 quantity 标准差是否保持显著差异（而非趋同）。

## 代码检查方法
- 确认没有 `_clamp_quantity_for_profit` 强制降低 quantity。
- 确认 evolution_limits 的 `max_delta` 处于适中水平（0.2 / 8 / 4）。
- 检查最终 16 轮的 price/qty 变异系数：若三者趋同则实验假设被否定。
