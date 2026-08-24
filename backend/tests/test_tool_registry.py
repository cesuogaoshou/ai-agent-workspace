from backend.app.tools.calculator import CalculatorTool
from backend.app.tools.base import ToolResult
from backend.app.tools.registry import ToolRegistry
from backend.app.api.tools import build_registry
from backend.app.config import Settings


class NamedTool:
    description = "A named test tool."
    requires_approval = False
    parameters = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
    }

    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, arguments: dict[str, object]) -> ToolResult:
        return ToolResult(ok=True, output={"name": self.name, **arguments})


def test_registry_lists_openai_compatible_tools() -> None:
    registry = ToolRegistry([CalculatorTool()])
    tools = registry.as_llm_tools()

    assert tools[0]["type"] == "function"
    assert tools[0]["function"]["name"] == "calculator"


def test_default_built_registry_exposes_calculator_metadata(monkeypatch) -> None:
    settings = Settings(_env_file=None)

    def fake_get_settings() -> Settings:
        return settings

    monkeypatch.setattr("backend.app.api.tools.get_settings", fake_get_settings)

    registry = build_registry()
    metadata = {item["name"]: item for item in registry.metadata()}

    assert metadata["calculator"]["description"] == CalculatorTool.description
    assert metadata["calculator"]["requires_approval"] == CalculatorTool.requires_approval


def test_built_registry_uses_mcp_calculator_mode(monkeypatch) -> None:
    settings = Settings(_env_file=None, calculator_tool_mode="mcp")

    def fake_get_settings() -> Settings:
        return settings

    monkeypatch.setattr("backend.app.api.tools.get_settings", fake_get_settings)

    registry = build_registry()
    result = registry.execute("calculator", {"expression": "2+2"})
    llm_tool = next(
        tool for tool in registry.as_llm_tools() if tool["function"]["name"] == "calculator"
    )

    assert settings.calculator_tool_mode == "mcp"
    assert result.ok is True
    assert result.output == {"result": 4}
    assert llm_tool["function"]["name"] == "calculator"
    assert llm_tool["function"]["parameters"] == CalculatorTool.parameters


def test_registry_dispatches_tool() -> None:
    registry = ToolRegistry([CalculatorTool()])
    result = registry.execute("calculator", {"expression": "10 / 2"})

    assert result.ok is True
    assert result.output == {"result": 5}


def test_registry_llm_tools_follow_sorted_names_order() -> None:
    registry = ToolRegistry([NamedTool("z"), NamedTool("a")])

    assert registry.names() == ["a", "z"]
    assert [tool["function"]["name"] for tool in registry.as_llm_tools()] == ["a", "z"]


def test_registry_llm_tool_metadata_includes_description_and_parameters() -> None:
    registry = ToolRegistry([CalculatorTool()])
    tool = registry.as_llm_tools()[0]

    assert tool["function"] == {
        "name": "calculator",
        "description": CalculatorTool.description,
        "parameters": CalculatorTool.parameters,
    }


def test_registry_rejects_duplicate_tool_names() -> None:
    duplicate_tools = [CalculatorTool(), CalculatorTool()]

    try:
        ToolRegistry(duplicate_tools)
    except ValueError as exc:
        assert str(exc) == "Duplicate tool name: calculator"
    else:
        raise AssertionError("Expected duplicate tool name to raise ValueError.")


def test_registry_returns_error_for_unknown_tool() -> None:
    registry = ToolRegistry([CalculatorTool()])

    result = registry.execute("missing", {})

    assert result == ToolResult(ok=False, error="Tool is not registered: missing")
