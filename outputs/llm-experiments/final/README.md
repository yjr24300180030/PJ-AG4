# PJ-AG4 最终场景实验数据

本目录整理了最终使用的 LLM 场景实验结果和 heuristic 对照组。文件名只保留实验含义，随机种子和轮数等口径统一写在说明中，避免把运行参数堆到路径里。

## 包含内容

- 各场景的 `simulation_results.csv`
- 各场景的 `simulation_report.md`
- 跨场景汇总文件：`simulation_result.csv`、`agent-summary.csv`
- 对齐实验说明：`report.md`
- 最终中文总结：`final-summary.md`
- CSV 压缩包：`experiment-csvs.zip`

## 主要实验组

- `heuristic`：启发式策略对照组。
- `llm-direct`：LLM 直接输出行动。
- `llm-context`：LLM 直接输出行动，并加入压缩历史上下文。
- `llm-adaptive`：LLM 更新 bounded strategy state。
- `llm-context-adaptive`：在 adaptive 策略更新中加入历史上下文。
- `calibrated`、`calibrated-final`：用于策略校准对比的补充结果。

## 统一实验口径

- 随机种子：`7`
- 轮数：`12`
- 场景：`baseline`、`price_war`、`supply_shock`、`high_volatility`、`no_reputation`、`no_transfer`

大型 HTML 可视化和临时 smoke 输出没有放入本目录，以保持仓库整洁。
