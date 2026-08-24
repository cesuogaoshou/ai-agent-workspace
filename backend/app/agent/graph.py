import json
from collections.abc import Callable
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.app.agent.state import (
    AgentRunResult,
    TraceStep,
    deserialize_resume_state,
    serialize_resume_state,
)
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
    pending_approval: dict[str, Any] | None
    approved_approval_id: str | None
    resume_from_tool: bool


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
        return self._invoke(
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
                "pending_approval": None,
                "approved_approval_id": None,
                "resume_from_tool": False,
            }
        )

    def resume(self, resume_state: dict[str, Any] | None, approval_id: str) -> AgentRunResult:
        if resume_state is None:
            raise ValueError("Resume state is required.")
        state = _coerce_graph_state(deserialize_resume_state(resume_state))
        state["status"] = "running"
        state["approved_approval_id"] = approval_id
        state["resume_from_tool"] = True
        return self._invoke(state)

    def _invoke(self, initial_state: AgentGraphState) -> AgentRunResult:
        final_state = self._graph.invoke(
            initial_state,
            config={"recursion_limit": (self.max_steps * 2) + 5},
        )
        return AgentRunResult(
            task=final_state["task"],
            status=final_state["status"],
            final_answer=final_state["final_answer"],
            steps=final_state["steps"],
            error=final_state["error"],
            pending_approval=final_state["pending_approval"],
            resume_state=(
                serialize_resume_state(final_state)
                if final_state["status"] == "waiting_for_approval"
                else None
            ),
        )

    def agent_node(self, state: AgentGraphState) -> dict[str, Any]:
        if state["status"] != "running":
            return {}
        if state["resume_from_tool"]:
            return {"resume_from_tool": False}
        if state["pending_tool_calls"]:
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
        remaining_tool_calls = list(state["pending_tool_calls"])

        for tool_call in state["pending_tool_calls"]:
            remaining_tool_calls = remaining_tool_calls[1:]
            function = tool_call["function"]
            arguments, argument_error = parse_tool_arguments(function)
            if self._requires_approval(function["name"], arguments):
                approval = {
                    "approval_id": _approval_id(step_number, tool_call["id"]),
                    "step_number": step_number,
                    "tool_call_id": tool_call["id"],
                    "tool_name": function["name"],
                    "tool_input": arguments,
                }
                if state["approved_approval_id"] != approval["approval_id"]:
                    self._emit("approval_required", approval)
                    self._emit("status_change", {"status": "waiting_for_approval"})
                    return {
                        "messages": messages,
                        "steps": steps,
                        "current_step": step_number,
                        "pending_tool_calls": [tool_call, *remaining_tool_calls],
                        "status": "waiting_for_approval",
                        "final_answer": None,
                        "error": None,
                        "pending_approval": approval,
                    }
            result = (
                argument_error
                if argument_error is not None
                else self.registry.execute(function["name"], arguments or {})
            )

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
                "pending_approval": None,
            }

        return {
            "messages": messages,
            "steps": steps,
            "current_step": next_step,
            "pending_tool_calls": [],
            "pending_approval": None,
            "approved_approval_id": None,
        }

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.on_event is not None:
            self.on_event({"event_type": event_type, "payload": payload})

    def _requires_approval(self, tool_name: str, arguments: dict[str, Any] | None) -> bool:
        return arguments is not None and self.registry.requires_approval(tool_name)


def execute_tool_call(
    registry: ToolRegistry,
    function: dict[str, Any],
) -> tuple[dict[str, Any] | None, ToolResult]:
    arguments, argument_error = parse_tool_arguments(function)
    if argument_error is not None:
        return arguments, argument_error
    return arguments, registry.execute(function["name"], arguments or {})


def parse_tool_arguments(function: dict[str, Any]) -> tuple[dict[str, Any] | None, ToolResult | None]:
    try:
        arguments = json.loads(function.get("arguments") or "{}")
    except json.JSONDecodeError:
        return None, ToolResult(ok=False, error=ARGUMENT_ERROR)
    if not isinstance(arguments, dict):
        return None, ToolResult(ok=False, error=ARGUMENT_ERROR)
    return arguments, None


def _approval_id(step_number: int, tool_call_id: str) -> str:
    return f"approval_{step_number}_{tool_call_id}"


def _coerce_graph_state(state: dict[str, Any]) -> AgentGraphState:
    return AgentGraphState(**state)
