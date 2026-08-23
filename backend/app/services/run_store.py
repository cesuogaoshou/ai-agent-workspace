from copy import deepcopy
from datetime import datetime, timezone
from itertools import count
from pathlib import Path
import re
from typing import Any, Protocol

from sqlalchemy import JSON, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from backend.app.agent.events import PublicRunEvent


class RunStore(Protocol):
    def create_run(self, task: str) -> dict[str, Any]:
        ...

    def append_event(self, run_id: str, event: PublicRunEvent) -> None:
        ...

    def finish_run(
        self,
        run_id: str,
        status: str,
        final_answer: str | None,
        error: str | None,
    ) -> None:
        ...

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        ...

    def list_runs(self) -> list[dict[str, Any]]:
        ...

    def list_events(self, run_id: str) -> list[PublicRunEvent]:
        ...


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
        self._events[run_id].append(_snapshot_event(event))
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
        return [_snapshot_event(event) for event in self._events.get(run_id, [])]


def _snapshot_event(event: PublicRunEvent) -> PublicRunEvent:
    return PublicRunEvent(
        run_id=event.run_id,
        event_type=event.event_type,
        sequence=event.sequence,
        payload=deepcopy(event.payload),
        created_at=event.created_at,
    )


class Base(DeclarativeBase):
    pass


class AgentRunRecord(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    task: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    final_answer: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    finished_at: Mapped[str | None] = mapped_column(String, nullable=True)
    step_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tool_call_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class RunEventRecord(Base):
    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class SqlAlchemyRunStore:
    def __init__(self, database_url: str) -> None:
        _ensure_sqlite_parent_exists(database_url)
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self._engine = create_engine(database_url, connect_args=connect_args)
        self._session_factory = sessionmaker(self._engine, expire_on_commit=False)
        Base.metadata.create_all(self._engine)

    def create_run(self, task: str) -> dict[str, Any]:
        with self._session_factory() as session:
            run = AgentRunRecord(
                id=self._next_run_id(session),
                task=task,
                status="running",
                final_answer=None,
                error=None,
                created_at=datetime.now(timezone.utc).isoformat(),
                finished_at=None,
                step_count=0,
                tool_call_count=0,
            )
            session.add(run)
            session.commit()
            return _run_record_to_dict(run)

    def append_event(self, run_id: str, event: PublicRunEvent) -> None:
        with self._session_factory() as session:
            run = session.get(AgentRunRecord, run_id)
            if run is None:
                raise KeyError(f"Unknown run id: {run_id}")
            saved_event = _snapshot_event(event)
            session.add(
                RunEventRecord(
                    run_id=saved_event.run_id,
                    event_type=saved_event.event_type,
                    sequence=saved_event.sequence,
                    payload=saved_event.payload,
                    created_at=saved_event.created_at,
                )
            )
            if saved_event.event_type == "tool_call":
                run.tool_call_count += 1
            if saved_event.event_type in {"tool_call", "final_answer"}:
                run.step_count += 1
            session.commit()

    def finish_run(
        self,
        run_id: str,
        status: str,
        final_answer: str | None,
        error: str | None,
    ) -> None:
        with self._session_factory() as session:
            run = session.get(AgentRunRecord, run_id)
            if run is None:
                raise KeyError(f"Unknown run id: {run_id}")
            run.status = status
            run.final_answer = final_answer
            run.error = error
            run.finished_at = datetime.now(timezone.utc).isoformat()
            session.commit()

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._session_factory() as session:
            run = session.get(AgentRunRecord, run_id)
            return _run_record_to_dict(run) if run is not None else None

    def list_runs(self) -> list[dict[str, Any]]:
        with self._session_factory() as session:
            runs = session.scalars(select(AgentRunRecord).order_by(AgentRunRecord.id)).all()
            return [_run_record_to_dict(run) for run in runs]

    def list_events(self, run_id: str) -> list[PublicRunEvent]:
        with self._session_factory() as session:
            events = session.scalars(
                select(RunEventRecord)
                .where(RunEventRecord.run_id == run_id)
                .order_by(RunEventRecord.sequence)
            ).all()
            return [_event_record_to_public_event(event) for event in events]

    def _next_run_id(self, session: Session) -> str:
        saved_ids = session.scalars(select(AgentRunRecord.id)).all()
        max_number = 0
        for saved_id in saved_ids:
            match = re.fullmatch(r"run_(\d+)", saved_id)
            if match:
                max_number = max(max_number, int(match.group(1)))
        return f"run_{max_number + 1}"


def _run_record_to_dict(run: AgentRunRecord) -> dict[str, Any]:
    return {
        "id": run.id,
        "task": run.task,
        "status": run.status,
        "final_answer": run.final_answer,
        "error": run.error,
        "created_at": run.created_at,
        "finished_at": run.finished_at,
        "step_count": run.step_count,
        "tool_call_count": run.tool_call_count,
    }


def _event_record_to_public_event(event: RunEventRecord) -> PublicRunEvent:
    return PublicRunEvent(
        run_id=event.run_id,
        event_type=event.event_type,
        sequence=event.sequence,
        payload=deepcopy(event.payload),
        created_at=event.created_at,
    )


def _ensure_sqlite_parent_exists(database_url: str) -> None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix) or database_url == "sqlite:///:memory:":
        return
    path_text = database_url[len(prefix) :]
    if not path_text or path_text.startswith(":"):
        return
    Path(path_text).parent.mkdir(parents=True, exist_ok=True)
