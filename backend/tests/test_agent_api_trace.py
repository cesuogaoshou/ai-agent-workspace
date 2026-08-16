from collections.abc import Iterator
from typing import Any

from fastapi.testclient import TestClient
import pytest

from backend.app.config import Settings, get_settings
from backend.app.llm.provider import LlmMessage
from backend.app.main import app
from backend.app.services.run_store import InMemoryRunStore


class FakeDeepSeekProvider:
    constructed = False

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        FakeDeepSeekProvider.constructed = True

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LlmMessage:
        return LlmMessage(role="assistant", content="done")


@pytest.fixture(autouse=True)
def isolated_agent_api(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
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
    monkeypatch.setattr("backend.app.api.agent.DeepSeekProvider", FakeDeepSeekProvider)
    monkeypatch.setattr("backend.app.api.agent.RUN_STORE", InMemoryRunStore())
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_agent_run_response_includes_run_metadata_and_event_steps() -> None:
    client = TestClient(app)

    response = client.post("/api/agent/runs", json={"task": "Return done."})

    assert response.status_code == 200
    body = response.json()
    assert body["id"].startswith("run_")
    assert isinstance(body["created_at"], str)
    assert isinstance(body["finished_at"], str)
    assert body["status"] == "success"
    assert body["final_answer"] == "done"
    assert body["steps"]
    assert body["steps"][0]["run_id"] == body["id"]
    assert body["steps"][0]["event_type"] == "status_change"
    assert body["steps"][0]["sequence"] == 1
    assert "payload" in body["steps"][0]
    assert "created_at" in body["steps"][0]
    assert FakeDeepSeekProvider.constructed is True


def test_list_runs_after_create() -> None:
    client = TestClient(app)
    created = client.post("/api/agent/runs", json={"task": "Return done."}).json()

    listed = client.get("/api/agent/runs")

    assert listed.status_code == 200
    items = listed.json()["items"]
    assert any(item["id"] == created["id"] for item in items)
    saved = next(item for item in items if item["id"] == created["id"])
    assert saved["task"] == "Return done."
    assert saved["status"] == "success"
    assert saved["final_answer"] == "done"
    assert saved["created_at"] == created["created_at"]
    assert saved["finished_at"] == created["finished_at"]
    assert saved["step_count"] == 1
    assert saved["tool_call_count"] == 0


def test_get_run_after_create_returns_run_with_steps() -> None:
    client = TestClient(app)
    created = client.post("/api/agent/runs", json={"task": "Return done."}).json()

    fetched = client.get(f"/api/agent/runs/{created['id']}")

    assert fetched.status_code == 200
    body = fetched.json()
    assert body["id"] == created["id"]
    assert body["steps"] == created["steps"]


def test_run_events_endpoint_streams_sse() -> None:
    client = TestClient(app)
    created = client.post("/api/agent/runs", json={"task": "Return done."}).json()

    response = client.get(f"/api/agent/runs/{created['id']}/events")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "event:" in response.text
    assert "data:" in response.text
    assert created["id"] in response.text


def test_unknown_run_and_events_return_404() -> None:
    client = TestClient(app)

    fetched = client.get("/api/agent/runs/run_missing")
    events = client.get("/api/agent/runs/run_missing/events")

    assert fetched.status_code == 404
    assert fetched.json() == {"detail": "Run not found."}
    assert events.status_code == 404
    assert events.json() == {"detail": "Run not found."}


def test_failed_provider_run_does_not_expose_sensitive_exception_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sensitive_text = "sensitive-token"

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
            raise RuntimeError(f"provider failed with {sensitive_text}")

    monkeypatch.setattr("backend.app.api.agent.DeepSeekProvider", RaisingDeepSeekProvider)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/api/agent/runs", json={"task": "Return done."})
    listed = client.get("/api/agent/runs")
    fetched = client.get("/api/agent/runs/run_1")
    events = client.get("/api/agent/runs/run_1/events")

    assert response.status_code == 500
    assert response.json() == {"detail": "Agent run failed."}
    assert sensitive_text not in response.text
    assert listed.status_code == 200
    assert fetched.status_code == 200
    assert events.status_code == 200
    for response_text in (listed.text, fetched.text, events.text):
        assert sensitive_text not in response_text
        assert "provider failed" not in response_text
    failed_run = listed.json()["items"][0]
    assert failed_run["status"] == "failed"
    assert failed_run["error"] == "Agent run failed."
    assert fetched.json()["error"] == "Agent run failed."
