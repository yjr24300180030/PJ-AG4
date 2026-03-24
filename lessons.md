# Lessons

## Anti-Regression Rules

### 2026-03-24
- Problem: Template-only control files were not specific enough to guide implementation.
- Root cause: the project had scenario design but no execution contract.
- Rule: every control file must name concrete artifacts, interfaces, or validation criteria.
- Verification: the doc stack now names CLI entrypoints, CSV columns, and implementation steps.
