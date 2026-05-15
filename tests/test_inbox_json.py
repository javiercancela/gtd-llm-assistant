import json
from pathlib import Path
from unittest.mock import patch

import pytest

from inbox_json import load_json_file


def test_load_json_file_reads_valid_json(tmp_path: Path) -> None:
    path = tmp_path / "drop.json"
    path.write_text(json.dumps({"message": "hello"}), encoding="utf-8")
    assert load_json_file(path) == {"message": "hello"}


def test_load_json_file_retries_then_succeeds(tmp_path: Path) -> None:
    path = tmp_path / "drop.json"
    path.write_text(json.dumps({"ok": True}), encoding="utf-8")
    calls = {"count": 0}
    real_open = Path.open

    def flaky_open(self, *args, **kwargs):
        if self == path and calls["count"] == 0:
            calls["count"] += 1
            raise OSError(11, "Resource deadlock avoided")
        return real_open(self, *args, **kwargs)

    with patch.object(Path, "open", flaky_open):
        with patch("inbox_json.time.sleep"):
            assert load_json_file(path, max_attempts=3) == {"ok": True}


def test_load_json_file_raises_after_exhausted_retries(tmp_path: Path) -> None:
    path = tmp_path / "drop.json"
    path.write_text("{}", encoding="utf-8")

    with patch.object(Path, "open", side_effect=OSError(11, "Resource deadlock avoided")):
        with patch("inbox_json._copy_with_timeout", side_effect=OSError(11, "Resource deadlock avoided")):
            with patch("inbox_json.time.sleep"):
                with pytest.raises(OSError) as exc_info:
                    load_json_file(path, max_attempts=2)
    assert exc_info.value.errno == 11


def test_load_json_file_sleeps_before_copy_fallback(tmp_path: Path) -> None:
    path = tmp_path / "drop.json"
    path.write_text("{}", encoding="utf-8")
    events: list[str] = []

    def flaky_open(self, *args, **kwargs):
        events.append("open")
        raise OSError(11, "Resource deadlock avoided")

    def track_sleep(_seconds: float) -> None:
        events.append("sleep")

    def track_copy(*_args, **_kwargs) -> None:
        events.append("copy")
        raise OSError(11, "Resource deadlock avoided")

    with patch.object(Path, "open", flaky_open):
        with patch("inbox_json.time.sleep", track_sleep):
            with patch("inbox_json._copy_with_timeout", track_copy):
                with pytest.raises(OSError):
                    load_json_file(path, max_attempts=2, on_waiting_for_sync=lambda _msg: None)

    assert events.index("sleep") < events.index("copy")


def test_copy_with_timeout_maps_timeout_to_resource_deadlock(tmp_path: Path) -> None:
    from inbox_json import _copy_with_timeout

    src = tmp_path / "src.json"
    dst = tmp_path / "dst.json"
    src.write_text("{}", encoding="utf-8")

    def slow_copy(_src: Path, _dst: Path) -> None:
        import time

        time.sleep(0.2)

    with patch("inbox_json.shutil.copy2", slow_copy):
        with pytest.raises(OSError) as exc_info:
            _copy_with_timeout(src, dst, timeout_seconds=0.01)
    assert exc_info.value.errno == 11
