"""Request and wait for iCloud Drive files to hydrate on macOS."""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from pathlib import Path

_Foundation = None
_FoundationImportFailed = object()


def _foundation():
    global _Foundation
    if _Foundation is _FoundationImportFailed:
        return None
    if _Foundation is None:
        try:
            import Foundation  # type: ignore[import-not-found]
        except ImportError:
            _Foundation = _FoundationImportFailed
            return None
        _Foundation = Foundation
    return _Foundation


def _download_status(foundation, url) -> str | None:
    keys = [foundation.NSURLUbiquitousItemDownloadingStatusKey]
    values, error = url.resourceValuesForKeys_error_(keys, None)
    if error is not None or values is None:
        return None
    return values.objectForKey_(foundation.NSURLUbiquitousItemDownloadingStatusKey)


def _is_icloud_item(foundation, url) -> bool:
    keys = [foundation.NSURLIsUbiquitousItemKey]
    values, error = url.resourceValuesForKeys_error_(keys, None)
    if error is not None or values is None:
        return False
    return bool(values.objectForKey_(foundation.NSURLIsUbiquitousItemKey))


def _is_ready_status(foundation, status: str | None) -> bool:
    if status is None:
        return False
    return status in {
        foundation.NSURLUbiquitousItemDownloadingStatusCurrent,
        foundation.NSURLUbiquitousItemDownloadingStatusDownloaded,
    }


def ensure_icloud_file_local(
    path: Path,
    *,
    max_wait_seconds: float = 60.0,
    poll_interval_seconds: float = 1.0,
    on_waiting: Callable[[str], None] | None = None,
) -> None:
    """Ask CloudDocs to download path and poll until a local copy is available."""
    if sys.platform != "darwin":
        return

    foundation = _foundation()
    if foundation is None:
        return

    file_url = foundation.NSURL.fileURLWithPath_(str(path))
    if not _is_icloud_item(foundation, file_url):
        return

    file_manager = foundation.NSFileManager.defaultManager()
    started, error = file_manager.startDownloadingUbiquitousItemAtURL_error_(file_url, None)
    if not started and error is not None and on_waiting is not None:
        on_waiting(
            f"icloud start download failed file={path.name} "
            f"error={error.localizedDescription()}",
        )

    deadline = time.monotonic() + max_wait_seconds
    while time.monotonic() < deadline:
        status = _download_status(foundation, file_url)
        if _is_ready_status(foundation, status):
            return
        if on_waiting is not None:
            on_waiting(f"icloud downloading file={path.name} status={status or 'unknown'}")
        time.sleep(poll_interval_seconds)
