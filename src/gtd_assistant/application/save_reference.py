"""Save classified references to the reference store."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from gtd_assistant.domain.reference import (
    DEFAULT_REFERENCE_LANGUAGE,
    NewReference,
    normalize_reference_tags,
    normalize_reference_url,
    reference_dedupe_key,
    reference_embedding_text,
)
from gtd_assistant.ports.embedder import Embedder
from gtd_assistant.ports.reference_store import ReferenceStore

REFERENCE_TASKLIST_LABEL = "references-db"


def save_reference(
    *,
    store: ReferenceStore,
    embedder: Embedder,
    item: dict[str, Any],
    capture: dict[str, Any],
    source_name: str,
    source_url: str | None = None,
) -> dict[str, str]:
    """Persist one classified reference and return a publish-shaped result."""
    reference = build_new_reference(
        item=item,
        capture=capture,
        source_name=source_name,
        source_url=source_url,
    )
    dedupe_key = reference_dedupe_key(
        title=reference.title,
        summary=reference.summary,
        url=reference.url,
    )

    if reference.url:
        existing = store.find_by_url(reference.url)
        if existing:
            return _result("deduped", existing.id)

    existing = store.find_by_dedupe_key(dedupe_key)
    if existing:
        return _result("deduped", existing.id)

    embedding = embedder.embed_documents([reference_embedding_text(reference)])[0]
    created = store.create_reference(reference, dedupe_key=dedupe_key, embedding=embedding)
    return _result("created", created.id)


def build_new_reference(
    *,
    item: dict[str, Any],
    capture: dict[str, Any],
    source_name: str,
    source_url: str | None = None,
) -> NewReference:
    """Normalize a classified reference item into a storage object."""
    url = normalize_reference_url(str(item.get("url", "")).strip() or source_url)
    summary = str(item.get("summary", "")).strip()
    if not summary:
        summary = _description_without_url(str(item.get("description", "")).strip(), url=url)

    return NewReference(
        title=str(item.get("title", "")).strip() or "Untitled reference",
        summary=summary,
        url=url,
        language=DEFAULT_REFERENCE_LANGUAGE,
        source=source_name,
        captured_at=_captured_at(capture),
        tags=normalize_reference_tags(item.get("tags")),
        metadata={"source_capture": source_name},
    )


def _description_without_url(description: str, *, url: str | None) -> str:
    if not description or not url:
        return description
    lines = [line for line in description.splitlines() if line.strip() != url]
    return "\n".join(lines).strip()


def _captured_at(capture: dict[str, Any]) -> str:
    for key in ("captured_at", "created_at", "timestamp", "date"):
        value = str(capture.get(key, "")).strip()
        if value:
            return value
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _result(status: str, reference_id: int) -> dict[str, str]:
    return {
        "status": status,
        "task_id": str(reference_id),
        "tasklist": REFERENCE_TASKLIST_LABEL,
        "type": "reference",
    }
