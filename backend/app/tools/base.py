from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    output: dict[str, Any] | None = None
    error: str | None = None


class Tool(Protocol):
    name: str
    description: str
    parameters: dict[str, Any]
    requires_approval: bool

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        ...
