"""Idempotency markers for inbox-derived tasks.

Each created task carries an `inbox_hash:<16-hex>` line in its notes so that
re-runs of the same drop can find and skip the existing task.
"""

from __future__ import annotations

import hashlib

IDEMPOTENCY_MARKER_PREFIX = "inbox_hash:"


def dedupe_marker(source_name: str, item: dict[str, str]) -> str:
    """Stable 16-hex digest over (source filename, type, title, description)."""
    payload = "|".join(
        [
            source_name,
            item.get("type", ""),
            item.get("title", ""),
            item.get("description", ""),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def notes_with_marker(notes: str, marker: str) -> str:
    """Append the marker line to existing notes (or use it as the only line)."""
    if notes:
        return f"{notes}\n\n{IDEMPOTENCY_MARKER_PREFIX}{marker}"
    return f"{IDEMPOTENCY_MARKER_PREFIX}{marker}"
