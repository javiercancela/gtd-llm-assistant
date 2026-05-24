# Plan: First-class reference store with LLM access via MCP

## 0. Decisions already settled

These were chosen before the plan was written and the rest of the document assumes them:

- **Content depth:** URL + LLM-generated summary only. No page fetching, no archival.
- **Retrieval:** Hybrid — keyword (SQLite FTS5) and semantic (embeddings) exposed as separate MCP tools, plus one hybrid tool that fuses them.
- **Access surface:** Local MCP server over stdio. Phone access happens via remote desktop into the Mac, so no networking, auth, or remote transport needs to be designed.
- **Google Tasks Reference list:** Replaced. New captures stop publishing references to Google Tasks. A one-shot migration script imports the existing Reference list into the new store.

## 1. What the system has to do

Capture-time path: when the inbox pipeline classifies an item as `reference`, the LLM already produces `{title, summary, url}`. Today that gets turned into a Google Tasks entry. After this change, it gets written to a local SQLite database with an embedding, and the Reference tasklist is left alone.

Query-time path: an MCP server runs locally and exposes tools to search, list, and fetch references. Claude Desktop, Claude Code, and Codex CLI all support stdio MCP servers, so the same server works in all three.

## 2. Storage

One SQLite file. Default path `~/.local/share/gtd-llm-assistant/references.sqlite3`, overridable with `GTD_REFERENCE_DB`.

Schema:

```
references(
  id            INTEGER PRIMARY KEY,
  url           TEXT,                       -- nullable; some references are just notes
  title         TEXT NOT NULL,
  summary       TEXT NOT NULL DEFAULT '',
  language      TEXT NOT NULL DEFAULT 'en',
  source        TEXT,                       -- capture file name, "migration:gtasks", "manual", ...
  captured_at   TEXT NOT NULL,              -- ISO-8601 UTC; when the item was captured upstream
  created_at    TEXT NOT NULL,              -- ISO-8601 UTC; row creation
  updated_at    TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}'  -- free-form: domain, gtasks_id, etc.
)

tags(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL)
reference_tags(reference_id INTEGER, tag_id INTEGER, PRIMARY KEY (reference_id, tag_id))

references_fts -- FTS5 contentless virtual table: title, summary, url, tags_text
references_vec -- sqlite-vec vec0 virtual table: rowid -> embedding (FLOAT[D])
```

`references_fts` and `references_vec` are kept in sync with `references` via triggers (or via the repository on every write — simpler than triggers, and the volume here is tiny).

Unique constraint: `url` when non-null, to prevent duplicate captures of the same URL. URL-less references dedupe by `(title, summary)` hash stored in `metadata_json`.

**Why SQLite + sqlite-vec rather than a dedicated vector DB:** single file, no daemon, no server, no schema-migration tooling needed for a personal store of (realistically) low thousands of rows. `sqlite-vec` is a tiny loadable extension actively maintained by Alex Garcia; runs on the macOS stdlib `sqlite3`. If it ever doesn't fit, the data is portable.

**Risk to validate up front:** macOS Python `sqlite3` must have `enable_load_extension` available. Quick check: `python -c "import sqlite3; c=sqlite3.connect(':memory:'); c.enable_load_extension(True)"`. If this fails on the user's Python build, fall back to `pysqlite3-binary`.

## 3. Embeddings

One port, two adapters:

- `Embedder` port: `embed(texts: list[str]) -> list[list[float]]` plus a `dimension` property.
- Default adapter: **Gemini** `text-embedding-004` (768d). Uses the existing `GEMINI_API_KEY`, so no new credentials. Batches of up to 100.
- Optional adapter: **Ollama** `nomic-embed-text` (768d) for fully-offline mode. Same dimension, so the schema doesn't change.

Selected via `GTD_EMBEDDER=gemini|ollama` (default `gemini`).

What gets embedded per reference: `title + "\n\n" + summary + "\n\n" + url`. Embedding only happens on insert and on explicit re-embed; queries embed the query string once.

**Dimension is locked at first insert.** Switching models means re-embedding everything. The migration script supports `--reembed-all`.

