from backend.app.tools.mcp_calculator import McpCalculatorTool


def test_mcp_calculator_returns_same_success_shape_as_local_calculator() -> None:
    result = McpCalculatorTool().execute({"expression": "2 + 3 * 4"})

    assert result.ok is True
    assert result.output == {"result": 14}
    assert result.error is None


def test_mcp_calculator_maps_tool_errors_to_tool_result() -> None:
    result = McpCalculatorTool().execute({"expression": "__import__('os')"})

    assert result.ok is False
    assert result.output is None
    assert result.error == "Expression contains unsupported syntax."
