import pytest

from backend.evaluation.dataset import load_evaluation_cases
from backend.evaluation.harness import evaluation_tool_metadata, run_evaluation_cases


def test_run_evaluation_cases_executes_fixed_dataset_with_scripted_provider() -> None:
    results = run_evaluation_cases(load_evaluation_cases())
    by_id = {result.case_id: result for result in results}

    assert by_id["no_tool_direct_answer"].status == "success"
    assert by_id["no_tool_direct_answer"].actual_tools == []
    assert by_id["calculator_success"].actual_tools == ["calculator"]
    assert by_id["web_search_stub_success"].actual_tools == ["web_search"]
    assert by_id["multi_tool_calculator_and_search"].actual_tools == [
        "calculator",
        "web_search",
    ]
    assert by_id["tool_failure_unknown_tool"].tool_failure_count == 1
    assert by_id["approval_required_sensitive_tool"].status == "waiting_for_approval"
    assert by_id["approval_required_sensitive_tool"].actual_tools == ["eval_sensitive_echo"]
    assert by_id["approval_required_sensitive_tool"].approval_required is True
    assert by_id["rag_deferred"].status == "skipped"
    assert by_id["rag_deferred"].skip_reason == "RAG tool is outside the current v0.7 scope."


def test_run_evaluation_cases_marks_success_against_expected_outcomes() -> None:
    results = run_evaluation_cases(load_evaluation_cases())
    by_id = {result.case_id: result for result in results}

    assert by_id["no_tool_direct_answer"].task_success is True
    assert by_id["calculator_success"].tool_selection_correct is True
    assert by_id["web_search_stub_success"].tool_selection_correct is True
    assert by_id["multi_tool_calculator_and_search"].tool_selection_correct is True
    assert by_id["tool_failure_unknown_tool"].task_success is True
    assert by_id["approval_required_sensitive_tool"].approval_correct is True
    assert by_id["rag_deferred"].task_success is None


def test_run_evaluation_cases_marks_wrong_final_answer_as_unsuccessful() -> None:
    case = load_evaluation_cases()[1]
    wrong_answer_case = case.__class__(
        case_id="wrong_answer",
        category=case.category,
        task=case.task,
        script=[
            {
                "type": "tool_call",
                "tool_name": "calculator",
                "arguments": {"expression": "21*2"},
            },
            {"type": "final", "content": "The result is 41."},
        ],
        expected_status=case.expected_status,
        expected_tools=case.expected_tools,
        expected_tool_failures=case.expected_tool_failures,
        expects_approval=case.expects_approval,
        expected_final_answer="The result is 42.",
    )

    result = run_evaluation_cases([wrong_answer_case])[0]

    assert result.status == "success"
    assert result.final_answer == "The result is 41."
    assert result.task_success is False


def test_run_evaluation_cases_marks_exhausted_script_as_failed() -> None:
    case = load_evaluation_cases()[1]
    exhausted_case = case.__class__(
        case_id="exhausted",
        category=case.category,
        task=case.task,
        script=[
            {
                "type": "tool_call",
                "tool_name": "calculator",
                "arguments": {"expression": "21*2"},
            }
        ],
        expected_status=case.expected_status,
        expected_tools=case.expected_tools,
        expected_tool_failures=case.expected_tool_failures,
        expects_approval=case.expects_approval,
        expected_final_answer="The result is 42.",
    )

    result = run_evaluation_cases([exhausted_case])[0]

    assert result.status == "failed"
    assert result.error == "Evaluation script exhausted."
    assert result.task_success is False


def test_evaluation_tool_metadata_defaults_to_local_calculator() -> None:
    metadata = evaluation_tool_metadata()
    calculator = next(tool for tool in metadata if tool["name"] == "calculator")

    assert calculator["description"] == "Evaluate deterministic arithmetic expressions."


def test_evaluation_tool_metadata_can_select_mcp_calculator() -> None:
    metadata = evaluation_tool_metadata(calculator_mode="mcp")
    calculator = next(tool for tool in metadata if tool["name"] == "calculator")

    assert (
        calculator["description"]
        == "Evaluate deterministic arithmetic expressions through a local MCP server."
    )


def test_evaluation_tool_metadata_rejects_unknown_calculator_mode() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported calculator mode: unknown. Expected 'local' or 'mcp'.",
    ):
        evaluation_tool_metadata(calculator_mode="unknown")
