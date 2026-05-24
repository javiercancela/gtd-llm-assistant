# infrastructure/

**Depends on:** standard library and domain constants for tasklist keys.
**Used by:** `delivery`, adapter logging wrappers.

## Files

- `config.py` — env-backed inbox paths.
- `gtd_task_lists.py` — env-backed Google Tasks list IDs.
- `reference_config.py` — env-backed SQLite reference database path.
- `inbox_run_log.py` — daily run log and `DailyRunLogger`.
- `gemini_exchange_log.py` — daily Gemini prompt/answer log.

## Invariants

- No business classification or routing decisions live here.
- Log helpers never record secrets or API keys.
