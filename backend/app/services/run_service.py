from typing import Any

from backend.app.agent.events import PublicRunEvent
from backend.app.agent.loop import AgentLoop
from backend.app.llm.provider import LlmProvider
from backend.app.services.run_store import RunStore
from backend.app.tools.registry import ToolRegistry

PUBLIC_RUN_FAILURE_ERROR = "Agent run failed."


class RunService:
    def __init__(
        self,
        store: RunStore,
        provider: LlmProvider,
        registry: ToolRegistry,
        max_steps: int,
        public_failure_error: str | None = None,
    ) -> None:
        self.store = store
        self.provider = provider
        self.registry = registry
        self.max_steps = max_steps
        self.public_failure_error = public_failure_error

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
        try:
            result = AgentLoop(
                self.provider,
                self.registry,
                self.max_steps,
                on_event=publish,
            ).run(task)
        except Exception as exc:
            public_error = self.public_failure_error or str(exc)
            publish(
                {
                    "event_type": "status_change",
                    "payload": {"status": "failed", "error": public_error},
                }
            )
            self.store.finish_run(
                run["id"],
                status="failed",
                final_answer=None,
                error=public_error,
            )
            raise
        if result.status == "waiting_for_approval":
            if result.pending_approval is None or result.resume_state is None:
                raise RuntimeError("Waiting run is missing approval state.")
            self.store.set_waiting_for_approval(
                run["id"],
                pending_approval=result.pending_approval,
                resume_state=result.resume_state,
            )
            waiting = self.store.get_run(run["id"])
            if waiting is None:
                raise RuntimeError("Run disappeared from store.")
            waiting["steps"] = [event.as_dict() for event in self.store.list_events(run["id"])]
            return waiting
        self.store.finish_run(
            run["id"],
            status=result.status,
            final_answer=result.final_answer,
            error=result.error,
        )
        return self._run_with_events(run["id"])

    def approve_run(self, run_id: str, approval_id: str) -> dict[str, Any]:
        run = self._get_waiting_run(run_id, approval_id)
        sequence = len(self.store.list_events(run_id))

        def publish(event: dict[str, Any]) -> None:
            nonlocal sequence
            sequence += 1
            self.store.append_event(
                run_id,
                PublicRunEvent(
                    run_id=run_id,
                    event_type=str(event["event_type"]),
                    sequence=sequence,
                    payload=dict(event["payload"]),
                ),
            )

        publish(
            {
                "event_type": "approval_decision",
                "payload": {"approval_id": approval_id, "decision": "approved"},
            }
        )
        publish({"event_type": "status_change", "payload": {"status": "running"}})
        result = AgentLoop(
            self.provider,
            self.registry,
            self.max_steps,
            on_event=publish,
        ).resume(run["resume_state"], approval_id=approval_id)
        self.store.finish_run(
            run_id,
            status=result.status,
            final_answer=result.final_answer,
            error=result.error,
        )
        return self._run_with_events(run_id)

    def reject_run(self, run_id: str, approval_id: str, reason: str | None = None) -> dict[str, Any]:
        self._get_waiting_run(run_id, approval_id)
        public_reason = reason.strip() if reason and reason.strip() else "Approval rejected."
        sequence = len(self.store.list_events(run_id))

        def publish(event: dict[str, Any]) -> None:
            nonlocal sequence
            sequence += 1
            self.store.append_event(
                run_id,
                PublicRunEvent(
                    run_id=run_id,
                    event_type=str(event["event_type"]),
                    sequence=sequence,
                    payload=dict(event["payload"]),
                ),
            )

        publish(
            {
                "event_type": "approval_decision",
                "payload": {
                    "approval_id": approval_id,
                    "decision": "rejected",
                    "reason": public_reason,
                },
            }
        )
        publish(
            {
                "event_type": "status_change",
                "payload": {"status": "rejected", "error": public_reason},
            }
        )
        self.store.finish_run(run_id, status="rejected", final_answer=None, error=public_reason)
        return self._run_with_events(run_id)

    def _get_waiting_run(self, run_id: str, approval_id: str) -> dict[str, Any]:
        run = self.store.get_run(run_id)
        if run is None:
            raise KeyError(f"Unknown run id: {run_id}")
        if run["status"] != "waiting_for_approval":
            raise ValueError("Run is not waiting for approval.")
        pending = run.get("pending_approval")
        if not isinstance(pending, dict) or pending.get("approval_id") != approval_id:
            raise ValueError("Approval id does not match pending approval.")
        if run.get("resume_state") is None:
            raise ValueError("Run is missing resume state.")
        return run

    def _run_with_events(self, run_id: str) -> dict[str, Any]:
        completed = self.store.get_run(run_id)
        if completed is None:
            raise RuntimeError("Run disappeared from store.")
        completed["steps"] = [event.as_dict() for event in self.store.list_events(run_id)]
        return completed
