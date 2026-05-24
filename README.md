# gtd-llm-assistant

Watches a Shortcuts / iCloud workflow folder for `*.json` files, classifies each payload via Gemini, moves completed files into the GTD inbox `processed` subfolder, and writes **OK** / **ERROR** (and run **INFO**) lines under the inbox `logs` directory.

## Run locally

From the repo root:

```bash
uv run main
```

Alternative options:

```bash
uv run python src/main.py
```

Or (ensures `src` is on the module path):

```bash
PYTHONPATH=src python3 -m main
```

```bash
cd src && python3 main.py
```

## Gemini authentication

- Set `GEMINI_API_KEY` in the environment where the job runs (shell for `uv run main`, or `~/.config/gtd-llm-assistant/env` for launchd — see below).
- The app uses the official `google-genai` Python SDK (`Client().models.generate_content(...)`) and reads the key from `GEMINI_API_KEY`.
- Model configured in code: `gemini-3-flash-preview`.
- Responses are requested as `application/json` and parsed into the inbox classification schema.
- The app sends requests with an API key and does not use browser OAuth.
- No local token cache file is created.

## Google Tasks helper module

`src/adapters/gcloud_tasks.py` exposes the low-level Google Tasks helpers:

- `list_tasklists()` lists available Google Tasks tasklists for the authenticated account.
- `list_tasks(tasklist)` lists all visible and completed tasks in a tasklist.
- `list_projects(tasklist)` lists parent tasks that currently have subtasks.
- `create_task(tasklist, title, notes=None, due_days_from_now=None)` creates a task.
- `create_project(tasklist, title, notes=None, due_days_from_now=None)` creates a parent task intended to hold subtasks.
- `add_task_to_project(tasklist, project_id, title, notes=None, due_days_from_now=None)` creates a subtask under a project parent task.

OAuth setup lives in `src/adapters/gcloud_auth.py`. All methods require an
explicit `tasklist` (for example, `@default`).

### Tasklist routing

Classified items are routed in `src/services/tasks.py`:

| Classification `type` | Task list (env var) |
|----------------------|---------------------|
| `task` (default) | `GTD_TASKLIST_WORK` |
| `project` | `GTD_TASKLIST_WORK` |
| `reference` | `GTD_TASKLIST_REFERENCE` |
| `waiting_for` | `GTD_TASKLIST_WAITING_FOR` |

JSON payloads that include a `text_es` field are classified with the Spanish prompt and all resulting items are created on `GTD_TASKLIST_PERSONAL` (any type).

Defaults in `src/services/tasklists.py` match this repo owner’s lists. If you get **Task list not found** (HTTP 404), list your lists and set IDs in `~/.config/gtd-llm-assistant/env`:

```bash
cd /path/to/gtd-llm-assistant
uv run python -c "
from adapters.gcloud_tasks import list_tasklists
for tl in list_tasklists():
    print(tl.get('title'), tl.get('id'))
"
```

Override `GTD_TASKLIST_PERSONAL`, `GTD_TASKLIST_WORK`, `GTD_TASKLIST_WAITING_FOR`, or `GTD_TASKLIST_REFERENCE` in env when your list IDs differ.

### Google Tasks OAuth setup

- Use **OAuth Client ID** credentials of type **Desktop app** in Google Cloud Console.
- Save the downloaded JSON as `client_secret.json` in the project root.
- The adapter rejects `web` credentials because local loopback OAuth (`run_local_server`) requires desktop-style installed app credentials.
- The callback port is selected dynamically (`localhost` with an ephemeral port), so no fixed `localhost:8000` redirect URI is required.

## Logs

Logs live under `…/GTD/00_Inbox/logs/` (UTC date in each filename):

- `inbox_YYYY-MM-DD.log` — run lifecycle, classification summary, task creation, and errors. Each line is JSON with `ts`, `level`, and `message`.
- `gemini_YYYY-MM-DD.log` — full prompts sent to Gemini and the raw model answer text. Each line is JSON with `ts`, `model`, `prompt`, and `answer` (or `error` on API failure).

## Prompt behavior

English inbox JSON (no `text_es` field) uses a two-step Gemini flow in `src/services/prompts.py`:

1. `CLASSIFY_ENGLISH_PROMPT` — splits the input and assigns each capture a `type` (`task`, `project`, `reference`, or `waiting_for`).
2. A type-specific enrichment prompt — `TASK_ENGLISH_PROMPT`, `PROJECT_ENGLISH_PROMPT`, `REFERENCE_ENGLISH_PROMPT`, or `WAITING_FOR_ENGLISH_PROMPT` — extracts titles, descriptions, subtasks, URLs, or waiting-for who/what as appropriate.

Spanish payloads (`text_es` present) still use a single `CLASSIFY_SPANISH_PROMPT` with one-shot examples.

## iCloud workflow drops

The watch folder lives under iCloud Drive. Before each read, `src/icloud_download.py` calls macOS `startDownloadingUbiquitousItem` and polls until the file’s iCloud download status is **Current** or **Downloaded** (requires `pyobjc-framework-Cocoa` on macOS). If a JSON file is still not local, reads may return **Resource deadlock avoided** (`errno 11`); `src/inbox_json.py` then retries with backoff (logging each attempt) and tries a timed local copy. Failed files stay in the watch folder for the next run. If you see repeated `waiting for iCloud sync` or `icloud downloading` lines in `inbox_*.log`, that drop was not ready yet—re-run after sync finishes or touch the watch folder again.

## launchd

launchd does not load your shell profile, so `GEMINI_API_KEY` must be provided another way. The plist runs `scripts/run-launchd.sh`, which sources `~/.config/gtd-llm-assistant/env` (or the path in `GTD_LLM_ASSISTANT_ENV`) before starting Python.

One-time secrets setup:

```bash
mkdir -p ~/.config/gtd-llm-assistant
cp config/env.example ~/.config/gtd-llm-assistant/env
# Edit ~/.config/gtd-llm-assistant/env and set GEMINI_API_KEY
chmod 600 ~/.config/gtd-llm-assistant/env
chmod +x scripts/run-launchd.sh
```

Install the agent:

```bash
cp com.javiercancela.gtdllmassistant.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.javiercancela.gtdllmassistant.plist
```

After changing the plist or wrapper, reload:

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.javiercancela.gtdllmassistant.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.javiercancela.gtdllmassistant.plist
```

Verify with:

```bash
launchctl print gui/$(id -u)/com.javiercancela.gtdllmassistant
```
