import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from icloud_download import ensure_icloud_file_local


def test_ensure_icloud_file_local_noop_off_darwin(tmp_path: Path) -> None:
    path = tmp_path / "drop.json"
    path.write_text("{}", encoding="utf-8")
    with patch.object(sys, "platform", "linux"):
        ensure_icloud_file_local(path, max_wait_seconds=1.0)


def test_ensure_icloud_file_local_polls_until_ready(tmp_path: Path) -> None:
    path = tmp_path / "drop.json"
    path.write_text("{}", encoding="utf-8")
    foundation = MagicMock()
    foundation.NSURLUbiquitousItemDownloadingStatusCurrent = "current"
    foundation.NSURLUbiquitousItemDownloadingStatusDownloaded = "downloaded"
    foundation.NSFileManager.defaultManager().startDownloadingUbiquitousItemAtURL_error_.return_value = (
        True,
        None,
    )
    statuses = ["not_downloaded", "current"]

    def download_status(_foundation, _url) -> str:
        return statuses.pop(0)

    with patch("icloud_download._foundation", return_value=foundation):
        with patch("icloud_download._is_icloud_item", return_value=True):
            with patch("icloud_download._download_status", side_effect=download_status):
                with patch("icloud_download.time.sleep"):
                    ensure_icloud_file_local(path, max_wait_seconds=5.0, poll_interval_seconds=0.01)

    foundation.NSFileManager.defaultManager().startDownloadingUbiquitousItemAtURL_error_.assert_called_once()


def test_ensure_icloud_file_local_skips_non_icloud_files(tmp_path: Path) -> None:
    path = tmp_path / "drop.json"
    path.write_text("{}", encoding="utf-8")
    foundation = MagicMock()

    with patch("icloud_download._foundation", return_value=foundation):
        with patch("icloud_download._is_icloud_item", return_value=False):
            ensure_icloud_file_local(path, max_wait_seconds=1.0)

    foundation.NSFileManager.defaultManager().startDownloadingUbiquitousItemAtURL_error_.assert_not_called()
