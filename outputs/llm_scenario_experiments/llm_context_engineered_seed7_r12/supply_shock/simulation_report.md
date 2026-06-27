# PJ-AG4 Simulation Report

## Run Parameters

| Seed | Scenario | Rounds | Agent Mode | Agents | Demand Window |
| --- | --- | --- | --- | --- | --- |
| 7 | supply_shock | 12 | llm-context | 3 | 5 |

## Market Summary

| Total Demand | Total Sales | Fulfillment | Average Market Price | Total Profit | Price Pressure Cost |
| --- | --- | --- | --- | --- | --- |
| 2532 | 2357.02 | 0.93 | 5.67 | 3736.26 | 0.00 |

## Agent Strategy Comparison

| Agent | Role | Final Cum Profit | Avg Profit | Avg Forecast Error | Avg Price | Total Sales | Avg Service Rate | Transfer In | Transfer Out | Price Pressure Cost | Dump Flags | Default Flags | Final Inventory | Final Reputation | Total Shortage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hyperscaler | hyperscaler | 991.20 | 82.60 | 10.83 | 4.60 | 1326.24 | 0.95 | 0.00 | 27.30 | 0.00 | 9 | 4 | 0.00 | 0.45 | 92.58 |
| PremiumCloud | premium | 1703.46 | 141.95 | 9.33 | 6.65 | 525.13 | 0.92 | 6.26 | 0.00 | 0.00 | 0 | 4 | 0.00 | 0.80 | 53.98 |
| SpotBroker | spot | 1041.60 | 86.80 | 4.75 | 5.75 | 505.65 | 0.94 | 21.04 | 0.00 | 0.00 | 0 | 3 | 0.79 | 0.78 | 28.43 |

## Round-Level Timeline

| Round | True Demand | Observed Demand | Sales | Avg Price | Profit | Shortage | Transfers | Reallocated | Backlog |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 181 | 184 | 180.00 | 5.27 | 544.19 | 1.00 | 12.92 | 20.88 | 0.64 |
| 1 | 196 | 194 | 189.36 | 5.47 | 242.80 | 6.64 | 6.30 | 18.44 | 3.14 |
| 2 | 196 | 195 | 186.86 | 5.53 | 245.51 | 9.14 | 5.02 | 16.53 | 4.35 |
| 3 | 203 | 205 | 195.65 | 5.60 | 270.06 | 7.35 | 1.38 | 6.57 | 3.12 |
| 4 | 196 | 197 | 194.93 | 5.67 | 252.19 | 1.07 | 0.80 | 0.89 | 0.31 |
| 5 | 184 | 185 | 183.69 | 5.67 | 262.16 | 0.31 | 0.88 | 1.32 | 0.09 |
| 6 | 169 | 173 | 162.24 | 5.60 | 214.71 | 6.76 | 0.00 | 6.02 | 2.25 |
| 7 | 194 | 196 | 192.80 | 5.67 | 330.61 | 1.20 | 0.00 | 0.00 | 0.33 |
| 8 | 253 | 244 | 220.99 | 5.80 | 334.34 | 32.01 | 0.00 | 2.64 | 12.44 |
| 9 | 256 | 254 | 217.56 | 5.87 | 341.07 | 38.44 | 0.00 | 4.25 | 11.53 |
| 10 | 257 | 257 | 208.47 | 5.93 | 309.52 | 48.53 | 0.00 | 0.00 | 14.63 |
| 11 | 247 | 244 | 224.47 | 5.93 | 389.09 | 22.53 | 0.00 | 8.61 | 6.55 |

## Findings

- **Finding 1: Reputation-weighted SLA posture can beat pure price cutting.** In scenario `supply_shock`, `PremiumCloud` ends first with cumulative profit `1703.46` and reputation `79.67%`.
- **Finding 2: Capacity pressure is now visible as customer migration and backlog.** Two-stage allocation reallocates `86.16` units and leaves final SLA backlog `6.55`.
- **Finding 3: Peer transfer is a stress valve, not the whole market.** Transfer volume totals `27.30` units while average forecast error is `8.31`, linking prediction quality to shortage/default risk.

## Key Events

| Round | True Demand | Sales | Signals |
| --- | --- | --- | --- |
| 10 | 257 | 208.47 | shock=60.00; shortage=48.53; dump_flags=1; default_flags=3 |
| 9 | 256 | 217.56 | shock=60.00; shortage=38.44; dump_flags=1; default_flags=2 |
| 8 | 253 | 220.99 | shock=60.00; shortage=32.01; dump_flags=1; default_flags=2 |
| 11 | 247 | 224.47 | shock=60.00; shortage=22.53; dump_flags=1; default_flags=1 |
| 2 | 196 | 186.86 | shortage=9.14; transfer=5.02; dump_flags=1; default_flags=2 |
| 1 | 196 | 189.36 | shortage=6.64; transfer=6.30; dump_flags=1 |
| 3 | 203 | 195.65 | shortage=7.35; transfer=1.38; dump_flags=1 |
| 6 | 169 | 162.24 | shortage=6.76; default_flags=1 |

