"""Append-only Gemini prompt/response lines under the inbox logs directory."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gtd_assistant.adapters.gemini.response_parser import response_text_from_gemini_payload


def append_gemini_log(
    logs_dir: Path,
    *,
    model: str,
    prompt: str,
    response_payload: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = logs_dir / f"gemini_{day}.log"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry: dict[str, str] = {
        "ts": ts,
        "model": model,
        "prompt": prompt,
    }
    if response_payload is not None:
        entry["answer"] = response_text_from_gemini_payload(response_payload)
    if error is not None:
        entry["error"] = error
    line = json.dumps(entry, ensure_ascii=False)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{line}\n")
