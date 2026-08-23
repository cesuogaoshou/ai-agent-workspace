from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from backend.app.services.run_store import InMemoryRunStore
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


def test_sqlalchemy_run_store_allocates_unique_run_ids_concurrently(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runs.sqlite3'}"
    store = SqlAlchemyRunStore(database_url)

    with ThreadPoolExecutor(max_workers=12) as executor:
        runs = list(executor.map(lambda task: store.create_run(task), [f"task {index}" for index in range(30)]))

    run_ids = [run["id"] for run in runs]
    assert len(set(run_ids)) == 30
    assert sorted(run_ids, key=lambda run_id: int(run_id.removeprefix("run_"))) == [
        f"run_{index}" for index in range(1, 31)
    ]


@pytest.mark.parametrize("store_factory", [InMemoryRunStore, SqlAlchemyRunStore])
def test_run_store_rejects_event_run_id_mismatch(
    tmp_path: Path,
    store_factory: type[InMemoryRunStore] | type[SqlAlchemyRunStore],
) -> None:
    store = store_factory() if store_factory is InMemoryRunStore else store_factory(f"sqlite:///{tmp_path / 'runs.sqlite3'}")
    run = store.create_run(task="hello")

    with pytest.raises(ValueError, match="Event run_id must match target run_id."):
        store.append_event(
            run["id"],
            PublicRunEvent(
                run_id="run_other",
                event_type="status_change",
                sequence=1,
                payload={"status": "running"},
            ),
        )


def test_sqlalchemy_run_store_lists_runs_in_creation_order_after_ten_runs(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runs.sqlite3'}"
    store = SqlAlchemyRunStore(database_url)

    for index in range(12):
        store.create_run(task=f"task {index}")

    assert [run["id"] for run in store.list_runs()] == [f"run_{index}" for index in range(1, 13)]
