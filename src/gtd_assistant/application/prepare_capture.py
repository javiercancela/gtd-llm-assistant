"""Prepare raw captures before classification."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gtd_assistant.ports.document_text_extractor import DocumentTextExtractor


@dataclass(frozen=True)
class SourceDocument:
    """Context for a capture backed by a local source document."""

    original_path: Path
    original_name: str
    extension: str
    content_hash: str
    full_text: str


def prepare_capture(
    capture: dict[str, Any],
    *,
    source_name: str,
    extractor: DocumentTextExtractor,
) -> tuple[dict[str, Any], SourceDocument | None]:
    """Return a classification-ready capture and optional source document context."""
    raw_source_path = str(capture.get("source_path", "")).strip()
    if not raw_source_path:
        return capture, None

    if str(capture.get("text", "")).strip():
        raise ValueError(f"{source_name}: capture cannot include both text and source_path")

    source_path = Path(raw_source_path).expanduser()
    if not source_path.is_absolute():
        raise ValueError(f"{source_name}: source_path must be an absolute path")

    source_path = source_path.resolve()
    if not source_path.is_file():
        raise ValueError(f"{source_name}: source_path is not a file: {source_path}")

    content_hash = _sha256_file(source_path)
    full_text = extractor.extract_text(source_path)
    prepared = dict(capture)
    prepared["text"] = full_text
    return prepared, SourceDocument(
        original_path=source_path,
        original_name=source_path.name,
        extension=source_path.suffix.lower(),
        content_hash=content_hash,
        full_text=full_text,
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
