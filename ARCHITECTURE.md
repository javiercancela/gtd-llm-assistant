# Architecture

Personal GTD inbox automation: a periodic job that reads JSON drops from an
iCloud-synced watch folder, classifies each capture with Gemini, and turns the
result into Google Tasks entries (with idempotency markers and per-bucket
routing). Successful drops are moved to a `processed` folder; every step
appends a structured line to a daily log under `logs/`.

This document describes the codebase as it stands today. The target layout
(layered: domain → application → ports → adapters → infrastructure) is in
[`docs/refactor-plan.md`](docs/refactor-plan.md). Per-package
`ARCHITECTURE.md` files cover layers introduced by the refactor.

## Run path

1. `main()` in `src/main.py` is the entry point (CLI script `main`, also
   triggered by launchd via `scripts/run-launchd.sh`).
2. It lists `*.json` files under the hardcoded `WATCH` folder.
3. For each candidate:
   - `inbox_json.load_json_file` reads the payload, waiting on iCloud
     hydration (`icloud_download.ensure_icloud_file_local`) when needed.
   - `application.classify_capture.classify_capture` returns `(language, items)`
     through the `services.gemini.classify_message` compatibility wrapper.
   - `services.tasks.create_item_from_classification` routes each item to a
     Google Tasks list (creating, deduping, or appending subtasks).
   - The drop is moved into `processed/`.
4. Every action appends a JSON line to `inbox_YYYY-MM-DD.log`; Gemini
   prompts/answers go to `gemini_YYYY-MM-DD.log`.

## Layer map (current)

| Layer | Directory / file | Responsibility |
|-------|------------------|----------------|
| Entry | `src/main.py` | Pipeline loop, hardcoded paths, top-level error handling. |
| Domain helpers | `src/domain/` | Language detection, normalization, routing, dedupe. |
| Application | `src/application/classify_capture.py`, `src/application/publish_classified_item.py` | Orchestrate classification and publishing through ports. |
| Prompts | `src/services/prompts.py` | English (classify + per-type enrich) and Spanish (single) prompt templates. |
| Adapters | `src/adapters/gemini/`, `src/adapters/gcloud_tasks.py`, `src/adapters/gcloud_auth.py` | Thin wrappers over `google-genai` and Google Tasks SDKs. |
| Infrastructure | `src/inbox_json.py`, `src/icloud_download.py`, `src/inbox_log.py`, `src/gemini_log.py`, `src/services/tasklists.py` | iCloud-aware JSON reads, hydration, log files, tasklist IDs. |

## Classification flow

- Spanish path (payload has `text_es`): one Gemini call with
  `CLASSIFY_SPANISH_PROMPT`. Items are normalized via
  `domain.classified_item.normalize_spanish_item`.
- English path: two Gemini calls — first `CLASSIFY_ENGLISH_PROMPT` to assign a
  `type` per capture, then a type-specific enrichment prompt (`TASK_…`,
  `PROJECT_…`, `REFERENCE_…`, `WAITING_FOR_…`). Items normalized via
  `domain.classified_item.normalize_english_item`. Project enrichment receives
  the current Work-list project titles through `TaskListRepository` so the LLM
  can reuse existing projects without importing the Google Tasks adapter.

## Publishing flow

- Routing: `domain.routing.gtd_list_for(item_kind, language, tasklists)` maps
  to a tasklist ID. Spanish always routes to Personal; English routes by kind
  (`reference` → Reference, `waiting_for` → Waiting For, otherwise Work).
- Idempotency: every created task gets an `inbox_hash:<16-hex>` line in its
  notes (`domain.dedupe`). Re-runs of the same drop find the marker and skip.
- Projects: a parent task is created and the classified subtasks (or a single
  `Define next action` placeholder) are inserted under it. When the LLM
  returns `existing_project_title`, the subtasks are appended to that project
  instead of creating a new one.

## Key types (canonical dict shapes today)

- **Capture** — raw workflow JSON: `{text, text_es?, language?, url?, …}`.
- **Classified item** — `{type, title, description, url?, subtasks?, existing_project_title?}` where `type ∈ {task, project, reference, waiting_for}`.
- **Publish result** — `{status: created|deduped|updated, task_id, tasklist, type}`.

Dataclass-backed versions of these are planned in the refactor (see
`docs/refactor-plan.md` §5).

## Extension points

- Add or change routing: `src/domain/routing.py`.
- Change idempotency hashing: `src/domain/dedupe.py`.
- Change classification prompts: `src/services/prompts.py`.
- Change normalization of LLM output: `src/domain/classified_item.py`.
- Change language detection: `src/domain/language.py`.
- Add / swap a tasklist destination: `src/services/tasklists.py` plus
  `domain.routing.gtd_list_for` if the routing rule itself changes.

## Configuration

- `GEMINI_API_KEY` — required by the Gemini adapter.
- `GTD_TASKLIST_PERSONAL|WORK|WAITING_FOR|REFERENCE` — override the default
  tasklist IDs in `src/services/tasklists.py`.
- Paths (watch / inbox / processed / logs) are hardcoded at the top of
  `src/main.py`; moved to a config module during refactor phase 4.
- Secrets and tokens must never be committed; logs must not contain API keys.

## Commands

- `uv run main` — run one pass over the watch folder.
- `uv run pytest` — run the unit tests in `tests/`.
