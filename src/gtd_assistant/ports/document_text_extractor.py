"""Port for extracting text from local documents."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class DocumentTextExtractor(Protocol):
    """Extract markdown/plain text from a supported local document."""

    def extract_text(self, path: Path) -> str:
        """Return markdown/plain text extracted from a supported local document."""