## Decision Trace Samples

| Round | Agent | Source | Forecast Base | Forecast Adj | Price Base | Price Adj | Qty Target | Risk Gate | Summary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Hyperscaler | llm-context | 184.00 | 6.00 | 4.60 | 0.00 | 80.00 | inventory target capped quantity | forecast 184.0 + 6.0; price 4.60 + 0.00; quantity target 80.0; risk gate inventory target capped quantity; final forecast=190, price=4.60, quantity=80 |
| 0 | PremiumCloud | llm-context | 184.00 | -4.00 | 6.80 | -0.40 | 30.00 | inventory target capped quantity | forecast 184.0 + -4.0; price 6.80 + -0.40; quantity target 30.0; risk gate inventory target capped quantity; final forecast=180, price=6.40, quantity=0 |
| 0 | SpotBroker | llm-context | 184.00 | 0.00 | 5.00 | -0.20 | 20.00 | none | forecast 184.0 + 0.0; price 5.00 + -0.20; quantity target 20.0; risk gate none; final forecast=184, price=4.80, quantity=20 |
| 1 | Hyperscaler | llm-context | 184.00 | 20.00 | 4.60 | 0.00 | 120.00 | none | forecast 184.0 + 20.0; price 4.60 + 0.00; quantity target 120.0; risk gate none; final forecast=204, price=4.60, quantity=120 |
| 1 | PremiumCloud | llm-context | 184.00 | 6.00 | 6.80 | -0.20 | 50.00 | sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity | forecast 184.0 + 6.0; price 6.80 + -0.20; quantity target 50.0; risk gate sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity; final forecast=190, price=6.60, quantity=40 |
| 1 | SpotBroker | llm-context | 184.00 | 16.00 | 5.00 | 0.20 | 30.00 | none | forecast 184.0 + 16.0; price 5.00 + 0.20; quantity target 30.0; risk gate none; final forecast=200, price=5.20, quantity=30 |
| 2 | Hyperscaler | llm-context | 196.00 | 9.00 | 4.60 | 0.00 | 120.00 | none | forecast 196.0 + 9.0; price 4.60 + 0.00; quantity target 120.0; risk gate none; final forecast=205, price=4.60, quantity=120 |
| 2 | PremiumCloud | llm-context | 192.00 | 4.00 | 7.00 | -0.40 | 50.00 | sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity | forecast 192.0 + 4.0; price 7.00 + -0.40; quantity target 50.0; risk gate sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity; final forecast=196, price=6.60, quantity=40 |
| 2 | SpotBroker | llm-context | 198.00 | -2.00 | 5.00 | 0.40 | 30.00 | none | forecast 198.0 + -2.0; price 5.00 + 0.40; quantity target 30.0; risk gate none; final forecast=196, price=5.40, quantity=30 |
| 3 | Hyperscaler | llm-context | 196.00 | 19.00 | 4.60 | 0.00 | 120.00 | none | forecast 196.0 + 19.0; price 4.60 + 0.00; quantity target 120.0; risk gate none; final forecast=215, price=4.60, quantity=120 |
| 3 | PremiumCloud | llm-context | 194.00 | 6.00 | 7.00 | -0.40 | 50.00 | sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity | forecast 194.0 + 6.0; price 7.00 + -0.40; quantity target 50.0; risk gate sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity; final forecast=200, price=6.60, quantity=40 |
| 3 | SpotBroker | llm-context | 198.00 | 7.00 | 5.00 | 0.60 | 40.00 | none | forecast 198.0 + 7.0; price 5.00 + 0.60; quantity target 40.0; risk gate none; final forecast=205, price=5.60, quantity=40 |

## Adaptive Strategy Trace Samples

| Round | Agent | Personality | Price Delta | Inventory Delta | Risk Delta | Price State | Inventory State | Risk State | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Conclusion Notes

- **Winner:** `PremiumCloud` ends with cumulative profit `1703.46`, the highest value in this run.
- **Service leader:** `Hyperscaler` posts the strongest average service rate at `94.56%`.
- **Pricing posture:** `PremiumCloud` maintains the highest average price at `6.65`.
- **Market fulfillment:** the run sells `2357.02` units against `2532.00` true demand for a fulfillment ratio of `93.09%`.
- **Operational stress:** peer transfers total `27.30` units, customer reallocation totals `86.16`, final SLA backlog is `6.55`, with `9` dump flags and `11` default flags.

## Appendix: Agent Configuration

| Agent | Forecast | Pricing | Allocation | Risk | Base Price | Max Quantity |
| --- | --- | --- | --- | --- | --- | --- |
| Hyperscaler | momentum_chaser | share_grabber | capacity_expander | growth_tolerant | 4.60 | 120 |
| PremiumCloud | signal_smoother | premium_keeper | buffered_allocator | sla_guard | 5.40 | 120 |
| SpotBroker | volatility_reader | spread_hunter | inventory_light | inventory_guard | 4.90 | 80 |
