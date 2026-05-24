"""Logging wrapper for Gemini JSON classification calls."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gtd_assistant.adapters.gemini.client import MODEL_FLASH, call_gemini
from gtd_assistant.adapters.gemini.response_parser import parse_json_from_gemini_payload
from gtd_assistant.infrastructure.gemini_exchange_log import append_gemini_log


class LoggingGeminiJsonClient:
    """JsonLlm that logs raw Gemini exchanges before parsing JSON."""

    def __init__(self, *, model: str = MODEL_FLASH, logs_dir: Path) -> None:
        self.model = model
        self.logs_dir = logs_dir

    def complete_json(self, prompt: str) -> Any:
        try:
            payload = call_gemini(prompt, self.model)
        except Exception as exc:
            append_gemini_log(self.logs_dir, model=self.model, prompt=prompt, error=str(exc))
            raise

        append_gemini_log(
            self.logs_dir,
            model=self.model,
            prompt=prompt,
            response_payload=payload,
        )
        return parse_json_from_gemini_payload(payload)
