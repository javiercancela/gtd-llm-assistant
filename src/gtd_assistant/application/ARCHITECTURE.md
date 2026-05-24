# application/

**Depends on:** `domain`, `ports`.
**Used by:** `delivery`.

## Files

- `classify_capture.py` — chooses Spanish one-pass vs English classify/enrich flow.
- `publish_classified_item.py` — creates, dedupes, updates, and adds project subtasks.
- `process_inbox_run.py` — processes pending JSON drops and archives successful files.

## Invariants

- Classification never writes to Google Tasks.
- Publishing always applies the dedupe marker before creating a task.
- Failed capture files stay in the watch folder for a later run.
