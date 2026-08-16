from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class LlmMessage:
    role: str
    content: str | None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class LlmProvider(Protocol):
    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LlmMessage:
        ...
