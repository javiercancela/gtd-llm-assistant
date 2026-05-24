"""Local document text extraction with direct reads and pandoc."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Protocol


class PandocRunner(Protocol):
    def __call__(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """Run pandoc and return the completed process."""


_DIRECT_READ_EXTENSIONS = {".txt", ".md", ".markdown"}
_PANDOC_FORMATS = {
    ".docx": "docx",
    ".odt": "odt",
    ".rtf": "rtf",
    ".html": "html",
    ".htm": "html",
    ".epub": "epub",
}


class PandocDocumentTextExtractor:
    """Extract text from local files supported by v1 document references."""

    def __init__(
        self,
        *,
        runner: PandocRunner | None = None,
        pandoc_binary: str = "pandoc",
    ) -> None:
        self._runner = runner
        self._pandoc_binary = pandoc_binary

    def extract_text(self, path: Path) -> str:
        """Return markdown/plain text extracted from a supported local document."""
        extension = path.suffix.lower()
        if extension in _DIRECT_READ_EXTENSIONS:
            return _require_text(path.read_text(encoding="utf-8"), path=path)
        if extension in _PANDOC_FORMATS:
            return _require_text(self._extract_with_pandoc(path), path=path)
        raise ValueError(f"unsupported document extension for {path.name}: {extension or '<none>'}")

    def _extract_with_pandoc(self, path: Path) -> str:
        if self._runner is None and shutil.which(self._pandoc_binary) is None:
            raise RuntimeError("pandoc is required to extract this document; install it with brew install pandoc")

        args = [
            self._pandoc_binary,
            "--from",
            _PANDOC_FORMATS[path.suffix.lower()],
            "--to",
            "gfm",
            "--wrap=none",
            str(path),
        ]
        runner = self._runner or _default_runner
        try:
            completed = runner(args)
        except FileNotFoundError as exc:
            raise RuntimeError(
                "pandoc is required to extract this document; install it with brew install pandoc"
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            detail = f": {stderr}" if stderr else ""
            raise RuntimeError(f"pandoc failed to extract {path.name}{detail}") from exc
        return completed.stdout


def _default_runner(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, capture_output=True, text=True)


def _require_text(text: str, *, path: Path) -> str:
    stripped = text.strip()
    if not stripped:
        raise ValueError(f"extracted text is empty for {path.name}")
    return stripped
