# sqlite_reference_store/

**Depends on:** `domain.reference`, SQLite stdlib, optional `sqlite_vec`.
**Used by:** `delivery`, tests, reference use cases through `ReferenceStore`.

## Files

- `schema.py` — creates the base reference tables, tag join table, FTS index,
  embedding fallback table, and optional sqlite-vec virtual table.
- `repository.py` — implements the `ReferenceStore` port and keeps FTS, tags,
  and vector rows synchronized on writes.

## Invariants

- The repository owns all SQLite-specific SQL and row mapping.
- FTS and vector indexes are updated in the same transaction as the reference
  row.
- If `sqlite_vec` is unavailable, semantic search falls back to brute-force
  cosine over stored JSON embeddings.
