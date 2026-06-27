# PJ-AG4 Simulation Report

## Run Parameters

| Seed | Scenario | Rounds | Agent Mode | Agents | Demand Window |
| --- | --- | --- | --- | --- | --- |
| 7 | high_volatility | 12 | llm-context | 3 | 5 |

## Market Summary

| Total Demand | Total Sales | Fulfillment | Average Market Price | Total Profit | Price Pressure Cost |
| --- | --- | --- | --- | --- | --- |
| 2279 | 2246.42 | 0.99 | 5.48 | 3324.45 | 0.00 |

## Agent Strategy Comparison

| Agent | Role | Final Cum Profit | Avg Profit | Avg Forecast Error | Avg Price | Total Sales | Avg Service Rate | Transfer In | Transfer Out | Price Pressure Cost | Dump Flags | Default Flags | Final Inventory | Final Reputation | Total Shortage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hyperscaler | hyperscaler | 1014.06 | 84.50 | 11.33 | 4.60 | 1293.79 | 1.00 | 0.00 | 9.94 | 0.00 | 9 | 0 | 12.37 | 0.72 | 0.00 |
| PremiumCloud | premium | 1465.50 | 122.12 | 8.17 | 6.37 | 488.57 | 0.94 | 0.00 | 0.00 | 0.00 | 0 | 2 | 0.00 | 0.92 | 30.43 |
| SpotBroker | spot | 844.89 | 70.41 | 5.08 | 5.47 | 464.06 | 0.99 | 9.94 | 0.00 | 0.00 | 0 | 0 | 0.00 | 0.89 | 2.15 |

## Round-Level Timeline

| Round | True Demand | Observed Demand | Sales | Avg Price | Profit | Shortage | Transfers | Reallocated | Backlog |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 179 | 184 | 179.00 | 5.20 | 504.93 | 0.00 | 0.00 | 25.64 | 0.00 |
| 1 | 200 | 197 | 189.35 | 5.33 | 262.67 | 10.65 | 0.00 | 29.78 | 5.69 |
| 2 | 195 | 193 | 190.36 | 5.33 | 198.40 | 4.64 | 3.63 | 12.92 | 2.20 |
| 3 | 211 | 215 | 208.80 | 5.47 | 324.44 | 2.20 | 0.00 | 17.09 | 1.33 |
| 4 | 202 | 204 | 199.40 | 5.53 | 269.07 | 2.60 | 0.00 | 19.20 | 1.52 |
| 5 | 184 | 186 | 184.00 | 5.47 | 167.09 | 0.00 | 2.95 | 10.62 | 0.00 |
| 6 | 155 | 164 | 155.00 | 5.47 | 263.74 | 0.00 | 3.36 | 12.01 | 0.00 |
| 7 | 193 | 198 | 193.00 | 5.53 | 291.15 | 0.00 | 0.00 | 11.61 | 0.00 |
| 8 | 186 | 169 | 179.22 | 5.53 | 285.88 | 6.78 | 0.00 | 17.29 | 3.33 |
| 9 | 191 | 186 | 187.67 | 5.60 | 230.22 | 3.33 | 0.00 | 6.76 | 1.57 |
| 10 | 197 | 197 | 195.43 | 5.67 | 316.66 | 1.57 | 0.00 | 8.11 | 0.81 |
| 11 | 186 | 180 | 185.19 | 5.60 | 210.21 | 0.81 | 0.00 | 8.58 | 0.41 |

## Findings

- **Finding 1: Reputation-weighted SLA posture can beat pure price cutting.** In scenario `high_volatility`, `PremiumCloud` ends first with cumulative profit `1465.50` and reputation `91.55%`.
- **Finding 2: Capacity pressure is now visible as customer migration and backlog.** Two-stage allocation reallocates `179.60` units and leaves final SLA backlog `0.41`.
- **Finding 3: Peer transfer is a stress valve, not the whole market.** Transfer volume totals `9.94` units while average forecast error is `8.19`, linking prediction quality to shortage/default risk.

## Key Events

| Round | True Demand | Sales | Signals |
| --- | --- | --- | --- |
| 1 | 200 | 189.35 | shortage=10.65; dump_flags=1; default_flags=1 |
| 2 | 195 | 190.36 | shortage=4.64; transfer=3.63; dump_flags=1 |
| 8 | 186 | 179.22 | shortage=6.78; default_flags=1 |
| 9 | 191 | 187.67 | shortage=3.33; dump_flags=1 |
| 5 | 184 | 184.00 | transfer=2.95; dump_flags=1 |
| 4 | 202 | 199.40 | shortage=2.60; dump_flags=1 |
| 3 | 211 | 208.80 | shortage=2.20; dump_flags=1 |
| 10 | 197 | 195.43 | shortage=1.57; dump_flags=1 |

## Decision Trace Samples

