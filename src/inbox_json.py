"""Read JSON inbox drops from iCloud-backed paths with hydration retries."""

from __future__ import annotations

import concurrent.futures
import json
import shutil
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

# macOS CloudDocs may return EAGAIN while a file is still downloading.
_ERRNO_RESOURCE_DEADLOCK = 11
_COPY_TIMEOUT_SECONDS = 10.0


def _read_json_text(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _copy_with_timeout(src: Path, dst: Path, *, timeout_seconds: float) -> None:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(shutil.copy2, src, dst)
        try:
            future.result(timeout=timeout_seconds)
        except concurrent.futures.TimeoutError as exc:
            raise OSError(
                _ERRNO_RESOURCE_DEADLOCK,
                f"iCloud copy timed out after {timeout_seconds}s",
            ) from exc


def _read_json_via_local_copy(path: Path, *, copy_timeout_seconds: float = _COPY_TIMEOUT_SECONDS) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        _copy_with_timeout(path, tmp_path, timeout_seconds=copy_timeout_seconds)
        return _read_json_text(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def load_json_file(
    path: Path,
    *,
    max_attempts: int = 24,
    on_waiting_for_sync: Callable[[str], None] | None = None,
) -> dict:
    """Load JSON from path, retrying while iCloud hydrates the file."""
    delay_seconds = 2

    for attempt in range(1, max_attempts + 1):
        try:
            return _read_json_text(path)
        except OSError as exc:
            if exc.errno != _ERRNO_RESOURCE_DEADLOCK:
                raise

        if on_waiting_for_sync is not None:
            on_waiting_for_sync(
                f"waiting for iCloud sync file={path.name} attempt={attempt}/{max_attempts}",
            )

        if attempt >= max_attempts:
            raise OSError(
                _ERRNO_RESOURCE_DEADLOCK,
                f"iCloud file not ready after {max_attempts} attempts: {path.name}",
            )

        time.sleep(delay_seconds)
        delay_seconds = min(delay_seconds * 1.5, 120.0)

        try:
            return _read_json_via_local_copy(path)
        except OSError as copy_exc:
            if copy_exc.errno != _ERRNO_RESOURCE_DEADLOCK:
                raise
