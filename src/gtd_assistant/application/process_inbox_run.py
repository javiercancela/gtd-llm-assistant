"""Process pending workflow JSON drops from the GTD inbox watch folder.

Entry: process_all_pending_captures(...)
Ports: CaptureReader, JsonLlm, TaskListRepository, RunLogger
"""

from __future__ import annotations

import shutil
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from gtd_assistant.application.archive_source_document import archive_source_document
from gtd_assistant.application.classify_capture import classify_capture
from gtd_assistant.application.prepare_capture import SourceDocument, prepare_capture
from gtd_assistant.application.publish_classified_item import publish_classified_item
from gtd_assistant.application.save_reference import save_reference
from gtd_assistant.domain.item_kind import ITEM_KIND_REFERENCE
from gtd_assistant.ports.capture_reader import CaptureReader
from gtd_assistant.ports.document_text_extractor import DocumentTextExtractor
from gtd_assistant.ports.embedder import Embedder
from gtd_assistant.ports.llm import JsonLlm
from gtd_assistant.ports.reference_store import ReferenceStore
from gtd_assistant.ports.run_logger import RunLogger
from gtd_assistant.ports.task_lists import TaskListRepository


class InboxRunConfig(Protocol):
    """Path values needed by the inbox run use case."""

    watch_dir: Path
    processed_dir: Path
    references_dir: Path


@dataclass(frozen=True)
class InboxRunDependencies:
    """Concrete dependencies supplied by delivery code."""

    capture_reader: CaptureReader
    llm: JsonLlm
    task_repository: TaskListRepository
    tasklists: dict[str, str]
    logger: RunLogger
    reference_store: ReferenceStore | None = None
    reference_embedder: Embedder | None = None
    document_text_extractor: DocumentTextExtractor | None = None


def process_all_pending_captures(config: InboxRunConfig, deps: InboxRunDependencies) -> None:
    """Process every pending JSON drop and archive successful files."""
    config.processed_dir.mkdir(parents=True, exist_ok=True)
    candidates = list_pending_capture_files(config.watch_dir)
    deps.logger.info(f"run start watch={config.watch_dir} candidates={len(candidates)}")

    for path in candidates:
        process_one_capture(
            path,
            processed_dir=config.processed_dir,
            references_dir=config.references_dir,
            deps=deps,
        )

    deps.logger.info("run complete")


def list_pending_capture_files(watch_dir: Path) -> list[Path]:
    """Return workflow JSON files that are ready to consider for processing."""
    return sorted(
        path
        for path in watch_dir.glob("*.json")
        if not (path.name.startswith(".") or path.name.endswith(".icloud"))
    )


def process_one_capture(
    path: Path,
    *,
    processed_dir: Path,
    references_dir: Path,
    deps: InboxRunDependencies,
) -> None:
    """Process one capture file, logging and leaving failed files in place."""
    try:
        capture = deps.capture_reader.read_capture(
            path,
            on_waiting_for_sync=deps.logger.info,
        )
        capture, source_document = _prepare_capture(path, capture, deps=deps)
        language, items = classify_capture(
            capture,
            llm=deps.llm,
            task_repository=deps.task_repository,
            work_tasklist=deps.tasklists["work"],
        )
        deps.logger.info(f"classified {path.name} lang={language} items={len(items)}")

        source_url = str(capture.get("url", "")).strip() or None
        for item in items:
            if item.get("type") == ITEM_KIND_REFERENCE and language != "es":
                if deps.reference_store is None or deps.reference_embedder is None:
                    raise RuntimeError("reference store and embedder are required for references")
                task_result = save_reference(
                    store=deps.reference_store,
                    embedder=deps.reference_embedder,
                    source_name=path.name,
                    item=item,
                    capture=capture,
                    source_url=source_url,
                    source_document=source_document,
                )
                _archive_created_source_document(
                    task_result,
                    source_document=source_document,
                    references_dir=references_dir,
                    store=deps.reference_store,
                    logger=deps.logger,
                )
            else:
                task_result = publish_classified_item(
                    repository=deps.task_repository,
                    tasklists=deps.tasklists,
                    source_name=path.name,
                    item=item,
                    language=language,
                    source_url=source_url,
                )
            deps.logger.ok(
                f"task {task_result['status']} file={path.name} "
                f"type={task_result['type']} task_id={task_result['task_id']} "
                f"tasklist={task_result['tasklist']}"
            )

        archived = archive_capture(path, processed_dir)
        deps.logger.ok(f"moved {path.name} -> processed/{archived.name}")
    except Exception as exc:
        deps.logger.error(f"{path.name}: {exc!s}\n{traceback.format_exc()}")


def archive_capture(path: Path, processed_dir: Path) -> Path:
    """Move a successfully processed capture into the processed directory."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    dest = processed_dir / path.name
    shutil.move(str(path), str(dest))
    return dest


def _prepare_capture(
    path: Path,
    capture: dict[str, Any],
    *,
    deps: InboxRunDependencies,
) -> tuple[dict[str, Any], SourceDocument | None]:
    if not str(capture.get("source_path", "")).strip():
        return capture, None
    if deps.document_text_extractor is None:
        raise RuntimeError("document text extractor is required for source_path captures")

    source_label = Path(str(capture["source_path"]).strip()).expanduser().name
    deps.logger.info(f"extracting source file={source_label} capture={path.name}")
    prepared, source_document = prepare_capture(
        capture,
        source_name=path.name,
        extractor=deps.document_text_extractor,
    )
    if source_document is not None:
        deps.logger.ok(
            f"extracted source file={source_document.original_name} "
            f"hash={source_document.content_hash[:8]}"
        )
    return prepared, source_document


def _archive_created_source_document(
    task_result: dict[str, str],
    *,
    source_document: SourceDocument | None,
    references_dir: Path,
    store: ReferenceStore,
    logger: RunLogger,
) -> None:
    if source_document is None or task_result["status"] != "created":
        return

    copied_path = archive_source_document(source_document, references_dir=references_dir)
    reference_id = int(task_result["task_id"])
    reference = store.get_reference(reference_id)
    if reference is None:
        raise RuntimeError(f"created reference {reference_id} could not be read")
    metadata = dict(reference.metadata)
    metadata["file_path"] = str(copied_path)
    store.update_metadata(reference_id, metadata)
    logger.ok(f"copied source file={source_document.original_name} -> {copied_path}")
