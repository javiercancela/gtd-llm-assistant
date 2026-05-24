# delivery/

**Depends on:** application use cases plus concrete adapters/infrastructure.
**Used by:** the `main` console script (`gtd_assistant.delivery.cli:main`).

## Files

- `cli.py` — resolves config, constructs real dependencies, and starts one inbox run.
- `mcp_server.py` — runs the stdio MCP server for searching and adding references.

## Invariants

- Delivery wires dependencies only; processing logic belongs in `application/`.
