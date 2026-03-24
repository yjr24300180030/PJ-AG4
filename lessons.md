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
