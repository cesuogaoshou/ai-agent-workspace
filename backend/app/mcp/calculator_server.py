from typing import Any

from mcp.server.mcpserver.server import MCPServer

from backend.app.tools.calculator import CalculatorTool


def calculator(expression: str) -> dict[str, Any]:
    result = CalculatorTool().execute({"expression": expression})
    if result.ok:
        return {"ok": True, "output": result.output}
    return {"ok": False, "error": result.error}


def create_server() -> MCPServer[Any]:
    server: MCPServer[Any] = MCPServer("ai-agent-workspace-calculator")
    server.add_tool(
        calculator,
        name=CalculatorTool.name,
        description=CalculatorTool.description,
        structured_output=True,
    )
    return server


def main() -> None:
    create_server().run("stdio")


if __name__ == "__main__":
    main()
