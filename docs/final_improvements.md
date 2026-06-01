# Final Improvements Summary

This branch turns the project into a presentation-ready market simulation package.

## Mechanism additions

- Customer segmentation: training burst, enterprise SLA, and spot workload demand now use different price, reputation, brand, and SLA weights.
- Two-stage allocation: unmet demand from constrained providers can migrate to competitors with surplus capacity before transfer/default.
- SLA queue: enterprise-like unmet demand can roll into an agent-level backlog with late-unit penalties.
- Scenario profiles: `baseline`, `price_war`, `supply_shock`, `high_volatility`, `no_reputation`, and `no_transfer`.

## Presentation additions

- Dashboard executive summary now shows winner, fulfillment, market payoff, transfer, reallocation, and backlog/default pressure.
- Agent cards show segment demand mix, SLA queue state, decision trace, and LLM adaptive strategy state when available.
- Markdown report includes numbered findings tied to the active scenario.
- `presentation/final_presentation.md` and `presentation/demo_script.md` provide the final talk path.

## Recommended final commands

```bash
pj-ag4-run --scenario supply_shock --rounds 30 --output-dir outputs/final
pj-ag4-scenarios --rounds 30 --seeds 7 11 23 --output-root outputs/final/scenario_sweep
```

For an LLM-adaptive demo:

```bash
pj-ag4-run \
  --agent-mode llm-adaptive \
  --scenario supply_shock \
  --rounds 12 \
  --llm-api-key "$PJ_AG4_OPENAI_API_KEY" \
  --output-dir outputs/final_llm_adaptive
```
