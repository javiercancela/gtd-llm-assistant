"""Parse JSON documents from Gemini response payloads."""

from __future__ import annotations

import json
import re
from typing import Any


def response_text_from_gemini_payload(response_payload: dict[str, Any]) -> str:
    """Return the raw text part from the first Gemini candidate."""
    candidates = response_payload.get("candidates") or []
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts") or []
    if not parts:
        return ""
    return str(parts[0].get("text", "")).strip()


def parse_json_from_gemini_payload(response_payload: dict[str, Any]) -> Any:
    """Extract and decode the JSON document Gemini returned in `response_payload`.

    Tolerates the model wrapping the JSON in a ``` or ```json fence.
    """
    raw_text = response_text_from_gemini_payload(response_payload)
    if not (response_payload.get("candidates") or []):
        raise RuntimeError("Gemini returned no candidates.")
    if not raw_text:
        raise RuntimeError("Gemini returned an empty response body.")
    if raw_text.startswith("```"):
        match = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```$", raw_text, flags=re.DOTALL)
        if match:
            raw_text = match.group(1).strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Gemini returned invalid JSON: {raw_text}") from exc
