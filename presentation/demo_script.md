# PJ-AG4 Final Demo Script

## 1 minute

我们模拟高端 GPU 算力供应商在需求波动下的定价、备货、履约和声誉竞争。最终版本加入了客户分层、容量约束下的二阶段改签、同行拆借、SLA backlog，以及 LLM 有边界自适应策略。核心结论是：单纯低价抢份额会带来利润和声誉代价，稳定 SLA 和声誉溢价在长期更有优势。

## 5 minutes

1. 先讲市场：三类客户分别偏好容量、SLA 和低价。
2. 再讲机制：需求分配后，如果供应商缺货，客户先改签到有余量的对手，再进入 transfer 或 SLA backlog。
3. 然后讲 agent：Hyperscaler、PremiumCloud、SpotBroker 的长期 personality 不同。
4. 打开 dashboard，先看 winner、fulfillment、transfer/backlog/default。
5. 选一个 `supply_shock` 高压 round，看 agent card 里的 segment allocation、decision trace 和 strategy update。
6. 最后展示 scenario report：baseline、price war、supply shock、no reputation、no transfer 的对比。

## 10 minutes

在 5 分钟版基础上增加公式和实验解释：

- logit allocation: price、brand、reputation、SLA 权重按客户段不同变化。
- reallocation: 低价但缺货的供应商会把客户送给仍有 surplus 的竞争者。
- SLA queue: 未履约企业需求会形成 backlog，后续继续产生压力。
- LLM adaptive: LLM 只调整 bounded strategy state，不直接输出最终动作。
- ablation: `no_reputation` 和 `no_transfer` 用来证明机制不是装饰字段。

## Fixed Commands

```bash
pj-ag4-run --scenario supply_shock --rounds 30 --output-dir outputs/final
pj-ag4-scenarios --rounds 30 --seeds 7 11 23 --output-root outputs/final/scenario_sweep
```
