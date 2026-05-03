# Agent guide

Personal GTD inbox automation: watch a folder for JSON drops, process them (LLM/API wiring lives in `src/main.py`), move successful files under the inbox `processed` directory, and append structured lines to daily log files under the inbox `logs` directory.

- **Entry point:** `src/main.py` (`main()`), intended to be invoked periodically by macOS `launchd`.
- **Paths:** Inbox-related roots are defined at the top of `src/main.py` (watch folder, inbox, `processed`, `logs`).
- **Logging helper:** `src/inbox_log.py` — timestamped append-only lines per UTC day (`inbox_YYYY-MM-DD.log`).
- **Prompt text:** `src/prompt_template.py` — classification schema for future LLM calls.

Do not commit credentials or tokens; keep secrets out of logs.
