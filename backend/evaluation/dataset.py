import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_DATASET_PATH = Path(__file__).with_name("cases.json")


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    category: str
    task: str
    script: list[dict[str, Any]]
    expected_status: str
    expected_tools: list[str]
    expected_tool_failures: int
    expects_approval: bool
    expected_final_answer: str | None = None
    skip_reason: str | None = None


def load_evaluation_cases(path: Path | None = None) -> list[EvaluationCase]:
    dataset_path = path or DEFAULT_DATASET_PATH
    raw_cases = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(raw_cases, list):
        raise ValueError("Evaluation dataset must be a JSON list.")
    cases = [_case_from_dict(raw_case) for raw_case in raw_cases]
    _ensure_unique_case_ids(cases)
    return cases


def _case_from_dict(raw_case: dict[str, Any]) -> EvaluationCase:
    if not isinstance(raw_case, dict):
        raise ValueError("Evaluation case must be a JSON object.")
    _validate_case_fields(raw_case)
    return EvaluationCase(
        case_id=raw_case["case_id"],
        category=raw_case["category"],
        task=raw_case["task"],
        script=raw_case["script"],
        expected_status=raw_case["expected_status"],
        expected_tools=raw_case["expected_tools"],
        expected_tool_failures=raw_case["expected_tool_failures"],
        expects_approval=raw_case["expects_approval"],
        expected_final_answer=raw_case.get("expected_final_answer"),
        skip_reason=raw_case.get("skip_reason"),
    )


def _ensure_unique_case_ids(cases: list[EvaluationCase]) -> None:
    seen: set[str] = set()
    for case in cases:
        if case.case_id in seen:
            raise ValueError(f"Duplicate evaluation case id: {case.case_id}")
        seen.add(case.case_id)


def _validate_case_fields(raw_case: dict[str, Any]) -> None:
    for field_name in [
        "case_id",
        "category",
        "task",
        "script",
        "expected_status",
        "expected_tools",
        "expected_tool_failures",
        "expects_approval",
    ]:
        if field_name not in raw_case:
            raise ValueError(f"Evaluation case is missing required field: {field_name}")

    for field_name in ["case_id", "category", "task", "expected_status"]:
        if not isinstance(raw_case[field_name], str) or not raw_case[field_name].strip():
            raise ValueError(f"{field_name} must be a non-empty string.")

    if raw_case["expected_status"] not in {"success", "failed", "waiting_for_approval", "skipped", "rejected"}:
        raise ValueError(f"Unsupported expected_status: {raw_case['expected_status']}")
    if not isinstance(raw_case["script"], list):
        raise ValueError("script must be a list.")
    if not isinstance(raw_case["expected_tools"], list) or not all(
        isinstance(tool, str) and tool.strip() for tool in raw_case["expected_tools"]
    ):
        raise ValueError("expected_tools must be a list of non-empty strings.")
    if not isinstance(raw_case["expected_tool_failures"], int) or raw_case["expected_tool_failures"] < 0:
        raise ValueError("expected_tool_failures must be a non-negative integer.")
    if not isinstance(raw_case["expects_approval"], bool):
        raise ValueError("expects_approval must be a boolean.")

    skip_reason = raw_case.get("skip_reason")
    if skip_reason is not None and (not isinstance(skip_reason, str) or not skip_reason.strip()):
        raise ValueError("skip_reason must be a non-empty string when provided.")
    if raw_case["expected_status"] == "skipped" and skip_reason is None:
        raise ValueError("skipped cases require skip_reason.")
    if skip_reason is not None and raw_case["script"]:
        raise ValueError("skipped cases must not define script actions.")

    expected_final_answer = raw_case.get("expected_final_answer")
    if expected_final_answer is not None and (
        not isinstance(expected_final_answer, str) or not expected_final_answer.strip()
    ):
        raise ValueError("expected_final_answer must be a non-empty string when provided.")
    if raw_case["expected_status"] == "success" and expected_final_answer is None:
        raise ValueError("success cases require expected_final_answer.")

    for action in raw_case["script"]:
        _validate_script_action(action)


def _validate_script_action(action: Any) -> None:
    if not isinstance(action, dict):
        raise ValueError("script action must be a JSON object.")
    action_type = action.get("type")
    if action_type == "final":
        if not isinstance(action.get("content"), str):
            raise ValueError("final script action requires string content.")
        return
    if action_type == "tool_call":
        if not isinstance(action.get("tool_name"), str) or not isinstance(action.get("arguments"), dict):
            raise ValueError("tool_call script action requires tool_name and arguments.")
        return
    raise ValueError(f"Unsupported script action type: {action_type}")
