"""Gemini integration for inbox classification.

Entry: `classify_message(capture) -> (language, items)`.

Pure helpers (language detection, item normalization, Spanish type map) live
in `domain/`. This module orchestrates the two-phase English flow and the
single-call Spanish flow and talks to the Gemini and Google Tasks adapters.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from adapters.gcloud_tasks import list_projects
from adapters.gemini import call_gemini, MODEL_FLASH
from domain.classified_item import normalize_english_item, normalize_spanish_item
from domain.language import detect_language_from_capture
from services.prompts import (
    CLASSIFY_ENGLISH_PROMPT,
    CLASSIFY_SPANISH_PROMPT,
    PROJECT_ENGLISH_PROMPT,
    REFERENCE_ENGLISH_PROMPT,
    TASK_ENGLISH_PROMPT,
    WAITING_FOR_ENGLISH_PROMPT,
)
from services.tasklists import WORK_TL

ENGLISH_TYPE_PROMPTS = {
    "task": TASK_ENGLISH_PROMPT,
    "project": PROJECT_ENGLISH_PROMPT,
    "reference": REFERENCE_ENGLISH_PROMPT,
    "waiting_for": WAITING_FOR_ENGLISH_PROMPT,
}


def parse_json_from_gemini_payload(response_payload: dict[str, Any]) -> Any:
    """Extract and decode the JSON document Gemini returned in `response_payload`.

    Tolerates the model wrapping the JSON in a ``` or ```json fence.
    """
    candidates = response_payload.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini returned no candidates.")

    parts = candidates[0].get("content", {}).get("parts") or []
    if not parts:
        raise RuntimeError("Gemini returned an empty response body.")

    raw_text = parts[0].get("text", "").strip()
    if raw_text.startswith("```"):
        match = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```$", raw_text, flags=re.DOTALL)
        if match:
            raw_text = match.group(1).strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Gemini returned invalid JSON: {raw_text}") from exc


def _as_item_list(parsed: Any) -> list[dict[str, Any]]:
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        return [parsed]
    raise RuntimeError(f"Gemini returned unexpected payload type: {type(parsed).__name__}")


def _build_enrich_input(data: dict[str, Any], classified: dict[str, Any]) -> dict[str, Any]:
    text = str(classified.get("text", "")).strip()
    if text:
        enriched = dict(data)
        enriched["text"] = text
        return enriched
    return data


def _render_prompt(template: str, *, input_json: str, existing_projects: list[str] | None = None) -> str:
    prompt = template.replace("{{INPUT_JSON}}", input_json)
    if "{{EXISTING_PROJECTS_JSON}}" in prompt:
        projects = existing_projects or []
        prompt = prompt.replace(
            "{{EXISTING_PROJECTS_JSON}}",
            json.dumps(projects, ensure_ascii=False, indent=2),
        )
    return prompt


def _call_gemini_items(
    template: str,
    *,
    data: dict[str, Any],
    logs_dir: Path | None,
    existing_projects: list[str] | None = None,
) -> list[dict[str, Any]]:
    prompt = _render_prompt(
        template,
        input_json=json.dumps(data, ensure_ascii=False, indent=2),
        existing_projects=existing_projects,
    )
    response = call_gemini(prompt, MODEL_FLASH, logs_dir=logs_dir)
    return _as_item_list(parse_json_from_gemini_payload(response))


def _existing_project_titles() -> list[str]:
    return [
        str(project.get("title", "")).strip()
        for project in list_projects(tasklist=WORK_TL)
        if str(project.get("title", "")).strip()
    ]


def _classify_english(
    data: dict[str, Any],
    *,
    logs_dir: Path | None,
) -> list[dict[str, Any]]:
    classified = _call_gemini_items(CLASSIFY_ENGLISH_PROMPT, data=data, logs_dir=logs_dir)
    return [
        {
            "type": str(item.get("type", "task")).strip().lower() or "task",
            "text": str(item.get("text", "")).strip(),
        }
        for item in classified
    ]


def _enrich_english(
    data: dict[str, Any],
    classified_items: list[dict[str, Any]],
    *,
    logs_dir: Path | None,
) -> list[dict[str, Any]]:
    needs_projects = any(item["type"] == "project" for item in classified_items)
    existing_projects = _existing_project_titles() if needs_projects else None
    enriched: list[dict[str, Any]] = []

    for classified in classified_items:
        item_type = classified["type"]
        if item_type not in ENGLISH_TYPE_PROMPTS:
            item_type = "task"

        enrich_input = _build_enrich_input(data, classified)
        template = ENGLISH_TYPE_PROMPTS[item_type]
        for item in _call_gemini_items(
            template,
            data=enrich_input,
            logs_dir=logs_dir,
            existing_projects=existing_projects,
        ):
            enriched.append(normalize_english_item(item, expected_type=item_type))

    return enriched


def classify_message(
    data: dict[str, Any],
    *,
    logs_dir: Path | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    language = detect_language_from_capture(data)
    if language == "es":
        items = _call_gemini_items(CLASSIFY_SPANISH_PROMPT, data=data, logs_dir=logs_dir)
        return language, [normalize_spanish_item(item) for item in items]

    classified = _classify_english(data, logs_dir=logs_dir)
    if not classified:
        classified = [{"type": "task", "text": ""}]
    return language, _enrich_english(data, classified, logs_dir=logs_dir)
