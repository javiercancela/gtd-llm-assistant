"""SQLite implementation of the ReferenceStore port."""

from __future__ import annotations

import json
import math
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gtd_assistant.adapters.sqlite_reference_store.schema import ensure_schema
from gtd_assistant.domain.reference import NewReference, ReferenceRecord, ReferenceSearchResult

_DEFAULT_VECTOR_DIMENSION = 1024


class SQLiteReferenceStore:
    """Reference store backed by one SQLite database file."""

    def __init__(
        self,
        path: Path | str | None = None,
        *,
        conn: sqlite3.Connection | None = None,
        vector_dimension: int = _DEFAULT_VECTOR_DIMENSION,
    ) -> None:
        if conn is None:
            if path is None:
                raise ValueError("path is required when conn is not supplied")
            db_path = Path(path).expanduser()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(db_path)
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.vector_dimension = vector_dimension
        self._sqlite_vec = self._load_sqlite_vec()
        ensure_schema(
            self.conn,
            vector_dimension=vector_dimension,
            vector_available=self._sqlite_vec is not None,
        )

    def find_by_url(self, url: str) -> ReferenceRecord | None:
        row = self.conn.execute("SELECT * FROM reference_records WHERE url = ?", (url,)).fetchone()
        return self._record_from_row(row) if row else None

    def find_by_dedupe_key(self, dedupe_key: str) -> ReferenceRecord | None:
        row = self.conn.execute(
            "SELECT * FROM reference_records WHERE dedupe_key = ?",
            (dedupe_key,),
        ).fetchone()
        return self._record_from_row(row) if row else None

    def find_by_content_hash(self, content_hash: str) -> ReferenceRecord | None:
        try:
            row = self.conn.execute(
                """
                SELECT *
                FROM reference_records
                WHERE json_extract(metadata_json, '$.content_hash') = ?
                """,
                (content_hash,),
            ).fetchone()
        except sqlite3.OperationalError:
            return self._find_by_content_hash_scan(content_hash)
        return self._record_from_row(row) if row else None

    def create_reference(
        self,
        reference: NewReference,
        *,
        dedupe_key: str,
        embedding: list[float],
    ) -> ReferenceRecord:
        now = _utc_now()
        captured_at = reference.captured_at or now
        metadata_json = json.dumps(reference.metadata, ensure_ascii=False, sort_keys=True)
        tags = tuple(reference.tags)

        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO reference_records(
                  url, dedupe_key, title, summary, language, source,
                  captured_at, created_at, updated_at, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reference.url,
                    dedupe_key,
                    reference.title,
                    reference.summary,
                    reference.language,
                    reference.source,
                    captured_at,
                    now,
                    now,
                    metadata_json,
                ),
            )
            reference_id = int(cursor.lastrowid)
            self._replace_tags(reference_id, tags)
            self._replace_fts(reference_id, reference.title, reference.summary, reference.url, tags)
            self._replace_embedding(reference_id, embedding)

        created = self.get_reference(reference_id)
        if created is None:
            raise RuntimeError(f"created reference {reference_id} could not be read")
        return created

    def get_reference(self, reference_id: int) -> ReferenceRecord | None:
        row = self.conn.execute("SELECT * FROM reference_records WHERE id = ?", (reference_id,)).fetchone()
        return self._record_from_row(row) if row else None

    def update_metadata(self, reference_id: int, metadata: dict[str, Any]) -> ReferenceRecord:
        now = _utc_now()
        metadata_json = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
        with self.conn:
            self.conn.execute(
                """
                UPDATE reference_records
                SET metadata_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (metadata_json, now, reference_id),
            )
        updated = self.get_reference(reference_id)
        if updated is None:
            raise ValueError(f"reference not found: {reference_id}")
        return updated

    def keyword_search(self, query: str, *, limit: int) -> list[ReferenceSearchResult]:
        match = _fts_match_query(query)
        if not match:
            return []
        try:
            rows = self.conn.execute(
                """
                SELECT r.*, bm25(references_fts) AS rank,
                       snippet(references_fts, 1, '[', ']', '...', 18) AS snippet
                FROM references_fts
                JOIN reference_records r ON r.id = references_fts.rowid
                WHERE references_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (match, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = self._like_search(query, limit=limit)
            return [
                ReferenceSearchResult(
                    reference=self._record_from_row(row),
                    score=1.0,
                    snippet=str(row["summary"]),
                )
                for row in rows
            ]

        results: list[ReferenceSearchResult] = []
        for row in rows:
            rank = float(row["rank"] or 0.0)
            results.append(
                ReferenceSearchResult(
                    reference=self._record_from_row(row),
                    score=1.0 / (1.0 + max(rank, 0.0)),
                    snippet=str(row["snippet"] or ""),
                )
            )
        return results

    def semantic_search(
        self,
        embedding: list[float],
        *,
        limit: int,
    ) -> list[ReferenceSearchResult]:
        if self._sqlite_vec is not None:
            rows = self.conn.execute(
                """
                SELECT r.*, v.distance
                FROM references_vec v
                JOIN reference_records r ON r.id = v.rowid
                WHERE v.embedding MATCH ? AND k = ?
                ORDER BY v.distance
                """,
                (self._serialize_vector(embedding), limit),
            ).fetchall()
            return [
                ReferenceSearchResult(
                    reference=self._record_from_row(row),
                    score=1.0 / (1.0 + float(row["distance"])),
                )
                for row in rows
            ]

        rows = self.conn.execute(
            """
            SELECT r.*, e.embedding_json
            FROM reference_records r
            JOIN reference_embeddings e ON e.reference_id = r.id
            """
        ).fetchall()
        scored = []
        for row in rows:
            stored = [float(value) for value in json.loads(str(row["embedding_json"]))]
            scored.append((_cosine(embedding, stored), row))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            ReferenceSearchResult(reference=self._record_from_row(row), score=score)
            for score, row in scored[:limit]
        ]

    def list_references(
        self,
        *,
        tag: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 50,
    ) -> list[ReferenceRecord]:
        where = []
        params: list[Any] = []
        join = ""
        if tag:
            join = """
            JOIN reference_tags rt ON rt.reference_id = r.id
            JOIN tags t ON t.id = rt.tag_id
            """
            where.append("t.name = ?")
            params.append(tag.strip().lower())
        if since:
            where.append("r.captured_at >= ?")
            params.append(since)
        if until:
            where.append("r.captured_at <= ?")
            params.append(until)

        sql = f"SELECT r.* FROM reference_records r {join}"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY r.captured_at DESC, r.id DESC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [self._record_from_row(row) for row in rows]

    def list_tags(self) -> list[tuple[str, int]]:
        rows = self.conn.execute(
            """
            SELECT t.name, COUNT(*) AS count
            FROM tags t
            JOIN reference_tags rt ON rt.tag_id = t.id
            GROUP BY t.id, t.name
            ORDER BY t.name
            """
        ).fetchall()
        return [(str(row["name"]), int(row["count"])) for row in rows]

    def close(self) -> None:
        self.conn.close()

    def _replace_tags(self, reference_id: int, tags: tuple[str, ...]) -> None:
        self.conn.execute("DELETE FROM reference_tags WHERE reference_id = ?", (reference_id,))
        for tag in tags:
            self.conn.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (tag,))
            row = self.conn.execute("SELECT id FROM tags WHERE name = ?", (tag,)).fetchone()
            if row:
                self.conn.execute(
                    "INSERT OR IGNORE INTO reference_tags(reference_id, tag_id) VALUES (?, ?)",
                    (reference_id, int(row["id"])),
                )

    def _replace_fts(
        self,
        reference_id: int,
        title: str,
        summary: str,
        url: str | None,
        tags: tuple[str, ...],
    ) -> None:
        self.conn.execute("DELETE FROM references_fts WHERE rowid = ?", (reference_id,))
        self.conn.execute(
            """
            INSERT INTO references_fts(rowid, title, summary, url, tags_text)
            VALUES (?, ?, ?, ?, ?)
            """,
            (reference_id, title, summary, url or "", " ".join(tags)),
        )

    def _replace_embedding(self, reference_id: int, embedding: list[float]) -> None:
        if len(embedding) != self.vector_dimension:
            raise ValueError(
                f"embedding dimension {len(embedding)} does not match {self.vector_dimension}"
            )
        self.conn.execute(
            """
            INSERT OR REPLACE INTO reference_embeddings(reference_id, embedding_json)
            VALUES (?, ?)
            """,
            (reference_id, json.dumps(embedding)),
        )
        if self._sqlite_vec is not None:
            self.conn.execute("DELETE FROM references_vec WHERE rowid = ?", (reference_id,))
            self.conn.execute(
                "INSERT INTO references_vec(rowid, embedding) VALUES (?, ?)",
                (reference_id, self._serialize_vector(embedding)),
            )

    def _record_from_row(self, row: sqlite3.Row) -> ReferenceRecord:
        metadata = json.loads(str(row["metadata_json"] or "{}"))
        tags = self._tags_for_reference(int(row["id"]))
        return ReferenceRecord(
            id=int(row["id"]),
            title=str(row["title"]),
            summary=str(row["summary"]),
            url=str(row["url"]) if row["url"] else None,
            language=str(row["language"]),
            source=str(row["source"]) if row["source"] else None,
            captured_at=str(row["captured_at"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            tags=tags,
            metadata=metadata if isinstance(metadata, dict) else {},
        )

    def _tags_for_reference(self, reference_id: int) -> tuple[str, ...]:
        rows = self.conn.execute(
            """
            SELECT t.name
            FROM tags t
            JOIN reference_tags rt ON rt.tag_id = t.id
            WHERE rt.reference_id = ?
            ORDER BY t.name
            """,
            (reference_id,),
        ).fetchall()
        return tuple(str(row["name"]) for row in rows)

    def _like_search(self, query: str, *, limit: int) -> list[sqlite3.Row]:
        like = f"%{query}%"
        return self.conn.execute(
            """
            SELECT *
            FROM reference_records
            WHERE title LIKE ? OR summary LIKE ? OR url LIKE ?
            ORDER BY captured_at DESC
            LIMIT ?
            """,
            (like, like, like, limit),
        ).fetchall()

    def _find_by_content_hash_scan(self, content_hash: str) -> ReferenceRecord | None:
        rows = self.conn.execute("SELECT * FROM reference_records").fetchall()
        for row in rows:
            metadata = json.loads(str(row["metadata_json"] or "{}"))
            if isinstance(metadata, dict) and metadata.get("content_hash") == content_hash:
                return self._record_from_row(row)
        return None

    def _load_sqlite_vec(self) -> Any | None:
        try:
            import sqlite_vec
        except ImportError:
            return None
        self.conn.enable_load_extension(True)
        try:
            sqlite_vec.load(self.conn)
        finally:
            self.conn.enable_load_extension(False)
        return sqlite_vec

    def _serialize_vector(self, embedding: list[float]) -> bytes:
        if self._sqlite_vec is None:
            raise RuntimeError("sqlite_vec is not loaded")
        return self._sqlite_vec.serialize_float32(embedding)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_FTS_MIN_TOKEN_LEN = 3

# Stop words filtered out before building the FTS MATCH expression so common
# question-shaped tokens like "what", "the", "is", "de", "para" do not dilute
# BM25 ranking with prefix-OR noise.
_FTS_STOP_WORDS = frozenset({
    # English
    "a", "about", "an", "and", "are", "as", "at", "be", "been", "being",
    "but", "by", "can", "could", "did", "do", "does", "doing", "done",
    "for", "from", "had", "has", "have", "having", "how", "i", "if", "in",
    "into", "is", "it", "its", "me", "my", "of", "on", "or", "should",
    "some", "such", "that", "the", "their", "them", "then", "there",
    "these", "they", "this", "those", "to", "was", "we", "were", "what",
    "when", "where", "which", "who", "whom", "why", "will", "with",
    "would", "you", "your",
    # Spanish
    "al", "como", "con", "cual", "cuando", "de", "del", "donde", "el", "en",
    "es", "esta", "este", "la", "las", "lo", "los", "mi", "mis", "no", "o",
    "para", "por", "que", "quien", "se", "si", "su", "sus", "te", "tu", "un",
    "una", "unas", "unos", "y", "ya", "yo",
})


def _fts_match_query(query: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9_]+", query.lower())
    meaningful = [
        token for token in tokens
        if len(token) >= _FTS_MIN_TOKEN_LEN and token not in _FTS_STOP_WORDS
    ]
    # If filtering removed every token (very short or all stop words), fall
    # back to the raw token list so we still return something for the FTS leg.
    chosen = meaningful or tokens
    return " OR ".join(f"{token}*" for token in chosen)


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)
