from typing import Any

from backend.app.agent.events import PublicRunEvent
from backend.app.llm.provider import LlmMessage
from backend.app.services.run_service import RunService
from backend.app.services.run_store import InMemoryRunStore
from backend.app.tools.calculator import CalculatorTool
from backend.app.tools.registry import ToolRegistry


class FinalAnswerProvider:
    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LlmMessage:
        return LlmMessage(role="assistant", content="done")


def test_run_store_saves_run_and_events() -> None:
    store = InMemoryRunStore()
    run = store.create_run(task="hello")
    event = PublicRunEvent(
        run_id=run["id"],
        event_type="status_change",
        sequence=1,
        payload={"status": "running"},
    )

    store.append_event(run["id"], event)
    store.finish_run(run["id"], status="success", final_answer="done", error=None)

    saved = store.get_run(run["id"])
    assert saved["task"] == "hello"
    assert saved["status"] == "success"
    assert saved["final_answer"] == "done"
    assert store.list_events(run["id"]) == [event]


def test_run_store_assigns_sequential_run_ids_and_lists_runs() -> None:
    store = InMemoryRunStore()

    first = store.create_run(task="first")
    second = store.create_run(task="second")

    assert first["id"] == "run_1"
    assert second["id"] == "run_2"
    assert store.list_runs() == [first, second]


def test_run_store_returns_copied_run_dicts() -> None:
    store = InMemoryRunStore()
    run = store.create_run(task="hello")

    run["task"] = "changed"
    store.get_run(run["id"])["status"] = "changed"
    store.list_runs()[0]["final_answer"] = "changed"

    saved = store.get_run(run["id"])
    assert saved["task"] == "hello"
    assert saved["status"] == "running"
    assert saved["final_answer"] is None


def test_run_store_returns_none_for_missing_run_and_no_events_for_missing_run() -> None:
    store = InMemoryRunStore()

    assert store.get_run("missing") is None
    assert store.list_events("missing") == []


def test_run_store_counts_tool_calls_and_steps() -> None:
    store = InMemoryRunStore()
    run = store.create_run(task="hello")

    store.append_event(
        run["id"],
        PublicRunEvent(
            run_id=run["id"],
            event_type="status_change",
            sequence=1,
            payload={"status": "running"},
        ),
    )
    store.append_event(
        run["id"],
        PublicRunEvent(
            run_id=run["id"],
            event_type="tool_call",
            sequence=2,
            payload={"tool_name": "calculator"},
        ),
    )
    store.append_event(
        run["id"],
        PublicRunEvent(
            run_id=run["id"],
            event_type="final_answer",
            sequence=3,
            payload={"final_answer": "done"},
        ),
    )

    saved = store.get_run(run["id"])
    assert saved["tool_call_count"] == 1
    assert saved["step_count"] == 2


def test_run_store_snapshots_event_payload_on_append() -> None:
    store = InMemoryRunStore()
    run = store.create_run(task="hello")
    event = PublicRunEvent(
        run_id=run["id"],
        event_type="status_change",
        sequence=1,
        payload={"status": "running"},
    )

    store.append_event(run["id"], event)
    event.payload["status"] = "mutated"

    saved_event = store.list_events(run["id"])[0]
    assert isinstance(saved_event, PublicRunEvent)
    assert saved_event.payload == {"status": "running"}


def test_run_store_returns_snapshot_event_payloads() -> None:
    store = InMemoryRunStore()
    run = store.create_run(task="hello")
    event = PublicRunEvent(
        run_id=run["id"],
        event_type="status_change",
        sequence=1,
        payload={"status": "running"},
    )

    store.append_event(run["id"], event)
    listed_event = store.list_events(run["id"])[0]
    listed_event.payload["status"] = "mutated"

    saved_event = store.list_events(run["id"])[0]
    assert isinstance(saved_event, PublicRunEvent)
    assert saved_event.payload == {"status": "running"}


def test_run_service_creates_completed_run_with_events() -> None:
    store = InMemoryRunStore()
    service = RunService(
        store=store,
        provider=FinalAnswerProvider(),
        registry=ToolRegistry([CalculatorTool()]),
        max_steps=4,
    )

    result = service.create_run("Say done.")

    assert result["status"] == "success"
    assert result["final_answer"] == "done"
    events = store.list_events(result["id"])
    assert [event.event_type for event in events] == ["status_change", "final_answer"]
