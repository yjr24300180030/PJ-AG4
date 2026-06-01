# LLM Adaptive Strategy Plan

## Summary

在新分支 `codex/llm-adaptive-strategy` 上新增 `llm-adaptive` 模式：LLM 每轮读取市场反馈，输出受限策略参数调整；系统用 agent 的持续性格先验约束这些调整，避免多个 agent 逐渐策略趋同。最终展示重点是：不同 agent 在同一市场反馈下会产生不同解释和不同策略更新。

## Key Changes

- 分支与工作区：
  - 从当前 `codex/dashboard-web-runtime` 创建 `codex/llm-adaptive-strategy`。
  - 不提交现有未跟踪文件和已存在的本地脏文件：`.gitignore`、`docs/ai/*`、`review.md`、PPT 目录等。
- 新增核心类型：
  - `StrategyState`：记录可学习策略参数，如 `risk_tolerance`、`price_aggressiveness`、`demand_sensitivity`、`inventory_caution`、`shock_responsiveness`、`competitor_reactivity`，范围固定为 `0.05-0.95`。
  - `StrategyPersonality`：记录持续性格先验，包括每个参数的 delta 权重、每个参数的最大调整幅度、目标偏好和 prompt guidance。
  - `StrategyUpdateTrace`：记录上一轮反馈、LLM 原始 delta、personality 约束后的 delta、新策略状态、fallback 状态和摘要。
  - `SettlementRow` 增加：`strategy_state`、`strategy_update_reason`、`strategy_update_trace`。
- 新增 `llm-adaptive` agent：
  - 每个 agent 初始 `StrategyState` 按角色不同设置。
  - 每个 agent 持有固定 `StrategyPersonality`，不仅影响初始化，也持续影响每轮策略更新。
  - 现有 `heuristic` fallback 仍负责生成安全动作；strategy state 作为参数影响 forecast / price / quantity。
  - LLM 不直接输出最终 `forecast_demand`、`price`、`quantity`。
- 持续性格机制：
  - LLM prompt 每轮包含 agent persona、role、当前 strategy state、上一轮 outcome、竞争者摘要，以及该 agent 的长期行为约束。
  - 同样的反馈会因 personality 不同产生不同解释：
    - Hyperscaler 更偏市场份额、产能扩张和价格进攻。
    - PremiumCloud 更偏声誉、服务稳定和价格溢价。
    - SpotBroker 更偏快速响应、贴近市场价和冲击套利。
  - LLM 原始 delta 先经过 JSON/schema 校验，再乘以 personality delta 权重，并按每个参数的 personality max delta 限幅，最后 clamp 到 `0.0-1.0`。
  - 这样 agent 能学习，但不会忘记自己是谁，避免策略趋同。
- LLM 策略更新阶段：
  - 在每轮 settlement 后调用 `observe_result(row, round_rows)`。
  - prompt 输入包括上一轮动作、profit、forecast error、inventory、shortage、service rate、market avg price、竞争者均价/利润、shock 信息、当前 strategy state 和 personality guidance。
  - LLM 只允许返回 JSON delta 和 `reason`：

```json
{
  "risk_tolerance_delta": 0.0,
  "price_aggressiveness_delta": 0.0,
  "demand_sensitivity_delta": 0.0,
  "inventory_caution_delta": 0.0,
  "shock_responsiveness_delta": 0.0,
  "competitor_reactivity_delta": 0.0,
  "reason": "..."
}
```

  - LLM 失败时使用 deterministic fallback update，并在 trace 中标记 `fallback_used=true`。
- Runtime / 输出 / 展示：
  - `SimulationRuntime.run()` 在 `env.step()` 后，把 settlement row 回传给对应 agent。
  - CSV 写入策略状态和更新 trace。
  - Markdown report 新增 "Adaptive Strategy Trace Samples"，展示 agent 为什么调参。
  - dashboard agent card 显示当前策略参数、策略变化摘要和 LLM 调整原因。
  - round log 显示类似：`learned: lowered price aggression, raised inventory caution after excess inventory`。
- CLI / registry：
  - `--agent-mode` 增加 `llm-adaptive`。
  - strategy registry 注册标题为 `LLM Adaptive`。
  - `llm-adaptive` 和现有 `llm` 一样要求 API key。

## Test Plan

- 单元测试：
  - `StrategyState` clamp 正确。
  - `StrategyPersonality` 会改变同一组 raw delta 的最终调整结果。
  - 不同 personality 面对同一 feedback 产生不同 bounded delta。
  - LLM adaptive 模式要求 API key。
  - LLM 返回非法 JSON 或调用失败时，使用 fallback update，仿真不中断。
- 集成测试：
  - `run_simulation(agent_mode="llm-adaptive", rounds=2)` 生成 6 行结果，并包含 `strategy_state` / `strategy_update_trace`。
  - fake LLM 返回固定 delta 后，下一轮 strategy state 发生可预测变化。
  - dashboard payload 包含 strategy state、personality label、update reason。
  - Markdown report 包含 adaptive trace 表格。
- 回归测试：
  - 现有 `heuristic`、`llm` 测试保持通过。
  - 执行 `pytest -q`、`git diff --check`。
- 手动验证：
  - 用 fake 或真实 OpenAI-compatible endpoint 跑 5-10 轮，确认 dashboard 能看到 agent 策略随反馈变化，并且三个 agent 不会迅速趋同。

## Assumptions

- 默认采用新增模式 `llm-adaptive`，不改变现有 `llm` 行为。
- LLM 每轮每个 agent 调用一次；第 0 轮没有上一轮反馈，所以从第 1 轮开始更新。
- LLM 是“策略反思与参数调整器”，不是直接动作控制器。
- Agent personality 是持续先验，不只是初始化条件。
- trace 文本优先服务 presentation：短、可解释、可展示，不暴露完整推理链。
