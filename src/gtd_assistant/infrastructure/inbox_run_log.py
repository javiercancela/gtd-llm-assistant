"""Append-only timestamped lines under the inbox logs directory."""

import json
from datetime import datetime, timezone
from pathlib import Path


class DailyRunLogger:
    """RunLogger backed by daily inbox log files."""

    def __init__(self, logs_dir: Path) -> None:
        self.logs_dir = logs_dir

    def info(self, message: str) -> None:
        append_inbox_log(self.logs_dir, "info", message)

    def ok(self, message: str) -> None:
        append_inbox_log(self.logs_dir, "ok", message)

    def error(self, message: str) -> None:
        append_inbox_log(self.logs_dir, "error", message)


def append_inbox_log(logs_dir: Path, level: str, message: str) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = logs_dir / f"inbox_{day}.log"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = json.dumps(
        {
            "ts": ts,
            "level": level.upper(),
            "message": message,
        },
        ensure_ascii=False,
    )
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{line}\n")
