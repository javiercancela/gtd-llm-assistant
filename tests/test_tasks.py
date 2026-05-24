from gtd_assistant.application.publish_classified_item import (
    PROJECT_FIRST_SUBTASK_TITLE,
    publish_classified_item,
)
from gtd_assistant.domain.dedupe import IDEMPOTENCY_MARKER_PREFIX, dedupe_marker
from gtd_assistant.domain.routing import (
    BUCKET_PERSONAL,
    BUCKET_REFERENCE,
    BUCKET_WAITING_FOR,
    BUCKET_WORK,
)
from fakes.task_lists import FakeTaskListRepository

_TASKLISTS = {
    BUCKET_PERSONAL: "PER",
    BUCKET_WORK: "WRK",
    BUCKET_WAITING_FOR: "WAIT",
    BUCKET_REFERENCE: "REF",
}


def _publish(
    repo: FakeTaskListRepository,
    *,
    source_name: str = "inbox.json",
    item: dict,
    language: str = "en",
    source_url: str | None = None,
) -> dict[str, str]:
    return publish_classified_item(
        repository=repo,
        tasklists=_TASKLISTS,
        source_name=source_name,
        item=item,
        language=language,
        source_url=source_url,
    )


def test_publish_classified_item_dedupes_by_marker() -> None:
    item = {"type": "task", "title": "T", "description": "D"}
    marker = dedupe_marker("inbox.json", item)
    repo = FakeTaskListRepository(
        tasks={"WRK": [{"id": "existing-1", "notes": f"{IDEMPOTENCY_MARKER_PREFIX}{marker}"}]}
    )

    result = _publish(repo, item=item)

    assert result["status"] == "deduped"
    assert result["task_id"] == "existing-1"
    assert repo.created_tasks == []


def test_english_task_routes_to_work() -> None:
    repo = FakeTaskListRepository()

    result = _publish(
        repo,
        item={"type": "task", "title": "Buy milk", "description": ""},
        language="en",
    )

    assert result["status"] == "created"
    assert repo.created_tasks[0]["tasklist"] == "WRK"


def test_english_waiting_for_routes_to_waiting_list() -> None:
    repo = FakeTaskListRepository()

    result = _publish(
        repo,
        item={"type": "waiting_for", "title": "Reply from Bob", "description": ""},
        language="en",
    )

    assert result["status"] == "created"
    assert repo.created_tasks[0]["tasklist"] == "WAIT"


def test_english_reference_routes_to_reference_list() -> None:
    repo = FakeTaskListRepository()

    result = _publish(
        repo,
        item={"type": "reference", "title": "Hotel confirmation", "description": ""},
        language="en",
    )

    assert result["status"] == "created"
    assert repo.created_tasks[0]["tasklist"] == "REF"


def test_spanish_task_routes_to_personal() -> None:
    repo = FakeTaskListRepository()

    result = _publish(
        repo,
        item={"type": "task", "title": "Leche", "description": ""},
        language="es",
    )

    assert result["status"] == "created"
    assert repo.created_tasks[0]["tasklist"] == "PER"


def test_create_project_adds_first_subtask_when_no_subtasks() -> None:
    repo = FakeTaskListRepository()

    result = _publish(
        repo,
        item={"type": "project", "title": "Plan trip", "description": ""},
    )

    assert result["status"] == "created"
    assert result["type"] == "project"
    assert result["task_id"] == "project-1"
    assert repo.created_projects[0]["tasklist"] == "WRK"
    assert IDEMPOTENCY_MARKER_PREFIX in repo.created_projects[0]["notes"]
    assert repo.added_subtasks[0]["project_id"] == "project-1"
    assert repo.added_subtasks[0]["title"] == PROJECT_FIRST_SUBTASK_TITLE


def test_create_project_adds_classified_subtasks() -> None:
    repo = FakeTaskListRepository()

    result = _publish(
        repo,
        item={
            "type": "project",
            "title": "Plan trip",
            "description": "",
            "subtasks": ["Book flights", "Reserve hotel"],
        },
    )

    assert result["status"] == "created"
    assert [subtask["title"] for subtask in repo.added_subtasks] == [
        "Book flights",
        "Reserve hotel",
    ]


def test_create_item_passes_source_url_to_create_task() -> None:
    repo = FakeTaskListRepository()

    result = _publish(
        repo,
        source_name="share.json",
        item={"type": "task", "title": "Read later", "description": ""},
        source_url="https://example.com/article",
    )

    assert result["status"] == "created"
    assert repo.created_tasks[0]["url"] == "https://example.com/article"


def test_create_item_prefers_item_url_over_source_url() -> None:
    repo = FakeTaskListRepository()

    _publish(
        repo,
        source_name="share.json",
        item={
            "type": "reference",
            "title": "Article",
            "description": "Summary",
            "url": "https://example.com/from-item",
        },
        source_url="https://example.com/from-source",
    )

    assert repo.created_tasks[0]["url"] == "https://example.com/from-item"


def test_create_project_reuses_existing_project() -> None:
    repo = FakeTaskListRepository(projects={"WRK": [{"id": "project-1", "title": "Plan trip"}]})

    result = _publish(
        repo,
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
    assert repo.created_projects == []
    assert [subtask["title"] for subtask in repo.added_subtasks] == ["Book flights"]
