"""Append-only timestamped lines under the inbox logs directory."""

from datetime import datetime, timezone
from pathlib import Path


def append_inbox_log(logs_dir: Path, level: str, message: str) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = logs_dir / f"inbox_{day}.log"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {level.upper()} {message}\n"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(line)
