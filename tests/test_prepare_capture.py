from pathlib import Path

import pytest

from gtd_assistant.application.prepare_capture import prepare_capture


class _Extractor:
    def extract_text(self, path: Path) -> str:
        return "Extracted text"


def test_text_only_capture_returns_unchanged() -> None:
    capture = {"text": "hello"}

    prepared, source_document = prepare_capture(
        capture,
        source_name="drop.json",
        extractor=_Extractor(),
    )

    assert prepared is capture
    assert source_document is None


def test_file_capture_populates_text_and_source_context(tmp_path: Path) -> None:
    source = tmp_path / "note.md"
    source.write_text("source bytes", encoding="utf-8")

    prepared, source_document = prepare_capture(
        {"source_path": str(source)},
        source_name="drop.json",
        extractor=_Extractor(),
    )

    assert prepared["text"] == "Extracted text"
    assert source_document is not None
    assert source_document.original_path == source.resolve()
    assert source_document.original_name == "note.md"
    assert source_document.extension == ".md"


def test_capture_with_text_and_source_path_fails(tmp_path: Path) -> None:
    source = tmp_path / "note.md"
    source.write_text("source", encoding="utf-8")

    with pytest.raises(ValueError, match="cannot include both text and source_path"):
        prepare_capture(
            {"text": "hello", "source_path": str(source)},
            source_name="drop.json",
            extractor=_Extractor(),
        )


def test_missing_source_file_fails(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="source_path is not a file"):
        prepare_capture(
            {"source_path": str(tmp_path / "missing.md")},
            source_name="drop.json",
            extractor=_Extractor(),
        )
