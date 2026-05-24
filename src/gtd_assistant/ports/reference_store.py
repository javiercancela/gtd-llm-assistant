"""Port for saving and retrieving references."""

from __future__ import annotations

from typing import Protocol

from gtd_assistant.domain.reference import NewReference, ReferenceRecord, ReferenceSearchResult


class ReferenceStore(Protocol):
    """Storage operations needed by reference use cases and MCP tools."""

    def find_by_url(self, url: str) -> ReferenceRecord | None:
        """Return an existing reference with this URL."""

    def find_by_dedupe_key(self, dedupe_key: str) -> ReferenceRecord | None:
        """Return an existing reference with this dedupe key."""

    def create_reference(
        self,
        reference: NewReference,
        *,
        dedupe_key: str,
        embedding: list[float],
    ) -> ReferenceRecord:
        """Create a reference and its search indexes."""

    def get_reference(self, reference_id: int) -> ReferenceRecord | None:
        """Return a full reference by ID."""

    def keyword_search(self, query: str, *, limit: int) -> list[ReferenceSearchResult]:
        """Search references with SQLite FTS."""

    def semantic_search(
        self,
        embedding: list[float],
        *,
        limit: int,
    ) -> list[ReferenceSearchResult]:
        """Search references by vector similarity."""

    def list_references(
        self,
        *,
        tag: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 50,
    ) -> list[ReferenceRecord]:
        """List references in reverse capture order with optional filters."""

    def list_tags(self) -> list[tuple[str, int]]:
        """Return tag names and reference counts."""
