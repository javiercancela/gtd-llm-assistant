"""Low-level Google Tasks API helpers (read and write)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from adapters.gcloud_auth import _build_tasks_service


def list_tasklists() -> list[dict]:
    service = _build_tasks_service()
    tasklists_resource = service.tasklists()
    all_tasklists: list[dict] = []
    page_token: str | None = None

    while True:
        response = tasklists_resource.list(pageToken=page_token).execute()
        all_tasklists.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return all_tasklists


def list_tasks(tasklist: str) -> list[dict]:
    service = _build_tasks_service()
    tasks_resource = service.tasks()
    all_tasks: list[dict] = []
    page_token: str | None = None

    while True:
        response = tasks_resource.list(
            tasklist=tasklist,
            showCompleted=True,
            showHidden=True,
            showDeleted=False,
            pageToken=page_token,
        ).execute()
        all_tasks.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return all_tasks


def list_projects(tasklist: str) -> list[dict]:
    """Parent tasks that currently have at least one subtask."""
    tasks = list_tasks(tasklist=tasklist)
    tasks_by_id = {task["id"]: task for task in tasks if task.get("id")}

    parent_ids: set[str] = set()
    for task in tasks:
        parent_id = task.get("parent")
        if parent_id and parent_id in tasks_by_id:
            parent_ids.add(parent_id)

    return [tasks_by_id[pid] for pid in parent_ids]


def _build_task_body(
    title: str,
    notes: str | None,
    due_days_from_now: int | None,
) -> dict:
    body: dict = {"title": title}

    if notes:
        body["notes"] = notes

    if due_days_from_now is not None:
        due = datetime.now(timezone.utc) + timedelta(days=due_days_from_now)
        # Google Tasks expects an RFC3339 timestamp (in practice it treats it as a date).
        body["due"] = due.isoformat().replace("+00:00", "Z")

    return body


def create_task(
    tasklist: str,
    title: str,
    notes: str | None = None,
    due_days_from_now: int | None = None,
) -> dict:
    service = _build_tasks_service()
    body = _build_task_body(title, notes, due_days_from_now)
    return service.tasks().insert(tasklist=tasklist, body=body).execute()


def create_project(
    tasklist: str,
    title: str,
    notes: str | None = None,
    due_days_from_now: int | None = None,
) -> dict:
    """Create a parent task intended to hold subtasks.

    At the API level a project is just a task; this alias exists to make the
    intent obvious at call sites. See PLAN.md (Phase 3) for the open question
    about marking childless projects so list_projects can find them.
    """
    return create_task(
        tasklist=tasklist,
        title=title,
        notes=notes,
        due_days_from_now=due_days_from_now,
    )


def add_task_to_project(
    tasklist: str,
    project_id: str,
    title: str,
    notes: str | None = None,
    due_days_from_now: int | None = None,
) -> dict:
    service = _build_tasks_service()
    body = _build_task_body(title, notes, due_days_from_now)
    return (
        service.tasks()
        .insert(tasklist=tasklist, parent=project_id, body=body)
        .execute()
    )
