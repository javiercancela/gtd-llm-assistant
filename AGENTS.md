# Agent guide

Personal GTD inbox automation: watch a folder for JSON drops, classify each payload with Gemini, move successful files under the inbox `processed` directory, append structured lines to daily log files under the inbox `logs` directory, and use the data classified by Gemini to create tasks and projects in Google Tasks.

- **Entry point:** CLI command `main` (configured in `pyproject.toml`) invoking `src/main.py` (`main()`), intended to be invoked periodically by macOS `launchd` via `scripts/run-launchd.sh` (sources `~/.config/gtd-llm-assistant/env` for `GEMINI_API_KEY`).
- **Paths:** Inbox-related roots are defined at the top of `src/main.py` (watch folder, inbox, `processed`, `logs`).
- **Logging helpers:** `src/inbox_log.py` — run/task lines per UTC day (`inbox_YYYY-MM-DD.log`); `src/gemini_log.py` — prompt and answer lines per UTC day (`gemini_YYYY-MM-DD.log`).
- **iCloud hydration:** `src/icloud_download.py` — `startDownloadingUbiquitousItem` + status polling on macOS (PyObjC).
- **Inbox JSON I/O:** `src/inbox_json.py` — read workflow drops from iCloud (hydration first), then retries and a local-copy fallback.
- **Prompt text:** `src/services/prompts.py` — English type classification plus per-type enrichment prompts (task, project, reference, waiting_for); Spanish uses a single combined prompt.
- **Gemini orchestration:** `src/application/classify_capture.py` — `classify_capture(data, ...)` uses Spanish when the payload has `text_es`; English runs `CLASSIFY_ENGLISH_PROMPT` then a type-specific enrichment prompt. `src/services/gemini.py` remains the compatibility wrapper for current callers.
- **Gemini adapter:** `src/adapters/gemini/` — thin `call_gemini(prompt, model)` wrapper and response parser over the official `google-genai` SDK.
- **Google Tasks adapter:** `src/adapters/gcloud_tasks.py` — list tasklists/tasks/projects and create tasks, projects, and subtasks on a selected tasklist.
- **Google Tasks auth:** `src/adapters/gcloud_auth.py` — OAuth Desktop App flow; requires `client_secret.json` (`installed` client type) in the project root and writes `.token.json`.
- **Tasklist IDs:** `src/services/tasklists.py` — GTD bucket IDs (PERSONAL / WORK / WAITING_FOR / REFERENCE), overridable via `GTD_TASKLIST_*` in `~/.config/gtd-llm-assistant/env`.

Do not commit credentials or tokens; keep secrets out of logs.
