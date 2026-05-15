from services import tasks
from services.tasklists import PERSONAL_TL, REFERENCE_TL, WAITING_FOR_TL, WORK_TL


def test_create_item_from_classification_dedupes_by_marker(monkeypatch) -> None:
    existing = {"id": "existing-1", "notes": "inbox_hash:abc123"}

    def fake_list_tasks(tasklist: str) -> list[dict]:
        return [existing]

    monkeypatch.setattr(tasks, "_build_idempotency_hash", lambda source_name, item: "abc123")
    monkeypatch.setattr(tasks, "list_tasks", fake_list_tasks)

    called = {"create_task": 0}

    def fake_create_task(*, tasklist: str, title: str, notes: str):
        called["create_task"] += 1
        return {"id": "new-1"}

    monkeypatch.setattr(tasks, "create_task", fake_create_task)

    result = tasks.create_item_from_classification(
        source_name="inbox.json",
        item={"type": "task", "title": "T", "description": "D"},
    )

    assert result["status"] == "deduped"
    assert result["task_id"] == "existing-1"
    assert called["create_task"] == 0


def test_english_task_routes_to_work(monkeypatch) -> None:
    monkeypatch.setattr(tasks, "list_tasks", lambda tasklist: [])
    monkeypatch.setattr(tasks, "_build_idempotency_hash", lambda source_name, item: "hash-en")

    captured: dict[str, str] = {}

    def fake_create_task(*, tasklist: str, title: str, notes: str):
        captured["tasklist"] = tasklist
        return {"id": "task-en-1"}

    monkeypatch.setattr(tasks, "create_task", fake_create_task)

    result = tasks.create_item_from_classification(
        source_name="inbox.json",
        item={"type": "task", "title": "Buy milk", "description": ""},
        language="en",
    )

    assert result["status"] == "created"
    assert captured["tasklist"] == WORK_TL


def test_english_waiting_for_routes_to_waiting_list(monkeypatch) -> None:
    monkeypatch.setattr(tasks, "list_tasks", lambda tasklist: [])
    monkeypatch.setattr(tasks, "_build_idempotency_hash", lambda source_name, item: "hash-wf")

    captured: dict[str, str] = {}

    def fake_create_task(*, tasklist: str, title: str, notes: str):
        captured["tasklist"] = tasklist
        return {"id": "task-wf-1"}

    monkeypatch.setattr(tasks, "create_task", fake_create_task)

    result = tasks.create_item_from_classification(
        source_name="inbox.json",
        item={"type": "waiting_for", "title": "Reply from Bob", "description": ""},
        language="en",
    )

    assert result["status"] == "created"
    assert captured["tasklist"] == WAITING_FOR_TL


def test_english_reference_routes_to_reference_list(monkeypatch) -> None:
    monkeypatch.setattr(tasks, "list_tasks", lambda tasklist: [])
    monkeypatch.setattr(tasks, "_build_idempotency_hash", lambda source_name, item: "hash-ref")

    captured: dict[str, str] = {}

    def fake_create_task(*, tasklist: str, title: str, notes: str):
        captured["tasklist"] = tasklist
        return {"id": "task-ref-1"}

    monkeypatch.setattr(tasks, "create_task", fake_create_task)

    result = tasks.create_item_from_classification(
        source_name="inbox.json",
        item={"type": "reference", "title": "Hotel confirmation", "description": ""},
        language="en",
    )

    assert result["status"] == "created"
    assert captured["tasklist"] == REFERENCE_TL


def test_spanish_task_routes_to_personal(monkeypatch) -> None:
    monkeypatch.setattr(tasks, "list_tasks", lambda tasklist: [])
    monkeypatch.setattr(tasks, "_build_idempotency_hash", lambda source_name, item: "hash-es")

    captured: dict[str, str] = {}

    def fake_create_task(*, tasklist: str, title: str, notes: str):
        captured["tasklist"] = tasklist
        return {"id": "task-es-1"}

    monkeypatch.setattr(tasks, "create_task", fake_create_task)

    result = tasks.create_item_from_classification(
        source_name="inbox.json",
        item={"type": "task", "title": "Leche", "description": ""},
        language="es",
    )

    assert result["status"] == "created"
    assert captured["tasklist"] == PERSONAL_TL


