"""Archive canonical copies of source documents for saved references."""

from __future__ import annotations

import re
import shutil
from datetime import date
from pathlib import Path

from gtd_assistant.application.prepare_capture import SourceDocument


def archive_source_document(
    source_document: SourceDocument,
    *,
    references_dir: Path,
    archived_on: date | None = None,
) -> Path:
    """Copy a source document into the owned references directory."""
    references_dir.mkdir(parents=True, exist_ok=True)
    day = (archived_on or date.today()).isoformat()
    hash_prefix = source_document.content_hash[:8]
    safe_name = _sanitize_name(source_document.original_name)
    base_name = f"{day}_{hash_prefix}_{safe_name}"
    destination = references_dir / base_name

    if destination.exists() and _sha256_file(destination) == source_document.content_hash:
        return destination

    candidate = destination
    counter = 2
    stem = destination.stem
    suffix = destination.suffix
    while candidate.exists():
        if _sha256_file(candidate) == source_document.content_hash:
            return candidate
        candidate = references_dir / f"{stem}-{counter}{suffix}"
        counter += 1

    shutil.copy2(source_document.original_path, candidate)
    return candidate


def _sanitize_name(name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip())
    sanitized = sanitized.strip(".-")
    return sanitized or "document"


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
