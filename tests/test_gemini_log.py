import json
from pathlib import Path

from gemini_log import append_gemini_log


def test_append_gemini_log_success(tmp_path: Path) -> None:
    append_gemini_log(
        tmp_path,
        model="gemini-test",
        prompt="classify this",
        response_payload={
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": '{"type":"task"}'}],
                    }
                }
            ]
        },
    )
    lines = (tmp_path / f"gemini_{_today()}.log").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["model"] == "gemini-test"
    assert entry["prompt"] == "classify this"
    assert entry["answer"] == '{"type":"task"}'
    assert "error" not in entry


def test_append_gemini_log_error(tmp_path: Path) -> None:
    append_gemini_log(
        tmp_path,
        model="gemini-test",
        prompt="classify this",
        error="quota exceeded",
    )
    entry = json.loads((tmp_path / f"gemini_{_today()}.log").read_text(encoding="utf-8").strip())
    assert entry["error"] == "quota exceeded"
    assert "answer" not in entry


def _today() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
