from backend.app.tools.web_search import StubWebSearchTool


def test_stub_search_returns_traceable_result() -> None:
    result = StubWebSearchTool().execute({"query": "AI Agent Workspace"})

    assert result.ok is True
    assert result.output == {
        "query": "AI Agent Workspace",
        "results": [
            {
                "title": "Stub search result",
                "url": "https://example.com/search",
                "snippet": "Replace WEB_SEARCH_MODE=stub with a real provider after provider selection.",
            }
        ],
    }
