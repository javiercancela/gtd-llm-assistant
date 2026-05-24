"""Google Tasks tasklist IDs for GTD buckets (env overrides with built-in defaults)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from gtd_assistant.domain.routing import (
    BUCKET_PERSONAL,
    BUCKET_REFERENCE,
    BUCKET_WAITING_FOR,
    BUCKET_WORK,
)

# Defaults match the authenticated account as of setup; override in
# ~/.config/gtd-llm-assistant/env (see config/env.example).
_DEFAULTS: dict[str, str] = {
    "GTD_TASKLIST_PERSONAL": "MDI3MDExMDU2NDE1NzMyNzA2NjE6MDow",
    "GTD_TASKLIST_WORK": "bVpBQk9RLTFpSk05YXpBdA",
    "GTD_TASKLIST_WAITING_FOR": "c1ZaRzY2WlFRWWtCLTBEeg",
    "GTD_TASKLIST_REFERENCE": "N0NUMnV3M2xway00S2JwRg",
}


def _tasklist_id(env_key: str) -> str:
    value = os.environ.get(env_key, _DEFAULTS[env_key]).strip()
    if not value:
        raise ValueError(f"{env_key} must not be empty")
    return value


@dataclass(frozen=True)
class GtdTaskLists:
    """Google Tasks list IDs for GTD buckets."""

    personal: str
    work: str
    waiting_for: str
    reference: str

    def as_dict(self) -> dict[str, str]:
        return {
            BUCKET_PERSONAL: self.personal,
            BUCKET_WORK: self.work,
            BUCKET_WAITING_FOR: self.waiting_for,
            BUCKET_REFERENCE: self.reference,
        }


def load_gtd_task_lists() -> GtdTaskLists:
    """Load tasklist IDs from environment with existing defaults."""
    return GtdTaskLists(
        personal=_tasklist_id("GTD_TASKLIST_PERSONAL"),
        work=_tasklist_id("GTD_TASKLIST_WORK"),
        waiting_for=_tasklist_id("GTD_TASKLIST_WAITING_FOR"),
        reference=_tasklist_id("GTD_TASKLIST_REFERENCE"),
    )


_DEFAULT_TASKLISTS = load_gtd_task_lists()

PERSONAL_TL = _DEFAULT_TASKLISTS.personal
WORK_TL = _DEFAULT_TASKLISTS.work
WAITING_FOR_TL = _DEFAULT_TASKLISTS.waiting_for
REFERENCE_TL = _DEFAULT_TASKLISTS.reference
