# PJ-AG4 Simulation Report

## Run Parameters

| Seed | Scenario | Rounds | Agent Mode | Agents | Demand Window |
| --- | --- | --- | --- | --- | --- |
| 7 | baseline | 12 | llm-context | 3 | 5 |

## Market Summary

| Total Demand | Total Sales | Fulfillment | Average Market Price | Total Profit | Price Pressure Cost |
| --- | --- | --- | --- | --- | --- |
| 2298 | 2227.26 | 0.97 | 5.70 | 3430.21 | 0.00 |

## Agent Strategy Comparison

| Agent | Role | Final Cum Profit | Avg Profit | Avg Forecast Error | Avg Price | Total Sales | Avg Service Rate | Transfer In | Transfer Out | Price Pressure Cost | Dump Flags | Default Flags | Final Inventory | Final Reputation | Total Shortage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hyperscaler | hyperscaler | 1040.89 | 86.74 | 7.17 | 4.60 | 1369.65 | 1.00 | 0.00 | 0.00 | 0.00 | 10 | 0 | 14.25 | 0.61 | 0.00 |
| PremiumCloud | premium | 1523.24 | 126.94 | 5.25 | 6.80 | 427.59 | 0.92 | 0.77 | 5.38 | 0.00 | 0 | 3 | 0.00 | 0.95 | 42.07 |
| SpotBroker | spot | 866.08 | 72.17 | 2.92 | 5.70 | 430.02 | 0.94 | 5.38 | 0.77 | 0.00 | 0 | 3 | 0.00 | 0.85 | 28.67 |

## Round-Level Timeline

| Round | True Demand | Observed Demand | Sales | Avg Price | Profit | Shortage | Transfers | Reallocated | Backlog |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 181 | 184 | 170.00 | 5.27 | 515.13 | 11.00 | 0.00 | 23.81 | 6.16 |
| 1 | 197 | 195 | 173.84 | 5.53 | 192.12 | 23.16 | 0.00 | 16.03 | 11.42 |
| 2 | 198 | 197 | 196.08 | 5.67 | 292.26 | 1.92 | 2.57 | 3.87 | 0.59 |
| 3 | 202 | 204 | 191.66 | 5.73 | 263.94 | 10.34 | 0.00 | 1.98 | 4.37 |
| 4 | 193 | 194 | 193.00 | 5.80 | 284.75 | 0.00 | 0.00 | 0.00 | 0.00 |
| 5 | 182 | 183 | 182.00 | 5.73 | 256.68 | 0.00 | 0.00 | 14.57 | 0.00 |
| 6 | 171 | 175 | 171.00 | 5.67 | 219.99 | 0.00 | 2.81 | 11.81 | 0.00 |
| 7 | 194 | 196 | 194.00 | 5.73 | 267.70 | 0.00 | 0.00 | 8.29 | 0.00 |
| 8 | 196 | 187 | 181.88 | 5.73 | 310.95 | 14.12 | 0.00 | 8.68 | 5.84 |
| 9 | 200 | 198 | 194.16 | 5.87 | 302.37 | 5.84 | 0.77 | 2.38 | 2.27 |
| 10 | 198 | 198 | 195.73 | 5.87 | 296.97 | 2.27 | 0.00 | 3.90 | 1.02 |
| 11 | 186 | 183 | 183.91 | 5.80 | 227.37 | 2.09 | 0.00 | 3.64 | 0.82 |

## Findings

- **Finding 1: Reputation-weighted SLA posture can beat pure price cutting.** In scenario `baseline`, `PremiumCloud` ends first with cumulative profit `1523.24` and reputation `94.80%`.
- **Finding 2: Capacity pressure is now visible as customer migration and backlog.** Two-stage allocation reallocates `98.94` units and leaves final SLA backlog `0.82`.
- **Finding 3: Peer transfer is a stress valve, not the whole market.** Transfer volume totals `6.15` units while average forecast error is `5.11`, linking prediction quality to shortage/default risk.

## Key Events

| Round | True Demand | Sales | Signals |
| --- | --- | --- | --- |
| 1 | 197 | 173.84 | shortage=23.16; dump_flags=1; default_flags=2 |
| 3 | 202 | 191.66 | shortage=10.34; dump_flags=1; default_flags=2 |
| 8 | 196 | 181.88 | shortage=14.12; default_flags=1 |
| 0 | 181 | 170.00 | shortage=11.00; default_flags=1 |
| 9 | 200 | 194.16 | shortage=5.84; transfer=0.77; dump_flags=1 |
| 2 | 198 | 196.08 | shortage=1.92; transfer=2.57; dump_flags=1 |
| 6 | 171 | 171.00 | transfer=2.81; dump_flags=1 |
| 10 | 198 | 195.73 | shortage=2.27; dump_flags=1 |

## Decision Trace Samples

