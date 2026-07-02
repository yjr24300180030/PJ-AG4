# PJ-AG4 最终实验结果整理

## 实验口径

- 随机种子：`seed=7`
- 轮数：`rounds=12`
- Agent 数量：3 个，分别是 `Hyperscaler`、`PremiumCloud`、`SpotBroker`
- 场景：`baseline`、`price_war`、`supply_shock`、`high_volatility`、`no_reputation`、`no_transfer`
- LLM API 服务：自部署或云端可访问接口，模型 `gemini-3-flash`
- 最新对齐汇总文件：`simulation_result.csv`

本轮最终比较 4 类模式：

| 模式 | 含义 |
| --- | --- |
| `llm` | LLM 直接输出 forecast、price、quantity |
| `llm-context` | 直接 LLM action，但 prompt 加入压缩历史上下文和 signals |
| `llm-adaptive` | LLM 不直接出 action，只更新 bounded strategy state |
| `llm-context-adaptive` | 在 adaptive 基础上加入 context payload |

校验结果：所有模式、所有 scenario 都是 36 行记录；新版 `llm-context` 和 `llm-context-adaptive` 均无 fallback。

## Scenario 结果总表

| 场景 | 最优模式 | Profit | Fulfillment | Defaults | Final Backlog | 说明 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `baseline` | `llm-context-adaptive` | 3823.67 | 99.20% | 3 | 0.58 | 稳态场景下 context-adaptive 收益最高，但 defaults 略多 |
| `price_war` | `llm-adaptive` | 3597.09 | 99.78% | 0 | 0.00 | 价格战中原 adaptive 更稳，context-adaptive 略低 |
| `supply_shock` | `llm-context-adaptive` | 4326.60 | 96.08% | 7 | 3.65 | 最强展示场景，context-adaptive 同时提高 profit 并大幅降低 backlog |
| `high_volatility` | `llm-context-adaptive` | 3745.00 | 99.27% | 2 | 1.10 | 波动场景下 context signals 帮助策略更稳 |
| `no_reputation` | `llm-context-adaptive` | 3693.09 | 98.96% | 5 | 2.63 | 声誉关闭后，历史上下文补充了部分趋势信息 |
| `no_transfer` | `llm-context-adaptive` | 3591.06 | 98.29% | 7 | 0.00 | 无 transfer 兜底时，context-adaptive 仍能压住 backlog |

## 关键发现

### Finding 1：最终推荐模式是 `llm-context-adaptive`

在 6 个场景中，`llm-context-adaptive` 有 5 个场景 profit 第一：

- `baseline`：3823.67，高于 `llm-adaptive` 的 3716.37
- `supply_shock`：4326.60，高于 `llm-adaptive` 的 4237.78
- `high_volatility`：3745.00，高于 `llm-adaptive` 的 3706.56
- `no_reputation`：3693.09，高于 `llm-adaptive` 的 3532.82
- `no_transfer`：3591.06，高于 `llm-adaptive` 的 3558.80

唯一例外是 `price_war`：`llm-adaptive` profit 为 3597.09，`llm-context-adaptive` 为 3501.24。

结论：最终展示时可以把 `llm-context-adaptive` 作为主模型，把 `price_war` 作为局限讨论。

### Finding 2：Context 单独加到 direct LLM 上并不稳定

`llm-context` 不是稳定提升：

- 在 `price_war` 和 `supply_shock` 中比旧 direct `llm` 更好。
- 在 `baseline`、`high_volatility`、`no_transfer` 中反而更差。

这说明“给 LLM 更多上下文”本身不是自动有效的。直接让 LLM 根据上下文输出 price/quantity，容易放大短期信号或产生不稳定 action。

答辩表达：context 的价值不是简单地把历史塞进 prompt，而是要和 bounded adaptive strategy update 结合。

### Finding 3：Context-adaptive 在冲击场景最有解释力

`supply_shock` 是最适合展示的 demo 场景：

| 模式 | Profit | Fulfillment | Defaults | Final Backlog | Transfer |
| --- | ---: | ---: | ---: | ---: | ---: |
| `llm` | 3597.16 | 93.22% | 9 | 11.10 | 15.15 |
| `llm-context` | 3696.31 | 95.10% | 9 | 11.19 | 50.31 |
| `llm-adaptive` | 4237.78 | 95.30% | 7 | 10.92 | 92.52 |
| `llm-context-adaptive` | 4326.60 | 96.08% | 7 | 3.65 | 83.96 |

相比前一版 prompt，当前 context payload 在 `supply_shock` 中：

- Profit 增加 141.62
- Fulfillment 增加 2.29 个百分点
- Final backlog 减少 7.10
- Defaults 不变

这可以讲成：context signals 让 agent 看到了连续服务压力和 shock/forecast error，从而更合理地调整 bounded strategy state。

### Finding 4：Adaptive 比 direct LLM 更适合这个市场模拟

直接 LLM 模式的 forecast MAE 较低，但 profit 通常低于 adaptive 系列。这是因为 direct LLM 更像在做单轮预测，而 adaptive 系列优化的是长期策略状态。

展示时可以强调：

- `llm` 更像黑箱 action generator。
- `llm-context` 有历史，但仍直接输出 action，不够稳。
- `llm-adaptive` 把 LLM 限制在策略参数更新上。
- `llm-context-adaptive` 进一步让策略更新有历史证据和 signal 标签。

## 推荐答辩叙事

1. 先讲市场机制：客户分层、二阶段 allocation、transfer、SLA backlog。
2. 再讲 agent 设计：从 heuristic 到 direct LLM，再到 bounded adaptive。
3. 重点解释 context：不是长 prompt，而是选择、压缩和标注历史证据。
4. 用 `supply_shock` 展示完整闭环：shock 出现、服务压力上升、context signals 进入 prompt、strategy state 更新、backlog 降低。
5. 最后讲局限：`price_war` 中 context-adaptive 没有超过原 adaptive，说明 context 会引入额外敏感性，需要进一步做 prompt calibration 或更长 seed sweep。

## 最终一句话结论

`llm-context-adaptive` 是当前项目最适合作为最终展示的 agent 模式：它把市场机制、agent 对抗、LLM 自适应和历史 context 结合起来，并且在 6 个场景中的 5 个取得最高 profit，尤其在 `supply_shock` 场景中显著降低 backlog。