## 4. New code layout

Fits the existing hex-arch.

```
src/gtd_assistant/
  domain/
    reference.py                 # Reference dataclass, ReferenceQuery, hash helpers
  ports/
    reference_store.py           # ReferenceStore protocol
    embedder.py                  # Embedder protocol
  application/
    save_reference.py            # use case: normalize + embed + upsert
    search_references.py         # use case: keyword / semantic / hybrid
  adapters/
    sqlite_reference_store/
      schema.py                  # CREATE TABLE/INDEX/FTS/VEC + migrations
      repository.py              # ReferenceStore impl
    embedders/
      gemini.py                  # Embedder impl over google-genai
      ollama.py                  # Embedder impl over local Ollama HTTP
  infrastructure/
    reference_config.py          # paths, embedder selection, dimension
  delivery/
    mcp_server.py                # stdio MCP server entry point (separate console script)
```

The existing `application/publish_classified_item.py` keeps doing what it does for tasks, projects, and waiting-for. For `reference`, it delegates to `save_reference` instead of the Google Tasks path. Routing in `domain/routing.py` no longer needs the `BUCKET_REFERENCE` branch for the publish path — it stays for backward-compat tests, then can be removed in a follow-up.

## 5. MCP server

Uses the official `mcp` Python SDK (`pip install mcp`) with stdio transport. Registered as a `[project.scripts]` entry point: `gtd-references-mcp = "gtd_assistant.delivery.mcp_server:main"`. Users wire it into Claude Desktop, Claude Code, and Codex CLI by pointing their MCP config at that command.

Tools exposed (intentionally small surface):

| Tool | Args | Returns |
|---|---|---|
| `search_references` | `query: str, limit: int = 10` | hybrid results (RRF fusion of FTS + vector) |
| `search_references_keyword` | `query: str, limit: int = 10` | FTS5 match results with snippets |
| `search_references_semantic` | `query: str, limit: int = 10` | vector cosine top-k |
| `list_references` | `tag?: str, since?: ISO, until?: ISO, limit: int = 50` | filtered chronological list |
| `get_reference` | `id: int` | one full record |
| `list_tags` | — | tag names with counts |
| `add_reference` | `url?: str, title?: str, summary?: str, tags?: list[str]` | created record (manual add path) |

Deliberately **not** in v1: delete, edit, bulk export, re-embed. They can be added once daily use proves they're needed; until then the CLI can do them.

Hybrid fusion: Reciprocal Rank Fusion with `k=60` over the two ranked lists. Simple, no tuning knobs, and well-behaved when one source returns nothing.

## 6. Capture-path change

In `application/process_inbox_run.process_one_capture`, the loop currently calls `publish_classified_item` for every item. Change it to:

- If `item["type"] == "reference"`: call `save_reference(store=..., embedder=..., item=..., capture=..., source_name=path.name)`. Log a result row identical in shape to the current task results (`status`, `task_id` → reference id, `tasklist` → `"references-db"`, `type`).
- Otherwise: unchanged.

`save_reference` is idempotent on URL: if the URL already exists, return `status="deduped"` with the existing id. No embeddings re-computed in that case.

`delivery/cli.py` grows one new dependency wire-up (open the SQLite store, build the embedder) and passes it into `InboxRunDependencies`. The protocol gains two fields; existing tests using `InboxRunDependencies` get fakes.

## 7. One-shot migration from Google Tasks

Standalone script at `scripts/migrate_references_from_gtasks.py`, invoked by hand once:

1. Auth into Google Tasks with the existing OAuth flow.
2. List every task in the Reference tasklist (`GTD_TASKLIST_REFERENCE`).
3. For each task, parse `notes` into `summary` + `url`. Heuristic: if the last non-empty line is a URL, that's the URL; the rest is the summary. Else inspect the task's `links` field.
4. Build a `Reference` with `source="migration:gtasks"`, `captured_at = task.updated`, `metadata_json.gtasks_id = task.id`.
5. Embed in batches, upsert. Dedupe on URL; rows missing a URL dedupe on title+summary hash.
6. Print a summary: `migrated=N skipped=M failed=K`. Failures go to a log file, not stderr.

