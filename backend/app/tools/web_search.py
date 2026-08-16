from typing import Any

from backend.app.tools.base import ToolResult


class StubWebSearchTool:
    name = "web_search"
    description = "Search the web. v0.1 uses a stub until a real search provider is selected."
    requires_approval = False
    parameters = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        query = str(arguments.get("query", ""))
        return ToolResult(
            ok=True,
            output={
                "query": query,
                "results": [
                    {
                        "title": "Stub search result",
                        "url": "https://example.com/search",
                        "snippet": "Replace WEB_SEARCH_MODE=stub with a real provider after provider selection.",
                    }
                ],
            },
        )
