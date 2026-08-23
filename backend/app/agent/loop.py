from collections.abc import Callable
from typing import Any

from backend.app.agent.graph import AgentGraphRunner, execute_tool_call
from backend.app.agent.state import AgentRunResult
from backend.app.llm.provider import LlmProvider
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
        return AgentGraphRunner(
            self.provider,
            self.registry,
            self.max_steps,
            on_event=self.on_event,
        ).run(task)

    def resume(self, resume_state: dict[str, Any] | None, approval_id: str) -> AgentRunResult:
        return AgentGraphRunner(
            self.provider,
            self.registry,
            self.max_steps,
            on_event=self.on_event,
        ).resume(resume_state, approval_id=approval_id)

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.on_event is not None:
            self.on_event({"event_type": event_type, "payload": payload})

    def _execute_tool_call(self, function: dict[str, Any]) -> Any:
        return execute_tool_call(self.registry, function)
