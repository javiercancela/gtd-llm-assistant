from __future__ import annotations

from datetime import datetime, timezone

from gtd_assistant.domain.reference import NewReference, ReferenceRecord, ReferenceSearchResult


class FakeReferenceStore:
    def __init__(self) -> None:
        self.records: dict[int, ReferenceRecord] = {}
        self.dedupe_keys: dict[str, int] = {}
        self.urls: dict[str, int] = {}
        self.embeddings: dict[int, list[float]] = {}
        self.next_id = 1

    def find_by_url(self, url: str) -> ReferenceRecord | None:
        reference_id = self.urls.get(url)
        return self.records.get(reference_id) if reference_id else None

    def find_by_dedupe_key(self, dedupe_key: str) -> ReferenceRecord | None:
        reference_id = self.dedupe_keys.get(dedupe_key)
        return self.records.get(reference_id) if reference_id else None

    def create_reference(
        self,
        reference: NewReference,
        *,
        dedupe_key: str,
        embedding: list[float],
    ) -> ReferenceRecord:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        record = ReferenceRecord(
            id=self.next_id,
            title=reference.title,
            summary=reference.summary,
            url=reference.url,
            language=reference.language,
            source=reference.source,
            captured_at=reference.captured_at or now,
            created_at=now,
            updated_at=now,
            tags=reference.tags,
            metadata=dict(reference.metadata),
        )
        self.records[record.id] = record
        self.dedupe_keys[dedupe_key] = record.id
        if record.url:
            self.urls[record.url] = record.id
        self.embeddings[record.id] = list(embedding)
        self.next_id += 1
        return record

    def get_reference(self, reference_id: int) -> ReferenceRecord | None:
        return self.records.get(reference_id)

    def keyword_search(self, query: str, *, limit: int) -> list[ReferenceSearchResult]:
        results = []
        for record in self.records.values():
            haystack = f"{record.title} {record.summary} {' '.join(record.tags)}".lower()
            if query.lower() in haystack:
                results.append(ReferenceSearchResult(record, score=1.0, snippet=record.summary))
        return results[:limit]

    def semantic_search(
        self,
        embedding: list[float],
        *,
        limit: int,
    ) -> list[ReferenceSearchResult]:
        results = [
            ReferenceSearchResult(record, score=1.0 / record.id)
            for record in self.records.values()
        ]
        return results[:limit]

    def list_references(
        self,
        *,
        tag: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 50,
    ) -> list[ReferenceRecord]:
        records = list(self.records.values())
        if tag:
            records = [record for record in records if tag in record.tags]
        if since:
            records = [record for record in records if record.captured_at >= since]
        if until:
            records = [record for record in records if record.captured_at <= until]
        return sorted(records, key=lambda record: record.captured_at, reverse=True)[:limit]

    def list_tags(self) -> list[tuple[str, int]]:
        counts: dict[str, int] = {}
        for record in self.records.values():
            for tag in record.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return sorted(counts.items())
