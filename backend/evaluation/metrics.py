from dataclasses import dataclass
from typing import Any

from backend.evaluation.harness import EvaluationResult


@dataclass(frozen=True)
class EvaluationSummary:
    total_cases: int
    evaluated_cases: int
    skipped_cases: int
    task_success_rate: float
    tool_selection_accuracy: float
    average_steps: float
    tool_failure_rate: float
    approval_accuracy: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_cases": self.total_cases,
            "evaluated_cases": self.evaluated_cases,
            "skipped_cases": self.skipped_cases,
            "metrics": {
                "task_success_rate": self.task_success_rate,
                "tool_selection_accuracy": self.tool_selection_accuracy,
                "average_steps": self.average_steps,
                "tool_failure_rate": self.tool_failure_rate,
                "approval_accuracy": self.approval_accuracy,
            },
        }


def summarize_evaluation_results(results: list[EvaluationResult]) -> EvaluationSummary:
    evaluated = [result for result in results if result.status != "skipped"]
    skipped_count = len(results) - len(evaluated)
    tool_steps = sum(result.executed_tool_count for result in evaluated)
    tool_failures = sum(result.tool_failure_count for result in evaluated)
    return EvaluationSummary(
        total_cases=len(results),
        evaluated_cases=len(evaluated),
        skipped_cases=skipped_count,
        task_success_rate=_ratio([result.task_success for result in evaluated]),
        tool_selection_accuracy=_ratio([result.tool_selection_correct for result in evaluated]),
        average_steps=_rounded_average([result.step_count for result in evaluated]),
        tool_failure_rate=round(tool_failures / tool_steps, 2) if tool_steps else 0.0,
        approval_accuracy=_ratio([result.approval_correct for result in evaluated]),
    )


def _ratio(values: list[bool | None]) -> float:
    evaluated = [value for value in values if value is not None]
    if not evaluated:
        return 0.0
    return round(sum(1 for value in evaluated if value) / len(evaluated), 2)


def _rounded_average(values: list[int]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)
