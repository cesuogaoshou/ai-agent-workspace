from collections.abc import Iterator
from typing import Any

from fastapi.testclient import TestClient
import pytest

from backend.app.config import Settings, get_settings
from backend.app.llm.provider import LlmMessage
from backend.app.main import app


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, Any]]:
    settings_values: dict[str, Any] = {
        "deepseek_api_key": "test-key",
        "deepseek_base_url": "https://api.deepseek.com",
        "deepseek_model": "deepseek-v4-flash",
        "agent_max_steps": 8,
        "file_reader_root": "workspace_files",
        "web_search_mode": "stub",
    }

    def fake_get_settings() -> Settings:
        return Settings(_env_file=None, **settings_values)

    monkeypatch.setattr("backend.app.api.agent.get_settings", fake_get_settings)
    monkeypatch.setattr("backend.app.api.tools.get_settings", fake_get_settings)
    get_settings.cache_clear()
    yield settings_values
    get_settings.cache_clear()


def test_tools_endpoint_lists_tools() -> None:
    client = TestClient(app)
    response = client.get("/api/tools")

    assert response.status_code == 200
    names = {item["name"] for item in response.json()["items"]}
    assert {"calculator", "file_reader", "web_search"}.issubset(names)


def test_agent_run_requires_task() -> None:
    client = TestClient(app)
    response = client.post("/api/agent/runs", json={})

    assert response.status_code == 422


def test_agent_run_success_serializes_trace_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDeepSeekProvider:
        def __init__(self, api_key: str, base_url: str, model: str) -> None:
            self.api_key = api_key
            self.base_url = base_url
            self.model = model

        def complete(
            self,
            messages: list[dict[str, Any]],
            tools: list[dict[str, Any]],
        ) -> LlmMessage:
            return LlmMessage(role="assistant", content="done")

    monkeypatch.setattr("backend.app.api.agent.DeepSeekProvider", FakeDeepSeekProvider)

    client = TestClient(app)
    response = client.post("/api/agent/runs", json={"task": "answer directly"})

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "task": "answer directly",
        "status": "success",
        "final_answer": "done",
        "steps": [
            {
                "step_number": 1,
                "step_type": "final_answer",
                "status": "success",
                "tool_name": None,
                "tool_input": None,
                "tool_output": None,
                "error": None,
            }
        ],
        "error": None,
    }


def test_agent_run_missing_api_key_returns_500_without_secret(
    isolated_settings: dict[str, Any],
) -> None:
    isolated_settings["deepseek_api_key"] = ""

    client = TestClient(app)
    response = client.post("/api/agent/runs", json={"task": "answer directly"})

    assert response.status_code == 500
    assert response.json() == {"detail": "DEEPSEEK_API_KEY is not configured."}
    assert "test-key" not in response.text


@pytest.mark.parametrize("max_steps", [0, 21])
def test_agent_run_rejects_max_steps_out_of_bounds(
    monkeypatch: pytest.MonkeyPatch,
    max_steps: int,
) -> None:
    def fail_provider(*args: object, **kwargs: object) -> object:
        raise AssertionError("provider should not be constructed")

    monkeypatch.setattr("backend.app.api.agent.DeepSeekProvider", fail_provider)

    client = TestClient(app)
    response = client.post(
        "/api/agent/runs",
        json={"task": "answer directly", "max_steps": max_steps},
    )

    assert response.status_code == 422


def test_agent_run_rejects_whitespace_task_before_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_provider(*args: object, **kwargs: object) -> object:
        raise AssertionError("provider should not be constructed")

    monkeypatch.setattr("backend.app.api.agent.DeepSeekProvider", fail_provider)

    client = TestClient(app)
    response = client.post("/api/agent/runs", json={"task": "   "})

    assert response.status_code == 422


def test_tools_endpoint_reads_requires_approval_from_tool_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("backend.app.tools.calculator.CalculatorTool.requires_approval", True)

    client = TestClient(app)
    response = client.get("/api/tools")

    assert response.status_code == 200
    tools = {item["name"]: item for item in response.json()["items"]}
    assert tools["calculator"]["requires_approval"] is True