Dry-run flag prints what would happen without writing.

## 8. Configuration

New env vars (added to `config/env.example`):

```
GTD_REFERENCE_DB=~/.local/share/gtd-llm-assistant/references.sqlite3
GTD_EMBEDDER=gemini                # gemini | ollama
GEMINI_EMBED_MODEL=text-embedding-004
OLLAMA_HOST=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
```

`GTD_TASKLIST_REFERENCE` stays defined so the migration script can read it, but the runtime path no longer uses it.

## 9. Testing strategy

Hex layers already make this clean:

- `domain/reference.py` — pure tests for the dataclass, URL hashing, dedupe key.
- `application/save_reference.py` — tests against a `FakeReferenceStore` and a `FakeEmbedder` (returns deterministic vectors).
- `application/search_references.py` — tests that hybrid fusion behaves correctly with synthetic ranked lists.
- `adapters/sqlite_reference_store/` — integration tests against `:memory:` SQLite with sqlite-vec loaded; verifies schema, FTS, vector top-k, triggers/sync.
- `adapters/embedders/gemini.py` — not tested live in CI; covered by a contract test that the adapter conforms to `Embedder`.
- `delivery/mcp_server.py` — one smoke test that boots the server in-process and round-trips a `search_references` call against a populated `:memory:` store.

## 10. Phased implementation

Each step has a verify check so the build can loop without me asking. Order is chosen so something is usable at every phase.

1. **Domain + ports + fakes.**
   Add `Reference`, `ReferenceQuery`, `ReferenceStore` protocol, `Embedder` protocol, `FakeReferenceStore`, `FakeEmbedder`.
   *Verify:* unit tests pass; nothing imports adapters from domain.

2. **SQLite adapter with schema + keyword search.**
   Implement schema, repository, FTS5. Skip vec table in this step.
   *Verify:* in-memory integration test inserts 3 rows, FTS query returns them ranked.

3. **`save_reference` use case + capture-path wiring + Gemini embedder + vec table.**
   Add embedder, vec0 table, semantic search. Hook into `process_one_capture` so live captures classified as reference write to SQLite instead of Google Tasks.
   *Verify:* run the inbox over a fixture capture marked as reference; the row exists in the DB with a non-empty embedding and no Google Tasks call is made.

4. **Migration script.**
   Build and run with `--dry-run`.
   *Verify:* dry-run counts match the live Reference tasklist size; one real run, then spot-check 3 random rows for correct URL/summary parsing.

5. **MCP server.**
   Implement the seven tools above, register as a console script.
   *Verify:* boot the server stdio in a test, call each tool, assert shapes. Then add it to Claude Desktop / Codex MCP config and run one real query end-to-end.

6. **Cleanup.**
   Remove the `BUCKET_REFERENCE` publish branch (or leave it dormant with a comment if the test suite still hits it). Update `ARCHITECTURE.md` to mention the reference store and MCP server. Add an `ARCHITECTURE.md` inside the new subpackages following the existing per-layer-doc convention.
   *Verify:* `uv run pytest` green; `uv run main` succeeds on a fixture batch; MCP server runs from Claude Desktop.

## 11. Open questions worth resolving before step 5

- **Tags.** Right now the LLM doesn't produce tags. Options: (a) skip tags entirely in v1, (b) extend the `REFERENCE_ENGLISH_PROMPT` to also produce 2–5 tags, (c) generate tags lazily later. Recommend (b) — costs nothing extra at classify time and immediately makes `list_references` useful for browsing without a query.
- **MCP tool descriptions.** These matter a lot for how well Claude/Codex pick the right tool. I'll draft them in step 5 and iterate based on observed picks.
- **Backups.** A SQLite file on the Mac is one disk failure away from gone. Easiest answer: put the DB path inside iCloud Drive or Time Machine's coverage. Not in scope for this plan but worth deciding before step 4 since the migration would be painful to redo.
