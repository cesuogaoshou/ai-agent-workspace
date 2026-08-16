from typing import Any

from backend.app.llm.provider import LlmMessage


class DeepSeekProvider:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.base_url = base_url
        self.model = model
        self._api_key = api_key
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self._api_key, base_url=self.base_url)
        return self._client

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LlmMessage:
        response = self._get_client().chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
        )
        if not response.choices:
            raise RuntimeError("DeepSeek response did not include any choices.")

        message = response.choices[0].message
        tool_calls = [tool_call.model_dump() for tool_call in message.tool_calls] if message.tool_calls else None
        return LlmMessage(role="assistant", content=message.content, tool_calls=tool_calls)
