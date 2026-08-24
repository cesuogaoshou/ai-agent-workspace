# Project Agent Instructions

## Read Order

Start each new session by reading these files:

1. `AGENTS.md`
2. `docs/PROJECT_INDEX.md`
3. `agent/HANDOFF.md`
4. `agent/TASK.md`

Read deeper documentation only when it is relevant to the current task.

## Project Context

- Project name: AI Agent Workspace.
- Goal: build a visual, traceable, extensible single-Agent workspace.
- Current implementation phase: v0.6 Memory / State complete and pushed.
- Recommended next implementation target: pause before v0.7 unless explicitly requested.
- Preferred stack direction: Vue 3 + TypeScript frontend, FastAPI + Python backend, SQLite + SQLAlchemy persistence.
- `docs/` and `agent/` are local documentation directories by current user request and are ignored by Git.

## Working Mode

- Keep changes small, scoped, and verifiable.
- Prefer the existing project patterns once source code exists.
- Update human-facing documentation in `docs/` when project behavior, architecture, setup, or status changes.
- Update AI working documentation in `agent/` after meaningful work.
- Record durable decisions in `agent/DECISIONS.md`.
- Refresh `docs/PROJECT_INDEX.md`, `agent/TASK.md`, and `agent/HANDOFF.md` after completing a phase or sub-phase.
- Do not expand the project into Multi-Agent, SaaS, auth, payment, Kubernetes, Redis/Celery, Browser Agent, or complex Vector Memory unless the user explicitly reopens that scope.
- First understand and implement the raw Tool Calling and Agent Loop mechanics before introducing LangGraph.
- Keep private Chain-of-Thought out of frontend traces; expose only public execution events, tool calls, tool results, status changes, and final answers.

## Git

- Repository: `https://github.com/cesuogaoshou/ai-agent-workspace.git`.
- Branch: `feature/v0.1-minimal-agent`.
- Do not overwrite or revert user changes unless explicitly requested.
- Keep `agent/` as AI working documentation and ignored by Git unless the user explicitly wants it versioned.
- Keep `docs/` ignored by Git per current user request. Local docs still matter for project coordination.
- v0.6 has been pushed on `feature/v0.1-minimal-agent`; use `git log -1` for the latest exact commit.

## Verification

- Run the minimum practical verification before claiming work is complete.
- Document verification commands and results in `agent/MEMORY.md`.
- If verification cannot be run, state why in the final response and in the handoff when relevant.
- For documentation-only work, verify by reading edited Markdown and checking for stale placeholders.
- For future implementation work, add concrete lint, test, build, and manual QA commands as soon as the stack is scaffolded.
- Current backend verification commands:
  - `.venv\Scripts\python.exe -m pytest backend/tests -v`
  - `.venv\Scripts\python.exe -m compileall backend`
- Latest v0.5 full verification: backend pytest `90 passed, 1 skipped`; compileall exit 0; frontend tests `13 passed`; frontend build exit 0.
- Latest v0.6 full verification: backend pytest `93 passed, 1 skipped`; compileall exit 0; frontend tests `13 passed`; frontend build exit 0.

## Local Environment Notes

- Current project root: `D:\demo\ai-agent-workspace`
- Current initialization date: 2026-08-15
- Project direction was defined from `F:\下载\AI_Agent_Workspace_开发方案.md`.
