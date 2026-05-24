# Architecture

Personal GTD inbox automation: a periodic job reads JSON drops from an
iCloud-synced watch folder, classifies each capture with Gemini, publishes
deduped Google Tasks entries or saved references, moves successful drops to
`processed/`, and logs run/Gemini exchanges under `logs/`.

## Run Path

1. CLI script `main` invokes `gtd_assistant.delivery.cli:main`.
2. `infrastructure.config.load_inbox_config` resolves watch, inbox, processed,
   and logs paths from env with current local defaults.
3. `application.process_inbox_run.process_all_pending_captures` lists pending
   `*.json` files, reads each capture, classifies it, publishes each task item
   to Google Tasks, saves each English reference item to SQLite, then archives
   the original file.
4. `adapters.icloud.json_reader` handles iCloud hydration and retry/copy
   fallback.
5. `adapters.gemini` calls Gemini and parses JSON; `logging_classifier` writes
   prompt/answer log lines.
6. `adapters.google_tasks.repository` creates, dedupes, updates, and nests
   Google Tasks through the application publishing use case.
7. `adapters.sqlite_reference_store.repository` stores references, tags, FTS
   rows, and embeddings for the reference use cases and MCP server.

## Layer Map

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| Delivery | `src/gtd_assistant/delivery/` | Build real dependencies and start a run. |
| Application | `src/gtd_assistant/application/` | Classify captures, publish items, process inbox files through ports. |
| Domain | `src/gtd_assistant/domain/` | Pure GTD rules: language, kind normalization, routing, dedupe. |
| Ports | `src/gtd_assistant/ports/` | Protocols for LLM, capture reader, task repository, run logger. |
| Adapters | `src/gtd_assistant/adapters/` | Gemini, Google Tasks, and iCloud implementations. |
| Infrastructure | `src/gtd_assistant/infrastructure/` | Env config, tasklist IDs, daily log files. |
| Prompts | `src/gtd_assistant/prompts/` | Prompt templates for English and Spanish classification. |

## Key Shapes

- **Capture:** raw workflow JSON, usually `{text, text_es?, language?, url?, ...}`.
- **Classified item:** `{type, title, description, summary?, url?, tags?, subtasks?, existing_project_title?}`.
- **Publish result:** `{status: created|deduped|updated, task_id, tasklist, type}`.
- **Reference record:** `{id, title, summary, url?, tags, captured_at, metadata}`.

## Extension Points

- Change routing: `src/gtd_assistant/domain/routing.py`.
- Change dedupe notes/hash: `src/gtd_assistant/domain/dedupe.py`.
- Change language detection: `src/gtd_assistant/domain/language.py`.
- Change prompt text: `src/gtd_assistant/prompts/templates.py`.
- Change path config: `src/gtd_assistant/infrastructure/config.py`.
- Change Google Tasks API behavior: `src/gtd_assistant/adapters/google_tasks/repository.py`.
- Change reference storage/search: `src/gtd_assistant/adapters/sqlite_reference_store/repository.py`.
- Change MCP reference tools: `src/gtd_assistant/delivery/mcp_server.py`.

## Secrets And Logs

- `GEMINI_API_KEY` is required for live Gemini calls.
- `GTD_TASKLIST_PERSONAL|WORK|WAITING_FOR|REFERENCE` override Google Tasks list IDs.
- `GTD_WATCH_DIR`, `GTD_INBOX_DIR`, `GTD_PROCESSED_DIR`, and `GTD_LOGS_DIR`
  override filesystem paths.
- `GTD_REFERENCE_DB` overrides the local SQLite reference database path.
- Never commit credentials or tokens. Log files are JSON lines named
  `inbox_YYYY-MM-DD.log` and `gemini_YYYY-MM-DD.log`.

## Commands

- `uv run main` — run one pass over the watch folder.
- `uv run gtd-references-mcp` — run the local stdio MCP server for references.
- `uv run pytest` — run the test suite.
