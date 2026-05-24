import sqlite3
from pathlib import Path

from fakes.embedder import FakeEmbedder
from fakes.llm import FakeJsonLlm
from fakes.reference_store import FakeReferenceStore
from fakes.task_lists import FakeTaskListRepository
from gtd_assistant.adapters.sqlite_reference_store import SQLiteReferenceStore
from gtd_assistant.application.process_inbox_run import InboxRunDependencies, process_all_pending_captures
from gtd_assistant.application.save_reference import save_reference
from gtd_assistant.application.search_references import search_references
from gtd_assistant.domain.reference import (
    NewReference,
    normalize_reference_tags,
    reference_dedupe_key,
)
from gtd_assistant.domain.routing import (
    BUCKET_PERSONAL,
    BUCKET_REFERENCE,
    BUCKET_WAITING_FOR,
    BUCKET_WORK,
)


def test_reference_dedupe_key_prefers_url() -> None:
    assert reference_dedupe_key(title="A", summary="B", url="https://example.com") == (
        "url:https://example.com"
    )


def test_reference_dedupe_key_for_url_less_content_is_stable() -> None:
    first = reference_dedupe_key(title="  My Note ", summary="Some   text", url=None)
    second = reference_dedupe_key(title="my note", summary="Some text", url="")

    assert first == second
    assert first.startswith("content:")


def test_normalize_reference_tags_dedupes_and_lowercases() -> None:
    assert normalize_reference_tags(["AI", " ai ", "", "Travel Plans"]) == (
        "ai",
        "travel plans",
    )


def test_save_reference_dedupes_by_url_without_reembedding() -> None:
    store = FakeReferenceStore()
    embedder = FakeEmbedder()
    item = {
        "type": "reference",
        "title": "Article",
        "summary": "Useful summary",
        "url": "https://example.com/article",
    }

    first = save_reference(
        store=store,
        embedder=embedder,
        item=item,
        capture={},
        source_name="drop.json",
    )
    second = save_reference(
        store=store,
        embedder=embedder,
        item=item,
        capture={},
        source_name="drop-again.json",
    )

    assert first["status"] == "created"
    assert second["status"] == "deduped"
    assert len(embedder.document_texts) == 1


def test_hybrid_reference_search_fuses_keyword_and_semantic_results() -> None:
    store = FakeReferenceStore()
    embedder = FakeEmbedder()
    save_reference(
        store=store,
        embedder=embedder,
        item={"type": "reference", "title": "SQLite notes", "summary": "FTS and vector search"},
        capture={},
        source_name="one.json",
    )

    results = search_references(store=store, embedder=embedder, query="SQLite", limit=10)

    assert results[0].reference.title == "SQLite notes"
    assert results[0].score > 0


def test_sqlite_reference_store_keyword_and_list_tags() -> None:
    conn = sqlite3.connect(":memory:")
    store = SQLiteReferenceStore(conn=conn, vector_dimension=4)
    created = store.create_reference(
        NewReference(
            title="Train booking",
            summary="Reference for booking train tickets in Spain",
            url="https://example.com/train",
            captured_at="2026-05-24T10:00:00Z",
            tags=("travel", "spain"),
        ),
        dedupe_key="url:https://example.com/train",
        embedding=[1.0, 0.0, 0.0, 0.0],
    )

    results = store.keyword_search("train", limit=5)

    assert created.id == 1
    assert results[0].reference.title == "Train booking"
    assert store.list_tags() == [("spain", 1), ("travel", 1)]


def test_sqlite_reference_store_semantic_falls_back_without_sqlite_vec() -> None:
    conn = sqlite3.connect(":memory:")
    store = SQLiteReferenceStore(conn=conn, vector_dimension=4)
    store.create_reference(
        NewReference(title="Closest", summary="", url=None, captured_at="2026-05-24T10:00:00Z"),
        dedupe_key="content:closest",
        embedding=[1.0, 0.0, 0.0, 0.0],
    )
    store.create_reference(
        NewReference(title="Farther", summary="", url=None, captured_at="2026-05-24T10:01:00Z"),
        dedupe_key="content:farther",
        embedding=[0.0, 1.0, 0.0, 0.0],
    )

    results = store.semantic_search([1.0, 0.0, 0.0, 0.0], limit=2)

    assert [result.reference.title for result in results] == ["Closest", "Farther"]


class _JsonReader:
    def read_capture(self, path: Path, *, on_waiting_for_sync=None) -> dict:
        return {"text": "Save this article", "url": "https://example.com/ref"}


class _Logger:
    def __init__(self) -> None:
        self.entries: list[tuple[str, str]] = []

    def info(self, message: str) -> None:
        self.entries.append(("info", message))

    def ok(self, message: str) -> None:
        self.entries.append(("ok", message))

    def error(self, message: str) -> None:
        self.entries.append(("error", message))


class _Config:
    def __init__(self, watch_dir: Path, processed_dir: Path) -> None:
        self.watch_dir = watch_dir
        self.processed_dir = processed_dir


def test_process_inbox_saves_reference_without_google_task(tmp_path: Path) -> None:
    watch_dir = tmp_path / "watch"
    processed_dir = tmp_path / "processed"
    watch_dir.mkdir()
    (watch_dir / "drop.json").write_text("{}", encoding="utf-8")
    llm = FakeJsonLlm(
        [
            [{"type": "reference", "text": "Save this article"}],
            [
                {
                    "type": "reference",
                    "title": "Example article",
                    "summary": "Useful reference",
                    "url": "https://example.com/ref",
                    "tags": ["example"],
                }
            ],
        ]
    )
    task_repo = FakeTaskListRepository()
    reference_store = FakeReferenceStore()

    process_all_pending_captures(
        _Config(watch_dir, processed_dir),
        InboxRunDependencies(
            capture_reader=_JsonReader(),
            llm=llm,
            task_repository=task_repo,
            tasklists={
                BUCKET_PERSONAL: "PER",
                BUCKET_WORK: "WRK",
                BUCKET_WAITING_FOR: "WAIT",
                BUCKET_REFERENCE: "REF",
            },
            logger=_Logger(),
            reference_store=reference_store,
            reference_embedder=FakeEmbedder(),
        ),
    )

    assert task_repo.created_tasks == []
    assert reference_store.records[1].title == "Example article"
    assert (processed_dir / "drop.json").exists()
