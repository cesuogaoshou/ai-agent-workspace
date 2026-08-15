# Project Agent Instructions

## Read Order

Start each new session by reading these files:

1. `AGENTS.md`
2. `docs/PROJECT_INDEX.md`
3. `agent/HANDOFF.md`
4. `agent/TASK.md`

Read deeper documentation only when it is relevant to the current task.

## Working Mode

- Keep changes small, scoped, and verifiable.
- Prefer the existing project patterns once source code exists.
- Update human-facing documentation in `docs/` when project behavior, architecture, setup, or status changes.
- Update AI working documentation in `agent/` after meaningful work.
- Record durable decisions in `agent/DECISIONS.md`.
- Refresh `docs/PROJECT_INDEX.md`, `agent/TASK.md`, and `agent/HANDOFF.md` after completing a phase or sub-phase.

## Git

- This workspace may start without Git initialized.
- Do not overwrite or revert user changes unless explicitly requested.
- If Git is initialized later, keep `agent/` as AI working documentation and usually ignore it unless the user explicitly wants it versioned.

## Verification

- Run the minimum practical verification before claiming work is complete.
- Document verification commands and results in `agent/MEMORY.md`.
- If verification cannot be run, state why in the final response and in the handoff when relevant.

## Local Environment Notes

- Current project root: `D:\demo\ai-agent-workspace`
- Current initialization date: 2026-08-15
- No project stack has been selected yet.
