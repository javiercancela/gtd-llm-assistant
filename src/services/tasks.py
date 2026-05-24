"""Compatibility wrapper for publishing classified inbox items.

New publishing logic lives in `application.publish_classified_item`; this
module wires it to the current Google Tasks adapter for existing callers.
"""

from __future__ import annotations

from typing import Any

from adapters import gcloud_tasks
from application.publish_classified_item import (
    PROJECT_FIRST_SUBTASK_TITLE as _PROJECT_FIRST_SUBTASK_TITLE,
    publish_classified_item,
)
from domain.routing import (
    BUCKET_PERSONAL,
    BUCKET_REFERENCE,
    BUCKET_WAITING_FOR,
    BUCKET_WORK,
)
from services.tasklists import PERSONAL_TL, REFERENCE_TL, WAITING_FOR_TL, WORK_TL

_GTD_TASKLISTS: dict[str, str] = {
    BUCKET_PERSONAL: PERSONAL_TL,
    BUCKET_WORK: WORK_TL,
    BUCKET_WAITING_FOR: WAITING_FOR_TL,
    BUCKET_REFERENCE: REFERENCE_TL,
}

PROJECT_FIRST_SUBTASK_TITLE = _PROJECT_FIRST_SUBTASK_TITLE


class GoogleTasksRepository:
    """TaskListRepository backed by the current Google Tasks adapter."""

    def list_tasks(self, tasklist: str) -> list[dict[str, Any]]:
        return gcloud_tasks.list_tasks(tasklist=tasklist)

    def list_projects(self, tasklist: str) -> list[dict[str, Any]]:
        return gcloud_tasks.list_projects(tasklist=tasklist)

    def create_task(
        self,
        *,
        tasklist: str,
        title: str,
        notes: str | None = None,
        url: str | None = None,
    ) -> dict[str, Any]:
        return gcloud_tasks.create_task(tasklist=tasklist, title=title, notes=notes, url=url)

    def create_project(
        self,
        *,
        tasklist: str,
        title: str,
        notes: str | None = None,
        url: str | None = None,
    ) -> dict[str, Any]:
        return gcloud_tasks.create_project(tasklist=tasklist, title=title, notes=notes, url=url)

    def add_task_to_project(
        self,
        *,
        tasklist: str,
        project_id: str,
        title: str,
    ) -> dict[str, Any]:
        return gcloud_tasks.add_task_to_project(
            tasklist=tasklist,
            project_id=project_id,
            title=title,
        )


def create_item_from_classification(
    *,
    source_name: str,
    item: dict[str, Any],
    language: str = "en",
    source_url: str | None = None,
) -> dict[str, str]:
    return publish_classified_item(
        repository=GoogleTasksRepository(),
        tasklists=_GTD_TASKLISTS,
        source_name=source_name,
        item=item,
        language=language,
        source_url=source_url,
    )
