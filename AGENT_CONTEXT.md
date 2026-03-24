# AGENT CONTEXT

## Project Rules

- Treat `docs/project_design.md` as the source of truth for the simulation scenario.
- Keep the baseline local, deterministic, and runnable on macOS without external credentials.
- Use the doc stack to drive implementation in small steps.
- Preserve existing user changes unless they directly conflict with the current task.
- Avoid introducing a web UI unless the user explicitly asks for one.

## Session Start Read Order
1. AGENT_CONTEXT.md
2. progress.txt
3. lessons.md
4. PRD.md
5. APP_FLOW.md
6. TECH_STACK.md
7. FRONTEND_GUIDELINES.md
8. BACKEND_STRUCTURE.md
9. IMPLEMENTATION_PLAN.md

## Access Timing Rules
- Before coding any step: re-read current step in IMPLEMENTATION_PLAN.md.
- Before UI work: read FRONTEND_GUIDELINES.md and APP_FLOW.md sections in scope.
- Before backend/API/auth work: read BACKEND_STRUCTURE.md and PRD.md acceptance criteria.
- Before dependency changes: read TECH_STACK.md policy.
- After each step: update progress.txt.
- After each fix/incident: update lessons.md with prevention rule.
- Keep changes narrowly scoped to the current implementation step.
