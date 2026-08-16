from typing import Any

from backend.app.agent.loop import AgentLoop
from backend.app.llm.provider import LlmMessage
from backend.app.tools.calculator import CalculatorTool
from backend.app.tools.registry import ToolRegistry


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


def test_agent_loop_executes_tool_and_returns_final_answer() -> None:
    loop = AgentLoop(FakeProvider(), ToolRegistry([CalculatorTool()]), max_steps=4)
    result = loop.run("What is 2+2?")

    assert result.status == "success"
    assert result.final_answer == "The result is 4."
    assert [step.step_type for step in result.steps] == ["tool_call", "final_answer"]
