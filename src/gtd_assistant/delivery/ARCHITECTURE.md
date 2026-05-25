# delivery/

**Depends on:** application use cases plus concrete adapters/infrastructure.
**Used by:** the `main` console script (`gtd_assistant.delivery.cli:main`).

## Files

- `cli.py` — resolves config, constructs real dependencies, and starts one inbox run.
- `reference_cli.py` — `gtd-references-query` command: prints Markdown evidence
  for a query against the local SQLite reference store. Supports hybrid
  (FTS + semantic) search by default and `--keyword-only` for fast lookups.

## Invariants

- Delivery wires dependencies only; processing logic belongs in `application/`.
