from typing import Any

import pytest

from backend.app.llm.provider import LlmMessage
from backend.app.services.run_service import RunService
from backend.app.services.run_store import InMemoryRunStore
from backend.app.tools.base import ToolResult
from backend.app.tools.registry import ToolRegistry


class SensitiveEchoTool:
    name = "sensitive_echo"
    description = "Echo input after approval."
    requires_approval = True
    parameters = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
    }

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(ok=True, output={"echo": arguments["value"]})


class ApprovalProvider:
    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LlmMessage:
        if any(message.get("role") == "tool" for message in messages):
            return LlmMessage(role="assistant", content="approved done")
        return LlmMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "sensitive_echo",
                        "arguments": '{"value":"hello"}',
                    },
                }
            ],
        )


def build_service(store: InMemoryRunStore) -> RunService:
    return RunService(
        store=store,
        provider=ApprovalProvider(),
        registry=ToolRegistry([SensitiveEchoTool()]),
        max_steps=4,
    )


def test_run_service_persists_waiting_for_approval_run() -> None:
    store = InMemoryRunStore()
    service = build_service(store)

    result = service.create_run("Use a sensitive tool.")

    assert result["status"] == "waiting_for_approval"
    assert result["finished_at"] is None
    assert result["pending_approval"]["approval_id"] == "approval_1"
    assert result["resume_state"] is not None
    events = store.list_events(result["id"])
    assert [event.event_type for event in events] == [
        "status_change",
        "approval_required",
        "status_change",
    ]
    assert events[1].payload["tool_name"] == "sensitive_echo"


def test_run_service_approve_resumes_waiting_run() -> None:
    store = InMemoryRunStore()
    service = build_service(store)
    waiting = service.create_run("Use a sensitive tool.")

    result = service.approve_run(waiting["id"], approval_id="approval_1")

    assert result["status"] == "success"
    assert result["final_answer"] == "approved done"
    assert result["pending_approval"] is None
    assert result["resume_state"] is None
    events = store.list_events(result["id"])
    assert [event.event_type for event in events] == [
        "status_change",
        "approval_required",
        "status_change",
        "approval_decision",
        "status_change",
        "tool_call",
        "final_answer",
    ]
    assert events[3].payload == {"approval_id": "approval_1", "decision": "approved"}


def test_run_service_reject_terminates_waiting_run() -> None:
    store = InMemoryRunStore()
    service = build_service(store)
    waiting = service.create_run("Use a sensitive tool.")

    result = service.reject_run(waiting["id"], approval_id="approval_1", reason="Too risky.")

    assert result["status"] == "rejected"
    assert result["error"] == "Too risky."
    assert result["finished_at"] is not None
    assert result["pending_approval"] is None
    events = store.list_events(result["id"])
    assert events[-2].payload == {
        "approval_id": "approval_1",
        "decision": "rejected",
        "reason": "Too risky.",
    }
    assert events[-1].payload == {"status": "rejected", "error": "Too risky."}


def test_run_service_rejects_mismatched_approval_id() -> None:
    store = InMemoryRunStore()
    service = build_service(store)
    waiting = service.create_run("Use a sensitive tool.")

    with pytest.raises(ValueError, match="Approval id does not match pending approval."):
        service.approve_run(waiting["id"], approval_id="wrong")
