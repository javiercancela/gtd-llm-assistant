"""Publish classified GTD items through a task-list repository.

Entry: publish_classified_item(...)
Port: TaskListRepository
"""

from __future__ import annotations

from typing import Any

from gtd_assistant.domain.dedupe import IDEMPOTENCY_MARKER_PREFIX, dedupe_marker, notes_with_marker
from gtd_assistant.domain.routing import gtd_list_for
from gtd_assistant.ports.task_lists import TaskListRepository

PROJECT_FIRST_SUBTASK_TITLE = "Define next action"


def publish_classified_item(
    *,
    repository: TaskListRepository,
    tasklists: dict[str, str],
    source_name: str,
    item: dict[str, Any],
    language: str = "en",
    source_url: str | None = None,
) -> dict[str, str]:
    """Create, dedupe, or update one classified item."""
    item_type = str(item.get("type", "task")).strip() or "task"
    title = str(item.get("title", "")).strip() or "Inbox item"
    description = str(item.get("description", "")).strip()
    url = _resolve_task_url(item, source_url)
    tasklist = gtd_list_for(item_type, language, tasklists=tasklists)
    marker = dedupe_marker(source_name, item)

    existing = _find_existing_task(repository, tasklist=tasklist, marker=marker)
    if existing:
        return {
            "status": "deduped",
            "task_id": str(existing.get("id", "")),
            "tasklist": tasklist,
            "type": item_type,
        }

    notes = notes_with_marker(description, marker)
    if item_type == "project":
        return _publish_project(
            repository=repository,
            tasklist=tasklist,
            title=title,
            notes=notes,
            url=url,
            item=item,
            item_type=item_type,
        )

    created = repository.create_task(tasklist=tasklist, title=title, notes=notes, url=url)
    return {
        "status": "created",
        "task_id": str(created.get("id", "")),
        "tasklist": tasklist,
        "type": item_type,
    }


def _find_existing_task(
    repository: TaskListRepository,
    *,
    tasklist: str,
    marker: str,
) -> dict[str, Any] | None:
    marker_text = f"{IDEMPOTENCY_MARKER_PREFIX}{marker}"
    for task in repository.list_tasks(tasklist):
        notes = str(task.get("notes", ""))
        if marker_text in notes:
            return task
    return None


def _find_project_by_title(
    repository: TaskListRepository,
    tasklist: str,
    title: str,
) -> dict[str, Any] | None:
    normalized = title.strip().lower()
    if not normalized:
        return None
    for project in repository.list_projects(tasklist):
        if str(project.get("title", "")).strip().lower() == normalized:
            return project
    return None


def _resolve_task_url(item: dict[str, Any], source_url: str | None) -> str | None:
    url = str(item.get("url", "")).strip()
    if not url and source_url:
        url = source_url.strip()
    return url or None


def _normalized_subtasks(item: dict[str, Any]) -> list[str]:
    subtasks = item.get("subtasks") or []
    if not isinstance(subtasks, list):
        return []
    return [str(subtask).strip() for subtask in subtasks if str(subtask).strip()]


def _add_project_subtasks(
    repository: TaskListRepository,
    *,
    tasklist: str,
    project_id: str,
    subtasks: list[str],
) -> None:
    for subtask_title in subtasks:
        repository.add_task_to_project(
            tasklist=tasklist,
            project_id=project_id,
            title=subtask_title,
        )


def _publish_project(
    *,
    repository: TaskListRepository,
    tasklist: str,
    title: str,
    notes: str,
    url: str | None,
    item: dict[str, Any],
    item_type: str,
) -> dict[str, str]:
    subtasks = _normalized_subtasks(item)
    existing_project_title = str(item.get("existing_project_title", "")).strip()
    matched = (
        _find_project_by_title(repository, tasklist, existing_project_title)
        if existing_project_title
        else None
    )
    if matched:
        project_id = str(matched.get("id", ""))
        if project_id and subtasks:
            _add_project_subtasks(
                repository,
                tasklist=tasklist,
                project_id=project_id,
                subtasks=subtasks,
            )
        return {
            "status": "updated",
            "task_id": project_id,
            "tasklist": tasklist,
            "type": item_type,
        }

    created = repository.create_project(tasklist=tasklist, title=title, notes=notes, url=url)
    project_id = str(created.get("id", ""))
    if project_id:
        if subtasks:
            _add_project_subtasks(
                repository,
                tasklist=tasklist,
                project_id=project_id,
                subtasks=subtasks,
            )
        else:
            repository.add_task_to_project(
                tasklist=tasklist,
                project_id=project_id,
                title=PROJECT_FIRST_SUBTASK_TITLE,
            )

    return {
        "status": "created",
        "task_id": project_id,
        "tasklist": tasklist,
        "type": item_type,
    }
