from typing import Any

from backend.app.agent.events import PublicRunEvent
from backend.app.agent.loop import AgentLoop
from backend.app.llm.provider import LlmProvider
from backend.app.services.run_store import InMemoryRunStore
from backend.app.tools.registry import ToolRegistry


class RunService:
    def __init__(
        self,
        store: InMemoryRunStore,
        provider: LlmProvider,
        registry: ToolRegistry,
        max_steps: int,
    ) -> None:
        self.store = store
        self.provider = provider
        self.registry = registry
        self.max_steps = max_steps

    def create_run(self, task: str) -> dict[str, Any]:
        run = self.store.create_run(task)
        sequence = 0

        def publish(event: dict[str, Any]) -> None:
            nonlocal sequence
            sequence += 1
            self.store.append_event(
                run["id"],
                PublicRunEvent(
                    run_id=run["id"],
                    event_type=str(event["event_type"]),
                    sequence=sequence,
                    payload=dict(event["payload"]),
                ),
            )

        publish({"event_type": "status_change", "payload": {"status": "running"}})
        result = AgentLoop(self.provider, self.registry, self.max_steps, on_event=publish).run(task)
        self.store.finish_run(
            run["id"],
            status=result.status,
            final_answer=result.final_answer,
            error=result.error,
        )
        completed = self.store.get_run(run["id"])
        if completed is None:
            raise RuntimeError("Run disappeared from in-memory store.")
        completed["steps"] = [event.as_dict() for event in self.store.list_events(run["id"])]
        return completed
