from unittest.mock import patch

from services.gemini import (
    _detect_language,
    _enrich_english,
    _extract_json_response,
    _normalize_english_item,
    classify_message,
)


def _payload(text: str) -> dict:
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": text,
                        }
                    ]
                }
            }
        ]
    }


def test_detect_language_text_es() -> None:
    assert _detect_language({"text_es": "Comprar leche"}) == "es"


def test_detect_language_explicit_en() -> None:
    assert _detect_language({"language": "en", "text": "Buy milk"}) == "en"


def test_extract_json_response_plain_json_object() -> None:
    parsed = _extract_json_response(_payload('{"type":"task","title":"T","description":"D"}'))
    assert parsed["type"] == "task"


def test_extract_json_response_json_fenced_block() -> None:
    parsed = _extract_json_response(
        _payload("""```json\n[{\"type\":\"task\",\"title\":\"Buy milk\",\"description\":\"\"}]\n```""")
    )
    assert isinstance(parsed, list)
    assert parsed[0]["title"] == "Buy milk"


def test_extract_json_response_non_json_raises() -> None:
    try:
        _extract_json_response(_payload("not-json"))
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "invalid JSON" in str(exc)


def test_normalize_english_reference_includes_url() -> None:
    normalized = _normalize_english_item(
        {
            "type": "reference",
            "title": "Article",
            "summary": "A useful read.",
            "url": "https://example.com",
        },
        expected_type="reference",
    )
    assert normalized["description"] == "A useful read.\n\nhttps://example.com"
    assert normalized["url"] == "https://example.com"


def test_normalize_english_project_keeps_subtasks() -> None:
    normalized = _normalize_english_item(
        {
            "type": "project",
            "title": "Plan trip",
            "description": "",
            "existing_project_title": None,
            "subtasks": ["Book flights", "Reserve hotel"],
        },
        expected_type="project",
    )
    assert normalized["subtasks"] == ["Book flights", "Reserve hotel"]


@patch("services.gemini.call_gemini")
@patch("services.gemini._existing_project_titles", return_value=["Plan trip"])
def test_classify_message_english_two_phase(mock_projects, mock_call_gemini) -> None:
    mock_call_gemini.side_effect = [
        _payload('[{"type":"task","text":"Buy milk"}]'),
        _payload('[{"type":"task","title":"Buy milk","description":""}]'),
    ]

    language, items = classify_message({"text": "Buy milk"})

    assert language == "en"
    assert items == [{"type": "task", "title": "Buy milk", "description": ""}]
    assert mock_call_gemini.call_count == 2


@patch("services.gemini.call_gemini")
def test_enrich_english_project_uses_existing_projects(mock_call_gemini) -> None:
    mock_call_gemini.return_value = _payload(
        """{
          "type": "project",
          "title": "Plan trip",
          "description": "",
          "existing_project_title": "Plan trip",
          "subtasks": ["Book flights"]
        }"""
    )

    items = _enrich_english(
        {"text": "Book flights for the trip"},
        [{"type": "project", "text": "Book flights for the trip"}],
        logs_dir=None,
    )

    assert items[0]["existing_project_title"] == "Plan trip"
    assert items[0]["subtasks"] == ["Book flights"]
