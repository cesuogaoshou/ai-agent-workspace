import sys
from types import SimpleNamespace

import pytest

from backend.app.llm.provider import LlmMessage
from backend.app.llm.deepseek import DeepSeekProvider


def test_deepseek_provider_uses_configured_values() -> None:
    provider = DeepSeekProvider(api_key="key", base_url="https://api.deepseek.com", model="deepseek-v4-flash")

    assert provider.model == "deepseek-v4-flash"
    assert provider.base_url == "https://api.deepseek.com"


def test_deepseek_provider_construction_does_not_load_openai_or_create_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(sys.modules, "openai", raising=False)

    provider = DeepSeekProvider(api_key="key", base_url="https://api.deepseek.com", model="deepseek-v4-flash")

    assert "openai" not in sys.modules
    assert provider._client is None


def test_deepseek_provider_complete_converts_response_to_llm_message() -> None:
    provider = DeepSeekProvider(api_key="key", base_url="https://api.deepseek.com", model="deepseek-v4-flash")
    tool_call_dump = {"id": "call_1", "type": "function", "function": {"name": "calculator", "arguments": "{}"}}
    provider._client = FakeClient(
        response=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="done",
                        tool_calls=[FakeToolCall(tool_call_dump)],
                    )
                )
            ]
        )
    )

    message = provider.complete(messages=[{"role": "user", "content": "calculate"}], tools=[{"type": "function"}])

    assert message == LlmMessage(role="assistant", content="done", tool_calls=[tool_call_dump])


def test_deepseek_provider_complete_raises_provider_error_for_empty_choices() -> None:
    provider = DeepSeekProvider(api_key="key", base_url="https://api.deepseek.com", model="deepseek-v4-flash")
    provider._client = FakeClient(response=SimpleNamespace(choices=[]))

    with pytest.raises(RuntimeError, match="DeepSeek response did not include any choices."):
        provider.complete(messages=[{"role": "user", "content": "hello"}], tools=[])


class FakeToolCall:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def model_dump(self) -> dict[str, object]:
        return self._payload


class FakeClient:
    def __init__(self, response: object) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions(response))


class FakeCompletions:
    def __init__(self, response: object) -> None:
        self._response = response

    def create(self, **kwargs: object) -> object:
        return self._response
