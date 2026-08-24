from pathlib import Path

from backend.evaluation.dataset import EvaluationCase, load_evaluation_cases


def test_load_evaluation_cases_returns_fixed_v0_7_dataset() -> None:
    cases = load_evaluation_cases()

    assert [case.case_id for case in cases] == [
        "no_tool_direct_answer",
        "calculator_success",
        "web_search_stub_success",
        "multi_tool_calculator_and_search",
        "tool_failure_unknown_tool",
        "approval_required_sensitive_tool",
        "rag_deferred",
    ]
    assert all(isinstance(case, EvaluationCase) for case in cases)


def test_load_evaluation_cases_exposes_expected_tools_and_skip_reason() -> None:
    cases = {case.case_id: case for case in load_evaluation_cases()}

    assert cases["no_tool_direct_answer"].expected_tools == []
    assert cases["no_tool_direct_answer"].expected_final_answer == "Hello from the evaluation harness."
    assert cases["calculator_success"].expected_tools == ["calculator"]
    assert cases["calculator_success"].expected_final_answer == "The result is 42."
    assert cases["web_search_stub_success"].expected_tools == ["web_search"]
    assert cases["multi_tool_calculator_and_search"].expected_tools == [
        "calculator",
        "web_search",
    ]
    assert cases["tool_failure_unknown_tool"].expected_tool_failures == 1
    assert cases["approval_required_sensitive_tool"].expected_status == "waiting_for_approval"
    assert cases["approval_required_sensitive_tool"].expected_tools == ["eval_sensitive_echo"]
    assert cases["approval_required_sensitive_tool"].expects_approval is True
    assert cases["rag_deferred"].skip_reason == "RAG tool is outside the current v0.7 scope."


def test_load_evaluation_cases_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.json"
    dataset.write_text(
        """[
          {
            "case_id": "duplicate",
            "category": "no_tool",
            "task": "Answer directly.",
            "script": [{"type": "final", "content": "done"}],
            "expected_status": "success",
            "expected_tools": [],
            "expected_tool_failures": 0,
            "expects_approval": false,
            "expected_final_answer": "done"
          },
          {
            "case_id": "duplicate",
            "category": "no_tool",
            "task": "Answer directly again.",
            "script": [{"type": "final", "content": "done"}],
            "expected_status": "success",
            "expected_tools": [],
            "expected_tool_failures": 0,
            "expects_approval": false,
            "expected_final_answer": "done"
          }
        ]""",
        encoding="utf-8",
    )

    try:
        load_evaluation_cases(dataset)
    except ValueError as exc:
        assert str(exc) == "Duplicate evaluation case id: duplicate"
    else:
        raise AssertionError("Expected duplicate case ids to be rejected.")


def test_load_evaluation_cases_rejects_malformed_boolean_fields(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.json"
    dataset.write_text(
        """[
          {
            "case_id": "bad_bool",
            "category": "no_tool",
            "task": "Answer directly.",
            "script": [{"type": "final", "content": "done"}],
            "expected_status": "success",
            "expected_tools": [],
            "expected_tool_failures": 0,
            "expects_approval": "false",
            "expected_final_answer": "done"
          }
        ]""",
        encoding="utf-8",
    )

    try:
        load_evaluation_cases(dataset)
    except ValueError as exc:
        assert "expects_approval must be a boolean" in str(exc)
    else:
        raise AssertionError("Expected malformed boolean field to be rejected.")


def test_load_evaluation_cases_rejects_malformed_script_actions(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.json"
    dataset.write_text(
        """[
          {
            "case_id": "bad_script",
            "category": "calculator",
            "task": "Calculate.",
            "script": [{"type": "tool_call", "tool_name": "calculator"}],
            "expected_status": "success",
            "expected_tools": ["calculator"],
            "expected_tool_failures": 0,
            "expects_approval": false,
            "expected_final_answer": "done"
          }
        ]""",
        encoding="utf-8",
    )

    try:
        load_evaluation_cases(dataset)
    except ValueError as exc:
        assert "tool_call script action requires tool_name and arguments" in str(exc)
    else:
        raise AssertionError("Expected malformed script action to be rejected.")
