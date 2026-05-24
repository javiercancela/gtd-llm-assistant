"""Environment-backed configuration for inbox processing paths."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_WATCH_DIR = Path(
    "/Users/javier.cancela/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents"
)
DEFAULT_INBOX_DIR = Path(
    "/Users/javier.cancela/Library/Mobile Documents/com~apple~CloudDocs/GTD/00_Inbox"
)


@dataclass(frozen=True)
class InboxConfig:
    """Resolved filesystem roots for one inbox run."""

    watch_dir: Path
    inbox_dir: Path
    processed_dir: Path
    logs_dir: Path


def load_inbox_config() -> InboxConfig:
    """Load path config from environment, preserving current local defaults."""
    watch_dir = _path_from_env("GTD_WATCH_DIR", DEFAULT_WATCH_DIR)
    inbox_dir = _path_from_env("GTD_INBOX_DIR", DEFAULT_INBOX_DIR)
    processed_dir = _path_from_env("GTD_PROCESSED_DIR", inbox_dir / "processed")
    logs_dir = _path_from_env("GTD_LOGS_DIR", inbox_dir / "logs")
    return InboxConfig(
        watch_dir=watch_dir,
        inbox_dir=inbox_dir,
        processed_dir=processed_dir,
        logs_dir=logs_dir,
    )


def _path_from_env(name: str, default: Path) -> Path:
    raw = os.environ.get(name, "").strip()
    return Path(raw).expanduser() if raw else default
