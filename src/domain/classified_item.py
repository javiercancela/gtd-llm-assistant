"""Normalize raw LLM output into the canonical classified-item dict.

A classified item has the shape `{type, title, description, ...}` where
`type` is one of `VALID_ITEM_KINDS`. References may add `url`; projects add
`subtasks` and `existing_project_title`; waiting-for items fold `who` into
the description.
"""

from __future__ import annotations

from typing import Any

from domain.item_kind import (
    ITEM_KIND_PROJECT,
    ITEM_KIND_REFERENCE,
    ITEM_KIND_TASK,
    ITEM_KIND_WAITING_FOR,
    SPANISH_TYPE_MAP,
    VALID_ITEM_KINDS,
)


def normalize_spanish_item(item: dict[str, Any]) -> dict[str, str]:
    """Map a Spanish-prompt LLM dict (`tipo/titulo/descripcion`) to canonical."""
    raw_type = str(item.get("tipo", "")).strip().lower()
    title = str(item.get("titulo", "")).strip()
    description = str(item.get("descripcion", "")).strip()

    kind = SPANISH_TYPE_MAP.get(raw_type, ITEM_KIND_TASK)
    if kind not in VALID_ITEM_KINDS:
        kind = ITEM_KIND_TASK

    return {"type": kind, "title": title, "description": description}


def normalize_english_item(item: dict[str, Any], *, expected_type: str) -> dict[str, Any]:
    """Map an English-enrichment LLM dict to canonical, per-kind shape.

    `expected_type` is the kind chosen during the classify phase; the
    enrichment LLM may echo it back and we keep the original when invalid.
    """
    item_type = str(item.get("type", expected_type)).strip().lower()
    if item_type not in VALID_ITEM_KINDS:
        item_type = expected_type

    if item_type == ITEM_KIND_REFERENCE:
        return _normalize_reference(item)
    if item_type == ITEM_KIND_PROJECT:
        return _normalize_project(item)
    if item_type == ITEM_KIND_WAITING_FOR:
        return _normalize_waiting_for(item)

    return {
        "type": ITEM_KIND_TASK,
        "title": str(item.get("title", "")).strip(),
        "description": str(item.get("description", "")).strip(),
    }


def _normalize_reference(item: dict[str, Any]) -> dict[str, Any]:
    title = str(item.get("title", "")).strip()
    summary = str(item.get("summary", "")).strip()
    url = str(item.get("url", "")).strip()

    description = summary
    if url:
        description = f"{summary}\n\n{url}".strip() if summary else url

    normalized: dict[str, Any] = {
        "type": ITEM_KIND_REFERENCE,
        "title": title,
        "description": description,
    }
    if url:
        normalized["url"] = url
    return normalized


def _normalize_project(item: dict[str, Any]) -> dict[str, Any]:
    raw_subtasks = item.get("subtasks") or []
    if not isinstance(raw_subtasks, list):
        raw_subtasks = []
    subtasks = [str(t).strip() for t in raw_subtasks if str(t).strip()]

    existing_title = item.get("existing_project_title")
    existing_project_title = (
        str(existing_title).strip() if existing_title not in (None, "", "null") else ""
    )

    return {
        "type": ITEM_KIND_PROJECT,
        "title": str(item.get("title", "")).strip(),
        "description": str(item.get("description", "")).strip(),
        "subtasks": subtasks,
        "existing_project_title": existing_project_title,
    }


def _normalize_waiting_for(item: dict[str, Any]) -> dict[str, Any]:
    title = str(item.get("title", "")).strip()
    description = str(item.get("description", "")).strip()
    who = str(item.get("who", "")).strip()
    if who and who.lower() not in description.lower():
        prefix = f"Who: {who}"
        description = f"{prefix}\n{description}".strip() if description else prefix
    return {"type": ITEM_KIND_WAITING_FOR, "title": title, "description": description}
