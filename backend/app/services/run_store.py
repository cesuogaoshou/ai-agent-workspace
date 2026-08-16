from datetime import datetime, timezone
from itertools import count
from typing import Any

from backend.app.agent.events import PublicRunEvent


class InMemoryRunStore:
    def __init__(self) -> None:
        self._ids = count(1)
        self._runs: dict[str, dict[str, Any]] = {}
        self._events: dict[str, list[PublicRunEvent]] = {}

    def create_run(self, task: str) -> dict[str, Any]:
        run_id = f"run_{next(self._ids)}"
        now = datetime.now(timezone.utc).isoformat()
        run = {
            "id": run_id,
            "task": task,
            "status": "running",
            "final_answer": None,
            "error": None,
            "created_at": now,
            "finished_at": None,
            "step_count": 0,
            "tool_call_count": 0,
        }
        self._runs[run_id] = run
        self._events[run_id] = []
        return run.copy()

    def append_event(self, run_id: str, event: PublicRunEvent) -> None:
        self._events[run_id].append(event)
        if event.event_type == "tool_call":
            self._runs[run_id]["tool_call_count"] += 1
        if event.event_type in {"tool_call", "final_answer"}:
            self._runs[run_id]["step_count"] += 1

    def finish_run(
        self,
        run_id: str,
        status: str,
        final_answer: str | None,
        error: str | None,
    ) -> None:
        self._runs[run_id]["status"] = status
        self._runs[run_id]["final_answer"] = final_answer
        self._runs[run_id]["error"] = error
        self._runs[run_id]["finished_at"] = datetime.now(timezone.utc).isoformat()

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        run = self._runs.get(run_id)
        return run.copy() if run is not None else None

    def list_runs(self) -> list[dict[str, Any]]:
        return [run.copy() for run in self._runs.values()]

    def list_events(self, run_id: str) -> list[PublicRunEvent]:
        return list(self._events.get(run_id, []))
