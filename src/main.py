import shutil
import traceback
from pathlib import Path

from services.gemini import classify_message
from inbox_json import load_json_file
from inbox_log import append_inbox_log
from services.tasks import create_item_from_classification

WATCH = Path("/Users/javier.cancela/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents")
INBOX = Path("/Users/javier.cancela/Library/Mobile Documents/com~apple~CloudDocs/GTD/00_Inbox")
PROCESSED = INBOX / "processed"
INBOX_LOGS = INBOX / "logs"


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    INBOX_LOGS.mkdir(parents=True, exist_ok=True)

    candidates = sorted(f for f in WATCH.glob("*.json") if not (f.name.startswith(".") or f.name.endswith(".icloud")))
    append_inbox_log(
        INBOX_LOGS,
        "info",
        f"run start watch={WATCH} candidates={len(candidates)}",
    )

    for f in candidates:
        try:
            data = load_json_file(
                f,
                on_waiting_for_sync=lambda message: append_inbox_log(INBOX_LOGS, "info", message),
            )
            language, items = classify_message(data, logs_dir=INBOX_LOGS)
            append_inbox_log(INBOX_LOGS, "info", f"classified {f.name} lang={language} items={len(items)}")

            source_url = str(data.get("url", "")).strip() or None
            for item in items:
                task_result = create_item_from_classification(
                    source_name=f.name,
                    item=item,
                    language=language,
                    source_url=source_url,
                )
                append_inbox_log(
                    INBOX_LOGS,
                    "ok",
                    (
                        f"task {task_result['status']} file={f.name} "
                        f"type={task_result['type']} task_id={task_result['task_id']} "
                        f"tasklist={task_result['tasklist']}"
                    ),
                )

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
