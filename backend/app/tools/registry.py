from typing import Any

from backend.app.tools.base import Tool, ToolResult


class ToolRegistry:
    def __init__(self, tools: list[Tool]) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools:
            if tool.name in self._tools:
                raise ValueError(f"Duplicate tool name: {tool.name}")
            self._tools[tool.name] = tool

    def names(self) -> list[str]:
        return sorted(self._tools)

    def metadata(self) -> list[dict[str, object]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "requires_approval": tool.requires_approval,
            }
            for tool in (self._tools[name] for name in self.names())
        ]

    def as_llm_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in (self._tools[name] for name in self.names())
        ]

    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(ok=False, error=f"Tool is not registered: {name}")
        return tool.execute(arguments)

    def requires_approval(self, name: str) -> bool:
        tool = self._tools.get(name)
        return bool(tool.requires_approval) if tool is not None else False
