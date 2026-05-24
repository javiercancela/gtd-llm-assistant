import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fakes.embedder import FakeEmbedder
from fakes.llm import FakeJsonLlm
from fakes.reference_store import FakeReferenceStore
from fakes.task_lists import FakeTaskListRepository
from gtd_assistant.application.process_inbox_run import (
    InboxRunDependencies,
    process_all_pending_captures,
)
from gtd_assistant.domain.routing import (
    BUCKET_PERSONAL,
    BUCKET_WAITING_FOR,
    BUCKET_WORK,
)


@dataclass(frozen=True)
class _Config:
    watch_dir: Path
    processed_dir: Path
    references_dir: Path


class _JsonReader:
    def read_capture(self, path: Path, *, on_waiting_for_sync=None) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))


class _Logger:
    def __init__(self) -> None:
        self.entries: list[tuple[str, str]] = []

    def info(self, message: str) -> None:
        self.entries.append(("info", message))

    def ok(self, message: str) -> None:
        self.entries.append(("ok", message))

    def error(self, message: str) -> None:
        self.entries.append(("error", message))


class _Extractor:
    def __init__(self, text: str = "Extracted reference text") -> None:
        self.text = text

    def extract_text(self, path: Path) -> str:
        return self.text


class _FailingExtractor:
    def extract_text(self, path: Path) -> str:
        raise ValueError("unsupported document extension")


def test_process_all_pending_captures_publishes_and_archives(tmp_path: Path) -> None:
    watch_dir = tmp_path / "watch"
    processed_dir = tmp_path / "processed"
    watch_dir.mkdir()
    capture = watch_dir / "drop.json"
    capture.write_text(json.dumps({"text": "Buy milk"}), encoding="utf-8")
    llm = FakeJsonLlm(
        [
            [{"type": "task", "text": "Buy milk"}],
            [{"type": "task", "title": "Buy milk", "description": ""}],
        ]
    )
    repo = FakeTaskListRepository()
    logger = _Logger()

    process_all_pending_captures(
        _Config(
            watch_dir=watch_dir,
            processed_dir=processed_dir,
            references_dir=tmp_path / "references",
        ),
        InboxRunDependencies(
            capture_reader=_JsonReader(),
            llm=llm,
            task_repository=repo,
            tasklists={
                BUCKET_PERSONAL: "PER",
                BUCKET_WORK: "WRK",
                BUCKET_WAITING_FOR: "WAIT",
            },
            logger=logger,
        ),
    )

    assert not capture.exists()
    assert (processed_dir / "drop.json").exists()
    assert repo.created_tasks[0]["title"] == "Buy milk"
    assert repo.created_tasks[0]["tasklist"] == "WRK"
    assert ("info", "run complete") in logger.entries


def test_process_file_capture_saves_reference_and_copies_source(tmp_path: Path) -> None:
    watch_dir = tmp_path / "watch"
    processed_dir = tmp_path / "processed"
    references_dir = tmp_path / "references"
    source_file = tmp_path / "Downloads" / "note.md"
    source_file.parent.mkdir()
    source_file.write_text("# Useful note\n\nReference body.", encoding="utf-8")
    watch_dir.mkdir()
    capture = watch_dir / "drop.json"
    capture.write_text(json.dumps({"source_path": str(source_file)}), encoding="utf-8")
    llm = FakeJsonLlm(
        [
            [{"type": "reference", "text": "Extracted reference text"}],
            [
                {
                    "type": "reference",
                    "title": "Useful note",
                    "summary": "A useful markdown note.",
                    "url": "",
                    "tags": ["notes"],
                }
            ],
        ]
    )
    repo = FakeTaskListRepository()
    reference_store = FakeReferenceStore()

    process_all_pending_captures(
        _Config(watch_dir=watch_dir, processed_dir=processed_dir, references_dir=references_dir),
        InboxRunDependencies(
            capture_reader=_JsonReader(),
            llm=llm,
            task_repository=repo,
            tasklists={
                BUCKET_PERSONAL: "PER",
                BUCKET_WORK: "WRK",
                BUCKET_WAITING_FOR: "WAIT",
            },
            logger=_Logger(),
            reference_store=reference_store,
            reference_embedder=FakeEmbedder(),
            document_text_extractor=_Extractor(),
        ),
    )

    record = reference_store.records[1]
    copied_path = Path(record.metadata["file_path"])
    assert source_file.exists()
    assert copied_path.exists()
    assert copied_path.parent == references_dir
    assert record.metadata["source_path"] == str(source_file)
    assert record.metadata["full_text"] == "Extracted reference text"
    assert (processed_dir / "drop.json").exists()


def test_process_file_capture_extraction_failure_leaves_drop(tmp_path: Path) -> None:
    watch_dir = tmp_path / "watch"
    processed_dir = tmp_path / "processed"
    references_dir = tmp_path / "references"
    source_file = tmp_path / "note.pdf"
    source_file.write_text("pdf-ish", encoding="utf-8")
    watch_dir.mkdir()
    capture = watch_dir / "drop.json"
    capture.write_text(json.dumps({"source_path": str(source_file)}), encoding="utf-8")
    logger = _Logger()

    process_all_pending_captures(
        _Config(watch_dir=watch_dir, processed_dir=processed_dir, references_dir=references_dir),
        InboxRunDependencies(
            capture_reader=_JsonReader(),
            llm=FakeJsonLlm([]),
            task_repository=FakeTaskListRepository(),
            tasklists={
                BUCKET_PERSONAL: "PER",
                BUCKET_WORK: "WRK",
                BUCKET_WAITING_FOR: "WAIT",
            },
            logger=logger,
            document_text_extractor=_FailingExtractor(),
        ),
    )

    assert capture.exists()
    assert not (processed_dir / "drop.json").exists()
    assert any(level == "error" and "unsupported document extension" in msg for level, msg in logger.entries)
