# PJ-AG4

PJ-AG4 是一个课程大作业项目，用于模拟高端 GPU 算力市场中的多智能体竞争与协作。项目把 GPU 服务商、客户需求、价格竞争、库存供给、声誉、SLA 违约和 LLM 策略调整放在同一个可复现的本地模拟环境中，最终通过 CSV、Markdown report 和 HTML dashboard 展示市场运行过程。

项目的核心问题是：

> 当多个 GPU 服务商面对不同类型客户和突发市场变化时，agent 如何在价格、供给、服务质量和长期声誉之间做权衡？

本项目不是一个纯前端展示页，而是一个完整的模拟实验系统。静态 HTML dashboard 是最终展示界面，背后还有可运行的市场环境、agent 决策逻辑、场景实验和量化输出。

## 项目目标

- 构建一个可复现的 GPU 市场模拟环境。
- 设计多个具有差异化定位的市场参与者。
- 模拟客户分层、价格竞争、供给不足、SLA backlog 和 agent 间 transfer。
- 引入 LLM 或 LLM-adaptive agent，让策略调整过程可以被记录和解释。
- 生成适合课程答辩的 dashboard、实验数据和展示材料。

## 功能概览

当前版本包含：

- 3 个 GPU 市场参与者：`Hyperscaler`、`PremiumCloud`、`SpotBroker`
- 3 种 agent 模式：`heuristic`、`llm`、`llm-adaptive`
- 6 个内置场景：`baseline`、`price_war`、`supply_shock`、`high_volatility`、`no_reputation`、`no_transfer`
- 多层市场机制：客户分层、二阶段 reallocation、agent transfer、SLA backlog、price pressure cost
- 多种输出：CSV、PDF 图表、Markdown report、HTML dashboard
- 批量实验工具：scenario sweep、benchmark、ablation 对比
- 本地 dashboard 服务和静态 dashboard 文件
- 自动化测试覆盖核心机制

## 项目结构

```text
src/pj_ag4/              核心模拟代码
  agents/                agent 决策逻辑，包括 heuristic、llm、llm-adaptive
  data/agents.json       三个 agent 的角色、成本、容量和初始声誉配置
  config.py              市场参数、scenario profile、LLM 配置
  environment.py         市场结算、allocation、transfer、backlog、profit 计算
  dashboard.py           静态 HTML dashboard 数据生成
  web.py                 本地 dashboard 服务

quant/                   多场景、多 seed 实验工具
docs/project_design.md   项目机制设计说明和 CSV 字段说明
presentation/            答辩草稿和 demo script
tests/                   单元测试和集成测试
dashboard_template.html  dashboard 前端模板
```

## 最终版市场机制

这一节对应代码中的 [src/pj_ag4/config.py](src/pj_ag4/config.py)、[src/pj_ag4/environment.py](src/pj_ag4/environment.py)、[src/pj_ag4/contracts.py](src/pj_ag4/contracts.py) 和 [src/pj_ag4/agents/adaptive.py](src/pj_ag4/agents/adaptive.py)。下面的字段名和参数都按当前代码整理。

### 1. 客户分层

总需求不再是一个单一池子，而是拆成三类客户：

| 客户段 | 默认占比 | 价格权重 | 声誉权重 | SLA/交付权重 | 合同需求比例 | 角色偏置 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `training_burst` | 45% | 0.75 | 0.80 | 0.35 | 10% | 偏向 `hyperscaler` |
| `enterprise_sla` | 35% | 0.35 | 1.45 | 1.10 | 75% | 偏向 `premium`，轻微排斥 `spot` |
| `spot_workload` | 20% | 1.15 | 0.45 | 0.15 | 5% | 偏向 `spot` |

每类客户会单独计算 agent 吸引力：

```text
segment_score =
  brand_weight * brand_strength
  + reputation_weight * reputation
  + sla_weight * delivery_reputation
  + role_bias
  - price_weight * price
```

然后对每个客户段单独做 softmax 分配。这样三个 agent 会自然分化：

- `Hyperscaler` 更容易吸引训练高峰和规模型需求。
- `PremiumCloud` 更容易吸引企业 SLA 客户，但也承担更多 backlog 和违约压力。
- `SpotBroker` 更容易吸引价格敏感的 spot workload。

### 2. 二阶段 allocation

第一阶段：客户按 segment-wise logit 选择 agent。

第二阶段：如果某个 agent 供给不足，未满足需求会尝试改签到仍有 surplus 的 agent。候选 agent 按通用吸引力排序，通用吸引力由品牌、总声誉和价格共同决定：

```text
attractiveness =
  brand_strength
  + market.reputation_weight * reputation
  - market.price_weight * price
```

默认情况下 `reallocation_fill_rate=1.0`，表示 reallocation 可以尽量填补剩余需求。`supply_shock` 场景中该值调为 `0.60`，是为了保留一部分局部短缺给 transfer 机制展示。

对应 CSV 字段：

- `reallocated_in`
- `reallocated_out`

这个机制用来解释“客户不是完全死等一个服务商”，而会在市场中寻找替代供给。

