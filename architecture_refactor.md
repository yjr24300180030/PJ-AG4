# PJ-AG4 架构重构蓝图

## 1. 文档目标

本文档用于为 PJ-AG4 提供一份正式的架构重构总纲。重构目标不是推翻现有实现，而是在保持现有仿真结果、交付物和核心规则不变的前提下，把当前实现从隐式总控结构调整为显式分层结构，从而为后续的多阶段 LLM Agent、量化实验和对照研究提供稳定底座。

本蓝图吸收了 TradingAgents 项目中值得迁移的架构模式，包括分层编排、职责拆分、条件路由、provider 抽象和可控记忆机制，但不会直接照搬其金融数据栈、外部新闻流或完整框架形态。

## 2. 必须保持不变的项目边界

架构重构期间，以下项目边界保持不变：

- 项目仍然是本地可运行、可复现的 LLM 驱动博弈与市场仿真系统。
- 正式场景仍然是 AI 算力芯片高端 GPU 现货与供应链博弈。
- 默认验收物仍然包括 `simulation_results.csv`、`strategy_analysis.pdf`、至少 3 个独立 Agent、至少 10 轮交互，以及累计收益统计和可视化输出。
- 市场规则、收益函数、声誉机制、有限理性、技术折旧和同行拆借机制仍以 [docs/project_design.md](/Users/yijunrong/Desktop/PJ-AG4/docs/project_design.md) 为事实来源。
- 默认基线运行仍要求本地可执行、无需网络、无需 API key。`heuristic` 继续作为正式 baseline，`llm` 继续作为可切换后端。
- 环境结算权仍然属于统一环境对象，Agent 不直接修改库存、收益、声誉和结算结果。
- `quant/` 继续定位为研究与实验层，不并入运行时内核。

## 3. 当前架构问题

当前仓库已经具备可运行能力，但核心运行路径仍然把过多职责压缩在少量文件中，主要瓶颈如下：

- [src/pj_ag4/simulation.py](/Users/yijunrong/Desktop/PJ-AG4/src/pj_ag4/simulation.py) 同时承担运行编排、观测拼装、Agent 构造、逐轮调度、结果收集和图表输出等职责。
- [src/pj_ag4/agents.py](/Users/yijunrong/Desktop/PJ-AG4/src/pj_ag4/agents.py) 同时承担 heuristic 策略、角色差异化逻辑、Prompt 组装、OpenAI-compatible 调用、JSON 解析、重试策略和 fallback 行为。
- [src/pj_ag4/environment.py](/Users/yijunrong/Desktop/PJ-AG4/src/pj_ag4/environment.py) 作为结算内核相对清晰，但它当前只接收最终动作，尚未为 forecast、pricing review、risk gate 等中间阶段提供自然承载点。
- [quant/run_benchmarks.py](/Users/yijunrong/Desktop/PJ-AG4/quant/run_benchmarks.py) 和 [quant/run_sensitivity.py](/Users/yijunrong/Desktop/PJ-AG4/quant/run_sensitivity.py) 为了批量实验而重复了部分仿真流程，说明研究层尚未消费一套真正稳定的公共运行接口。

当前最需要拆解的不是环境规则本身，而是由 `simulation.py + agents.py` 共同形成的隐式总控层。只要这一层仍然高度耦合，后续引入 TradingAgents 风格的多角色流水线，就会把复杂度继续堆叠在原有结构上。

## 4. TradingAgents 中值得迁移的模式

TradingAgents 最值得借鉴的内容是架构组织方式，而不是股票交易题材本身。以下模式适合迁移到 PJ-AG4：

