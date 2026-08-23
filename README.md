# AI Agent Workspace

AI Agent Workspace is a visual, traceable, extensible single-Agent workspace. A user submits a task, the backend runs a Tool Calling Agent loop, public execution events are recorded, and the frontend shows the run, trace, tool calls, and final result.

The project is intentionally not a generic chatbot. The UI emphasizes task execution, tool calls, public trace events, state, and final answers.

## Current Status

- v0.1 Minimal Agent: complete.
- v0.2A Backend Execution Trace: complete.
- v0.2B Frontend Trace UI: complete.
- v0.3 Persistence: complete locally on `feature/v0.1-minimal-agent`.
- Web Search remains stubbed.
- LangGraph, approval flows, MCP, Docker, CI, auth, and SaaS scope remain deferred.

## Current Stack

Frontend:

- Vue 3
- TypeScript
- Vite
- Vitest

Backend:

- Python
- FastAPI
- Pydantic
- Uvicorn
- DeepSeek OpenAI-compatible provider
- SQLite + SQLAlchemy durable run store

## Repository Layout

```text
frontend/
  src/
    api/
    components/
    types/

backend/
  app/
    api/
    agent/
    llm/
    schemas/
    services/
    tools/
  tests/

workspace_files/
  sample.md
```

Local coordination docs live in `docs/` and `agent/`. They are intentionally ignored by Git in this workspace.

## Backend

Install dependencies into the local virtual environment:

```powershell
.venv\Scripts\pip.exe install -r backend\requirements.txt
```

Start the API server from the repo root:

```powershell
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Run history is stored in SQLite by default at `workspace_files/agent_runs.sqlite3`. Override it with `DATABASE_URL` when needed, for example `sqlite:///workspace_files/custom_runs.sqlite3`.

Useful backend endpoints:

- `POST /api/agent/runs`
- `GET /api/agent/runs`
- `GET /api/agent/runs/{run_id}`
- `GET /api/agent/runs/{run_id}/events`
- `GET /api/tools`

## Frontend

Install frontend dependencies:

```powershell
cd frontend
npm install
```

Start the Vite dev server:

```powershell
cd frontend
npm run dev
```

The frontend normally runs at `http://127.0.0.1:5173/` and proxies `/api` to `http://127.0.0.1:8000`.

Build and test:

```powershell
cd frontend
npm test
npm run build
```

## Verification

Frontend:

```powershell
cd frontend
npm test
npm run build
```

Backend:

```powershell
.venv\Scripts\python.exe -m pytest backend/tests -v --basetemp D:\demo\ai-agent-workspace\.tmp-pytest -p no:cacheprovider
.venv\Scripts\python.exe -m compileall backend
```

The explicit `--basetemp` and disabled cache are useful in restricted Windows sandbox sessions where the default user temp directory or `.pytest_cache` may be unreadable.

## Version Route

```text
v0.1 Minimal Agent
  -> Tool Calling / Tool Registry / Agent Loop / basic tools

v0.2 Agent Loop + Execution Trace
  -> backend run records, public events, SSE, frontend trace UI

v0.3 Persistence
  -> SQLite / SQLAlchemy / durable run history across backend restarts

v0.4 LangGraph
  -> explicit state graph after raw loop mechanics are understood

v0.5 Human-in-the-loop
  -> sensitive tool approval flow

v0.6 Memory / State
  -> short-term state and limited durable records

v0.7 Agent Evaluation
  -> fixed eval cases and metrics

v0.8 MCP
  -> migrate one or two tools to MCP for comparison

v1.0 Project Freeze
  -> complete portfolio-ready demo, tests, and packaging
```
