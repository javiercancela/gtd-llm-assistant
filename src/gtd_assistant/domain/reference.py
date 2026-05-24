"""Pure reference-record shapes and dedupe helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


DEFAULT_REFERENCE_LANGUAGE = "en"


@dataclass(frozen=True)
class ReferenceRecord:
    """A saved reference as returned by the reference store."""

    id: int
    title: str
    summary: str
    url: str | None
    language: str
    source: str | None
    captured_at: str
    created_at: str
    updated_at: str
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NewReference:
    """A reference ready to be inserted into storage."""

    title: str
    summary: str
    url: str | None
    language: str = DEFAULT_REFERENCE_LANGUAGE
    source: str | None = None
    captured_at: str = ""
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReferenceSearchResult:
    """A ranked reference search hit."""

    reference: ReferenceRecord
    score: float
    snippet: str = ""


def normalize_reference_url(url: str | None) -> str | None:
    """Normalize empty URL strings to None."""
    normalized = (url or "").strip()
    return normalized or None


def normalize_reference_tags(tags: Any) -> tuple[str, ...]:
    """Return stable, lowercase tag names from LLM or manual input."""
    if not isinstance(tags, list | tuple):
        return ()

    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        name = " ".join(str(tag).strip().lower().split())
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return tuple(normalized)


def reference_dedupe_key(*, title: str, summary: str, url: str | None) -> str:
    """Return the stable dedupe key for URL and URL-less references."""
    normalized_url = normalize_reference_url(url)
    if normalized_url:
        return f"url:{normalized_url}"

    payload = json.dumps(
        {
            "title": " ".join(title.strip().lower().split()),
            "summary": " ".join(summary.strip().lower().split()),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"content:{digest}"


def reference_embedding_text(reference: NewReference | ReferenceRecord) -> str:
    """Text embedded for document-side semantic search."""
    parts = [reference.title, reference.summary]
    if reference.url:
        parts.append(reference.url)
    return "\n\n".join(part for part in parts if part)
