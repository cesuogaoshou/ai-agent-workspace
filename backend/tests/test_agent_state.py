from typing import Any

from backend.app.agent.state import TraceStep, deserialize_resume_state, serialize_resume_state


def test_resume_state_round_trips_trace_steps() -> None:
    state: dict[str, Any] = {
        "task": "needs approval",
        "messages": [{"role": "user", "content": "needs approval"}],
        "steps": [
            TraceStep(
                step_number=1,
                step_type="tool_call",
                status="success",
                tool_name="calculator",
                tool_input={"expression": "2+2"},
                tool_output={"result": 4},
            )
        ],
        "current_step": 2,
        "latest_response": object(),
        "pending_tool_calls": [
            {
                "id": "call_2",
                "type": "function",
                "function": {"name": "sensitive_echo", "arguments": '{"value":"hello"}'},
            }
        ],
        "status": "waiting_for_approval",
        "final_answer": None,
        "error": None,
        "pending_approval": {
            "approval_id": "approval_2_call_2",
            "step_number": 2,
            "tool_call_id": "call_2",
            "tool_name": "sensitive_echo",
            "tool_input": {"value": "hello"},
        },
        "approved_approval_id": "approval_2_call_2",
        "resume_from_tool": True,
    }

    serialized = serialize_resume_state(state)
    restored = deserialize_resume_state(serialized)

    assert serialized["latest_response"] is None
    assert serialized["approved_approval_id"] is None
    assert serialized["resume_from_tool"] is False
    assert restored["steps"] == state["steps"]
    assert restored["pending_tool_calls"] == state["pending_tool_calls"]
    assert restored["pending_approval"] == state["pending_approval"]


def test_resume_state_deserializes_missing_optional_runtime_fields() -> None:
    restored = deserialize_resume_state(
        {
            "task": "legacy approval",
            "messages": [{"role": "user", "content": "legacy approval"}],
            "steps": [],
            "current_step": 1,
            "pending_tool_calls": [],
            "status": "waiting_for_approval",
        }
    )

    assert restored["task"] == "legacy approval"
    assert restored["latest_response"] is None
    assert restored["final_answer"] is None
    assert restored["error"] is None
    assert restored["pending_approval"] is None
    assert restored["approved_approval_id"] is None
    assert restored["resume_from_tool"] is False
