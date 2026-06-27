# LLM Context Engineered Rerun Report

## Setting

- Mode: `llm-context` with engineered rolling-context signals.
- Scenarios: `baseline`, `price_war`, `supply_shock`, `high_volatility`, `no_reputation`, `no_transfer`.
- Seed: `7`.
- Rounds: `12`.
- Model: `gemini-3-flash`.
- Endpoint: `http://127.0.0.1:8045/v1`.
- Output root: `outputs/llm_scenario_experiments/llm_context_engineered_seed7_r12`.

## Fallback Audit

| Mode | Rows | Decision fallback | Strategy fallback |
| --- | ---: | ---: | ---: |
| `llm-context-engineered` | 216 | 0 | 0 |

## Scenario Summary

| Scenario | Profit | Fulfillment | Forecast MAE | Transfer | Defaults | Final backlog |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `baseline` | 3430.21 | 96.92% | 5.11 | 6.15 | 6 | 0.82 |
| `price_war` | 2991.81 | 99.10% | 5.50 | 16.44 | 0 | 0.21 |
| `supply_shock` | 3736.26 | 93.09% | 8.31 | 27.30 | 11 | 6.55 |
| `high_volatility` | 3324.45 | 98.57% | 8.19 | 9.94 | 2 | 0.41 |
| `no_reputation` | 3365.86 | 99.74% | 5.67 | 3.32 | 1 | 0.23 |
| `no_transfer` | 3545.44 | 98.20% | 5.39 | 0.00 | 3 | 0.16 |

## Comparison With Previous `llm-context`

| Scenario | Profit delta | Fulfillment delta | Forecast MAE delta | Defaults delta | Final backlog delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| `baseline` | -84.54 | -2.45% | -1.47 | 5 | 0.78 |
| `price_war` | 143.91 | 1.17% | -0.47 | -1 | -0.46 |
| `supply_shock` | 273.11 | 0.27% | -0.61 | 0 | -1.26 |
| `high_volatility` | -79.50 | 0.51% | 0.89 | -3 | 0.41 |
| `no_reputation` | -45.99 | 2.16% | -0.81 | -4 | 0.14 |
| `no_transfer` | 23.01 | -0.63% | -0.94 | 1 | -0.09 |

## Files

- `outputs/llm_scenario_experiments/llm_context_engineered_seed7_r12_summary.csv`
- `outputs/llm_scenario_experiments/llm_context_engineered_seed7_r12_agent_summary.csv`
- `outputs/llm_scenario_experiments/llm_context_engineered_seed7_r12_comparison.csv`
