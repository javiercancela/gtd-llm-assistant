import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fakes.llm import FakeJsonLlm
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
        _Config(watch_dir=watch_dir, processed_dir=processed_dir),
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
