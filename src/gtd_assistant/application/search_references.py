"""Search saved references through keyword, semantic, and hybrid use cases."""

from __future__ import annotations

from gtd_assistant.domain.reference import ReferenceSearchResult
from gtd_assistant.ports.embedder import Embedder
from gtd_assistant.ports.reference_store import ReferenceStore

_RRF_K = 60


def search_references_keyword(
    *,
    store: ReferenceStore,
    query: str,
    limit: int = 10,
) -> list[ReferenceSearchResult]:
    """Search references with FTS only."""
    return store.keyword_search(query, limit=_clean_limit(limit))


def search_references_semantic(
    *,
    store: ReferenceStore,
    embedder: Embedder,
    query: str,
    limit: int = 10,
) -> list[ReferenceSearchResult]:
    """Search references with vector similarity only."""
    embedding = embedder.embed_query(query)
    return store.semantic_search(embedding, limit=_clean_limit(limit))


def search_references(
    *,
    store: ReferenceStore,
    embedder: Embedder,
    query: str,
    limit: int = 10,
) -> list[ReferenceSearchResult]:
    """Hybrid search using Reciprocal Rank Fusion over FTS and vector results."""
    limit = _clean_limit(limit)
    keyword = store.keyword_search(query, limit=limit)
    semantic = search_references_semantic(
        store=store,
        embedder=embedder,
        query=query,
        limit=limit,
    )
    return _rrf_fuse(keyword, semantic, limit=limit)


def _rrf_fuse(
    keyword: list[ReferenceSearchResult],
    semantic: list[ReferenceSearchResult],
    *,
    limit: int,
) -> list[ReferenceSearchResult]:
    by_id: dict[int, ReferenceSearchResult] = {}
    scores: dict[int, float] = {}

    for results in (keyword, semantic):
        for rank, result in enumerate(results, start=1):
            reference_id = result.reference.id
            by_id.setdefault(reference_id, result)
            scores[reference_id] = scores.get(reference_id, 0.0) + 1.0 / (_RRF_K + rank)

    ranked_ids = sorted(scores, key=lambda reference_id: scores[reference_id], reverse=True)
    fused: list[ReferenceSearchResult] = []
    for reference_id in ranked_ids[:limit]:
        result = by_id[reference_id]
        fused.append(
            ReferenceSearchResult(
                reference=result.reference,
                score=scores[reference_id],
                snippet=result.snippet,
            )
        )
    return fused


def _clean_limit(limit: int) -> int:
    return max(1, min(int(limit), 50))
