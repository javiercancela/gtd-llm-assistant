"""Route a classified item to a GTD tasklist.

Pure mapping; the caller supplies the `tasklists` lookup so this module has
no infrastructure dependency.
"""

from __future__ import annotations

from domain.item_kind import ITEM_KIND_REFERENCE, ITEM_KIND_WAITING_FOR

# Bucket names recognized by `gtd_list_for`.
BUCKET_PERSONAL = "personal"
BUCKET_WORK = "work"
BUCKET_WAITING_FOR = "waiting_for"
BUCKET_REFERENCE = "reference"


def gtd_list_for(item_kind: str, language: str, *, tasklists: dict[str, str]) -> str:
    """Return the tasklist ID for `item_kind` under `language`.

    Spanish captures always go to Personal. English routes by kind: reference
    and waiting-for to their dedicated lists; everything else (tasks and
    projects) to Work.
    """
    if language == "es":
        return tasklists[BUCKET_PERSONAL]
    if item_kind == ITEM_KIND_REFERENCE:
        return tasklists[BUCKET_REFERENCE]
    if item_kind == ITEM_KIND_WAITING_FOR:
        return tasklists[BUCKET_WAITING_FOR]
    return tasklists[BUCKET_WORK]
