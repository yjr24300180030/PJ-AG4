# PJ-AG4 Simulation Report

## Run Parameters

| Seed | Scenario | Rounds | Agent Mode | Agents | Demand Window |
| --- | --- | --- | --- | --- | --- |
| 7 | price_war | 12 | llm-context | 3 | 5 |

## Market Summary

| Total Demand | Total Sales | Fulfillment | Average Market Price | Total Profit | Price Pressure Cost |
| --- | --- | --- | --- | --- | --- |
| 2298 | 2277.24 | 0.99 | 5.57 | 2991.81 | 230.18 |

## Agent Strategy Comparison

| Agent | Role | Final Cum Profit | Avg Profit | Avg Forecast Error | Avg Price | Total Sales | Avg Service Rate | Transfer In | Transfer Out | Price Pressure Cost | Dump Flags | Default Flags | Final Inventory | Final Reputation | Total Shortage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hyperscaler | hyperscaler | 957.31 | 79.78 | 7.83 | 4.60 | 1397.52 | 0.99 | 0.00 | 0.00 | 155.26 | 10 | 0 | 0.00 | 0.57 | 17.36 |
| PremiumCloud | premium | 1149.00 | 95.75 | 6.00 | 6.55 | 339.76 | 1.00 | 0.00 | 16.44 | 6.86 | 0 | 0 | 4.87 | 0.82 | 0.00 |
| SpotBroker | spot | 885.50 | 73.79 | 2.67 | 5.55 | 539.95 | 0.99 | 16.44 | 0.00 | 68.06 | 0 | 0 | 0.00 | 0.85 | 3.41 |

## Round-Level Timeline

| Round | True Demand | Observed Demand | Sales | Avg Price | Profit | Shortage | Transfers | Reallocated | Backlog |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 181 | 184 | 180.00 | 5.20 | 510.94 | 1.00 | 13.78 | 22.96 | 0.16 |
| 1 | 197 | 195 | 196.75 | 5.33 | 191.30 | 0.25 | 2.66 | 18.05 | 0.04 |
| 2 | 198 | 197 | 197.46 | 5.53 | 215.64 | 0.54 | 0.00 | 3.69 | 0.09 |
| 3 | 202 | 204 | 199.77 | 5.60 | 239.16 | 2.23 | 0.00 | 3.73 | 0.24 |
| 4 | 193 | 194 | 188.36 | 5.67 | 222.63 | 4.64 | 0.00 | 3.32 | 0.46 |
| 5 | 182 | 183 | 181.34 | 5.60 | 177.88 | 0.66 | 0.00 | 4.87 | 0.15 |
| 6 | 171 | 175 | 170.85 | 5.60 | 273.42 | 0.15 | 0.00 | 8.12 | 0.03 |
| 7 | 194 | 196 | 192.10 | 5.67 | 205.33 | 1.90 | 0.00 | 6.75 | 0.20 |
| 8 | 196 | 187 | 195.80 | 5.60 | 264.27 | 0.20 | 0.00 | 7.35 | 0.02 |
| 9 | 200 | 198 | 197.38 | 5.67 | 236.50 | 2.62 | 0.00 | 9.27 | 0.27 |
| 10 | 198 | 198 | 193.37 | 5.67 | 254.60 | 4.63 | 0.00 | 6.65 | 0.54 |
| 11 | 186 | 183 | 184.05 | 5.67 | 200.14 | 1.95 | 0.00 | 0.75 | 0.21 |

## Findings

- **Finding 1: Reputation-weighted SLA posture can beat pure price cutting.** In scenario `price_war`, `PremiumCloud` ends first with cumulative profit `1149.00` and reputation `82.06%`.
- **Finding 2: Capacity pressure is now visible as customer migration and backlog.** Two-stage allocation reallocates `95.51` units and leaves final SLA backlog `0.21`.
- **Finding 3: Peer transfer is a stress valve, not the whole market.** Transfer volume totals `16.44` units while average forecast error is `5.50`, linking prediction quality to shortage/default risk.

## Key Events

| Round | True Demand | Sales | Signals |
| --- | --- | --- | --- |
| 0 | 181 | 180.00 | shortage=1.00; transfer=13.78 |
| 4 | 193 | 188.36 | shortage=4.64; dump_flags=1 |
| 10 | 198 | 193.37 | shortage=4.63; dump_flags=1 |
| 1 | 197 | 196.75 | shortage=0.25; transfer=2.66; dump_flags=1 |
| 9 | 200 | 197.38 | shortage=2.62; dump_flags=1 |
| 3 | 202 | 199.77 | shortage=2.23; dump_flags=1 |
| 11 | 186 | 184.05 | shortage=1.95; dump_flags=1 |
| 7 | 194 | 192.10 | shortage=1.90; dump_flags=1 |

## Decision Trace Samples

