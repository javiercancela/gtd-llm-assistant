"""Qwen3 sentence-transformers embedder for saved references."""

from __future__ import annotations

from typing import Any

QWEN_EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-0.6B"
QWEN_EMBEDDING_DIMENSION = 1024
QWEN_QUERY_INSTRUCTION = (
    "Instruct: Given a search query, retrieve relevant saved references that match the query\n"
    "Query: "
)


class QwenReferenceEmbedder:
    """Lazy in-process Qwen3 embedder with explicit query/document asymmetry."""

    dimension = QWEN_EMBEDDING_DIMENSION

    def __init__(self) -> None:
        self._model: Any | None = None

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self._load_model().encode(texts, normalize_embeddings=True)
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        vector = self._load_model().encode(
            text,
            prompt=QWEN_QUERY_INSTRUCTION,
            normalize_embeddings=True,
        )
        return vector.tolist()

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model

        import torch
        from sentence_transformers import SentenceTransformer

        device = "mps" if torch.backends.mps.is_available() else "cpu"
        model_kwargs = {"torch_dtype": torch.float16} if device == "mps" else {}
        self._model = SentenceTransformer(
            QWEN_EMBEDDING_MODEL,
            device=device,
            model_kwargs=model_kwargs,
        )
        return self._model
