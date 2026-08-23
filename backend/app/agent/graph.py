import json
from collections.abc import Callable
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.app.agent.state import AgentRunResult, TraceStep
from backend.app.llm.provider import LlmMessage, LlmProvider
from backend.app.tools.base import ToolResult
from backend.app.tools.registry import ToolRegistry


ARGUMENT_ERROR = "Tool arguments must be a JSON object."
EventCallback = Callable[[dict[str, Any]], None]
RouteName = Literal["tool", "__end__"]


class AgentGraphState(TypedDict):
    task: str
    messages: list[dict[str, Any]]
    steps: list[TraceStep]
    current_step: int
    latest_response: LlmMessage | None
    pending_tool_calls: list[dict[str, Any]]
    status: str
    final_answer: str | None
    error: str | None


def describe_agent_graph() -> dict[str, Any]:
    return {
        "nodes": ["agent", "tool"],
        "entrypoint": "agent",
        "conditional_edges": {"agent": ["tool", "__end__"]},
        "edges": {"tool": "agent"},
    }


def build_agent_graph(runner: "AgentGraphRunner") -> Any:
    graph = StateGraph(AgentGraphState)
    graph.add_node("agent", runner.agent_node)
    graph.add_node("tool", runner.tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", runner.route_after_agent, {"tool": "tool", "__end__": END})
    graph.add_edge("tool", "agent")
    return graph.compile()


class AgentGraphRunner:
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
        self._graph = build_agent_graph(self)

    def run(self, task: str) -> AgentRunResult:
        final_state = self._graph.invoke(
            {
                "task": task,
                "messages": [{"role": "user", "content": task}],
                "steps": [],
                "current_step": 1,
                "latest_response": None,
                "pending_tool_calls": [],
                "status": "running",
                "final_answer": None,
                "error": None,
            },
            config={"recursion_limit": (self.max_steps * 2) + 5},
        )
        return AgentRunResult(
            task=task,
            status=final_state["status"],
            final_answer=final_state["final_answer"],
            steps=final_state["steps"],
            error=final_state["error"],
        )

    def agent_node(self, state: AgentGraphState) -> dict[str, Any]:
        if state["status"] != "running":
            return {}

        response = self.provider.complete(state["messages"], self.registry.as_llm_tools())
        if not response.tool_calls:
            final_answer = response.content or ""
            step = TraceStep(
                step_number=state["current_step"],
                step_type="final_answer",
                status="success",
            )
            self._emit(
                "final_answer",
                {
                    "step_number": step.step_number,
                    "status": "success",
                    "final_answer": final_answer,
                },
            )
            return {
                "steps": [*state["steps"], step],
                "latest_response": response,
                "pending_tool_calls": [],
                "status": "success",
                "final_answer": final_answer,
                "error": None,
            }

        return {
            "messages": [
                *state["messages"],
                {
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": response.tool_calls,
                },
            ],
            "latest_response": response,
            "pending_tool_calls": response.tool_calls,
        }

    def route_after_agent(self, state: AgentGraphState) -> RouteName:
        if state["status"] != "running":
            return "__end__"
        if state["pending_tool_calls"]:
            return "tool"
        return "__end__"

    def tool_node(self, state: AgentGraphState) -> dict[str, Any]:
        messages = list(state["messages"])
        steps = list(state["steps"])
        step_number = state["current_step"]

        for tool_call in state["pending_tool_calls"]:
            function = tool_call["function"]
            arguments, result = execute_tool_call(self.registry, function)
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

        next_step = step_number + 1
        if next_step > self.max_steps:
            self._emit("status_change", {"status": "failed", "error": "Max steps reached."})
            return {
                "messages": messages,
                "steps": steps,
                "current_step": next_step,
                "pending_tool_calls": [],
                "status": "failed",
                "final_answer": None,
                "error": "Max steps reached.",
            }

        return {
            "messages": messages,
            "steps": steps,
            "current_step": next_step,
            "pending_tool_calls": [],
        }

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.on_event is not None:
            self.on_event({"event_type": event_type, "payload": payload})


def execute_tool_call(
    registry: ToolRegistry,
    function: dict[str, Any],
) -> tuple[dict[str, Any] | None, ToolResult]:
    try:
        arguments = json.loads(function.get("arguments") or "{}")
    except json.JSONDecodeError:
        return None, ToolResult(ok=False, error=ARGUMENT_ERROR)
    if not isinstance(arguments, dict):
        return None, ToolResult(ok=False, error=ARGUMENT_ERROR)
    return arguments, registry.execute(function["name"], arguments)
