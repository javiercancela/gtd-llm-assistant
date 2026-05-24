"""Command-line entry point that wires real adapters for one inbox run."""

from __future__ import annotations

from gtd_assistant.adapters.gemini import MODEL_FLASH
from gtd_assistant.adapters.gemini.logging_classifier import LoggingGeminiJsonClient
from gtd_assistant.adapters.google_tasks.repository import GoogleTasksRepository
from gtd_assistant.adapters.icloud.json_reader import IcloudJsonCaptureReader
from gtd_assistant.adapters.qwen_embedder import QwenReferenceEmbedder
from gtd_assistant.adapters.sqlite_reference_store import SQLiteReferenceStore
from gtd_assistant.application.process_inbox_run import (
    InboxRunDependencies,
    process_all_pending_captures,
)
from gtd_assistant.infrastructure.config import load_inbox_config
from gtd_assistant.infrastructure.gtd_task_lists import load_gtd_task_lists
from gtd_assistant.infrastructure.inbox_run_log import DailyRunLogger
from gtd_assistant.infrastructure.reference_config import load_reference_db_path


def main() -> None:
    """Run one pass over pending inbox captures."""
    config = load_inbox_config()
    task_repository = GoogleTasksRepository()
    reference_embedder = QwenReferenceEmbedder()
    deps = InboxRunDependencies(
        capture_reader=IcloudJsonCaptureReader(),
        llm=LoggingGeminiJsonClient(model=MODEL_FLASH, logs_dir=config.logs_dir),
        task_repository=task_repository,
        tasklists=load_gtd_task_lists().as_dict(),
        logger=DailyRunLogger(config.logs_dir),
        reference_store=SQLiteReferenceStore(
            load_reference_db_path(),
            vector_dimension=reference_embedder.dimension,
        ),
        reference_embedder=reference_embedder,
    )
    process_all_pending_captures(config, deps)


if __name__ == "__main__":
    main()
