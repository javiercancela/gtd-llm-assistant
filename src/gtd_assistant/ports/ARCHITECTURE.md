# ports/

**Depends on:** standard library typing only.
**Used by:** `application`, implemented by `adapters` and `infrastructure`.

## Files

- `llm.py` — `JsonLlm.complete_json(prompt)`.
- `task_lists.py` — narrow Google Tasks repository operations.
- `reference_store.py` — storage, listing, and search operations for references.
- `embedder.py` — asymmetric document/query embedding operations.
- `capture_reader.py` — reads one capture payload from a path.
- `run_logger.py` — run log levels used by inbox processing.

## Invariants

- Ports describe behavior only; no SDK, filesystem, or network imports.
