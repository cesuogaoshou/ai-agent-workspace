from backend.evaluation.dataset import load_evaluation_cases
from backend.evaluation.harness import EvaluationResult, run_evaluation_cases
from backend.evaluation.metrics import summarize_evaluation_results


def test_summarize_evaluation_results_reports_basic_v0_7_metrics() -> None:
    results = run_evaluation_cases(load_evaluation_cases())

    summary = summarize_evaluation_results(results)

    assert summary.total_cases == 7
    assert summary.evaluated_cases == 6
    assert summary.skipped_cases == 1
    assert summary.task_success_rate == 1.0
    assert summary.tool_selection_accuracy == 1.0
    assert summary.tool_failure_rate == 0.2
    assert summary.approval_accuracy == 1.0
    assert summary.average_steps == 1.67


def test_summarize_evaluation_results_serializes_to_plain_dict() -> None:
    results = run_evaluation_cases(load_evaluation_cases())

    summary = summarize_evaluation_results(results).as_dict()

    assert summary["total_cases"] == 7
    assert summary["evaluated_cases"] == 6
    assert summary["skipped_cases"] == 1
    assert summary["metrics"]["task_success_rate"] == 1.0
    assert summary["metrics"]["average_steps"] == 1.67


def test_summarize_evaluation_results_counts_approval_false_positives() -> None:
    results = [
        EvaluationResult(
            case_id="false_positive",
            category="no_tool",
            status="waiting_for_approval",
            actual_tools=["eval_sensitive_echo"],
            expected_tools=[],
            final_answer=None,
            expected_final_answer=None,
            step_count=0,
            tool_failure_count=0,
            task_success=False,
            tool_selection_correct=False,
            approval_required=True,
            approval_correct=False,
        ),
        EvaluationResult(
            case_id="true_negative",
            category="no_tool",
            status="success",
            actual_tools=[],
            expected_tools=[],
            final_answer="done",
            expected_final_answer="done",
            step_count=1,
            tool_failure_count=0,
            task_success=True,
            tool_selection_correct=True,
            approval_required=False,
            approval_correct=True,
        ),
    ]

    summary = summarize_evaluation_results(results)

    assert summary.approval_accuracy == 0.5
