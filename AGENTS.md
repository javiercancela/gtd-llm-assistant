# Agent Guide

Read [ARCHITECTURE.md](ARCHITECTURE.md) before structural changes. It maps the
run path, layers, extension points, env vars, and commands.

- Entry point: CLI command `main` → `gtd_assistant.delivery.cli:main`.
- launchd wrapper: `scripts/run-launchd.sh`, which sources
  `~/.config/gtd-llm-assistant/env` or `GTD_LLM_ASSISTANT_ENV`.
- Config: `src/gtd_assistant/infrastructure/config.py` for paths and
  `src/gtd_assistant/infrastructure/gtd_task_lists.py` for tasklist IDs.
- For questions about saved/local references, run
  `uv run gtd-references-query "$USER_QUESTION" --limit 8 --format markdown`,
  then answer from the returned local references and include relevant URLs or
  local document paths. If no strong references are returned, say so.
- Do not import adapters from `domain/` or `application/`; use ports and fakes.
- Do not commit credentials or tokens; keep secrets out of logs.
