"""Google Tasks tasklist IDs for GTD buckets (env overrides with built-in defaults)."""

from __future__ import annotations

import os

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


PERSONAL_TL = _tasklist_id("GTD_TASKLIST_PERSONAL")
WORK_TL = _tasklist_id("GTD_TASKLIST_WORK")
WAITING_FOR_TL = _tasklist_id("GTD_TASKLIST_WAITING_FOR")
REFERENCE_TL = _tasklist_id("GTD_TASKLIST_REFERENCE")