| Round | Agent | Source | Forecast Base | Forecast Adj | Price Base | Price Adj | Qty Target | Risk Gate | Summary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Hyperscaler | llm-context | 184.00 | 16.00 | 4.60 | 0.00 | 90.00 | inventory target capped quantity | forecast 184.0 + 16.0; price 4.60 + 0.00; quantity target 90.0; risk gate inventory target capped quantity; final forecast=200, price=4.60, quantity=80 |
| 0 | PremiumCloud | llm-context | 184.00 | -4.00 | 6.80 | -0.60 | 40.00 | inventory target capped quantity | forecast 184.0 + -4.0; price 6.80 + -0.60; quantity target 40.0; risk gate inventory target capped quantity; final forecast=180, price=6.20, quantity=10 |
| 0 | SpotBroker | llm-context | 184.00 | -4.00 | 5.00 | -0.20 | 20.00 | none | forecast 184.0 + -4.0; price 5.00 + -0.20; quantity target 20.0; risk gate none; final forecast=180, price=4.80, quantity=20 |
| 1 | Hyperscaler | llm-context | 184.00 | 26.00 | 4.60 | 0.00 | 110.00 | none | forecast 184.0 + 26.0; price 4.60 + 0.00; quantity target 110.0; risk gate none; final forecast=210, price=4.60, quantity=110 |
| 1 | PremiumCloud | llm-context | 184.00 | 6.00 | 6.80 | -0.40 | 40.00 | none | forecast 184.0 + 6.0; price 6.80 + -0.40; quantity target 40.0; risk gate none; final forecast=190, price=6.40, quantity=40 |
| 1 | SpotBroker | llm-context | 184.00 | 11.00 | 5.00 | 0.00 | 30.00 | none | forecast 184.0 + 11.0; price 5.00 + 0.00; quantity target 30.0; risk gate none; final forecast=195, price=5.00, quantity=30 |
| 2 | Hyperscaler | llm-context | 200.00 | 5.00 | 4.60 | 0.00 | 120.00 | none | forecast 200.0 + 5.0; price 4.60 + 0.00; quantity target 120.0; risk gate none; final forecast=205, price=4.60, quantity=120 |
| 2 | PremiumCloud | llm-context | 195.00 | -5.00 | 7.00 | -0.80 | 50.00 | sla_guard reduced quantity under SLA/reputation pressure | forecast 195.0 + -5.0; price 7.00 + -0.80; quantity target 50.0; risk gate sla_guard reduced quantity under SLA/reputation pressure; final forecast=190, price=6.20, quantity=50 |
| 2 | SpotBroker | llm-context | 203.00 | -8.00 | 5.40 | -0.20 | 40.00 | inventory_guard lifted price under volatility | forecast 203.0 + -8.0; price 5.40 + -0.20; quantity target 40.0; risk gate inventory_guard lifted price under volatility; final forecast=195, price=5.20, quantity=40 |
| 3 | Hyperscaler | llm-context | 195.00 | 25.00 | 4.60 | 0.00 | 110.00 | none | forecast 195.0 + 25.0; price 4.60 + 0.00; quantity target 110.0; risk gate none; final forecast=220, price=4.60, quantity=110 |
| 3 | PremiumCloud | llm-context | 193.00 | 7.00 | 7.00 | -0.60 | 60.00 | sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity | forecast 193.0 + 7.0; price 7.00 + -0.60; quantity target 60.0; risk gate sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity; final forecast=200, price=6.40, quantity=40 |
| 3 | SpotBroker | llm-context | 197.00 | 18.00 | 5.20 | 0.20 | 50.00 | none | forecast 197.0 + 18.0; price 5.20 + 0.20; quantity target 50.0; risk gate none; final forecast=215, price=5.40, quantity=50 |

## Adaptive Strategy Trace Samples

| Round | Agent | Personality | Price Delta | Inventory Delta | Risk Delta | Price State | Inventory State | Risk State | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Conclusion Notes

- **Winner:** `PremiumCloud` ends with cumulative profit `1465.50`, the highest value in this run.
- **Service leader:** `Hyperscaler` posts the strongest average service rate at `100.00%`.
- **Pricing posture:** `PremiumCloud` maintains the highest average price at `6.37`.
- **Market fulfillment:** the run sells `2246.42` units against `2279.00` true demand for a fulfillment ratio of `98.57%`.
- **Operational stress:** peer transfers total `9.94` units, customer reallocation totals `179.60`, final SLA backlog is `0.41`, with `9` dump flags and `2` default flags.

## Appendix: Agent Configuration

| Agent | Forecast | Pricing | Allocation | Risk | Base Price | Max Quantity |
| --- | --- | --- | --- | --- | --- | --- |
| Hyperscaler | momentum_chaser | share_grabber | capacity_expander | growth_tolerant | 4.60 | 120 |
| PremiumCloud | signal_smoother | premium_keeper | buffered_allocator | sla_guard | 5.40 | 120 |
| SpotBroker | volatility_reader | spread_hunter | inventory_light | inventory_guard | 4.90 | 80 |
