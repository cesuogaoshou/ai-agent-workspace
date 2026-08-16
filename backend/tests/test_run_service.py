from typing import Any

import pytest

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


class RaisingProvider:
    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LlmMessage:
        raise RuntimeError("provider failed")


class ToolCallThenFinalProvider:
    def __init__(self) -> None:
        self.calls = 0

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LlmMessage:
        self.calls += 1
        if self.calls == 1:
            return LlmMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "calculator",
                            "arguments": '{"expression":"2+2"}',
                        },
                    }
                ],
            )
        return LlmMessage(role="assistant", content="The result is 4.")


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
        registry=ToolRegistry([]),
        max_steps=4,
    )

    result = service.create_run("Say done.")

    assert result["status"] == "success"
    assert result["final_answer"] == "done"
    events = store.list_events(result["id"])
    assert [event.event_type for event in events] == ["status_change", "final_answer"]


def test_run_service_records_failed_run_when_agent_loop_raises() -> None:
    store = InMemoryRunStore()
    service = RunService(
        store=store,
        provider=RaisingProvider(),
        registry=ToolRegistry([]),
        max_steps=4,
    )

    with pytest.raises(RuntimeError, match="provider failed"):
        service.create_run("Raise.")

    saved = store.get_run("run_1")
    assert saved is not None
    assert saved["status"] == "failed"
    assert saved["final_answer"] is None
    assert saved["error"] == "provider failed"
    assert saved["finished_at"] is not None
    events = store.list_events("run_1")
    assert [event.event_type for event in events] == ["status_change", "status_change"]
    assert [event.sequence for event in events] == [1, 2]
    assert events[0].payload == {"status": "running"}
    assert events[1].payload == {"status": "failed", "error": "provider failed"}


def test_run_service_failed_status_event_uses_public_failure_error() -> None:
    store = InMemoryRunStore()
    service = RunService(
        store=store,
        provider=RaisingProvider(),
        registry=ToolRegistry([]),
        max_steps=4,
        public_failure_error="Public failure.",
    )

    with pytest.raises(RuntimeError, match="provider failed"):
        service.create_run("Raise.")

    saved = store.get_run("run_1")
    assert saved is not None
    assert saved["status"] == "failed"
    assert saved["error"] == "Public failure."
    events = store.list_events("run_1")
    assert [event.event_type for event in events] == ["status_change", "status_change"]
    assert events[1].sequence == 2
    assert events[1].payload == {"status": "failed", "error": "Public failure."}


def test_run_service_records_tool_call_events_and_serialized_steps() -> None:
    store = InMemoryRunStore()
    service = RunService(
        store=store,
        provider=ToolCallThenFinalProvider(),
        registry=ToolRegistry([CalculatorTool()]),
        max_steps=4,
    )

    result = service.create_run("What is 2+2?")

    assert result["status"] == "success"
    assert result["final_answer"] == "The result is 4."
    events = store.list_events(result["id"])
    assert [event.event_type for event in events] == [
        "status_change",
        "tool_call",
        "final_answer",
    ]
    assert [event.sequence for event in events] == [1, 2, 3]
    assert {event.run_id for event in events} == {result["id"]}
    assert events[0].payload == {"status": "running"}
    assert events[1].payload == {
        "step_number": 1,
        "tool_name": "calculator",
        "status": "success",
        "tool_input": {"expression": "2+2"},
        "tool_output": {"result": 4},
        "error": None,
    }
    assert events[2].payload == {
        "step_number": 2,
        "status": "success",
        "final_answer": "The result is 4.",
    }
    assert result["steps"] == [event.as_dict() for event in events]
