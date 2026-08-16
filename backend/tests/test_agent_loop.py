from typing import Any

from backend.app.agent.loop import AgentLoop
from backend.app.llm.provider import LlmMessage
from backend.app.tools.calculator import CalculatorTool
from backend.app.tools.registry import ToolRegistry


ARGUMENT_ERROR = "Tool arguments must be a JSON object."


class FakeProvider:
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
                        "function": {"name": "calculator", "arguments": '{"expression":"2+2"}'},
                    }
                ],
            )
        return LlmMessage(role="assistant", content="The result is 4.")


class ToolCallThenFinalProvider:
    def __init__(self, function_name: str, arguments: str) -> None:
        self.calls = 0
        self.function_name = function_name
        self.arguments = arguments
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
                        "function": {"name": self.function_name, "arguments": self.arguments},
                    }
                ],
            )
        return LlmMessage(role="assistant", content="Done.")


class EndlessToolCallProvider:
    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LlmMessage:
        return LlmMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "calculator", "arguments": '{"expression":"2+2"}'},
                }
            ],
        )


def test_agent_loop_executes_tool_and_returns_final_answer() -> None:
    loop = AgentLoop(FakeProvider(), ToolRegistry([CalculatorTool()]), max_steps=4)
    result = loop.run("What is 2+2?")

    assert result.status == "success"
    assert result.final_answer == "The result is 4."
    assert [step.step_type for step in result.steps] == ["tool_call", "final_answer"]


def test_agent_loop_records_failed_tool_call_for_malformed_json_arguments() -> None:
    provider = ToolCallThenFinalProvider("calculator", "{bad json")
    loop = AgentLoop(provider, ToolRegistry([CalculatorTool()]), max_steps=4)
    result = loop.run("What is 2+2?")

    assert result.status == "success"
    assert result.final_answer == "Done."
    assert result.steps[0].step_type == "tool_call"
    assert result.steps[0].status == "failed"
    assert result.steps[0].tool_name == "calculator"
    assert result.steps[0].tool_input is None
    assert result.steps[0].tool_output is None
    assert result.steps[0].error == ARGUMENT_ERROR


def test_agent_loop_records_failed_tool_call_for_non_object_json_arguments() -> None:
    provider = ToolCallThenFinalProvider("calculator", "[]")
    loop = AgentLoop(provider, ToolRegistry([CalculatorTool()]), max_steps=4)
    result = loop.run("What is 2+2?")

    assert result.status == "success"
    assert result.final_answer == "Done."
    assert result.steps[0].status == "failed"
    assert result.steps[0].tool_name == "calculator"
    assert result.steps[0].tool_input is None
    assert result.steps[0].error == ARGUMENT_ERROR


def test_agent_loop_records_unknown_tool_failure_and_continues_to_final_answer() -> None:
    provider = ToolCallThenFinalProvider("missing", '{"query":"hello"}')
    loop = AgentLoop(provider, ToolRegistry([CalculatorTool()]), max_steps=4)
    result = loop.run("Use a missing tool.")

    assert result.status == "success"
    assert result.final_answer == "Done."
    assert result.steps[0].status == "failed"
    assert result.steps[0].tool_name == "missing"
    assert result.steps[0].tool_input == {"query": "hello"}
    assert result.steps[0].error == "Tool is not registered: missing"


def test_agent_loop_records_tool_execution_failure_and_continues_to_final_answer() -> None:
    provider = ToolCallThenFinalProvider("calculator", '{"expression":"__import__(\\"os\\")"}')
    loop = AgentLoop(provider, ToolRegistry([CalculatorTool()]), max_steps=4)
    result = loop.run("Use unsafe calculator input.")

    assert result.status == "success"
    assert result.final_answer == "Done."
    assert result.steps[0].status == "failed"
    assert result.steps[0].tool_name == "calculator"
    assert result.steps[0].tool_input == {"expression": '__import__("os")'}
    assert result.steps[0].error == "Expression contains unsupported syntax."


def test_agent_loop_returns_failed_when_max_steps_reached() -> None:
    loop = AgentLoop(EndlessToolCallProvider(), ToolRegistry([CalculatorTool()]), max_steps=2)
    result = loop.run("Keep calculating.")

    assert result.status == "failed"
    assert result.final_answer is None
    assert result.error == "Max steps reached."
    assert [step.step_type for step in result.steps] == ["tool_call", "tool_call"]


def test_agent_loop_sends_tool_response_in_message_history() -> None:
    provider = ToolCallThenFinalProvider("calculator", '{"expression":"2+2"}')
    loop = AgentLoop(provider, ToolRegistry([CalculatorTool()]), max_steps=4)
    loop.run("What is 2+2?")

    second_call_messages = provider.messages_seen[1]
    assert second_call_messages[0] == {"role": "user", "content": "What is 2+2?"}
    assert second_call_messages[1]["role"] == "assistant"
    assert second_call_messages[1]["tool_calls"][0]["id"] == "call_1"
    assert second_call_messages[2] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": '{"result": 4}',
    }
