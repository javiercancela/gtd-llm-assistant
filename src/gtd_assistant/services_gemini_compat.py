"""Compatibility wrapper for Gemini-backed inbox classification.

New classification orchestration lives in `application.classify_capture`; this
module wires it to the current Gemini and Google Tasks adapters for existing
callers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gtd_assistant.adapters.gemini import (
    GeminiJsonClient,
    MODEL_FLASH,
    parse_json_from_gemini_payload,
)
from gtd_assistant.adapters.gemini.logging_classifier import LoggingGeminiJsonClient
from gtd_assistant.adapters.google_tasks.repository import GoogleTasksRepository
from gtd_assistant.application.classify_capture import classify_capture
from gtd_assistant.infrastructure.gtd_task_lists import WORK_TL

__all__ = ["classify_message", "parse_json_from_gemini_payload"]


def classify_message(
    data: dict[str, Any],
    *,
    logs_dir: Path | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    llm = (
        LoggingGeminiJsonClient(model=MODEL_FLASH, logs_dir=logs_dir)
        if logs_dir is not None
        else GeminiJsonClient(model=MODEL_FLASH)
    )
    return classify_capture(
        data,
        llm=llm,
        task_repository=GoogleTasksRepository(),
        work_tasklist=WORK_TL,
    )
