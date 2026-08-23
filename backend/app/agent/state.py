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
