import subprocess
from pathlib import Path

import pytest

from gtd_assistant.adapters.local_documents.extractor import PandocDocumentTextExtractor


def test_direct_read_markdown(tmp_path: Path) -> None:
    path = tmp_path / "note.md"
    path.write_text("# Title\n\nBody", encoding="utf-8")

    assert PandocDocumentTextExtractor().extract_text(path) == "# Title\n\nBody"


def test_direct_read_text(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("Plain text", encoding="utf-8")

    assert PandocDocumentTextExtractor().extract_text(path) == "Plain text"


def test_pdf_is_unsupported(tmp_path: Path) -> None:
    path = tmp_path / "paper.pdf"
    path.write_text("content", encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported document extension"):
        PandocDocumentTextExtractor().extract_text(path)


def test_docx_uses_pandoc_runner(tmp_path: Path) -> None:
    path = tmp_path / "document.docx"
    path.write_bytes(b"docx")
    calls: list[list[str]] = []

    def runner(args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="Converted **markdown**")

    text = PandocDocumentTextExtractor(runner=runner).extract_text(path)

    assert text == "Converted **markdown**"
    assert calls == [
        [
            "pandoc",
            "--from",
            "docx",
            "--to",
            "gfm",
            "--wrap=none",
            str(path),
        ]
    ]