### 3. Agent transfer

二阶段 allocation 后，如果仍有局部短缺，agent 之间可以发生 transfer：

- 有 surplus 的 agent 可以向短缺 agent 提供 GPU 量。
- transfer 有接受概率，受合作声誉、供需压力和历史行为影响。
- transfer 有 markup，表示互助不是免费的。

代码里的接受概率是 sigmoid 形式，主要由以下因素决定：

```text
willingness =
  sigmoid(
    cooperation_alpha0
    + cooperation_alpha1 * requester_cooperation_reputation
    - cooperation_alpha2 * provider_load_ratio
    - cooperation_alpha3 * requester_last_dump_flag
  )
```

其中 `provider_load_ratio` 越高，供给方越不愿意帮；请求方上一轮如果有 dump 行为，也会降低别人帮助它的概率。每次 transfer 的最大量由 `max_transfer` 控制。

对应 CSV 字段：

- `transfer_in`
- `transfer_out`
- `transfer_attempts`
- `transfer_accepts`
- `coop_probability`
- `coop_accept_rate`

### 4. SLA backlog 队列

SLA backlog 是按 agent 聚合的轻量队列，不建复杂合同对象。每轮结算时：

1. 先读取上一轮遗留的 `backlog_start`。
2. 本轮可用供给会优先交付历史 backlog，形成 `delivered_backlog`。
3. 当前需求中，按各 segment 的 `contract_fraction` 估算合同型需求。
4. 当前供给不足部分中，合同型比例对应的短缺进入新的 backlog。
5. 上一轮 backlog 若仍未交付，会形成 `late_units` 和 `sla_queue_penalty`。

这意味着企业 SLA 客户没有被满足时，不是简单消失，而是会把服务压力带到后续轮次。

对应 CSV 字段：

- `backlog_start`
- `new_contract_demand`
- `delivered_backlog`
- `backlog_end`
- `late_units`
- `sla_queue_penalty`

这个机制让服务质量有跨轮影响，适合答辩展示“短期缺货会造成长期压力”。

### 5. Price pressure cost

`price_war` 场景中，价格战不是免费抢客户。系统加入了 `price_pressure_cost`，表示促销、竞价、获客补贴等摩擦成本。当前代码公式是：

```text
discount_depth = max(0, base_price - action.price)
price_pressure_cost =
  price_pressure_cost_rate
  * (0.45 * spot_workload_allocated + realized_sales * discount_depth)
```

其中 `price_war` 的 `price_pressure_cost_rate=0.55`。所以这个成本来自两部分：

- 吸引 spot workload 的市场/渠道摩擦成本。
- 实际成交价格低于该 agent `base_price` 时的折扣压力。

这样可以解释：

- 降价或抢 spot 客户可能提高履约和市场份额。
- 但激进价格竞争会侵蚀利润。

### 6. LLM-adaptive 策略更新

`llm-adaptive` 模式下，LLM 不直接输出最终价格和数量，而是根据上一轮结果调整一个 bounded strategy state：

- `risk_tolerance`
- `price_aggressiveness`
- `demand_sensitivity`
- `inventory_caution`
- `shock_responsiveness`
- `competitor_reactivity`

具体流程：

1. 先用 heuristic agent 生成一个 fallback action。
2. 用当前 strategy state 调整 forecast、price、quantity。
3. 通过 risk gate 做最终合法性和风险约束。
4. 本轮结算后，把 profit、service rate、shortage、backlog、price pressure cost 等反馈给 LLM。
5. LLM 输出各策略参数的 delta，而不是直接输出下一轮价格或数量。
6. delta 会经过角色权重、每参数最大步长和边界阻尼处理。

策略状态的实际更新区间是 `[0.05, 0.95]`，不是完整 `[0, 1]`。这样做是为了避免 12 轮内很快贴到极端值。

三个角色的初始策略也不同：

| 角色 | 初始倾向 |
| --- | --- |
| `hyperscaler` | 更高 risk tolerance 和 price aggression，更低 inventory caution |
| `premium` | 更高 inventory caution，策略更保守 |
| `spot` | 更高 shock responsiveness 和 competitor reactivity |

## 内置场景

| Scenario | 代码里的主要变化 | 适合展示什么 |
| --- | --- | --- |
| `baseline` | 默认市场参数；客户分层、reallocation、transfer、SLA backlog 都开启 | 正常市场、客户分层、角色分化 |
| `price_war` | `price_weight=1.15`，`reputation_weight=0.85`，spot 占比提高到 40%，spot 价格权重提高到 1.70，`price_pressure_cost_rate=0.55` | 价格战能吸引价格敏感客户，但不是免费增长 |
| `supply_shock` | `shock_round=8`，`shock_magnitude=60.0`，`max_transfer=35.0`，`transfer_markup=0.04`，`cooperation_alpha0=0.25`，`reallocation_fill_rate=0.60` | 需求冲击、default/backlog、reallocation 和 transfer 缓冲 |
| `high_volatility` | `ar_sigma=16.0`，`observation_noise_sigma=10.0`，7 日季节振幅提高到 25，`shock_round=12`，`shock_magnitude=35.0` | 高波动下的预测误差和服务压力 |
| `no_reputation` | 总声誉权重归零，delivery/pricing/cooperation reputation 权重归零；客户段中的 reputation 和 SLA 权重也归零 | 声誉和 SLA 信号消融 |
| `no_transfer` | `transfer_enabled=False`，`max_transfer=0.0` | 关闭 agent 间互助后的对照实验 |

