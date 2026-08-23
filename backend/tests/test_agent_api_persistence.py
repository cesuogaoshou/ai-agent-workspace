from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
import pytest

from backend.app.api import agent as agent_api
from backend.app.config import Settings, get_settings
from backend.app.llm.provider import LlmMessage
from backend.app.main import app


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