| TradingAgents 模式 | 迁移动机 | PJ-AG4 对应做法 |
| --- | --- | --- |
| 显式 orchestrator / graph setup | 把流程控制与角色逻辑分离 | 将当前 `simulation.py` 拆成显式 orchestrator，只负责轮次顺序、分支和回退 |
| 角色拆分 | 避免单个 prompt 同时承担全部决策职责 | 将单体 Agent 拆成 `Forecaster / Pricer / Allocator / RiskGate` 四段 |
| 条件路由 | 把高成本推理限制在关键状态 | 只在缺货风险、声誉下滑、冲击期或高分歧时触发复核 |
| provider 抽象 | 将模型供应商差异与业务逻辑解耦 | 将 OpenAI-compatible 调用、解析、重试和 fallback 下沉到 `providers/` |
| 反思与记忆 | 为跨轮决策提供可控上下文 | 增加滚动摘要或有限记忆，并将其作为实验变量 |
| dataflow / observation interface | 标准化可见信息 | 使用统一的 `ObservationBuilder` 管理有限理性窗口内的可见特征 |

以下内容不直接迁移：

- 股票新闻、社媒、基本面和技术面等外部数据流；
- 完整 LangGraph 依赖和重型图执行框架；
- 无上限的长期记忆系统；
- 生产级实时交易执行栈。

## 5. 优先级最高的 5 个改造切口

为了降低风险，重构顺序应遵循“先拆边界，再拆角色”的原则。优先级从高到低如下：

1. 抽离 provider adapter  
   主要切口位于 [src/pj_ag4/agents.py](/Users/yijunrong/Desktop/PJ-AG4/src/pj_ag4/agents.py) 和 [src/pj_ag4/config.py](/Users/yijunrong/Desktop/PJ-AG4/src/pj_ag4/config.py)。先把模型调用、响应解析、重试策略和 fallback 从策略逻辑中拆出。

2. 抽离 observation adapter  
   主要切口位于 [src/pj_ag4/simulation.py](/Users/yijunrong/Desktop/PJ-AG4/src/pj_ag4/simulation.py)。先把 `_build_observation()` 升级为正式的观测构造模块，为多阶段角色提供统一输入。

3. 建立 strategy registry  
   主要切口位于 [src/pj_ag4/agents.py](/Users/yijunrong/Desktop/PJ-AG4/src/pj_ag4/agents.py)、[quant/common.py](/Users/yijunrong/Desktop/PJ-AG4/quant/common.py) 和 [quant/strategies.py](/Users/yijunrong/Desktop/PJ-AG4/quant/strategies.py)。目标是统一 heuristic、llm 和 rule-based 策略的注册与调度入口，消除 monkey-patch 风险。

4. 将 `run_simulation()` 降级为 orchestrator shell  
   当前 [src/pj_ag4/simulation.py](/Users/yijunrong/Desktop/PJ-AG4/src/pj_ag4/simulation.py) 既是执行引擎，也是实验脚本入口。重构后它应只保留运行编排，结果落盘和图表生成通过独立接口完成。

5. 将单体 Agent 拆为 role pipeline  
   在前四步稳定之后，再把 Agent 决策从单函数升级为 `Forecaster -> Pricer -> Allocator -> RiskGate`。这是收益最高的一步，也是最应该最后做的一步。

## 6. 目标分层结构

目标结构采用“运行时内核 + 角色流水线 + 研究评估层”三层逻辑，并在代码目录上体现为如下形态：

```text
src/pj_ag4/
  core/
    config.py
    orchestrator.py
    runtime.py
    types.py
  domain/
    demand.py
    settlement.py
    reputation.py
    transfers.py
  data/
    observation.py
    feature_window.py
  providers/
    llm_client.py
    prompts.py
    fallback.py
  agents/
    base.py
    roles/
      hyperscaler.py
      premium_cloud.py
      spot_broker.py
    stages/
      forecaster.py
      pricer.py
      allocator.py
      risk_gate.py
    memory.py
  analysis/
    metrics.py
    reporting.py
  visualization/
    summary_figure.py

quant/
  common.py
  metrics.py
  reporting.py
  strategies.py
  run_benchmarks.py
  run_sensitivity.py
  run_full_quant.py
```

现有模块到目标结构的映射关系如下：

