from gtd_assistant.adapters.google_tasks.repository import _build_task_body


def test_build_task_body_includes_links_when_url_present() -> None:
    body = _build_task_body("Title", "Notes", None, "https://example.com/page")

    assert body["links"] == [{"type": "generic", "link": "https://example.com/page"}]


def test_build_task_body_omits_links_without_url() -> None:
    body = _build_task_body("Title", "Notes", None, None)

    assert "links" not in body
