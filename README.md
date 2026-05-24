# gtd-llm-assistant

Watches a Shortcuts / iCloud workflow folder for `*.json` drops, classifies
each capture with Gemini, creates deduped Google Tasks entries, moves completed
files to `processed/`, and writes daily JSON-line logs.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the run path, layer map, and edit
points.

## Run Locally

```bash
uv run main
```

Direct module entry point:

```bash
uv run python -m gtd_assistant.delivery.cli
```

The legacy direct script still works for launchd compatibility:

```bash
uv run python src/main.py
```

## Configuration

Copy the example env file and set secrets/list IDs as needed:

```bash
mkdir -p ~/.config/gtd-llm-assistant
cp config/env.example ~/.config/gtd-llm-assistant/env
chmod 600 ~/.config/gtd-llm-assistant/env
```

Required:

- `GEMINI_API_KEY`

Optional path overrides:

- `GTD_WATCH_DIR`
- `GTD_INBOX_DIR`
- `GTD_PROCESSED_DIR`
- `GTD_LOGS_DIR`

Optional Google Tasks list overrides:

- `GTD_TASKLIST_PERSONAL`
- `GTD_TASKLIST_WORK`
- `GTD_TASKLIST_WAITING_FOR`
- `GTD_TASKLIST_REFERENCE`

## Google Tasks OAuth

Use a Google Cloud OAuth Client ID of type **Desktop app**. Save the downloaded
file as `client_secret.json` in the project root. The adapter writes `.token.json`
after the first consent flow.

To list tasklists:

```bash
uv run python -c "
from gtd_assistant.adapters.google_tasks.repository import list_tasklists
for tl in list_tasklists():
    print(tl.get('title'), tl.get('id'))
"
```

## Logs

Logs live under the configured logs directory:

- `inbox_YYYY-MM-DD.log` — run lifecycle, classification summary, publish
  results, and errors.
- `gemini_YYYY-MM-DD.log` — prompts and raw model answer text, or error text.

## Tests

```bash
uv run pytest
```

## launchd

The plist runs `scripts/run-launchd.sh`, which sources
`~/.config/gtd-llm-assistant/env` or `GTD_LLM_ASSISTANT_ENV` before starting
Python.

Install:

```bash
chmod +x scripts/run-launchd.sh
cp com.javiercancela.gtdllmassistant.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.javiercancela.gtdllmassistant.plist
```

Reload after changes:

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.javiercancela.gtdllmassistant.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.javiercancela.gtdllmassistant.plist
```
