from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
import pytest

from backend.app.api import agent as agent_api
from backend.app.config import Settings, get_settings
from backend.app.llm.provider import LlmMessage
from backend.app.main import app
from backend.app.tools.base import ToolResult
from backend.app.tools.registry import ToolRegistry


class PersistentSensitiveEchoTool:
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


class PersistentFakeDeepSeekProvider:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LlmMessage:
        return LlmMessage(role="assistant", content="persisted answer")


class PersistentApprovalProvider:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LlmMessage:
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


@pytest.fixture()
def persisted_agent_api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_settings() -> Settings:
        return Settings(
            _env_file=None,
            deepseek_api_key="test-key",
            deepseek_base_url="https://api.deepseek.com",
            deepseek_model="deepseek-v4-flash",
            agent_max_steps=8,
            file_reader_root="workspace_files",
            web_search_mode="stub",
            database_url=f"sqlite:///{tmp_path / 'api-runs.sqlite3'}",
        )

    monkeypatch.setattr("backend.app.api.agent.get_settings", fake_get_settings)
    monkeypatch.setattr("backend.app.api.agent.DeepSeekProvider", PersistentFakeDeepSeekProvider)
    agent_api.RUN_STORE = None
    get_settings.cache_clear()
    yield
    agent_api.RUN_STORE = None
    get_settings.cache_clear()


def test_agent_api_reads_persisted_run_after_store_reinitializes(
    persisted_agent_api: None,
) -> None:
    client = TestClient(app)
    created = client.post("/api/agent/runs", json={"task": "Return a persisted answer."}).json()

    agent_api.RUN_STORE = None

    listed = client.get("/api/agent/runs")
    fetched = client.get(f"/api/agent/runs/{created['id']}")
    events = client.get(f"/api/agent/runs/{created['id']}/events")

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [created["id"]]
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]
    assert fetched.json()["final_answer"] == "persisted answer"
    assert fetched.json()["steps"] == created["steps"]
    assert events.status_code == 200
    assert "text/event-stream" in events.headers["content-type"]
    assert created["id"] in events.text


def test_agent_api_reads_persisted_failed_run_after_store_reinitializes(
    persisted_agent_api: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sensitive_text = "secret-provider-detail"

    class RaisingDeepSeekProvider:
        def __init__(self, api_key: str, base_url: str, model: str) -> None:
            self.api_key = api_key
            self.base_url = base_url
            self.model = model

        def complete(
            self,
            messages: list[dict[str, Any]],
            tools: list[dict[str, Any]],
        ) -> LlmMessage:
            raise RuntimeError(sensitive_text)

    monkeypatch.setattr("backend.app.api.agent.DeepSeekProvider", RaisingDeepSeekProvider)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/api/agent/runs", json={"task": "Fail safely."})
    agent_api.RUN_STORE = None

    listed = client.get("/api/agent/runs")
    fetched = client.get("/api/agent/runs/run_1")
    events = client.get("/api/agent/runs/run_1/events")

    assert response.status_code == 500
    assert listed.json()["items"][0]["status"] == "failed"
    assert listed.json()["items"][0]["error"] == "Agent run failed."
    assert fetched.json()["status"] == "failed"
    assert fetched.json()["error"] == "Agent run failed."
    assert '"status":"failed"' in events.text
    assert '"error":"Agent run failed."' in events.text
    assert sensitive_text not in listed.text
    assert sensitive_text not in fetched.text
    assert sensitive_text not in events.text


def test_agent_api_does_not_expose_persisted_resume_state_after_store_reinitializes(
    persisted_agent_api: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("backend.app.api.agent.DeepSeekProvider", PersistentApprovalProvider)
    monkeypatch.setattr(
        "backend.app.api.agent.build_registry",
        lambda: ToolRegistry([PersistentSensitiveEchoTool()]),
    )
    client = TestClient(app)

    created = client.post("/api/agent/runs", json={"task": "Needs approval."})
    agent_api.RUN_STORE = None

    fetched = client.get(f"/api/agent/runs/{created.json()['id']}")
    listed = client.get("/api/agent/runs")
    events = client.get(f"/api/agent/runs/{created.json()['id']}/events")

    assert created.status_code == 200
    assert fetched.status_code == 200
    assert listed.status_code == 200
    assert events.status_code == 200
    assert created.json()["status"] == "waiting_for_approval"
    assert fetched.json()["status"] == "waiting_for_approval"
    assert fetched.json()["pending_approval"]["approval_id"] == "approval_1_call_1"
    assert "resume_state" not in created.text
    assert "resume_state" not in fetched.text
    assert "resume_state" not in listed.text
    assert "resume_state" not in events.text
