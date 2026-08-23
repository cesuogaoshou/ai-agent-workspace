from collections.abc import Iterator
from typing import Any

from fastapi.testclient import TestClient
import pytest

from backend.app.api import agent as agent_api
from backend.app.config import Settings, get_settings
from backend.app.llm.provider import LlmMessage
from backend.app.main import app
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


class ApprovalDeepSeekProvider:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

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


@pytest.fixture(autouse=True)
def approval_api(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    def fake_get_settings() -> Settings:
        return Settings(
            _env_file=None,
            deepseek_api_key="test-key",
            deepseek_base_url="https://api.deepseek.com",
            deepseek_model="deepseek-v4-flash",
            agent_max_steps=8,
            file_reader_root="workspace_files",
            web_search_mode="stub",
        )

    monkeypatch.setattr("backend.app.api.agent.get_settings", fake_get_settings)
    monkeypatch.setattr("backend.app.api.tools.get_settings", fake_get_settings)
    monkeypatch.setattr("backend.app.api.agent.DeepSeekProvider", ApprovalDeepSeekProvider)
    monkeypatch.setattr(
        "backend.app.api.agent.build_registry",
        lambda: ToolRegistry([SensitiveEchoTool()]),
    )
    monkeypatch.setattr("backend.app.api.agent.RUN_STORE", InMemoryRunStore())
    get_settings.cache_clear()
    yield
    agent_api.RUN_STORE = None
    get_settings.cache_clear()


def test_agent_api_returns_waiting_run_with_pending_approval() -> None:
    client = TestClient(app)

    response = client.post("/api/agent/runs", json={"task": "Use a sensitive tool."})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "waiting_for_approval"
    assert body["finished_at"] is None
    assert body["pending_approval"]["approval_id"] == "approval_1_call_1"
    assert "resume_state" not in body
    assert [event["event_type"] for event in body["steps"]] == [
        "status_change",
        "approval_required",
        "status_change",
    ]


def test_agent_api_approve_resumes_waiting_run() -> None:
    client = TestClient(app)
    waiting = client.post("/api/agent/runs", json={"task": "Use a sensitive tool."}).json()

    response = client.post(
        f"/api/agent/runs/{waiting['id']}/approve",
        json={"approval_id": "approval_1_call_1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["final_answer"] == "approved done"
    assert body["pending_approval"] is None
    assert [event["event_type"] for event in body["steps"]] == [
        "status_change",
        "approval_required",
        "status_change",
        "approval_decision",
        "status_change",
        "tool_call",
        "final_answer",
    ]


def test_agent_api_reject_terminates_waiting_run() -> None:
    client = TestClient(app)
    waiting = client.post("/api/agent/runs", json={"task": "Use a sensitive tool."}).json()

    response = client.post(
        f"/api/agent/runs/{waiting['id']}/reject",
        json={"approval_id": "approval_1_call_1", "reason": "Too risky."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["error"] == "Too risky."
    assert body["pending_approval"] is None


def test_agent_api_rejects_mismatched_approval_id() -> None:
    client = TestClient(app)
    waiting = client.post("/api/agent/runs", json={"task": "Use a sensitive tool."}).json()

    response = client.post(
        f"/api/agent/runs/{waiting['id']}/approve",
        json={"approval_id": "wrong"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Approval id does not match pending approval."}
