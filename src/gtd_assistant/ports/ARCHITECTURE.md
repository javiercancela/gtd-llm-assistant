# ports/

**Depends on:** standard library typing only.
**Used by:** `application`, implemented by `adapters` and `infrastructure`.

## Files

- `llm.py` — `JsonLlm.complete_json(prompt)`.
- `task_lists.py` — narrow Google Tasks repository operations.
- `capture_reader.py` — reads one capture payload from a path.
- `run_logger.py` — run log levels used by inbox processing.

## Invariants

- Ports describe behavior only; no SDK, filesystem, or network imports.
