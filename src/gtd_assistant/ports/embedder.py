"""Port for document and query embeddings."""

from __future__ import annotations

from typing import Protocol


class Embedder(Protocol):
    """Asymmetric embedding model used for saved references."""

    dimension: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed document-side texts."""

    def embed_query(self, text: str) -> list[float]:
        """Embed a query-side text."""
