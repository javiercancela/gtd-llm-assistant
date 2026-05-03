# gtd-llm-assistant

Watches a Shortcuts / iCloud workflow folder for `*.json` files, runs processing (placeholder in `main()` for API calls), moves completed files into the GTD inbox `processed` subfolder, and writes **OK** / **ERROR** (and run **INFO**) lines under the inbox `logs` directory.

## Run locally

From the repo root (ensures `src` is on the module path):

```bash
PYTHONPATH=src python3 -m main
```

Or:

```bash
cd src && python3 main.py
```

## Logs

Logs are appended to `…/GTD/00_Inbox/logs/inbox_YYYY-MM-DD.log` (UTC date in the filename). Each line is prefixed with an ISO-like UTC timestamp and a level (`INFO`, `OK`, `ERROR`).

## launchd

Point your plist `ProgramArguments` at the same interpreter and script you use above (for example `python3` with `PYTHONPATH` set to the repo `src` directory, or a small wrapper shell script that exports `PYTHONPATH` then runs `main`).
