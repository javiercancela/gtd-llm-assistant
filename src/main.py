import shutil
import traceback
from pathlib import Path

from inbox_log import append_inbox_log

WATCH = Path("/Users/javier.cancela/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents")
INBOX = Path("/Users/javier.cancela/Library/Mobile Documents/com~apple~CloudDocs/GTD/00_Inbox")
PROCESSED = INBOX / "processed"
INBOX_LOGS = INBOX / "logs"


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    INBOX_LOGS.mkdir(parents=True, exist_ok=True)

    candidates = sorted(
        f
        for f in WATCH.glob("*.json")
        if not (f.name.startswith(".") or f.name.endswith(".icloud"))
    )
    append_inbox_log(
        INBOX_LOGS,
        "info",
        f"run start watch={WATCH} candidates={len(candidates)}",
    )

    for f in candidates:
        try:
            # process(f), call Google API, etc.
            dest = PROCESSED / f.name
            shutil.move(str(f), str(dest))
            append_inbox_log(
                INBOX_LOGS,
                "ok",
                f"moved {f.name} -> processed/{dest.name}",
            )
        except Exception as exc:
            append_inbox_log(
                INBOX_LOGS,
                "error",
                f"{f.name}: {exc!s}\n{traceback.format_exc()}",
            )

    append_inbox_log(INBOX_LOGS, "info", "run complete")


if __name__ == "__main__":
    main()
