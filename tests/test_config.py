from pathlib import Path

from gtd_assistant.infrastructure.config import load_inbox_config


def test_references_dir_defaults_under_inbox_dir(monkeypatch) -> None:
    inbox_dir = Path("~/GTD/00_Inbox").expanduser()
    monkeypatch.setenv("GTD_INBOX_DIR", str(inbox_dir))
    monkeypatch.delenv("GTD_REFERENCES_DIR", raising=False)

    config = load_inbox_config()

    assert config.references_dir == inbox_dir / "references"


def test_references_dir_env_override(monkeypatch, tmp_path: Path) -> None:
    references_dir = tmp_path / "owned-references"
    monkeypatch.setenv("GTD_REFERENCES_DIR", str(references_dir))

    config = load_inbox_config()

    assert config.references_dir == references_dir
