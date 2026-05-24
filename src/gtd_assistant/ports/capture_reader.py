"""Port for reading inbox capture payloads.

Application code depends on this protocol instead of iCloud filesystem details.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol


class CaptureReader(Protocol):
    """Reader for one workflow JSON drop."""

    def read_capture(
        self,
        path: Path,
        *,
        on_waiting_for_sync: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Return the decoded capture payload at `path`."""
