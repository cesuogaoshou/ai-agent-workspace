import json
from dataclasses import dataclass
from typing import Any

from backend.app.agent.loop import AgentLoop
from backend.app.llm.provider import LlmMessage
from backend.app.tools.base import ToolResult
from backend.app.tools.calculator import CalculatorTool
from backend.app.tools.mcp_calculator import McpCalculatorTool
from backend.app.tools.registry import ToolRegistry
from backend.app.tools.web_search import StubWebSearchTool
from backend.evaluation.dataset import EvaluationCase


@dataclass(frozen=True)
class EvaluationResult:
    case_id: str
    category: str
    status: str
    actual_tools: list[str]
    expected_tools: list[str]
    final_answer: str | None
    expected_final_answer: str | None
    step_count: int
    tool_failure_count: int
    task_success: bool | None
    tool_selection_correct: bool | None
    approval_required: bool
    approval_correct: bool | None
    executed_tool_count: int = 0
    error: str | None = None
    skip_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "status": self.status,
            "actual_tools": self.actual_tools,
            "expected_tools": self.expected_tools,
            "final_answer": self.final_answer,
            "expected_final_answer": self.expected_final_answer,
            "step_count": self.step_count,
            "tool_failure_count": self.tool_failure_count,
            "task_success": self.task_success,
            "tool_selection_correct": self.tool_selection_correct,
            "approval_required": self.approval_required,
            "approval_correct": self.approval_correct,
            "executed_tool_count": self.executed_tool_count,
            "error": self.error,
            "skip_reason": self.skip_reason,
        }


def run_evaluation_cases(
    cases: list[EvaluationCase],
    max_steps: int = 8,
    calculator_mode: str = "local",
) -> list[EvaluationResult]:
    return [
        _run_evaluation_case(case, max_steps=max_steps, calculator_mode=calculator_mode)
        for case in cases
    ]


def _run_evaluation_case(
    case: EvaluationCase,
    max_steps: int,
    calculator_mode: str,
) -> EvaluationResult:
    if case.skip_reason is not None:
        return EvaluationResult(
            case_id=case.case_id,
            category=case.category,
            status="skipped",
            actual_tools=[],
            expected_tools=case.expected_tools,
            final_answer=None,
            expected_final_answer=case.expected_final_answer,
            step_count=0,
            tool_failure_count=0,
            task_success=None,
            tool_selection_correct=None,
            approval_required=False,
            approval_correct=None,
            executed_tool_count=0,
            skip_reason=case.skip_reason,
        )

    try:
        result = AgentLoop(
            ScriptedEvaluationProvider(case.script),
            _evaluation_registry(calculator_mode=calculator_mode),
            max_steps=max_steps,
        ).run(case.task)
    except EvaluationScriptExhausted as exc:
        return EvaluationResult(
            case_id=case.case_id,
            category=case.category,
            status="failed",
            actual_tools=[],
            expected_tools=case.expected_tools,
            final_answer=None,
            expected_final_answer=case.expected_final_answer,
            step_count=0,
            tool_failure_count=0,
            task_success=False,
            tool_selection_correct=False,
            approval_required=False,
            approval_correct=False,
            error=str(exc),
        )
    executed_tool_steps = [step for step in result.steps if step.step_type == "tool_call"]
    actual_tools = [step.tool_name for step in executed_tool_steps if step.tool_name]
    if result.pending_approval is not None:
        actual_tools.append(str(result.pending_approval["tool_name"]))
    tool_failure_count = sum(1 for step in executed_tool_steps if step.status == "failed")
    approval_required = result.pending_approval is not None
    final_answer_correct = (
        result.final_answer == case.expected_final_answer if case.expected_final_answer is not None else True
    )
    task_success = (
        result.status == case.expected_status
        and tool_failure_count == case.expected_tool_failures
        and final_answer_correct
    )
    approval_correct = approval_required == case.expects_approval

    return EvaluationResult(
        case_id=case.case_id,
        category=case.category,
        status=result.status,
        actual_tools=actual_tools,
        expected_tools=case.expected_tools,
        final_answer=result.final_answer,
        expected_final_answer=case.expected_final_answer,
        step_count=len(result.steps),
        tool_failure_count=tool_failure_count,
        task_success=task_success,
        tool_selection_correct=actual_tools == case.expected_tools,
        approval_required=approval_required,
        approval_correct=approval_correct,
        executed_tool_count=len(executed_tool_steps),
        error=result.error,
    )


class EvaluationScriptExhausted(RuntimeError):
    pass


class ScriptedEvaluationProvider:
    def __init__(self, script: list[dict[str, Any]]) -> None:
        self._script = list(script)
        self._index = 0

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LlmMessage:
        if self._index >= len(self._script):
            raise EvaluationScriptExhausted("Evaluation script exhausted.")
        action = self._script[self._index]
        self._index += 1
        if action["type"] == "final":
            return LlmMessage(role="assistant", content=str(action["content"]))
        if action["type"] == "tool_call":
            return LlmMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    {
                        "id": f"eval_call_{self._index}",
                        "type": "function",
                        "function": {
                            "name": str(action["tool_name"]),
                            "arguments": json.dumps(action["arguments"]),
                        },
                    }
                ],
            )
        raise ValueError(f"Unsupported evaluation script action: {action['type']}")


class EvaluationSensitiveEchoTool:
    name = "eval_sensitive_echo"
    description = "Echo an evaluation value after approval."
    requires_approval = True
    parameters = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
    }

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(ok=True, output={"echo": str(arguments["value"])})


def _calculator_tool(calculator_mode: str) -> CalculatorTool | McpCalculatorTool:
    if calculator_mode == "local":
        return CalculatorTool()
    if calculator_mode == "mcp":
        return McpCalculatorTool()
    raise ValueError(
        f"Unsupported calculator mode: {calculator_mode}. Expected 'local' or 'mcp'."
    )


def _evaluation_registry(calculator_mode: str = "local") -> ToolRegistry:
    return ToolRegistry(
        [
            _calculator_tool(calculator_mode),
            StubWebSearchTool(),
            EvaluationSensitiveEchoTool(),
        ]
    )


def evaluation_tool_metadata(calculator_mode: str = "local") -> list[dict[str, object]]:
    return _evaluation_registry(calculator_mode=calculator_mode).metadata()
