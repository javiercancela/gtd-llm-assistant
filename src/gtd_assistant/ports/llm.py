"""Port for JSON-oriented LLM completions.

Application code depends on this protocol instead of a Gemini response shape.
"""

from __future__ import annotations

from typing import Any, Protocol


class JsonLlm(Protocol):
    """LLM client that returns parsed JSON for a prompt."""

    def complete_json(self, prompt: str) -> Any:
        """Return the decoded JSON document produced for `prompt`."""
