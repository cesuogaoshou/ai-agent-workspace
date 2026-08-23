from pathlib import Path

from backend.app.agent.events import PublicRunEvent
from backend.app.services.run_store import SqlAlchemyRunStore


def test_sqlalchemy_run_store_persists_runs_and_events_across_instances(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runs.sqlite3'}"
    first_store = SqlAlchemyRunStore(database_url)
    run = first_store.create_run(task="persist this")

    first_store.append_event(
        run["id"],
        PublicRunEvent(
            run_id=run["id"],
            event_type="status_change",
            sequence=1,
            payload={"status": "running"},
        ),
    )
    first_store.append_event(
        run["id"],
        PublicRunEvent(
            run_id=run["id"],
            event_type="final_answer",
            sequence=2,
            payload={"step_number": 1, "status": "success", "final_answer": "done"},
        ),
    )
    first_store.finish_run(run["id"], status="success", final_answer="done", error=None)

    second_store = SqlAlchemyRunStore(database_url)

    saved = second_store.get_run(run["id"])
    assert saved is not None
    assert saved["task"] == "persist this"
    assert saved["status"] == "success"
    assert saved["final_answer"] == "done"
    assert saved["step_count"] == 1
    assert saved["tool_call_count"] == 0
    assert second_store.list_runs() == [saved]
    assert [event.as_dict() for event in second_store.list_events(run["id"])] == [
        {
            "run_id": run["id"],
            "event_type": "status_change",
            "sequence": 1,
            "payload": {"status": "running"},
            "created_at": second_store.list_events(run["id"])[0].created_at,
        },
        {
            "run_id": run["id"],
            "event_type": "final_answer",
            "sequence": 2,
            "payload": {"step_number": 1, "status": "success", "final_answer": "done"},
            "created_at": second_store.list_events(run["id"])[1].created_at,
        },
    ]


def test_sqlalchemy_run_store_continues_run_ids_after_restart(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runs.sqlite3'}"
    first_store = SqlAlchemyRunStore(database_url)

    first = first_store.create_run(task="first")

    second_store = SqlAlchemyRunStore(database_url)
    second = second_store.create_run(task="second")

    assert first["id"] == "run_1"
    assert second["id"] == "run_2"
