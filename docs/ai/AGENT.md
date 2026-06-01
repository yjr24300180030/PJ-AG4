# AGENT CONTEXT

## Project Rules

- Treat `docs/project_design.md` as the source of truth for the simulation scenario.
- Keep the baseline local, deterministic, and runnable on macOS without external credentials.
- Use the doc stack to drive implementation in small steps.
- Preserve existing user changes unless they directly conflict with the current task.
- Avoid introducing a web UI unless the user explicitly asks for one.

## Session Start Read Order
1. docs/ai/AGENT.md
2. progress.txt
3. lessons.md
4. docs/ai/PRD.md
5. docs/ai/APP_FLOW.md
6. docs/ai/TECH_STACK.md
7. docs/ai/FRONTEND_GUIDELINES.md
8. docs/ai/BACKEND_STRUCTURE.md
9. docs/ai/IMPLEMENTATION_PLAN.md

## Access Timing Rules
- Before coding any step: re-read the current step in `docs/ai/IMPLEMENTATION_PLAN.md`.
- Before UI work: read `docs/ai/FRONTEND_GUIDELINES.md` and `docs/ai/APP_FLOW.md` sections in scope.
- Before backend/API/auth work: read `docs/ai/BACKEND_STRUCTURE.md` and `docs/ai/PRD.md` acceptance criteria.
- Before dependency changes: read `docs/ai/TECH_STACK.md` policy.
- After each step: update progress.txt.
- After each fix/incident: update lessons.md with prevention rule.
- Keep changes narrowly scoped to the current implementation step.
