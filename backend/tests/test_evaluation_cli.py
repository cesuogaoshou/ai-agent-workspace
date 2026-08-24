import json
import subprocess
import sys


def test_evaluation_cli_prints_json_summary() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "backend.evaluation.run"],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["metadata"]["dataset"] == {
        "name": "v0.7-agent-evaluation",
        "case_count": 7,
    }
    assert payload["metadata"]["runtime"] == "langgraph_agent_loop"
    assert payload["metadata"]["provider"] == "scripted_evaluation_provider"
    assert payload["metadata"]["max_steps"] == 8
    assert payload["metadata"]["tool_selection_metric"] == "exact_sequence"
    assert [tool["name"] for tool in payload["metadata"]["tools"]] == [
        "calculator",
        "eval_sensitive_echo",
        "web_search",
    ]
    assert payload["summary"]["total_cases"] == 7
    assert payload["summary"]["evaluated_cases"] == 6
    assert payload["results"][0]["case_id"] == "no_tool_direct_answer"
    assert payload["results"][-1]["status"] == "skipped"
