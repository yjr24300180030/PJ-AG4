# Lessons

## Anti-Regression Rules

### 2026-03-24
- Problem: Template-only control files were not specific enough to guide implementation.
- Root cause: the project had scenario design but no execution contract.
- Rule: every control file must name concrete artifacts, interfaces, or validation criteria.
- Verification: the doc stack now names CLI entrypoints, CSV columns, and implementation steps.

### 2026-03-24
- Problem: LLM integration can silently destabilize a working baseline when parsing or endpoint behavior changes.
- Root cause: agent outputs from external model endpoints are less structured than deterministic heuristic code.
- Rule: every LLM-backed policy path must keep a local fallback action and must not hardcode secrets into tracked files.
- Verification: `LLMPolicyAgent` falls back to heuristic behavior on parse or request failure, and the API key is passed via CLI or environment variable.

### 2026-03-24
- Problem: some OpenAI-compatible endpoints can return `finish_reason="length"` and cut the JSON object mid-stream.
- Root cause: the model exceeded the output token cap before finishing the structured response.
- Rule: the LLM adapter must treat `finish_reason="length"` as a retry signal and retry once with a more compact JSON-only prompt and a larger token cap.
- Verification: the LLM test suite now includes a mocked `finish_reason="length"` first response and succeeds on retry.

### 2026-03-24
- Problem: quant experiments drifted away from the main simulation path through monkey-patching and duplicated run loops.
- Root cause: the core runtime did not expose a stable public hook for strategy selection and observation assembly.
- Rule: research tooling must consume the shared simulation entrypoint and strategy registry instead of replacing internal builders or copying the per-round loop.
- Verification: `quant/run_benchmarks.py` and `quant/common.py` now call the shared simulation path, and smoke runs complete without monkey-patching.

### 2026-03-24
- Problem: a decision pipeline can look more sophisticated without actually having distinct behavioral styles at each stage.
- Root cause: if all stage outputs are effectively driven by one undifferentiated policy, the pipeline becomes structural only and loses explanatory value.
- Rule: when introducing staged agent pipelines, encode explicit stage-style profiles in configuration and let both heuristic logic and LLM prompting consume them.
- Verification: agent configs now carry forecaster, pricer, allocator, and risk styles, and styled simulation runs produce more distinct pricing and allocation behavior across agents.

### 2026-03-24
- Problem: agents kept provisioning against total market demand, which created chronic oversupply and inventory accumulation even when each agent only wins a fraction of the market.
- Root cause: the decision chain treated the demand forecast as a direct replenishment target instead of converting it into an expected captured share before sizing inventory.
- Rule: allocation and risk controls should size new quantity against expected captured demand share plus a style-specific service buffer, while preserving the existing market settlement logic.
- Verification: the recalibrated heuristic 10-round run in `outputs/heuristic_market_calibrated_10_v2` reduced terminal inventories to single-digit levels and lifted fill rate to 0.994 without changing the payoff or transfer equations.

### 2026-03-24
- Problem: the heuristic forecaster severely underpredicted round 0 because an empty history still passed through the weighted-history blend.
- Root cause: with no history, the implementation only retained the 30% current-observation branch, turning an observed demand around 180 into an initial forecast around 55.
- Rule: when no demand history exists, the first-round heuristic forecast should anchor directly to the current observed demand before style adjustments.
- Verification: `tests/test_agent_styles.py::test_first_round_heuristic_forecast_anchors_to_current_observation` now guards the initialization behavior.
