"""Classify inbox captures into canonical GTD items.

Entry: classify_capture(...)
Ports: JsonLlm, TaskListRepository
"""

from __future__ import annotations

import json
from typing import Any

from gtd_assistant.domain.classified_item import normalize_english_item, normalize_spanish_item
from gtd_assistant.domain.language import detect_language_from_capture
from gtd_assistant.ports.llm import JsonLlm
from gtd_assistant.ports.task_lists import TaskListRepository
from gtd_assistant.prompts.templates import (
    CLASSIFY_ENGLISH_PROMPT,
    CLASSIFY_SPANISH_PROMPT,
    PROJECT_ENGLISH_PROMPT,
    REFERENCE_ENGLISH_PROMPT,
    TASK_ENGLISH_PROMPT,
    WAITING_FOR_ENGLISH_PROMPT,
)

ENGLISH_TYPE_PROMPTS = {
    "task": TASK_ENGLISH_PROMPT,
    "project": PROJECT_ENGLISH_PROMPT,
    "reference": REFERENCE_ENGLISH_PROMPT,
    "waiting_for": WAITING_FOR_ENGLISH_PROMPT,
}


def classify_capture(
    capture: dict[str, Any],
    *,
    llm: JsonLlm,
    task_repository: TaskListRepository,
    work_tasklist: str,
) -> tuple[str, list[dict[str, Any]]]:
    """Classify a raw inbox capture without depending on a concrete LLM or task SDK."""
    language = detect_language_from_capture(capture)
    if language == "es":
        items = _llm_items(llm, CLASSIFY_SPANISH_PROMPT, capture=capture)
        return language, [normalize_spanish_item(item) for item in items]

    classified = _classify_english(capture, llm=llm)
    if not classified:
        classified = [{"type": "task", "text": ""}]
    return language, _enrich_english(
        capture,
        classified,
        llm=llm,
        task_repository=task_repository,
        work_tasklist=work_tasklist,
    )


def _classify_english(
    capture: dict[str, Any],
    *,
    llm: JsonLlm,
) -> list[dict[str, Any]]:
    classified = _llm_items(llm, CLASSIFY_ENGLISH_PROMPT, capture=capture)
    return [
        {
            "type": str(item.get("type", "task")).strip().lower() or "task",
            "text": str(item.get("text", "")).strip(),
        }
        for item in classified
    ]


def _enrich_english(
    capture: dict[str, Any],
    classified_items: list[dict[str, Any]],
    *,
    llm: JsonLlm,
    task_repository: TaskListRepository,
    work_tasklist: str,
) -> list[dict[str, Any]]:
    needs_projects = any(item["type"] == "project" for item in classified_items)
    existing_projects = (
        _existing_project_titles(task_repository, tasklist=work_tasklist)
        if needs_projects
        else None
    )
    enriched: list[dict[str, Any]] = []

    for classified in classified_items:
        item_type = classified["type"]
        if item_type not in ENGLISH_TYPE_PROMPTS:
            item_type = "task"

        enrich_input = _build_enrich_input(capture, classified)
        template = ENGLISH_TYPE_PROMPTS[item_type]
        for item in _llm_items(
            llm,
            template,
            capture=enrich_input,
            existing_projects=existing_projects,
        ):
            enriched.append(normalize_english_item(item, expected_type=item_type))

    return enriched


def _existing_project_titles(
    task_repository: TaskListRepository,
    *,
    tasklist: str,
) -> list[str]:
    return [
        str(project.get("title", "")).strip()
        for project in task_repository.list_projects(tasklist)
        if str(project.get("title", "")).strip()
    ]


def _llm_items(
    llm: JsonLlm,
    template: str,
    *,
    capture: dict[str, Any],
    existing_projects: list[str] | None = None,
) -> list[dict[str, Any]]:
    prompt = _render_prompt(
        template,
        input_json=json.dumps(capture, ensure_ascii=False, indent=2),
        existing_projects=existing_projects,
    )
    return _as_item_list(llm.complete_json(prompt))


def _as_item_list(parsed: Any) -> list[dict[str, Any]]:
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        return [parsed]
    raise RuntimeError(f"LLM returned unexpected payload type: {type(parsed).__name__}")


def _build_enrich_input(data: dict[str, Any], classified: dict[str, Any]) -> dict[str, Any]:
    text = str(classified.get("text", "")).strip()
    if text:
        enriched = dict(data)
        enriched["text"] = text
        return enriched
    return data


def _render_prompt(
    template: str,
    *,
    input_json: str,
    existing_projects: list[str] | None = None,
) -> str:
    prompt = template.replace("{{INPUT_JSON}}", input_json)
    if "{{EXISTING_PROJECTS_JSON}}" in prompt:
        projects = existing_projects or []
        prompt = prompt.replace(
            "{{EXISTING_PROJECTS_JSON}}",
            json.dumps(projects, ensure_ascii=False, indent=2),
        )
    return prompt
