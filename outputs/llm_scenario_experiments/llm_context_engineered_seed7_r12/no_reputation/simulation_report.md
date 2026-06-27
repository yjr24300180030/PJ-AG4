# PJ-AG4 Simulation Report

## Run Parameters

| Seed | Scenario | Rounds | Agent Mode | Agents | Demand Window |
| --- | --- | --- | --- | --- | --- |
| 7 | no_reputation | 12 | llm-context | 3 | 5 |

## Market Summary

| Total Demand | Total Sales | Fulfillment | Average Market Price | Total Profit | Price Pressure Cost |
| --- | --- | --- | --- | --- | --- |
| 2298 | 2292.01 | 1.00 | 5.64 | 3365.86 | 0.00 |

## Agent Strategy Comparison

| Agent | Role | Final Cum Profit | Avg Profit | Avg Forecast Error | Avg Price | Total Sales | Avg Service Rate | Transfer In | Transfer Out | Price Pressure Cost | Dump Flags | Default Flags | Final Inventory | Final Reputation | Total Shortage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hyperscaler | hyperscaler | 1038.31 | 86.53 | 8.25 | 4.60 | 1375.94 | 1.00 | 0.00 | 3.32 | 0.00 | 10 | 0 | 6.85 | 0.00 | 0.00 |
| PremiumCloud | premium | 1320.31 | 110.03 | 6.00 | 6.75 | 380.56 | 0.99 | 2.22 | 0.00 | 0.00 | 0 | 1 | 3.40 | 0.00 | 5.30 |
| SpotBroker | spot | 1007.24 | 83.94 | 2.75 | 5.57 | 535.52 | 1.00 | 1.11 | 0.00 | 0.00 | 0 | 0 | 0.00 | 0.00 | 0.69 |

## Round-Level Timeline

| Round | True Demand | Observed Demand | Sales | Avg Price | Profit | Shortage | Transfers | Reallocated | Backlog |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 181 | 184 | 181.00 | 5.27 | 505.88 | 0.00 | 0.00 | 19.39 | 0.00 |
| 1 | 197 | 195 | 197.00 | 5.40 | 276.86 | 0.00 | 0.00 | 19.41 | 0.00 |
| 2 | 198 | 197 | 198.00 | 5.53 | 227.56 | 0.00 | 1.11 | 4.95 | 0.00 |
| 3 | 202 | 204 | 202.00 | 5.60 | 274.16 | 0.00 | 0.00 | 12.59 | 0.00 |
| 4 | 193 | 194 | 193.00 | 5.67 | 237.53 | 0.00 | 0.00 | 6.66 | 0.00 |
| 5 | 182 | 183 | 182.00 | 5.60 | 207.82 | 0.00 | 0.00 | 15.90 | 0.00 |
| 6 | 171 | 175 | 171.00 | 5.67 | 288.74 | 0.00 | 0.00 | 16.78 | 0.00 |
| 7 | 194 | 196 | 194.00 | 5.80 | 256.99 | 0.00 | 0.99 | 3.64 | 0.00 |
| 8 | 196 | 187 | 196.00 | 5.73 | 291.09 | 0.00 | 0.00 | 13.27 | 0.00 |
| 9 | 200 | 198 | 200.00 | 5.80 | 288.00 | 0.00 | 1.22 | 4.48 | 0.00 |
| 10 | 198 | 198 | 192.70 | 5.80 | 275.37 | 5.30 | 0.00 | 5.83 | 2.85 |
| 11 | 186 | 183 | 185.31 | 5.80 | 235.86 | 0.69 | 0.00 | 3.72 | 0.23 |

## Findings

- **Finding 1: Reputation-weighted SLA posture can beat pure price cutting.** In scenario `no_reputation`, `PremiumCloud` ends first with cumulative profit `1320.31` and reputation `0.00%`.
- **Finding 2: Capacity pressure is now visible as customer migration and backlog.** Two-stage allocation reallocates `126.62` units and leaves final SLA backlog `0.23`.
- **Finding 3: Peer transfer is a stress valve, not the whole market.** Transfer volume totals `3.32` units while average forecast error is `5.67`, linking prediction quality to shortage/default risk.

## Key Events

| Round | True Demand | Sales | Signals |
| --- | --- | --- | --- |
| 10 | 198 | 192.70 | shortage=5.30; dump_flags=1; default_flags=1 |
| 9 | 200 | 200.00 | transfer=1.22; dump_flags=1 |
| 2 | 198 | 198.00 | transfer=1.11; dump_flags=1 |
| 7 | 194 | 194.00 | transfer=0.99; dump_flags=1 |
| 11 | 186 | 185.31 | shortage=0.69; dump_flags=1 |
| 1 | 197 | 197.00 | dump_flags=1 |
| 3 | 202 | 202.00 | dump_flags=1 |
| 4 | 193 | 193.00 | dump_flags=1 |

## Decision Trace Samples

