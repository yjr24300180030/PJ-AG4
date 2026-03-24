# TECH STACK

## Runtime and Framework Versions

- Python 3.12.x
- macOS / Darwin development environment
- Clang-compatible tooling only for any native extensions

## Dependencies (Pinned Versions)

- `numpy`
- `pandas`
- `matplotlib`
- `pydantic`
- `pytest`
- `rich`
- Optional later: `openai` for LLM-backed agent adapters

## External Services

- None required for the baseline simulation.
- Optional later: OpenAI API or another compatible LLM endpoint behind a local adapter interface.

## Tooling and Quality Gates

- `pytest` for unit tests.
- CLI smoke test for one full simulation run.
- CSV schema validation after each run.
- Plot generation check for the required figure artifact.

## Disallowed Dependencies

- Web frameworks for the baseline.
- GUI toolkits.
- External services required for the default run.
- Linux-only or Windows-only system APIs.
