# PJ-AG4 Simulation Report

## Run Parameters

| Seed | Scenario | Rounds | Agent Mode | Agents | Demand Window |
| --- | --- | --- | --- | --- | --- |
| 7 | no_transfer | 12 | llm-context | 3 | 5 |

## Market Summary

| Total Demand | Total Sales | Fulfillment | Average Market Price | Total Profit | Price Pressure Cost |
| --- | --- | --- | --- | --- | --- |
| 2298 | 2256.63 | 0.98 | 5.68 | 3545.44 | 0.00 |

## Agent Strategy Comparison

| Agent | Role | Final Cum Profit | Avg Profit | Avg Forecast Error | Avg Price | Total Sales | Avg Service Rate | Transfer In | Transfer Out | Price Pressure Cost | Dump Flags | Default Flags | Final Inventory | Final Reputation | Total Shortage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hyperscaler | hyperscaler | 1080.26 | 90.02 | 7.83 | 4.60 | 1367.72 | 1.00 | 0.00 | 0.00 | 0.00 | 11 | 0 | 5.52 | 0.63 | 0.00 |
| PremiumCloud | premium | 1496.11 | 124.68 | 5.83 | 6.58 | 457.66 | 0.94 | 0.00 | 0.00 | 0.00 | 0 | 2 | 0.00 | 0.95 | 31.91 |
| SpotBroker | spot | 969.07 | 80.76 | 2.50 | 5.87 | 431.24 | 0.98 | 0.00 | 0.00 | 0.00 | 0 | 1 | 0.00 | 0.89 | 9.47 |

## Round-Level Timeline

| Round | True Demand | Observed Demand | Sales | Avg Price | Profit | Shortage | Transfers | Reallocated | Backlog |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 181 | 184 | 170.00 | 5.27 | 515.13 | 11.00 | 0.00 | 23.81 | 6.16 |
| 1 | 197 | 195 | 183.84 | 5.47 | 229.84 | 13.16 | 0.00 | 20.46 | 6.21 |
| 2 | 198 | 197 | 191.79 | 5.60 | 259.31 | 6.21 | 0.00 | 4.89 | 2.68 |
| 3 | 202 | 204 | 199.02 | 5.67 | 289.16 | 2.98 | 0.00 | 6.39 | 1.39 |
| 4 | 193 | 194 | 191.10 | 5.73 | 254.36 | 1.90 | 0.00 | 3.15 | 1.03 |
| 5 | 182 | 183 | 180.97 | 5.80 | 287.70 | 1.03 | 0.00 | 6.70 | 0.56 |
| 6 | 171 | 175 | 170.44 | 5.73 | 229.84 | 0.56 | 0.00 | 7.39 | 0.29 |
| 7 | 194 | 196 | 192.01 | 5.80 | 307.41 | 1.99 | 0.00 | 6.36 | 1.15 |
| 8 | 196 | 187 | 194.85 | 5.73 | 322.09 | 1.15 | 0.00 | 10.30 | 0.69 |
| 9 | 200 | 198 | 199.31 | 5.80 | 300.42 | 0.69 | 0.00 | 10.65 | 0.44 |
| 10 | 198 | 198 | 197.56 | 5.80 | 291.38 | 0.44 | 0.00 | 10.48 | 0.28 |
| 11 | 186 | 183 | 185.72 | 5.80 | 258.79 | 0.28 | 0.00 | 15.56 | 0.16 |

## Findings

- **Finding 1: Reputation-weighted SLA posture can beat pure price cutting.** In scenario `no_transfer`, `PremiumCloud` ends first with cumulative profit `1496.11` and reputation `94.78%`.
- **Finding 2: Capacity pressure is now visible as customer migration and backlog.** Two-stage allocation reallocates `126.15` units and leaves final SLA backlog `0.16`.
- **Finding 3: Peer transfer is a stress valve, not the whole market.** Transfer volume totals `0.00` units while average forecast error is `5.39`, linking prediction quality to shortage/default risk.

## Key Events

| Round | True Demand | Sales | Signals |
| --- | --- | --- | --- |
| 1 | 197 | 183.84 | shortage=13.16; dump_flags=1; default_flags=2 |
| 0 | 181 | 170.00 | shortage=11.00; default_flags=1 |
| 2 | 198 | 191.79 | shortage=6.21; dump_flags=1 |
| 3 | 202 | 199.02 | shortage=2.98; dump_flags=1 |
| 7 | 194 | 192.01 | shortage=1.99; dump_flags=1 |
| 4 | 193 | 191.10 | shortage=1.90; dump_flags=1 |
| 8 | 196 | 194.85 | shortage=1.15; dump_flags=1 |
| 5 | 182 | 180.97 | shortage=1.03; dump_flags=1 |

## Decision Trace Samples

