import asyncio
from types import SimpleNamespace

import pytest

from backend.app.tools import mcp_calculator
from backend.app.tools.mcp_calculator import McpCalculatorTool, _extract_payload


def test_mcp_calculator_returns_same_success_shape_as_local_calculator() -> None:
    result = McpCalculatorTool().execute({"expression": "2 + 3 * 4"})

    assert result.ok is True
    assert result.output == {"result": 14}
    assert result.error is None


def test_mcp_calculator_normalizes_numeric_expression_like_local_calculator() -> None:
    result = McpCalculatorTool().execute({"expression": 123})

    assert result.ok is True
    assert result.output == {"result": 123}
    assert result.error is None


def test_mcp_calculator_maps_tool_errors_to_tool_result() -> None:
    result = McpCalculatorTool().execute({"expression": "__import__('os')"})

    assert result.ok is False
    assert result.output is None
    assert result.error == "Expression contains unsupported syntax."


@pytest.mark.parametrize("error_attr", ["isError", "is_error"])
def test_extract_payload_maps_mcp_error_text_without_json_decode_error(
    error_attr: str,
) -> None:
    result = SimpleNamespace(content=[SimpleNamespace(text="Input validation error")])
    setattr(result, error_attr, True)

    assert _extract_payload(result) == {
        "ok": False,
        "error": "Input validation error",
    }


def test_run_async_raises_timeout_when_helper_thread_does_not_finish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StuckThread:
        daemon = False

        def __init__(self, target, **kwargs):
            self.target = target
            self.daemon = kwargs.get("daemon", False)

        def start(self) -> None:
            pass

        def join(self, timeout=None) -> None:
            pass

        def is_alive(self) -> bool:
            return True

    monkeypatch.setattr(mcp_calculator, "Thread", StuckThread)
    monkeypatch.setattr(mcp_calculator, "MCP_CALL_TIMEOUT_SECONDS", 0.01, raising=False)

    async def run_inside_existing_loop() -> None:
        mcp_calculator._run_async(object())

    with pytest.raises(TimeoutError, match="MCP calculator timed out"):
        asyncio.run(run_inside_existing_loop())


def test_execute_maps_timeout_to_tool_result(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_timeout(coro):
        coro.close()
        raise TimeoutError("MCP calculator timed out.")

    monkeypatch.setattr(mcp_calculator, "_run_async", raise_timeout)

    result = McpCalculatorTool().execute({"expression": "2 + 3"})

    assert result.ok is False
    assert result.output is None
    assert result.error == "MCP calculator failed: MCP calculator timed out."
