# domain/

**Depends on:** standard library only.
**Used by:** `application/`.

Pure functions and constants that encode GTD business rules. No I/O, no
network, no SDK imports.

## Files

- `item_kind.py` — valid GTD kinds (`task` / `project` / `reference` /
  `waiting_for`) and the Spanish-label → kind map used by the LLM output.
- `language.py` — `detect_language_from_capture(capture)`, plus the Spanish
  hint set used by the heuristic.
- `classified_item.py` — `normalize_spanish_item`, `normalize_english_item`:
  map raw LLM dicts into the canonical `{type, title, description, …}` shape.
- `routing.py` — `gtd_list_for(item_kind, language, *, tasklists)`: returns
  the tasklist ID for a classified item.
- `dedupe.py` — `dedupe_marker(source_name, item)` and
  `notes_with_marker(notes, marker)` plus the `inbox_hash:` prefix.

## Invariants

- Functions take and return plain values (dicts, strings, sets); no side
  effects, no globals beyond constants in this package.
- No imports from `adapters/`, `google.*`, `Foundation`, or any module that does I/O.
