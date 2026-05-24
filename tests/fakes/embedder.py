from __future__ import annotations


class FakeEmbedder:
    dimension = 4

    def __init__(self) -> None:
        self.document_texts: list[str] = []
        self.query_texts: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_texts.extend(texts)
        return [_vector_for(text, self.dimension) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        self.query_texts.append(text)
        return _vector_for(f"query:{text}", self.dimension)


def _vector_for(text: str, dimension: int) -> list[float]:
    values = [float((sum(text.encode("utf-8")) + index) % 10) for index in range(dimension)]
    total = sum(value * value for value in values) ** 0.5 or 1.0
    return [value / total for value in values]
