import json
from typing import Any

from backend.app.agent.state import AgentRunResult, TraceStep
from backend.app.llm.provider import LlmProvider
from backend.app.tools.base import ToolResult
from backend.app.tools.registry import ToolRegistry


ARGUMENT_ERROR = "Tool arguments must be a JSON object."


class AgentLoop:
    def __init__(self, provider: LlmProvider, registry: ToolRegistry, max_steps: int) -> None:
        self.provider = provider
        self.registry = registry
        self.max_steps = max_steps

    def run(self, task: str) -> AgentRunResult:
        messages: list[dict[str, Any]] = [{"role": "user", "content": task}]
        steps: list[TraceStep] = []

        for step_number in range(1, self.max_steps + 1):
            response = self.provider.complete(messages, self.registry.as_llm_tools())
            if not response.tool_calls:
                final_answer = response.content or ""
                steps.append(TraceStep(step_number=step_number, step_type="final_answer", status="success"))
                return AgentRunResult(task=task, status="success", final_answer=final_answer, steps=steps)

            messages.append({"role": "assistant", "content": response.content, "tool_calls": response.tool_calls})
            for tool_call in response.tool_calls:
                function = tool_call["function"]
                arguments, result = self._execute_tool_call(function)
                steps.append(
                    TraceStep(
                        step_number=step_number,
                        step_type="tool_call",
                        status="success" if result.ok else "failed",
                        tool_name=function["name"],
                        tool_input=arguments,
                        tool_output=result.output,
                        error=result.error,
                    )
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(result.output if result.ok else {"error": result.error}),
                    }
                )
        return AgentRunResult(task=task, status="failed", final_answer=None, steps=steps, error="Max steps reached.")

    def _execute_tool_call(self, function: dict[str, Any]) -> tuple[dict[str, Any] | None, ToolResult]:
        try:
            arguments = json.loads(function.get("arguments") or "{}")
        except json.JSONDecodeError:
            return None, ToolResult(ok=False, error=ARGUMENT_ERROR)
        if not isinstance(arguments, dict):
            return None, ToolResult(ok=False, error=ARGUMENT_ERROR)
        return arguments, self.registry.execute(function["name"], arguments)
