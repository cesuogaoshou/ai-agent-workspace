from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TraceStep:
    step_number: int
    step_type: str
    status: str
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: dict[str, Any] | None = None
    error: str | None = None


@dataclass(frozen=True)
class AgentRunResult:
    task: str
    status: str
    final_answer: str | None
    steps: list[TraceStep] = field(default_factory=list)
    error: str | None = None
    pending_approval: dict[str, Any] | None = None
    resume_state: dict[str, Any] | None = None


AgentRuntimeState = dict[str, Any]


def serialize_resume_state(state: AgentRuntimeState) -> dict[str, Any]:
    return {
        "task": state["task"],
        "messages": state["messages"],
        "steps": [step.__dict__ for step in state["steps"]],
        "current_step": state["current_step"],
        "latest_response": None,
        "pending_tool_calls": state["pending_tool_calls"],
        "status": state["status"],
        "final_answer": state["final_answer"],
        "error": state["error"],
        "pending_approval": state["pending_approval"],
        "approved_approval_id": None,
        "resume_from_tool": False,
    }


def deserialize_resume_state(state: dict[str, Any]) -> AgentRuntimeState:
    return {
        "task": str(state["task"]),
        "messages": list(state["messages"]),
        "steps": [TraceStep(**step) for step in state.get("steps", [])],
        "current_step": int(state["current_step"]),
        "latest_response": None,
        "pending_tool_calls": list(state.get("pending_tool_calls", [])),
        "status": str(state["status"]),
        "final_answer": state.get("final_answer"),
        "error": state.get("error"),
        "pending_approval": state.get("pending_approval"),
        "approved_approval_id": state.get("approved_approval_id"),
        "resume_from_tool": bool(state.get("resume_from_tool", False)),
    }
