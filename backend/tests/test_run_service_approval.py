from typing import Any
from concurrent.futures import ThreadPoolExecutor

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

    def __init__(self) -> None:
        self.executions: list[dict[str, Any]] = []

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        self.executions.append(arguments)
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


class TwoRoundApprovalProvider:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LlmMessage:
        self.calls += 1
        return LlmMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": f"call_{self.calls}",
                    "type": "function",
                    "function": {
                        "name": "sensitive_echo",
                        "arguments": f'{{"value":"round-{self.calls}"}}',
                    },
                }
            ],
        )


class FailingAfterToolProvider:
    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LlmMessage:
        if any(message.get("role") == "tool" for message in messages):
            raise RuntimeError("provider failed after approval")
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


class EndlessSensitiveProvider:
    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LlmMessage:
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


def build_service(
    store: InMemoryRunStore,
    provider: Any | None = None,
    tool: SensitiveEchoTool | None = None,
    max_steps: int = 4,
    public_failure_error: str | None = None,
) -> RunService:
    return RunService(
        store=store,
        provider=provider or ApprovalProvider(),
        registry=ToolRegistry([tool or SensitiveEchoTool()]),
        max_steps=max_steps,
        public_failure_error=public_failure_error,
    )


def test_run_service_persists_waiting_for_approval_run() -> None:
    store = InMemoryRunStore()
    service = build_service(store)

    result = service.create_run("Use a sensitive tool.")

    assert result["status"] == "waiting_for_approval"
    assert result["finished_at"] is None
    assert result["pending_approval"]["approval_id"] == "approval_1_call_1"
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

    result = service.approve_run(waiting["id"], approval_id="approval_1_call_1")

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
    assert events[3].payload == {"approval_id": "approval_1_call_1", "decision": "approved"}


def test_run_service_reject_terminates_waiting_run() -> None:
    store = InMemoryRunStore()
    service = build_service(store)
    waiting = service.create_run("Use a sensitive tool.")

    result = service.reject_run(waiting["id"], approval_id="approval_1_call_1", reason="Too risky.")

    assert result["status"] == "rejected"
    assert result["error"] == "Too risky."
    assert result["finished_at"] is not None
    assert result["pending_approval"] is None
    events = store.list_events(result["id"])
    assert events[-2].payload == {
        "approval_id": "approval_1_call_1",
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


def test_run_service_preserves_next_pending_approval_after_resume() -> None:
    store = InMemoryRunStore()
    service = build_service(store, provider=TwoRoundApprovalProvider())
    waiting = service.create_run("Use two sensitive tools.")

    result = service.approve_run(waiting["id"], approval_id="approval_1_call_1")

    assert result["status"] == "waiting_for_approval"
    assert result["finished_at"] is None
    assert result["pending_approval"]["approval_id"] == "approval_2_call_2"
    assert result["resume_state"] is not None
    assert [event.event_type for event in store.list_events(result["id"])] == [
        "status_change",
        "approval_required",
        "status_change",
        "approval_decision",
        "status_change",
        "tool_call",
        "approval_required",
        "status_change",
    ]


def test_run_service_records_failed_run_when_approval_resume_raises() -> None:
    store = InMemoryRunStore()
    service = build_service(
        store,
        provider=FailingAfterToolProvider(),
        public_failure_error="Public failure.",
    )
    waiting = service.create_run("Use a sensitive tool.")

    with pytest.raises(RuntimeError, match="provider failed after approval"):
        service.approve_run(waiting["id"], approval_id="approval_1_call_1")

    saved = store.get_run(waiting["id"])
    assert saved is not None
    assert saved["status"] == "failed"
    assert saved["error"] == "Public failure."
    assert saved["pending_approval"] is None
    events = store.list_events(waiting["id"])
    assert events[-1].payload == {"status": "failed", "error": "Public failure."}


def test_run_service_allows_only_one_concurrent_approval_to_execute() -> None:
    store = InMemoryRunStore()
    tool = SensitiveEchoTool()
    service = build_service(store, tool=tool)
    waiting = service.create_run("Use a sensitive tool.")

    def approve_once() -> str:
        try:
            result = service.approve_run(waiting["id"], approval_id="approval_1_call_1")
            return str(result["status"])
        except ValueError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: approve_once(), range(2)))

    assert results.count("success") == 1
    assert results.count("Run is not waiting for approval.") == 1
    assert tool.executions == [{"value": "hello"}]


def test_run_service_preserves_created_run_max_steps_on_approval_resume() -> None:
    store = InMemoryRunStore()
    service = build_service(store, provider=EndlessSensitiveProvider(), max_steps=1)
    waiting = service.create_run("Use a sensitive tool.")

    result = service.approve_run(waiting["id"], approval_id="approval_1_call_1")

    assert result["status"] == "failed"
    assert result["error"] == "Max steps reached."
