---
marp: true
theme: default
paginate: true
size: 16:9
footer: "PJ-AG4 GPU Market Simulation"
---

<style>
section {
  background: #0d1117;
  color: #d8dee9;
  font-family: "Inter", "Aptos", "Noto Sans SC", sans-serif;
  padding: 54px;
  border-left: 6px solid #7ee787;
}
h1, h2, h3 {
  color: #58a6ff;
  letter-spacing: 0;
}
h1 {
  font-size: 52px;
}
h2 {
  font-size: 38px;
  border-bottom: 1px solid #30363d;
  padding-bottom: 12px;
}
strong {
  color: #7ee787;
}
code {
  color: #7ee787;
  background: #161b22;
  border-radius: 4px;
  padding: 2px 6px;
}
table {
  width: 100%;
  font-size: 20px;
}
th {
  color: #7ee787;
}
.lead {
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.lead p {
  font-size: 24px;
}
</style>

<!-- _class: lead -->

# PJ-AG4

GPU Spot Market Simulation with LLM-Adaptive Agents

---

## Problem

- GPU capacity is scarce and volatile
- Providers compete on price, SLA, and reputation
- Shortage creates transfer and default pressure
- Strategy must adapt across repeated rounds

---

## Mechanism

```text
Demand segments
  -> Agent forecast / price / quantity
  -> Segment-wise logit allocation
  -> Capacity-constrained reallocation
  -> Peer transfer + SLA backlog
  -> Profit + reputation update
  -> LLM strategy adaptation
```

---

## Segments

| Segment | Preference | Expected Winner |
| --- | --- | --- |
| Training burst | capacity + price | Hyperscaler |
| Enterprise SLA | reputation + service | PremiumCloud |
| Spot workload | low price + agility | SpotBroker |

---

## Agents

- **Hyperscaler**: scale leader, share capture, capacity risk
- **PremiumCloud**: SLA-first, premium pricing, reputation moat
- **SpotBroker**: agile broker, shock response, light inventory
- **LLM adaptive**: updates bounded strategy parameters after feedback

---

## Innovation

- `DecisionTrace`: explains forecast, price, quantity, risk gate
- `StrategyState`: learns bounded policy parameters
- `StrategyPersonality`: prevents strategy convergence
- `StrategyUpdateTrace`: records why each agent changed strategy

---

## Experiments

| Scenario | Purpose |
| --- | --- |
| baseline | stable reference run |
| price_war | dumping and margin stress |
| supply_shock | shortage, transfer, default, backlog |
| high_volatility | forecast and inventory risk |
| no_reputation / no_transfer | mechanism ablations |

---

## Demo Path

- Open `outputs/final/strategy_dashboard.html`
- Start with executive summary KPIs
- Pick a high-stress round in `supply_shock`
- Show agent cards: segments, backlog, trace, adaptation
- Compare ablation report for mechanism evidence

---

## Takeaway

- Pure price cutting does not guarantee dominance
- Reputation and SLA discipline create long-run advantage
- Transfer and reallocation make service pressure visible
- LLM agents are useful when strategy updates are bounded and inspectable
