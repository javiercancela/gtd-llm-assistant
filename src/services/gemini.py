"""Compatibility wrapper for Gemini-backed inbox classification.

New classification orchestration lives in `application.classify_capture`; this
module wires it to the current Gemini and Google Tasks adapters for existing
callers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from adapters.gemini import GeminiJsonClient, MODEL_FLASH, parse_json_from_gemini_payload
from application.classify_capture import classify_capture
from services.tasklists import WORK_TL
from services.tasks import GoogleTasksRepository

__all__ = ["classify_message", "parse_json_from_gemini_payload"]


def classify_message(
    data: dict[str, Any],
    *,
    logs_dir: Path | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    return classify_capture(
        data,
        llm=GeminiJsonClient(model=MODEL_FLASH, logs_dir=logs_dir),
        task_repository=GoogleTasksRepository(),
        work_tasklist=WORK_TL,
    )
