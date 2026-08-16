import json
from collections.abc import Callable
from typing import Any

from backend.app.agent.state import AgentRunResult, TraceStep
from backend.app.llm.provider import LlmProvider
from backend.app.tools.base import ToolResult
from backend.app.tools.registry import ToolRegistry


ARGUMENT_ERROR = "Tool arguments must be a JSON object."
EventCallback = Callable[[dict[str, Any]], None]


class AgentLoop:
    def __init__(
        self,
        provider: LlmProvider,
        registry: ToolRegistry,
        max_steps: int,
        on_event: EventCallback | None = None,
    ) -> None:
        self.provider = provider
        self.registry = registry
        self.max_steps = max_steps
        self.on_event = on_event

    def run(self, task: str) -> AgentRunResult:
        messages: list[dict[str, Any]] = [{"role": "user", "content": task}]
        steps: list[TraceStep] = []

        for step_number in range(1, self.max_steps + 1):
            response = self.provider.complete(messages, self.registry.as_llm_tools())
            if not response.tool_calls:
                final_answer = response.content or ""
                steps.append(TraceStep(step_number=step_number, step_type="final_answer", status="success"))
                self._emit(
                    "final_answer",
                    {"step_number": step_number, "status": "success", "final_answer": final_answer},
                )
                return AgentRunResult(task=task, status="success", final_answer=final_answer, steps=steps)

            messages.append({"role": "assistant", "content": response.content, "tool_calls": response.tool_calls})
            for tool_call in response.tool_calls:
                function = tool_call["function"]
                arguments, result = self._execute_tool_call(function)
                step = TraceStep(
                    step_number=step_number,
                    step_type="tool_call",
                    status="success" if result.ok else "failed",
                    tool_name=function["name"],
                    tool_input=arguments,
                    tool_output=result.output,
                    error=result.error,
                )
                steps.append(step)
                self._emit(
                    "tool_call",
                    {
                        "step_number": step.step_number,
                        "tool_name": step.tool_name,
                        "status": step.status,
                        "tool_input": step.tool_input,
                        "tool_output": step.tool_output,
                        "error": step.error,
                    },
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(result.output if result.ok else {"error": result.error}),
                    }
                )
        self._emit("status_change", {"status": "failed", "error": "Max steps reached."})
        return AgentRunResult(task=task, status="failed", final_answer=None, steps=steps, error="Max steps reached.")

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.on_event is not None:
            self.on_event({"event_type": event_type, "payload": payload})

    def _execute_tool_call(self, function: dict[str, Any]) -> tuple[dict[str, Any] | None, ToolResult]:
        try:
            arguments = json.loads(function.get("arguments") or "{}")
        except json.JSONDecodeError:
            return None, ToolResult(ok=False, error=ARGUMENT_ERROR)
        if not isinstance(arguments, dict):
            return None, ToolResult(ok=False, error=ARGUMENT_ERROR)
        return arguments, self.registry.execute(function["name"], arguments)
