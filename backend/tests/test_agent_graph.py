from typing import Any

from backend.app.agent.graph import AgentGraphRunner, describe_agent_graph
from backend.app.llm.provider import LlmMessage
from backend.app.tools.calculator import CalculatorTool
from backend.app.tools.mcp_calculator import McpCalculatorTool
from backend.app.tools.registry import ToolRegistry


class FinalAnswerProvider:
    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LlmMessage:
        return LlmMessage(role="assistant", content="direct answer")


class ToolCallThenFinalProvider:
    def __init__(self, function_name: str = "calculator", arguments: str = '{"expression":"2+2"}') -> None:
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


def test_agent_graph_description_exposes_v0_4_workflow_shape() -> None:
    description = describe_agent_graph()

    assert description == {
        "nodes": ["agent", "tool"],
        "entrypoint": "agent",
        "conditional_edges": {"agent": ["tool", "__end__"]},
        "edges": {"tool": "agent"},
    }


def test_agent_graph_returns_direct_final_answer() -> None:
    runner = AgentGraphRunner(FinalAnswerProvider(), ToolRegistry([]), max_steps=4)

    result = runner.run("Answer directly.")

    assert result.status == "success"
    assert result.final_answer == "direct answer"
    assert [step.step_type for step in result.steps] == ["final_answer"]


def test_agent_graph_executes_tool_and_returns_final_answer() -> None:
    provider = ToolCallThenFinalProvider()
    runner = AgentGraphRunner(provider, ToolRegistry([CalculatorTool()]), max_steps=4)

    result = runner.run("What is 2+2?")

    assert result.status == "success"
    assert result.final_answer == "Done."
    assert [step.step_type for step in result.steps] == ["tool_call", "final_answer"]
    assert result.steps[0].tool_name == "calculator"
    assert result.steps[0].tool_input == {"expression": "2+2"}
    assert result.steps[0].tool_output == {"result": 4}
    assert provider.messages_seen[1][2] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": '{"result": 4}',
    }


def test_agent_graph_executes_mcp_calculator_tool_and_returns_final_answer() -> None:
    provider = ToolCallThenFinalProvider()
    runner = AgentGraphRunner(provider, ToolRegistry([McpCalculatorTool()]), max_steps=4)

    result = runner.run("What is 2+2?")

    assert result.status == "success"
    assert result.final_answer == "Done."
    assert result.steps[0].step_type == "tool_call"
    assert result.steps[0].tool_name == "calculator"
    assert result.steps[0].tool_input == {"expression": "2+2"}
    assert result.steps[0].tool_output == {"result": 4}
    assert provider.messages_seen[1][2] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": '{"result": 4}',
    }


def test_agent_graph_records_failed_tool_call_and_continues() -> None:
    runner = AgentGraphRunner(
        ToolCallThenFinalProvider(function_name="missing", arguments='{"query":"hello"}'),
        ToolRegistry([CalculatorTool()]),
        max_steps=4,
    )

    result = runner.run("Use a missing tool.")

    assert result.status == "success"
    assert result.final_answer == "Done."
    assert result.steps[0].status == "failed"
    assert result.steps[0].tool_name == "missing"
    assert result.steps[0].tool_input == {"query": "hello"}
    assert result.steps[0].error == "Tool is not registered: missing"


def test_agent_graph_returns_failed_when_max_steps_reached() -> None:
    events: list[dict[str, Any]] = []
    runner = AgentGraphRunner(
        EndlessToolCallProvider(),
        ToolRegistry([CalculatorTool()]),
        max_steps=2,
        on_event=events.append,
    )

    result = runner.run("Keep calculating.")

    assert result.status == "failed"
    assert result.error == "Max steps reached."
    assert [step.step_type for step in result.steps] == ["tool_call", "tool_call"]
    assert [event["event_type"] for event in events] == ["tool_call", "tool_call", "status_change"]