## 安装与基础运行

建议先安装 editable package：

```bash
python3 -m pip install -e '.[dev]' --no-build-isolation
```

运行默认模拟：

```bash
pj-ag4-run --rounds 30 --output-dir outputs/default_run
```

生成的主要文件：

```text
outputs/default_run/simulation_results.csv
outputs/default_run/strategy_analysis.pdf
outputs/default_run/strategy_dashboard.html
outputs/default_run/simulation_report.md
```

## 最终展示推荐命令

### 1. 跑答辩 demo 场景

```bash
pj-ag4-run --scenario supply_shock --rounds 30 --output-dir outputs/final
```

重点看：

- `outputs/final/strategy_dashboard.html`
- `outputs/final/simulation_report.md`
- `outputs/final/simulation_results.csv`

### 2. 跑多场景 sweep

```bash
pj-ag4-scenarios \
  --rounds 30 \
  --seeds 7 11 23 \
  --output-root outputs/final/scenario_sweep
```

输出：

```text
outputs/final/scenario_sweep/scenario_summary.csv
outputs/final/scenario_sweep/scenario_report.md
```

### 3. 跑真实 LLM-adaptive demo

本地需要有 OpenAI-compatible 网关，例如：

```text
http://127.0.0.1:8045/v1
```

运行：

```bash
pj-ag4-run \
  --agent-mode llm-adaptive \
  --scenario supply_shock \
  --rounds 12 \
  --seed 7 \
  --llm-base-url http://127.0.0.1:8045/v1 \
  --llm-api-key local-dev-key \
  --llm-model gemini-3-flash \
  --output-dir outputs/llm_demo
```

如果使用自己的 key，也可以通过 `.env` 配置：

```env
PJ_AG4_OPENAI_API_KEY=your-api-key-here
PJ_AG4_OPENAI_BASE_URL=http://127.0.0.1:8045/v1
PJ_AG4_OPENAI_MODEL=gemini-3-flash
```

优先级：

1. CLI 参数，例如 `--llm-api-key`
2. `.env` 或环境变量
3. 代码内置默认值

## Dashboard 使用

静态 dashboard 文件会生成在每次输出目录中：

```text
outputs/<run_name>/strategy_dashboard.html
```

它适合答辩时展示：

- executive summary
- winner、fulfillment、total profit
- transfer/default/backlog 事件
- 每个 agent 的客户段销售构成
- LLM adaptive strategy state
- event timeline
- decision trace 和 strategy update trace

如果要启动本地服务：

```bash
python3 -m pj_ag4.web --host 127.0.0.1 --port 8766
```

或：

```bash
pj-ag4-web --host 127.0.0.1 --port 8766
```

打开：

```text
http://127.0.0.1:8766/
http://127.0.0.1:8766/?scenario=supply_shock
http://127.0.0.1:8766/?agent_mode=llm-adaptive&scenario=supply_shock
```

## 答辩建议讲法

推荐按这条链条讲：

```text
客户分层
  -> agent 角色分化
  -> 场景冲击或价格竞争
  -> reallocation / transfer / SLA backlog
  -> profit、reputation、service rate 变化
  -> LLM-adaptive 策略更新
```

最清楚的展示路径：

1. `baseline`：说明三类客户和三个 agent 的定位。
2. `price_war`：说明价格敏感客户增加，但 price pressure cost 侵蚀利润。
3. `supply_shock`：说明需求冲击如何造成 default/backlog，以及 transfer 如何缓冲局部错配。
4. `no_reputation`：说明声誉/SLA 信号的价值。
5. `no_transfer`：说明 transfer 机制的价值。

## 测试

运行：

```bash
pytest -q
```

当前预期结果：

```text
46 passed
```

## 重要文档

- [docs/project_design.md](docs/project_design.md)：完整机制设计和 CSV 字段说明
- [docs/final_improvements.md](docs/final_improvements.md)：最终版改进摘要
- [docs/llm_adaptive_strategy_plan.md](docs/llm_adaptive_strategy_plan.md)：LLM 自适应策略设计
- [presentation/final_presentation.md](presentation/final_presentation.md)：答辩 slides 草稿
- [presentation/demo_script.md](presentation/demo_script.md)：答辩 demo 讲稿

## 当前状态

当前 `main` 已包含最终展示版机制：

- 可复现模拟核心
- 启发式、LLM、LLM-adaptive 三种 agent 模式
- 客户分层、二阶段 reallocation、transfer、SLA backlog、price pressure cost
- 多场景实验和 ablation
- CSV、PDF、Markdown report、HTML dashboard
- 通过测试的最终代码
