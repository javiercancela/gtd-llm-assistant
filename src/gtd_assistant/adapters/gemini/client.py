"""Google Gemini JSON client adapter."""

from __future__ import annotations

import os
from typing import Any

from google import genai
from google.genai import errors, types

from gtd_assistant.adapters.gemini.response_parser import parse_json_from_gemini_payload

API_KEY_ENV = "GEMINI_API_KEY"
MODEL_FLASH = "gemini-3-flash-preview"
MODEL_PRO = "gemini-3.1-pro-preview"


class GeminiJsonClient:
    """JsonLlm backed by Gemini's generate_content API."""

    def __init__(self, *, model: str = MODEL_FLASH) -> None:
        self.model = model

    def complete_json(self, prompt: str) -> Any:
        response = call_gemini(prompt, self.model)
        return parse_json_from_gemini_payload(response)


def _load_api_key() -> str:
    api_key = os.getenv(API_KEY_ENV, "").strip()
    if not api_key:
        raise RuntimeError(f"Missing API key. Set {API_KEY_ENV} in the environment before running.")
    return api_key


def call_gemini(
    prompt: str,
    model: str,
) -> dict[str, Any]:
    api_key = _load_api_key()
    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
    except errors.APIError as exc:
        raise RuntimeError(f"Gemini API error: {exc.message}") from exc

    return response.model_dump(mode="json")
