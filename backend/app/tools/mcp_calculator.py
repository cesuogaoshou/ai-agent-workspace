import asyncio
import json
import sys
from pathlib import Path
from threading import Thread
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from backend.app.tools.base import ToolResult
from backend.app.tools.calculator import CalculatorTool


class McpCalculatorTool:
    name = CalculatorTool.name
    description = "Evaluate deterministic arithmetic expressions through a local MCP server."
    parameters = CalculatorTool.parameters
    requires_approval = CalculatorTool.requires_approval

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        try:
            payload = _run_async(_call_mcp_calculator(arguments))
        except Exception as exc:
            return ToolResult(ok=False, error=f"MCP calculator failed: {exc}")

        if payload.get("ok") is True:
            return ToolResult(ok=True, output=payload.get("output"))
        return ToolResult(ok=False, error=payload.get("error") or "MCP calculator failed.")


async def _call_mcp_calculator(arguments: dict[str, Any]) -> dict[str, Any]:
    project_root = Path(__file__).resolve().parents[3]
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "backend.app.mcp.calculator_server"],
        cwd=str(project_root),
    )
    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(CalculatorTool.name, arguments)
            return _extract_payload(result)


def _extract_payload(result: Any) -> dict[str, Any]:
    payload = getattr(result, "structured_content", None)
    if payload is None:
        payload = getattr(result, "structuredContent", None)
    if isinstance(payload, dict):
        return payload

    content = getattr(result, "content", None)
    if content:
        text = getattr(content[0], "text", None)
        if text:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed

    raise ValueError("MCP calculator returned an unsupported response shape.")


def _run_async(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:
            error["value"] = exc

    thread = Thread(target=runner)
    thread.start()
    thread.join()

    if "value" in error:
        raise error["value"]
    return result["value"]
