from typing import Any

from pydantic import BaseModel, Field, field_validator


class CreateRunRequest(BaseModel):
    task: str = Field(min_length=1)
    max_steps: int | None = Field(default=None, ge=1, le=20)

    @field_validator("task")
    @classmethod
    def task_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Task must not be blank.")
        return stripped


class ApprovalDecisionRequest(BaseModel):
    approval_id: str = Field(min_length=1)


class RejectApprovalRequest(ApprovalDecisionRequest):
    reason: str | None = None


class TraceStepResponse(BaseModel):
    step_number: int
    step_type: str
    status: str
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: dict[str, Any] | None = None
    error: str | None = None


class RunSummaryResponse(BaseModel):
    id: str
    task: str
    status: str
    final_answer: str | None = None
    error: str | None = None
    created_at: str
    finished_at: str | None = None
    step_count: int
    tool_call_count: int


class RunListResponse(BaseModel):
    items: list[RunSummaryResponse]


class RunEventResponse(BaseModel):
    run_id: str
    event_type: str
    sequence: int
    payload: dict[str, Any]
    created_at: str


class AgentRunResponse(BaseModel):
    id: str | None = None
    task: str
    status: str
    final_answer: str | None
    steps: list[TraceStepResponse | RunEventResponse]
    error: str | None = None
    created_at: str | None = None
    finished_at: str | None = None
    pending_approval: dict[str, Any] | None = None
