# prompts/

**Depends on:** no project modules.
**Used by:** `application.classify_capture`.

## Files

- `templates.py` — English classify prompt, English type-specific enrich prompts,
  and the Spanish one-pass prompt.

## Invariants

- Change classify prompts when item type selection is wrong.
- Change enrich prompts when title, description, URL, or subtasks extraction is wrong.
