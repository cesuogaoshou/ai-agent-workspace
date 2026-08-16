from backend.app.agent.events import PublicRunEvent
from backend.app.services.run_store import InMemoryRunStore


def test_run_store_saves_run_and_events() -> None:
    store = InMemoryRunStore()
    run = store.create_run(task="hello")
    event = PublicRunEvent(
        run_id=run["id"],
        event_type="status_change",
        sequence=1,
        payload={"status": "running"},
    )

    store.append_event(run["id"], event)
    store.finish_run(run["id"], status="success", final_answer="done", error=None)

    saved = store.get_run(run["id"])
    assert saved["task"] == "hello"
    assert saved["status"] == "success"
    assert saved["final_answer"] == "done"
    assert store.list_events(run["id"]) == [event]
