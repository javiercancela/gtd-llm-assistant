# delivery/

**Depends on:** application use cases plus concrete adapters/infrastructure.
**Used by:** the `main` console script (`gtd_assistant.delivery.cli:main`).

## Files

- `cli.py` — resolves config, constructs real dependencies, and starts one inbox run.

## Invariants

- Delivery wires dependencies only; processing logic belongs in `application/`.
