from typing import Any

from mcp.server.fastmcp import FastMCP

from backend.app.tools.calculator import CalculatorTool


mcp = FastMCP("ai-agent-workspace-calculator")


@mcp.tool(name=CalculatorTool.name, description=CalculatorTool.description)
def calculator(expression: str) -> dict[str, Any]:
    result = CalculatorTool().execute({"expression": expression})
    if result.ok:
        return {"ok": True, "output": result.output}
    return {"ok": False, "error": result.error}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