| Round | Agent | Source | Forecast Base | Forecast Adj | Price Base | Price Adj | Qty Target | Risk Gate | Summary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Hyperscaler | llm-context | 184.00 | 0.00 | 4.60 | 0.00 | 80.00 | inventory target capped quantity | forecast 184.0 + 0.0; price 4.60 + 0.00; quantity target 80.0; risk gate inventory target capped quantity; final forecast=184, price=4.60, quantity=70 |
| 0 | PremiumCloud | llm-context | 184.00 | -4.00 | 6.80 | -0.40 | 70.00 | inventory target capped quantity | forecast 184.0 + -4.0; price 6.80 + -0.40; quantity target 70.0; risk gate inventory target capped quantity; final forecast=180, price=6.40, quantity=0 |
| 0 | SpotBroker | llm-context | 184.00 | -4.00 | 5.00 | -0.20 | 20.00 | none | forecast 184.0 + -4.0; price 5.00 + -0.20; quantity target 20.0; risk gate none; final forecast=180, price=4.80, quantity=20 |
| 1 | Hyperscaler | llm-context | 184.00 | 22.00 | 4.60 | 0.00 | 120.00 | none | forecast 184.0 + 22.0; price 4.60 + 0.00; quantity target 120.0; risk gate none; final forecast=206, price=4.60, quantity=120 |
| 1 | PremiumCloud | llm-context | 184.00 | 4.00 | 6.60 | 0.00 | 30.00 | sla_guard reduced quantity under SLA/reputation pressure | forecast 184.0 + 4.0; price 6.60 + 0.00; quantity target 30.0; risk gate sla_guard reduced quantity under SLA/reputation pressure; final forecast=188, price=6.60, quantity=30 |
| 1 | SpotBroker | llm-context | 184.00 | 16.00 | 5.00 | 0.40 | 30.00 | none | forecast 184.0 + 16.0; price 5.00 + 0.40; quantity target 30.0; risk gate none; final forecast=200, price=5.40, quantity=30 |
| 2 | Hyperscaler | llm-context | 198.00 | 10.00 | 4.60 | 0.00 | 120.00 | none | forecast 198.0 + 10.0; price 4.60 + 0.00; quantity target 120.0; risk gate none; final forecast=208, price=4.60, quantity=120 |
| 2 | PremiumCloud | llm-context | 193.00 | 2.00 | 7.00 | -0.20 | 50.00 | sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity | forecast 193.0 + 2.0; price 7.00 + -0.20; quantity target 50.0; risk gate sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity; final forecast=195, price=6.80, quantity=50 |
| 2 | SpotBroker | llm-context | 200.00 | 0.00 | 5.40 | 0.20 | 40.00 | none | forecast 200.0 + 0.0; price 5.40 + 0.20; quantity target 40.0; risk gate none; final forecast=200, price=5.60, quantity=40 |
| 3 | Hyperscaler | llm-context | 198.00 | 12.00 | 4.60 | 0.00 | 120.00 | none | forecast 198.0 + 12.0; price 4.60 + 0.00; quantity target 120.0; risk gate none; final forecast=210, price=4.60, quantity=120 |
| 3 | PremiumCloud | llm-context | 195.00 | 5.00 | 7.00 | -0.20 | 40.00 | sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity | forecast 195.0 + 5.0; price 7.00 + -0.20; quantity target 40.0; risk gate sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity; final forecast=200, price=6.80, quantity=30 |
| 3 | SpotBroker | llm-context | 200.00 | 8.00 | 5.40 | 0.40 | 40.00 | none | forecast 200.0 + 8.0; price 5.40 + 0.40; quantity target 40.0; risk gate none; final forecast=208, price=5.80, quantity=40 |

## Adaptive Strategy Trace Samples

| Round | Agent | Personality | Price Delta | Inventory Delta | Risk Delta | Price State | Inventory State | Risk State | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Conclusion Notes

- **Winner:** `PremiumCloud` ends with cumulative profit `1523.24`, the highest value in this run.
- **Service leader:** `Hyperscaler` posts the strongest average service rate at `100.00%`.
- **Pricing posture:** `PremiumCloud` maintains the highest average price at `6.80`.
- **Market fulfillment:** the run sells `2227.26` units against `2298.00` true demand for a fulfillment ratio of `96.92%`.
- **Operational stress:** peer transfers total `6.15` units, customer reallocation totals `98.94`, final SLA backlog is `0.82`, with `10` dump flags and `6` default flags.

## Appendix: Agent Configuration

| Agent | Forecast | Pricing | Allocation | Risk | Base Price | Max Quantity |
| --- | --- | --- | --- | --- | --- | --- |
| Hyperscaler | momentum_chaser | share_grabber | capacity_expander | growth_tolerant | 4.60 | 120 |
| PremiumCloud | signal_smoother | premium_keeper | buffered_allocator | sla_guard | 5.40 | 120 |
| SpotBroker | volatility_reader | spread_hunter | inventory_light | inventory_guard | 4.90 | 80 |
