# adapters/

**Depends on:** `ports`, `infrastructure` for logging, external SDKs.
**Used by:** `delivery`.

## Files

- `gemini/client.py` — raw Gemini API call and JSON client.
- `gemini/logging_classifier.py` — logs prompt/response exchanges around Gemini calls.
- `gemini/response_parser.py` — extracts raw response text and parses JSON.
- `google_tasks/auth.py` — OAuth Desktop App credentials and service creation.
- `google_tasks/repository.py` — Google Tasks CRUD and `TaskListRepository`.
- `icloud/hydrate.py` / `icloud/json_reader.py` — iCloud hydration and JSON capture reads.
- `sqlite_reference_store/` — SQLite reference storage, tags, FTS, and vector index.
- `qwen_embedder.py` — lazy sentence-transformers adapter for Qwen3 embeddings.

## Invariants

- SDK-specific types stay in adapters.
- The raw Gemini client has no log-file side effects.
