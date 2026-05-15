import os
from pathlib import Path
from typing import Any

from google import genai
from google.genai import errors, types

from gemini_log import append_gemini_log

API_KEY_ENV = "GEMINI_API_KEY"
MODEL_FLASH = "gemini-3-flash-preview"
MODEL_PRO = "gemini-3.1-pro-preview"


def _load_api_key() -> str:
    api_key = os.getenv(API_KEY_ENV, "").strip()
    if not api_key:
        raise RuntimeError(f"Missing API key. Set {API_KEY_ENV} in the environment before running.")
    return api_key


def call_gemini(
    prompt: str,
    model: str,
    *,
    logs_dir: Path | None = None,
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
        if logs_dir is not None:
            append_gemini_log(logs_dir, model=model, prompt=prompt, error=exc.message)
        raise RuntimeError(f"Gemini API error: {exc.message}") from exc

    payload = response.model_dump(mode="json")
    if logs_dir is not None:
        append_gemini_log(logs_dir, model=model, prompt=prompt, response_payload=payload)
    return payload
