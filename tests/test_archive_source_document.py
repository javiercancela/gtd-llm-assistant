import hashlib
from datetime import date
from pathlib import Path

from gtd_assistant.application.archive_source_document import archive_source_document
from gtd_assistant.application.prepare_capture import SourceDocument


def test_archive_source_document_copies_expected_file(tmp_path: Path) -> None:
    source = tmp_path / "My Note.md"
    source.write_text("hello", encoding="utf-8")
    content_hash = _sha256(source)

    copied = archive_source_document(
        _source_document(source, content_hash),
        references_dir=tmp_path / "references",
        archived_on=date(2026, 5, 24),
    )

    assert copied.name == f"2026-05-24_{content_hash[:8]}_My-Note.md"
    assert copied.read_text(encoding="utf-8") == "hello"


def test_archive_source_document_reuses_existing_same_hash(tmp_path: Path) -> None:
    source = tmp_path / "note.md"
    source.write_text("hello", encoding="utf-8")
    content_hash = _sha256(source)
    references_dir = tmp_path / "references"
    first = archive_source_document(
        _source_document(source, content_hash),
        references_dir=references_dir,
        archived_on=date(2026, 5, 24),
    )

    second = archive_source_document(
        _source_document(source, content_hash),
        references_dir=references_dir,
        archived_on=date(2026, 5, 24),
    )

    assert second == first


def test_archive_source_document_avoids_overwriting_different_file(tmp_path: Path) -> None:
    source = tmp_path / "note.md"
    source.write_text("hello", encoding="utf-8")
    content_hash = _sha256(source)
    references_dir = tmp_path / "references"
    references_dir.mkdir()
    existing = references_dir / f"2026-05-24_{content_hash[:8]}_note.md"
    existing.write_text("different", encoding="utf-8")

    copied = archive_source_document(
        _source_document(source, content_hash),
        references_dir=references_dir,
        archived_on=date(2026, 5, 24),
    )

    assert copied.name == f"2026-05-24_{content_hash[:8]}_note-2.md"
    assert existing.read_text(encoding="utf-8") == "different"
    assert copied.read_text(encoding="utf-8") == "hello"


def _source_document(path: Path, content_hash: str) -> SourceDocument:
    return SourceDocument(
        original_path=path,
        original_name=path.name,
        extension=path.suffix,
        content_hash=content_hash,
        full_text="hello",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
