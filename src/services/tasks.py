"""Domain-level routing from classified inbox items to Google Tasks."""

from __future__ import annotations

import hashlib

from adapters.gcloud_tasks import add_task_to_project, create_project, create_task, list_projects, list_tasks
from services.tasklists import PERSONAL_TL, REFERENCE_TL, WAITING_FOR_TL, WORK_TL

PROJECT_FIRST_SUBTASK_TITLE = "Define next action"
IDEMPOTENCY_MARKER_PREFIX = "inbox_hash:"


def _build_idempotency_hash(source_name: str, item: dict[str, str]) -> str:
    payload = "|".join(
        [
            source_name,
            item.get("type", ""),
            item.get("title", ""),
            item.get("description", ""),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _with_marker(notes: str, marker: str) -> str:
    if notes:
        return f"{notes}\n\n{IDEMPOTENCY_MARKER_PREFIX}{marker}"
    return f"{IDEMPOTENCY_MARKER_PREFIX}{marker}"


def _find_existing_task(tasklist: str, marker: str) -> dict | None:
    marker_text = f"{IDEMPOTENCY_MARKER_PREFIX}{marker}"
    for task in list_tasks(tasklist=tasklist):
        notes = task.get("notes", "")
        if marker_text in notes:
            return task
    return None


def _find_project_by_title(tasklist: str, title: str) -> dict | None:
    normalized = title.strip().lower()
    if not normalized:
        return None
    for project in list_projects(tasklist=tasklist):
        if str(project.get("title", "")).strip().lower() == normalized:
            return project
    return None


def _resolve_task_url(item: dict[str, str], source_url: str | None) -> str | None:
    url = str(item.get("url", "")).strip()
    if not url and source_url:
        url = source_url.strip()
    return url or None


def _target_tasklist(item_type: str, *, language: str = "en") -> str:
    if language == "es":
        return PERSONAL_TL
    if item_type == "reference":
        return REFERENCE_TL
    if item_type == "waiting_for":
        return WAITING_FOR_TL
    return WORK_TL


def _add_project_subtasks(
    *,
    tasklist: str,
    project_id: str,
    subtasks: list[str],
) -> None:
    for subtask_title in subtasks:
        add_task_to_project(
            tasklist=tasklist,
            project_id=project_id,
            title=subtask_title,
        )


def create_item_from_classification(
    *,
    source_name: str,
    item: dict[str, str],
    language: str = "en",
    source_url: str | None = None,
) -> dict[str, str]:
    item_type = item.get("type", "task")
    title = item.get("title", "").strip() or "Inbox item"
    description = item.get("description", "").strip()
    url = _resolve_task_url(item, source_url)
    tasklist = _target_tasklist(item_type, language=language)
    marker = _build_idempotency_hash(source_name, item)

    existing = _find_existing_task(tasklist=tasklist, marker=marker)
    if existing:
        return {
            "status": "deduped",
            "task_id": existing.get("id", ""),
            "tasklist": tasklist,
            "type": item_type,
        }

    notes = _with_marker(description, marker)
    if item_type == "project":
        subtasks = item.get("subtasks") or []
        if not isinstance(subtasks, list):
            subtasks = []
        subtasks = [str(subtask).strip() for subtask in subtasks if str(subtask).strip()]

        existing_project_title = str(item.get("existing_project_title", "")).strip()
        matched = _find_project_by_title(tasklist, existing_project_title) if existing_project_title else None
        if matched:
            project_id = matched.get("id")
            if project_id and subtasks:
                _add_project_subtasks(tasklist=tasklist, project_id=project_id, subtasks=subtasks)
            return {
                "status": "updated",
                "task_id": project_id or "",
                "tasklist": tasklist,
                "type": item_type,
            }

        created = create_project(tasklist=tasklist, title=title, notes=notes, url=url)
        project_id = created.get("id")
        if project_id:
            if subtasks:
                _add_project_subtasks(tasklist=tasklist, project_id=project_id, subtasks=subtasks)
            else:
                add_task_to_project(
                    tasklist=tasklist,
                    project_id=project_id,
                    title=PROJECT_FIRST_SUBTASK_TITLE,
                )
    else:
        created = create_task(tasklist=tasklist, title=title, notes=notes, url=url)

    return {
        "status": "created",
        "task_id": created.get("id", ""),
        "tasklist": tasklist,
        "type": item_type,
    }