| Round | Agent | Source | Forecast Base | Forecast Adj | Price Base | Price Adj | Qty Target | Risk Gate | Summary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Hyperscaler | llm-context | 184.00 | 0.00 | 4.60 | 0.00 | 80.00 | inventory target capped quantity | forecast 184.0 + 0.0; price 4.60 + 0.00; quantity target 80.0; risk gate inventory target capped quantity; final forecast=184, price=4.60, quantity=70 |
| 0 | PremiumCloud | llm-context | 184.00 | -4.00 | 6.80 | -0.60 | 30.00 | inventory target capped quantity | forecast 184.0 + -4.0; price 6.80 + -0.60; quantity target 30.0; risk gate inventory target capped quantity; final forecast=180, price=6.20, quantity=10 |
| 0 | SpotBroker | llm-context | 184.00 | 0.00 | 5.00 | -0.20 | 20.00 | none | forecast 184.0 + 0.0; price 5.00 + -0.20; quantity target 20.0; risk gate none; final forecast=184, price=4.80, quantity=20 |
| 1 | Hyperscaler | llm-context | 184.00 | 21.00 | 4.60 | 0.00 | 120.00 | none | forecast 184.0 + 21.0; price 4.60 + 0.00; quantity target 120.0; risk gate none; final forecast=205, price=4.60, quantity=120 |
| 1 | PremiumCloud | llm-context | 184.00 | 6.00 | 6.80 | -0.40 | 30.00 | none | forecast 184.0 + 6.0; price 6.80 + -0.40; quantity target 30.0; risk gate none; final forecast=190, price=6.40, quantity=30 |
| 1 | SpotBroker | llm-context | 184.00 | 11.00 | 5.00 | 0.00 | 50.00 | none | forecast 184.0 + 11.0; price 5.00 + 0.00; quantity target 50.0; risk gate none; final forecast=195, price=5.00, quantity=50 |
| 2 | Hyperscaler | llm-context | 198.00 | 12.00 | 4.60 | 0.00 | 120.00 | inventory target capped quantity | forecast 198.0 + 12.0; price 4.60 + 0.00; quantity target 120.0; risk gate inventory target capped quantity; final forecast=210, price=4.60, quantity=120 |
| 2 | PremiumCloud | llm-context | 193.00 | 3.00 | 7.00 | -0.40 | 30.00 | none | forecast 193.0 + 3.0; price 7.00 + -0.40; quantity target 30.0; risk gate none; final forecast=196, price=6.60, quantity=30 |
| 2 | SpotBroker | llm-context | 200.00 | 0.00 | 5.20 | 0.20 | 50.00 | none | forecast 200.0 + 0.0; price 5.20 + 0.20; quantity target 50.0; risk gate none; final forecast=200, price=5.40, quantity=50 |
| 3 | Hyperscaler | llm-context | 198.00 | 14.00 | 4.60 | 0.00 | 120.00 | inventory target capped quantity | forecast 198.0 + 14.0; price 4.60 + 0.00; quantity target 120.0; risk gate inventory target capped quantity; final forecast=212, price=4.60, quantity=120 |
| 3 | PremiumCloud | llm-context | 195.00 | 5.00 | 7.00 | -0.40 | 30.00 | none | forecast 195.0 + 5.0; price 7.00 + -0.40; quantity target 30.0; risk gate none; final forecast=200, price=6.60, quantity=30 |
| 3 | SpotBroker | llm-context | 200.00 | 4.00 | 5.40 | 0.20 | 50.00 | none | forecast 200.0 + 4.0; price 5.40 + 0.20; quantity target 50.0; risk gate none; final forecast=204, price=5.60, quantity=50 |

## Adaptive Strategy Trace Samples

| Round | Agent | Personality | Price Delta | Inventory Delta | Risk Delta | Price State | Inventory State | Risk State | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Conclusion Notes

- **Winner:** `PremiumCloud` ends with cumulative profit `1149.00`, the highest value in this run.
- **Service leader:** `PremiumCloud` posts the strongest average service rate at `100.00%`.
- **Pricing posture:** `PremiumCloud` maintains the highest average price at `6.55`.
- **Market fulfillment:** the run sells `2277.24` units against `2298.00` true demand for a fulfillment ratio of `99.10%`.
- **Operational stress:** peer transfers total `16.44` units, customer reallocation totals `95.51`, final SLA backlog is `0.21`, with `10` dump flags and `0` default flags.

## Appendix: Agent Configuration

| Agent | Forecast | Pricing | Allocation | Risk | Base Price | Max Quantity |
| --- | --- | --- | --- | --- | --- | --- |
| Hyperscaler | momentum_chaser | share_grabber | capacity_expander | growth_tolerant | 4.60 | 120 |
| PremiumCloud | signal_smoother | premium_keeper | buffered_allocator | sla_guard | 5.40 | 120 |
| SpotBroker | volatility_reader | spread_hunter | inventory_light | inventory_guard | 4.90 | 80 |
