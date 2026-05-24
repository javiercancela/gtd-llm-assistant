"""stdio MCP server exposing the local reference store."""

from __future__ import annotations

from typing import Any

from gtd_assistant.adapters.qwen_embedder import QwenReferenceEmbedder
from gtd_assistant.adapters.sqlite_reference_store import SQLiteReferenceStore
from gtd_assistant.application.save_reference import save_reference
from gtd_assistant.application.search_references import (
    search_references as search_references_use_case,
    search_references_keyword as search_references_keyword_use_case,
    search_references_semantic as search_references_semantic_use_case,
)
from gtd_assistant.domain.reference import ReferenceRecord, ReferenceSearchResult
from gtd_assistant.infrastructure.reference_config import load_reference_db_path


def main() -> None:
    """Run the reference MCP server over stdio."""
    from mcp.server.fastmcp import FastMCP

    embedder = QwenReferenceEmbedder()
    store = SQLiteReferenceStore(load_reference_db_path(), vector_dimension=embedder.dimension)
    mcp = FastMCP("gtd-references")

    @mcp.tool()
    def search_references(query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Hybrid search over saved references using keyword and semantic ranking."""
        return _search_results(
            search_references_use_case(store=store, embedder=embedder, query=query, limit=limit)
        )

    @mcp.tool()
    def search_references_keyword(query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Keyword search over saved reference titles, summaries, URLs, and tags."""
        return _search_results(
            search_references_keyword_use_case(store=store, query=query, limit=limit)
        )

    @mcp.tool()
    def search_references_semantic(query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Semantic search over saved references using local Qwen embeddings."""
        return _search_results(
            search_references_semantic_use_case(
                store=store,
                embedder=embedder,
                query=query,
                limit=limit,
            )
        )

    @mcp.tool()
    def list_references(
        tag: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List saved references, optionally filtered by tag or captured_at range."""
        return [
            _reference_dict(reference)
            for reference in store.list_references(tag=tag, since=since, until=until, limit=limit)
        ]

    @mcp.tool()
    def get_reference(id: int) -> dict[str, Any] | None:
        """Fetch one saved reference by id."""
        reference = store.get_reference(id)
        return _reference_dict(reference) if reference else None

    @mcp.tool()
    def list_tags() -> list[dict[str, Any]]:
        """List saved reference tags with counts."""
        return [{"tag": tag, "count": count} for tag, count in store.list_tags()]

    @mcp.tool()
    def add_reference(
        url: str | None = None,
        title: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, str]:
        """Add a reference manually without fetching or archiving page content."""
        return save_reference(
            store=store,
            embedder=embedder,
            item={
                "type": "reference",
                "title": title or url or "Untitled reference",
                "summary": summary or "",
                "url": url or "",
                "tags": tags or [],
            },
            capture={},
            source_name="manual",
        )

    mcp.run()


def _search_results(results: list[ReferenceSearchResult]) -> list[dict[str, Any]]:
    return [
        {
            **_reference_dict(result.reference),
            "score": result.score,
            "snippet": result.snippet,
        }
        for result in results
    ]


def _reference_dict(reference: ReferenceRecord) -> dict[str, Any]:
    return {
        "id": reference.id,
        "url": reference.url,
        "title": reference.title,
        "summary": reference.summary,
        "language": reference.language,
        "source": reference.source,
        "captured_at": reference.captured_at,
        "created_at": reference.created_at,
        "updated_at": reference.updated_at,
        "tags": list(reference.tags),
        "metadata": reference.metadata,
    }


if __name__ == "__main__":
    main()
