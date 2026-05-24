"""Port for append-only inbox run logging."""

from __future__ import annotations

from typing import Protocol


class RunLogger(Protocol):
    """Logger used by the inbox processing use case."""

    def info(self, message: str) -> None:
        """Record an informational run event."""

    def ok(self, message: str) -> None:
        """Record a successful processing event."""

    def error(self, message: str) -> None:
        """Record a failed processing event."""