| Round | Agent | Source | Forecast Base | Forecast Adj | Price Base | Price Adj | Qty Target | Risk Gate | Summary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Hyperscaler | llm-context | 184.00 | 0.00 | 4.60 | 0.00 | 80.00 | inventory target capped quantity | forecast 184.0 + 0.0; price 4.60 + 0.00; quantity target 80.0; risk gate inventory target capped quantity; final forecast=184, price=4.60, quantity=70 |
| 0 | PremiumCloud | llm-context | 184.00 | -4.00 | 6.80 | -0.40 | 40.00 | inventory target capped quantity | forecast 184.0 + -4.0; price 6.80 + -0.40; quantity target 40.0; risk gate inventory target capped quantity; final forecast=180, price=6.40, quantity=0 |
| 0 | SpotBroker | llm-context | 184.00 | -4.00 | 5.00 | -0.20 | 20.00 | none | forecast 184.0 + -4.0; price 5.00 + -0.20; quantity target 20.0; risk gate none; final forecast=180, price=4.80, quantity=20 |
| 1 | Hyperscaler | llm-context | 184.00 | 21.00 | 4.60 | 0.00 | 120.00 | none | forecast 184.0 + 21.0; price 4.60 + 0.00; quantity target 120.0; risk gate none; final forecast=205, price=4.60, quantity=120 |
| 1 | PremiumCloud | llm-context | 184.00 | 4.00 | 6.60 | 0.00 | 40.00 | sla_guard reduced quantity under SLA/reputation pressure | forecast 184.0 + 4.0; price 6.60 + 0.00; quantity target 40.0; risk gate sla_guard reduced quantity under SLA/reputation pressure; final forecast=188, price=6.60, quantity=40 |
| 1 | SpotBroker | llm-context | 184.00 | 11.00 | 5.00 | 0.20 | 30.00 | none | forecast 184.0 + 11.0; price 5.00 + 0.20; quantity target 30.0; risk gate none; final forecast=195, price=5.20, quantity=30 |
| 2 | Hyperscaler | llm-context | 198.00 | 12.00 | 4.60 | 0.00 | 120.00 | none | forecast 198.0 + 12.0; price 4.60 + 0.00; quantity target 120.0; risk gate none; final forecast=210, price=4.60, quantity=120 |
| 2 | PremiumCloud | llm-context | 193.00 | 3.00 | 7.00 | -0.40 | 50.00 | sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity | forecast 193.0 + 3.0; price 7.00 + -0.40; quantity target 50.0; risk gate sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity; final forecast=196, price=6.60, quantity=40 |
| 2 | SpotBroker | llm-context | 200.00 | 0.00 | 5.40 | 0.20 | 40.00 | none | forecast 200.0 + 0.0; price 5.40 + 0.20; quantity target 40.0; risk gate none; final forecast=200, price=5.60, quantity=40 |
| 3 | Hyperscaler | llm-context | 198.00 | 14.00 | 4.60 | 0.00 | 120.00 | none | forecast 198.0 + 14.0; price 4.60 + 0.00; quantity target 120.0; risk gate none; final forecast=212, price=4.60, quantity=120 |
| 3 | PremiumCloud | llm-context | 195.00 | 5.00 | 7.00 | -0.40 | 50.00 | sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity | forecast 195.0 + 5.0; price 7.00 + -0.40; quantity target 50.0; risk gate sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity; final forecast=200, price=6.60, quantity=40 |
| 3 | SpotBroker | llm-context | 200.00 | 5.00 | 5.40 | 0.40 | 40.00 | none | forecast 200.0 + 5.0; price 5.40 + 0.40; quantity target 40.0; risk gate none; final forecast=205, price=5.80, quantity=40 |

## Adaptive Strategy Trace Samples

| Round | Agent | Personality | Price Delta | Inventory Delta | Risk Delta | Price State | Inventory State | Risk State | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Conclusion Notes

- **Winner:** `PremiumCloud` ends with cumulative profit `1496.11`, the highest value in this run.
- **Service leader:** `Hyperscaler` posts the strongest average service rate at `100.00%`.
- **Pricing posture:** `PremiumCloud` maintains the highest average price at `6.58`.
- **Market fulfillment:** the run sells `2256.63` units against `2298.00` true demand for a fulfillment ratio of `98.20%`.
- **Operational stress:** peer transfers total `0.00` units, customer reallocation totals `126.15`, final SLA backlog is `0.16`, with `11` dump flags and `3` default flags.

## Appendix: Agent Configuration

| Agent | Forecast | Pricing | Allocation | Risk | Base Price | Max Quantity |
| --- | --- | --- | --- | --- | --- | --- |
| Hyperscaler | momentum_chaser | share_grabber | capacity_expander | growth_tolerant | 4.60 | 120 |
| PremiumCloud | signal_smoother | premium_keeper | buffered_allocator | sla_guard | 5.40 | 120 |
| SpotBroker | volatility_reader | spread_hunter | inventory_light | inventory_guard | 4.90 | 80 |
