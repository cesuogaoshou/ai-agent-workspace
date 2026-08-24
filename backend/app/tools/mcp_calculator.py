import asyncio
import json
import os
import sys
from datetime import timedelta
from pathlib import Path
from threading import Thread
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from backend.app.tools.base import ToolResult
from backend.app.tools.calculator import CalculatorTool


MCP_CALL_TIMEOUT_SECONDS = 5.0


class McpCalculatorTool:
    name = CalculatorTool.name
    description = "Evaluate deterministic arithmetic expressions through a local MCP server."
    parameters = CalculatorTool.parameters
    requires_approval = CalculatorTool.requires_approval

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        mcp_arguments = {"expression": str(arguments.get("expression", ""))}
        try:
            payload = _run_async(_call_mcp_calculator(mcp_arguments))
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
    with open(os.devnull, "w", encoding="utf-8") as errlog:
        stdio_context = stdio_client(server, errlog=errlog)
        read_stream, write_stream = await asyncio.wait_for(
            stdio_context.__aenter__(),
            timeout=MCP_CALL_TIMEOUT_SECONDS,
        )
        try:
            session_context = ClientSession(read_stream, write_stream)
            session = await asyncio.wait_for(
                session_context.__aenter__(),
                timeout=MCP_CALL_TIMEOUT_SECONDS,
            )
            try:
                await asyncio.wait_for(
                    session.initialize(),
                    timeout=MCP_CALL_TIMEOUT_SECONDS,
                )
                result = await asyncio.wait_for(
                    session.call_tool(
                        CalculatorTool.name,
                        arguments,
                        read_timeout_seconds=timedelta(seconds=MCP_CALL_TIMEOUT_SECONDS),
                    ),
                    timeout=MCP_CALL_TIMEOUT_SECONDS,
                )
                return _extract_payload(result)
            finally:
                await asyncio.wait_for(
                    session_context.__aexit__(None, None, None),
                    timeout=MCP_CALL_TIMEOUT_SECONDS,
                )
        finally:
            await asyncio.wait_for(
                stdio_context.__aexit__(None, None, None),
                timeout=MCP_CALL_TIMEOUT_SECONDS,
            )


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
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                if getattr(result, "isError", False) or getattr(
                    result, "is_error", False
                ):
                    return {"ok": False, "error": text}
                raise ValueError(
                    "MCP calculator returned a non-JSON text response."
                ) from exc
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

    thread = Thread(target=runner, daemon=True)
    thread.start()
    thread.join(MCP_CALL_TIMEOUT_SECONDS)

    if thread.is_alive():
        raise TimeoutError("MCP calculator timed out.")

    if "value" in error:
        raise error["value"]
    return result["value"]
