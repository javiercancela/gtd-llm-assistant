"""Language detection for inbox captures.

Public entry: `detect_language_from_capture(capture) -> 'en' | 'es'`.
"""

from __future__ import annotations

import re
from typing import Any

SUPPORTED_LANGUAGES: frozenset[str] = frozenset({"en", "es"})

# Common Spanish tokens used as a heuristic when no explicit signal is present.
SPANISH_HINTS: frozenset[str] = frozenset(
    {"el", "la", "los", "las", "de", "que", "para", "con", "por", "en"}
)


def detect_language_from_capture(capture: dict[str, Any]) -> str:
    """Return 'es' when the capture is Spanish, otherwise 'en'.

    Detection order: explicit `text_es` key, explicit `language` field,
    Spanish-only characters in `text`, then a frequency heuristic over
    `SPANISH_HINTS`.
    """
    if "text_es" in capture:
        return "es"

    language = str(capture.get("language", "")).strip().lower()
    if language in SUPPORTED_LANGUAGES:
        return language

    text = str(capture.get("text", ""))
    if re.search(r"[áéíóúñ¿¡]", text, flags=re.IGNORECASE):
        return "es"

    tokens = {token.lower() for token in re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]+", text)}
    if len(tokens & SPANISH_HINTS) >= 2:
        return "es"

    return "en"
