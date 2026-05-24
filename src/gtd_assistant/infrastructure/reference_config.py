"""Environment-backed configuration for the reference database."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_REFERENCE_DB = Path("~/.local/share/gtd-llm-assistant/references.sqlite3")


def load_reference_db_path() -> Path:
    """Return the SQLite database path for saved references."""
    raw = os.environ.get("GTD_REFERENCE_DB", "").strip()
    return Path(raw).expanduser() if raw else DEFAULT_REFERENCE_DB.expanduser()
