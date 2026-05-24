"""Compatibility wrapper for publishing classified inbox items.

New publishing logic lives in `application.publish_classified_item`; this
module wires it to the current Google Tasks adapter for existing callers.
"""

from __future__ import annotations

from typing import Any

from gtd_assistant.application.publish_classified_item import (
    PROJECT_FIRST_SUBTASK_TITLE as _PROJECT_FIRST_SUBTASK_TITLE,
    publish_classified_item,
)
from gtd_assistant.adapters.google_tasks.repository import GoogleTasksRepository
from gtd_assistant.domain.routing import (
    BUCKET_PERSONAL,
    BUCKET_REFERENCE,
    BUCKET_WAITING_FOR,
    BUCKET_WORK,
)
from gtd_assistant.infrastructure.gtd_task_lists import (
    PERSONAL_TL,
    REFERENCE_TL,
    WAITING_FOR_TL,
    WORK_TL,
)

_GTD_TASKLISTS: dict[str, str] = {
    BUCKET_PERSONAL: PERSONAL_TL,
    BUCKET_WORK: WORK_TL,
    BUCKET_WAITING_FOR: WAITING_FOR_TL,
    BUCKET_REFERENCE: REFERENCE_TL,
}

PROJECT_FIRST_SUBTASK_TITLE = _PROJECT_FIRST_SUBTASK_TITLE


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
