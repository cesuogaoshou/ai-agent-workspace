from typing import Any

from backend.app.agent.graph import AgentGraphRunner
from backend.app.llm.provider import LlmMessage
from backend.app.tools.base import ToolResult
from backend.app.tools.registry import ToolRegistry


class SensitiveEchoTool:
    name = "sensitive_echo"
    description = "Echo input after approval."
    requires_approval = True
    parameters = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
    }

    def __init__(self) -> None:
        self.executions: list[dict[str, Any]] = []

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        self.executions.append(arguments)
        return ToolResult(ok=True, output={"echo": arguments["value"]})


class ToolCallThenFinalProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.messages_seen: list[list[dict[str, Any]]] = []

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LlmMessage:
        self.calls += 1
        self.messages_seen.append([message.copy() for message in messages])
        if self.calls == 1:
            return LlmMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "sensitive_echo",
                            "arguments": '{"value":"hello"}',
                        },
                    }
                ],
            )
        return LlmMessage(role="assistant", content="approved done")


class TwoSensitiveToolCallsThenFinalProvider:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LlmMessage:
        self.calls += 1
        if self.calls == 1:
            return LlmMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "sensitive_echo",
                            "arguments": '{"value":"first"}',
                        },
                    },
                    {
                        "id": "call_2",
                        "type": "function",
                        "function": {
                            "name": "sensitive_echo",
                            "arguments": '{"value":"second"}',
                        },
                    },
                ],
            )
        return LlmMessage(role="assistant", content="approved done")


def test_agent_graph_waits_for_approval_before_sensitive_tool_executes() -> None:
    events: list[dict[str, Any]] = []
    tool = SensitiveEchoTool()
    runner = AgentGraphRunner(
        ToolCallThenFinalProvider(),
        ToolRegistry([tool]),
        max_steps=4,
        on_event=events.append,
    )

    result = runner.run("Use a sensitive tool.")

    assert result.status == "waiting_for_approval"
    assert result.final_answer is None
    assert result.pending_approval == {
        "approval_id": "approval_1_call_1",
        "step_number": 1,
        "tool_call_id": "call_1",
        "tool_name": "sensitive_echo",
        "tool_input": {"value": "hello"},
    }
    assert result.resume_state is not None
    assert tool.executions == []
    assert [event["event_type"] for event in events] == [
        "approval_required",
        "status_change",
    ]


def test_agent_graph_resumes_after_sensitive_tool_approval() -> None:
    tool = SensitiveEchoTool()
    provider = ToolCallThenFinalProvider()
    runner = AgentGraphRunner(provider, ToolRegistry([tool]), max_steps=4)
    waiting = runner.run("Use a sensitive tool.")

    result = runner.resume(waiting.resume_state, approval_id="approval_1_call_1")

    assert result.status == "success"
    assert result.final_answer == "approved done"
    assert tool.executions == [{"value": "hello"}]
    assert [step.step_type for step in result.steps] == ["tool_call", "final_answer"]
    assert result.steps[0].tool_name == "sensitive_echo"
    assert result.steps[0].tool_output == {"echo": "hello"}
    assert provider.messages_seen[1][2] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": '{"echo": "hello"}',
    }


def test_agent_graph_requires_separate_approval_for_each_sensitive_tool_call() -> None:
    tool = SensitiveEchoTool()
    runner = AgentGraphRunner(
        TwoSensitiveToolCallsThenFinalProvider(),
        ToolRegistry([tool]),
        max_steps=4,
    )
    waiting = runner.run("Use two sensitive tools.")

    second_waiting = runner.resume(waiting.resume_state, approval_id="approval_1_call_1")

    assert second_waiting.status == "waiting_for_approval"
    assert second_waiting.pending_approval == {
        "approval_id": "approval_1_call_2",
        "step_number": 1,
        "tool_call_id": "call_2",
        "tool_name": "sensitive_echo",
        "tool_input": {"value": "second"},
    }
    assert tool.executions == [{"value": "first"}]
