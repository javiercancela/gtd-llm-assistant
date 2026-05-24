#!/usr/bin/env python
"""Migrate the old Google Tasks Reference list into the local reference store."""

from __future__ import annotations

import argparse
import traceback
from pathlib import Path
from typing import Any

from gtd_assistant.adapters.google_tasks.repository import list_tasks
from gtd_assistant.adapters.qwen_embedder import QwenReferenceEmbedder
from gtd_assistant.adapters.sqlite_reference_store import SQLiteReferenceStore
from gtd_assistant.application.save_reference import save_reference
from gtd_assistant.domain.dedupe import IDEMPOTENCY_MARKER_PREFIX
from gtd_assistant.infrastructure.reference_config import load_reference_db_path


def main() -> None:
    args = _parse_args()
    tasks = list_tasks(args.tasklist_id)
    failures: list[str] = []

    if args.dry_run:
        print(f"dry_run=true reference_tasks={len(tasks)}")
        return

    embedder = QwenReferenceEmbedder()
    store = SQLiteReferenceStore(load_reference_db_path(), vector_dimension=embedder.dimension)
    migrated = 0
    skipped = 0

    for task in tasks:
        try:
            item = _reference_item_from_task(task)
            result = save_reference(
                store=store,
                embedder=embedder,
                item=item,
                capture={"captured_at": task.get("updated", "")},
                source_name="migration:gtasks",
            )
            if result["status"] == "created":
                migrated += 1
            else:
                skipped += 1
        except Exception:
            failures.append(f"{task.get('id', '<missing-id>')}: {traceback.format_exc()}")

    if failures:
        log_path = Path(args.failure_log).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("\n\n".join(failures), encoding="utf-8")

    print(f"migrated={migrated} skipped={skipped} failed={len(failures)}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tasklist-id",
        required=True,
        help="Google Tasks list ID to read legacy reference tasks from",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--failure-log",
        default="~/.local/share/gtd-llm-assistant/reference-migration-failures.log",
    )
    return parser.parse_args()


def _reference_item_from_task(task: dict[str, Any]) -> dict[str, Any]:
    notes = _clean_notes(str(task.get("notes") or ""))
    summary, url = _split_summary_url(notes)
    if not url:
        url = _url_from_links(task)
    return {
        "type": "reference",
        "title": str(task.get("title") or "").strip() or "Untitled reference",
        "summary": summary,
        "url": url or "",
        "tags": ["migration"],
    }


def _clean_notes(notes: str) -> str:
    lines = [
        line
        for line in notes.splitlines()
        if not line.strip().startswith(IDEMPOTENCY_MARKER_PREFIX)
    ]
    return "\n".join(lines).strip()


def _split_summary_url(notes: str) -> tuple[str, str]:
    lines = [line.strip() for line in notes.splitlines() if line.strip()]
    if lines and lines[-1].startswith(("http://", "https://")):
        return "\n".join(lines[:-1]).strip(), lines[-1]
    return notes, ""


def _url_from_links(task: dict[str, Any]) -> str:
    links = task.get("links") or []
    if not isinstance(links, list):
        return ""
    for link in links:
        if isinstance(link, dict):
            value = str(link.get("link", "")).strip()
            if value.startswith(("http://", "https://")):
                return value
    return ""


if __name__ == "__main__":
    main()