def test_create_project_adds_first_subtask_when_no_subtasks(monkeypatch) -> None:
    monkeypatch.setattr(tasks, "list_tasks", lambda tasklist: [])
    monkeypatch.setattr(tasks, "list_projects", lambda tasklist: [])
    monkeypatch.setattr(tasks, "_build_idempotency_hash", lambda source_name, item: "hashxyz")

    calls = {"create_project": 0, "add_task_to_project": 0, "tasklist": ""}

    def fake_create_project(*, tasklist: str, title: str, notes: str):
        calls["create_project"] += 1
        calls["tasklist"] = tasklist
        assert "inbox_hash:hashxyz" in notes
        return {"id": "project-1"}

    def fake_add_task_to_project(*, tasklist: str, project_id: str, title: str):
        calls["add_task_to_project"] += 1
        assert project_id == "project-1"
        assert title == tasks.PROJECT_FIRST_SUBTASK_TITLE
        return {"id": "sub-1"}

    monkeypatch.setattr(tasks, "create_project", fake_create_project)
    monkeypatch.setattr(tasks, "add_task_to_project", fake_add_task_to_project)

    result = tasks.create_item_from_classification(
        source_name="inbox.json",
        item={"type": "project", "title": "Plan trip", "description": ""},
    )

    assert result["status"] == "created"
    assert result["type"] == "project"
    assert result["task_id"] == "project-1"
    assert calls["create_project"] == 1
    assert calls["add_task_to_project"] == 1
    assert calls["tasklist"] == WORK_TL


def test_create_project_adds_classified_subtasks(monkeypatch) -> None:
    monkeypatch.setattr(tasks, "list_tasks", lambda tasklist: [])
    monkeypatch.setattr(tasks, "list_projects", lambda tasklist: [])
    monkeypatch.setattr(tasks, "_build_idempotency_hash", lambda source_name, item: "hashxyz")

    subtask_titles: list[str] = []

    def fake_create_project(*, tasklist: str, title: str, notes: str):
        return {"id": "project-1"}

    def fake_add_task_to_project(*, tasklist: str, project_id: str, title: str):
        subtask_titles.append(title)
        return {"id": f"sub-{len(subtask_titles)}"}

    monkeypatch.setattr(tasks, "create_project", fake_create_project)
    monkeypatch.setattr(tasks, "add_task_to_project", fake_add_task_to_project)

    result = tasks.create_item_from_classification(
        source_name="inbox.json",
        item={
            "type": "project",
            "title": "Plan trip",
            "description": "",
            "subtasks": ["Book flights", "Reserve hotel"],
        },
    )

    assert result["status"] == "created"
    assert subtask_titles == ["Book flights", "Reserve hotel"]


def test_create_project_reuses_existing_project(monkeypatch) -> None:
    monkeypatch.setattr(tasks, "list_tasks", lambda tasklist: [])
    monkeypatch.setattr(
        tasks,
        "list_projects",
        lambda tasklist: [{"id": "project-1", "title": "Plan trip"}],
    )
    monkeypatch.setattr(tasks, "_build_idempotency_hash", lambda source_name, item: "hashxyz")

    subtask_titles: list[str] = []

    def fake_add_task_to_project(*, tasklist: str, project_id: str, title: str):
        subtask_titles.append(title)
        return {"id": "sub-1"}

    monkeypatch.setattr(tasks, "create_project", lambda **kwargs: {"id": "new"})
    monkeypatch.setattr(tasks, "add_task_to_project", fake_add_task_to_project)

    result = tasks.create_item_from_classification(
        source_name="inbox.json",
        item={
            "type": "project",
            "title": "Plan trip",
            "description": "",
            "existing_project_title": "Plan trip",
            "subtasks": ["Book flights"],
        },
    )

    assert result["status"] == "updated"
    assert result["task_id"] == "project-1"
    assert subtask_titles == ["Book flights"]
