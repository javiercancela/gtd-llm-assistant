from __future__ import annotations

from typing import Any


class FakeJsonLlm:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []

    def complete_json(self, prompt: str) -> Any:
        self.prompts.append(prompt)
        if not self.responses:
            raise AssertionError("FakeJsonLlm received more prompts than responses")
        return self.responses.pop(0)
