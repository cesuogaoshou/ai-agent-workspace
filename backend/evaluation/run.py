import json

from backend.evaluation.dataset import load_evaluation_cases
from backend.evaluation.harness import evaluation_tool_metadata, run_evaluation_cases
from backend.evaluation.metrics import summarize_evaluation_results

DEFAULT_MAX_STEPS = 8
DEFAULT_CALCULATOR_MODE = "local"


def main() -> None:
    cases = load_evaluation_cases()
    results = run_evaluation_cases(
        cases,
        max_steps=DEFAULT_MAX_STEPS,
        calculator_mode=DEFAULT_CALCULATOR_MODE,
    )
    summary = summarize_evaluation_results(results)
    print(
        json.dumps(
            {
                "metadata": {
                    "dataset": {
                        "name": "v0.7-agent-evaluation",
                        "case_count": len(cases),
                    },
                    "runtime": "langgraph_agent_loop",
                    "provider": "scripted_evaluation_provider",
                    "max_steps": DEFAULT_MAX_STEPS,
                    "tool_selection_metric": "exact_sequence",
                    "tool_modes": {"calculator": DEFAULT_CALCULATOR_MODE},
                    "tools": evaluation_tool_metadata(
                        calculator_mode=DEFAULT_CALCULATOR_MODE
                    ),
                },
                "summary": summary.as_dict(),
                "results": [result.as_dict() for result in results],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
