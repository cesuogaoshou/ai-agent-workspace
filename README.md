# AI Agent Workspace

AI Agent Workspace is a visual, traceable, extensible single-Agent workspace. A user submits a task, the backend runs a Tool Calling Agent loop, public execution events are recorded, and the frontend shows the run, trace, tool calls, and final result.

The project is intentionally not a generic chatbot. The UI emphasizes task execution, tool calls, public trace events, state, and final answers.

## Current Status

- v0.1 Minimal Agent: complete.
- v0.2A Backend Execution Trace: complete.
- v0.2B Frontend Trace UI: complete.
- v0.3 Persistence: complete and pushed on `feature/v0.1-minimal-agent`.
- v0.4 LangGraph: complete and pushed.
- v0.5 Human-in-the-loop: complete and pushed.
- v0.6 Memory / State: complete and pushed on `feature/v0.1-minimal-agent`.
- v0.7 Agent Evaluation: complete and pushed.
- v0.8 MCP: complete and pushed; adds one optional MCP-backed Calculator path for comparison.
- v1.0 Project Freeze: complete; setup, verification, demo materials, and scope closure are finalized.
- Web Search remains stubbed.
- Docker, CI, auth, SaaS, multi-agent, real Web Search, RAG, and complex Vector Memory scope remain deferred.

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
- MCP Python SDK for the optional MCP-backed Calculator tool path

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
  evaluation/
  tests/

workspace_files/
  sample.md
```

Local coordination docs live in `docs/` and `agent/`. They are intentionally ignored by Git in this workspace.

## Prerequisites

- Windows PowerShell.
- Python virtual environment at `.venv\`.
- Node.js and npm for the Vue frontend.
- DeepSeek-compatible API credentials in `.env` for live LLM runs.

Do not commit `.env` or print its contents.

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

Calculator uses the local Python tool by default. Set `CALCULATOR_TOOL_MODE=mcp` to route calculator calls through the local MCP-backed Calculator adapter for comparison.

Start the backend with the optional MCP-backed Calculator mode:

```powershell
$env:CALCULATOR_TOOL_MODE='mcp'
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

The default Calculator mode remains `local`.

### Function Tool vs MCP Tool

The local Function Tool path is the default because it is simple, fast, and runs in-process. It is the right fit for built-in deterministic tools such as Calculator.

The MCP-backed Calculator path proves the extension point for tools that may later live outside the backend process or be shared across clients. It adds stdio subprocess overhead and transport failure modes, so v0.8 keeps it opt-in and limited to Calculator instead of migrating every tool.

Useful backend endpoints:

- `POST /api/agent/runs`
- `GET /api/agent/runs`
- `GET /api/agent/runs/{run_id}`
- `GET /api/agent/runs/{run_id}/events`
- `POST /api/agent/runs/{run_id}/approve`
- `POST /api/agent/runs/{run_id}/reject`
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

Latest v1.0 freeze verification:

- `.venv\Scripts\python.exe -m pytest backend/tests -v --basetemp D:\demo\ai-agent-workspace\.tmp-pytest -p no:cacheprovider`: `119 passed, 1 skipped`.
- `.venv\Scripts\python.exe -m compileall backend`: exit 0.
- `.venv\Scripts\python.exe -m pip check`: no broken requirements.
- `.venv\Scripts\python.exe -m backend.evaluation.run`: exit 0 with `metadata.tool_modes.calculator` set to `local`.
- `npm.cmd test -- --run` in `frontend/`: `2 passed` test files, `13 passed` tests.
- `npm.cmd run build` in `frontend/`: exit 0.

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

Run the deterministic v0.7 evaluation harness:

```powershell
.venv\Scripts\python.exe -m backend.evaluation.run
```

## Demo Walkthrough

Use the final demo to show the existing single-Agent workspace rather than new v1.0 product scope:

1. Calculator tool call: start backend and frontend, submit a calculator task, then confirm the trace shows agent decision, tool call, tool result, status change, and final answer.
2. Approval: submit a task that triggers a tool marked `requires_approval=True`, approve it, then confirm approval and final result events appear in the trace.
3. Persistence: complete a run, restart the backend, reopen the frontend, then confirm previous runs remain visible.
4. Evaluation: run `.venv\Scripts\python.exe -m backend.evaluation.run` and confirm deterministic metrics plus `metadata.tool_modes.calculator`.

Local `docs/DEMO.md` contains the capture checklist used for this workspace.

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
  -> one MCP-backed Calculator path for comparison with the local Function Tool

v1.0 Project Freeze
  -> complete portfolio-ready demo, tests, and packaging
```
