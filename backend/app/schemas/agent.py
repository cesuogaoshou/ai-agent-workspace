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


class TraceStepResponse(BaseModel):
    step_number: int
    step_type: str
    status: str
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: dict[str, Any] | None = None
    error: str | None = None


class AgentRunResponse(BaseModel):
    task: str
    status: str
    final_answer: str | None
    steps: list[TraceStepResponse]
    error: str | None = None
