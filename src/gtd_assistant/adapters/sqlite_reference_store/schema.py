"""SQLite schema for the first-class reference store."""

from __future__ import annotations

import sqlite3


def ensure_schema(
    conn: sqlite3.Connection,
    *,
    vector_dimension: int,
    vector_available: bool,
) -> None:
    """Create reference tables and search indexes if missing."""
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS reference_records(
          id INTEGER PRIMARY KEY,
          url TEXT UNIQUE,
          dedupe_key TEXT NOT NULL UNIQUE,
          title TEXT NOT NULL,
          summary TEXT NOT NULL DEFAULT '',
          language TEXT NOT NULL DEFAULT 'en',
          source TEXT,
          captured_at TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS tags(
          id INTEGER PRIMARY KEY,
          name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reference_tags(
          reference_id INTEGER NOT NULL REFERENCES reference_records(id) ON DELETE CASCADE,
          tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
          PRIMARY KEY (reference_id, tag_id)
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS references_fts USING fts5(
          title,
          summary,
          url,
          tags_text,
          tokenize = 'porter unicode61'
        );

        CREATE TABLE IF NOT EXISTS reference_embeddings(
          reference_id INTEGER PRIMARY KEY REFERENCES reference_records(id) ON DELETE CASCADE,
          embedding_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_references_captured_at
          ON reference_records(captured_at);
        CREATE INDEX IF NOT EXISTS idx_tags_name
          ON tags(name);
        CREATE INDEX IF NOT EXISTS idx_references_content_hash
          ON reference_records(json_extract(metadata_json, '$.content_hash'));
        """
    )
    if vector_available:
        conn.execute(
            f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS references_vec
            USING vec0(embedding float[{vector_dimension}])
            """
        )
    conn.commit()