| Round | Agent | Source | Forecast Base | Forecast Adj | Price Base | Price Adj | Qty Target | Risk Gate | Summary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Hyperscaler | llm-context | 184.00 | 6.00 | 4.60 | 0.00 | 80.00 | none | forecast 184.0 + 6.0; price 4.60 + 0.00; quantity target 80.0; risk gate none; final forecast=190, price=4.60, quantity=80 |
| 0 | PremiumCloud | llm-context | 184.00 | -4.00 | 6.20 | 0.00 | 30.00 | sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity | forecast 184.0 + -4.0; price 6.20 + 0.00; quantity target 30.0; risk gate sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity; final forecast=180, price=6.20, quantity=0 |
| 0 | SpotBroker | llm-context | 184.00 | -4.00 | 5.00 | -0.20 | 30.00 | low reputation fallback lifted price | forecast 184.0 + -4.0; price 5.00 + -0.20; quantity target 30.0; risk gate low reputation fallback lifted price; final forecast=180, price=5.00, quantity=30 |
| 1 | Hyperscaler | llm-context | 184.00 | 21.00 | 4.60 | 0.00 | 110.00 | none | forecast 184.0 + 21.0; price 4.60 + 0.00; quantity target 110.0; risk gate none; final forecast=205, price=4.60, quantity=110 |
| 1 | PremiumCloud | llm-context | 184.00 | 6.00 | 6.20 | 0.00 | 40.00 | sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity | forecast 184.0 + 6.0; price 6.20 + 0.00; quantity target 40.0; risk gate sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity; final forecast=190, price=6.20, quantity=30 |
| 1 | SpotBroker | llm-context | 184.00 | 11.00 | 5.00 | 0.40 | 50.00 | none | forecast 184.0 + 11.0; price 5.00 + 0.40; quantity target 50.0; risk gate none; final forecast=195, price=5.40, quantity=50 |
| 2 | Hyperscaler | llm-context | 198.00 | 12.00 | 4.60 | 0.00 | 120.00 | none | forecast 198.0 + 12.0; price 4.60 + 0.00; quantity target 120.0; risk gate none; final forecast=210, price=4.60, quantity=120 |
| 2 | PremiumCloud | llm-context | 193.00 | 3.00 | 6.60 | -0.40 | 40.00 | sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity; low reputation fallback lifted price | forecast 193.0 + 3.0; price 6.60 + -0.40; quantity target 40.0; risk gate sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity; low reputation fallback lifted price; final forecast=196, price=6.60, quantity=40 |
| 2 | SpotBroker | llm-context | 200.00 | 0.00 | 5.40 | -0.20 | 50.00 | inventory_guard lifted price under volatility; low reputation fallback lifted price | forecast 200.0 + 0.0; price 5.40 + -0.20; quantity target 50.0; risk gate inventory_guard lifted price under volatility; low reputation fallback lifted price; final forecast=200, price=5.40, quantity=50 |
| 3 | Hyperscaler | llm-context | 198.00 | 17.00 | 4.60 | 0.00 | 120.00 | none | forecast 198.0 + 17.0; price 4.60 + 0.00; quantity target 120.0; risk gate none; final forecast=215, price=4.60, quantity=120 |
| 3 | PremiumCloud | llm-context | 195.00 | 5.00 | 6.60 | 0.00 | 40.00 | sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity | forecast 195.0 + 5.0; price 6.60 + 0.00; quantity target 40.0; risk gate sla_guard reduced quantity under SLA/reputation pressure; inventory target capped quantity; final forecast=200, price=6.60, quantity=30 |
| 3 | SpotBroker | llm-context | 200.00 | 8.00 | 5.40 | 0.20 | 50.00 | none | forecast 200.0 + 8.0; price 5.40 + 0.20; quantity target 50.0; risk gate none; final forecast=208, price=5.60, quantity=50 |

## Adaptive Strategy Trace Samples

| Round | Agent | Personality | Price Delta | Inventory Delta | Risk Delta | Price State | Inventory State | Risk State | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Conclusion Notes

- **Winner:** `PremiumCloud` ends with cumulative profit `1320.31`, the highest value in this run.
- **Service leader:** `Hyperscaler` posts the strongest average service rate at `100.00%`.
- **Pricing posture:** `PremiumCloud` maintains the highest average price at `6.75`.
- **Market fulfillment:** the run sells `2292.01` units against `2298.00` true demand for a fulfillment ratio of `99.74%`.
- **Operational stress:** peer transfers total `3.32` units, customer reallocation totals `126.62`, final SLA backlog is `0.23`, with `10` dump flags and `1` default flags.

## Appendix: Agent Configuration

| Agent | Forecast | Pricing | Allocation | Risk | Base Price | Max Quantity |
| --- | --- | --- | --- | --- | --- | --- |
| Hyperscaler | momentum_chaser | share_grabber | capacity_expander | growth_tolerant | 4.60 | 120 |
| PremiumCloud | signal_smoother | premium_keeper | buffered_allocator | sla_guard | 5.40 | 120 |
| SpotBroker | volatility_reader | spread_hunter | inventory_light | inventory_guard | 4.90 | 80 |
