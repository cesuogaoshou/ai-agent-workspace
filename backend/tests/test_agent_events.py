import json

from backend.app.agent.events import PublicRunEvent


def test_public_run_event_serializes_to_sse_message() -> None:
    event = PublicRunEvent(
        run_id="run_1",
        event_type="tool_call",
        sequence=2,
        payload={"tool_name": "calculator", "status": "success"},
    )

    sse_message = event.to_sse()

    assert sse_message.startswith("event: tool_call\ndata: ")
    assert sse_message.endswith("\n\n")

    data = json.loads(sse_message.removeprefix("event: tool_call\ndata: ").removesuffix("\n\n"))
    assert data["run_id"] == "run_1"
    assert data["event_type"] == "tool_call"
    assert data["sequence"] == 2
    assert data["payload"] == {"tool_name": "calculator", "status": "success"}
    assert isinstance(data["created_at"], str)
    assert data["created_at"]
