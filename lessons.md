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