- [src/pj_ag4/environment.py](/Users/yijunrong/Desktop/PJ-AG4/src/pj_ag4/environment.py) 归入 `domain/`；
- [src/pj_ag4/timeseries.py](/Users/yijunrong/Desktop/PJ-AG4/src/pj_ag4/timeseries.py) 归入 `domain/demand.py`；
- [src/pj_ag4/simulation.py](/Users/yijunrong/Desktop/PJ-AG4/src/pj_ag4/simulation.py) 归入 `core/orchestrator.py`；
- [src/pj_ag4/agents.py](/Users/yijunrong/Desktop/PJ-AG4/src/pj_ag4/agents.py) 拆分为 `agents/` 与 `providers/` 两层；
- `quant/` 保持独立，仅依赖稳定公开接口，不直接绑定内部私有实现。

## 7. 三阶段路线图

### 阶段一：冻结内核

第一阶段只做结构抽离，不改变行为结果，目标是把环境、策略和实验三类职责切开。

- 从 `simulation.py` 中抽出 `ObservationBuilder`；
- 从 `agents.py` 中抽出 provider 适配层；
- 建立统一的 strategy registry；
- 保持现有 CSV 字段、图表产物和测试结果不变。

阶段完成标志：

- baseline 仿真结果与当前实现保持一致；
- `heuristic` 与 `llm` 两种模式仍可运行；
- 批量实验不再依赖复制主循环逻辑。

### 阶段二：角色流水线化

第二阶段引入 TradingAgents 风格的内部决策分工，但仍保持外部环境规则不变。

- 每个市场参与者改为四段式流程：`Forecaster -> Pricer -> Allocator -> RiskGate`；
- 条件路由保持浅层、明确、可测；
- 仅在冲击、缺货、声誉恶化或分歧过大时触发复核；
- 记忆或轮后反思只作为可控实验变量接入。

阶段完成标志：

- Agent 内部职责被拆开，但环境结算接口保持稳定；
- 角色流水线可与 heuristic backend 和 llm backend 同时兼容；
- 角色拆分提升了解释性，而不削弱复现性。

### 阶段三：研究化与量化化

第三阶段让 `quant/` 成为正式的研究评估层。

- 多 seed 批量回测通过统一 API 运行；
- benchmark、ablation、敏感性分析和 regime analysis 消费同一套结果模式；
- 自动生成表格、Markdown 报告和图形摘要；
- 对 heuristic、llm 和 rule-based 策略进行统一对照。

阶段完成标志：

- `quant/` 不再复制主运行逻辑；
- 项目可输出更强的量化证据，包括风险指标、鲁棒性分析和对照表。

## 8. `quant/` 的定位

`quant/` 应明确定位为实验与报告层，而不是市场内核的一部分。

- 它负责多 seed 回测、benchmark、参数敏感性、风险指标和自动化报告输出；
- 它依赖稳定的策略接口、CSV 结构和统一运行入口；
- 它不应重新实现市场结算规则；
- 它是项目“量化味”的主要承载层，但不应反向侵入 `src/pj_ag4/` 的运行时内核。

## 9. 明确的不做事项

本次重构不包含以下目标：

- 不新增 Web UI；
- 不把项目改造成生产级真实交易系统；
- 不引入外部新闻、社媒或实时市场数据；
- 不将 heuristic baseline 移除或降级；
- 不把 `simulation_results.csv`、`strategy_analysis.pdf`、图表与测试降为附属产物；
- 不在角色流水线尚未稳定前引入重型框架依赖。

## 10. 预期结果

完成本蓝图后，PJ-AG4 将保持现有课程项目交付能力，同时获得更清晰的架构边界：

- 市场环境内核负责规则和结算；
- 角色流水线负责可解释的策略形成；
- provider 层负责模型调用细节；
- `quant/` 负责实验、对照与量化分析。

这样，项目就能从“可运行的多 Agent 市场仿真”进一步升级为“可重构、可比较、可研究的 LLM 市场实验系统”。
