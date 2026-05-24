from gtd_assistant.adapters.gemini.response_parser import parse_json_from_gemini_payload
from gtd_assistant.application.classify_capture import classify_capture
from gtd_assistant.domain.classified_item import normalize_english_item
from gtd_assistant.domain.language import detect_language_from_capture
from fakes.llm import FakeJsonLlm
from fakes.task_lists import FakeTaskListRepository


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
    assert detect_language_from_capture({"text_es": "Comprar leche"}) == "es"


def test_detect_language_explicit_en() -> None:
    assert detect_language_from_capture({"language": "en", "text": "Buy milk"}) == "en"


def test_parse_json_from_gemini_payload_plain_object() -> None:
    parsed = parse_json_from_gemini_payload(
        _payload('{"type":"task","title":"T","description":"D"}')
    )
    assert parsed["type"] == "task"


def test_parse_json_from_gemini_payload_fenced_block() -> None:
    parsed = parse_json_from_gemini_payload(
        _payload("""```json\n[{\"type\":\"task\",\"title\":\"Buy milk\",\"description\":\"\"}]\n```""")
    )
    assert isinstance(parsed, list)
    assert parsed[0]["title"] == "Buy milk"


def test_parse_json_from_gemini_payload_non_json_raises() -> None:
    try:
        parse_json_from_gemini_payload(_payload("not-json"))
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "invalid JSON" in str(exc)


def test_normalize_english_reference_includes_url() -> None:
    normalized = normalize_english_item(
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
    normalized = normalize_english_item(
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


def test_classify_capture_english_two_phase() -> None:
    llm = FakeJsonLlm(
        [
            [{"type": "task", "text": "Buy milk"}],
            [{"type": "task", "title": "Buy milk", "description": ""}],
        ]
    )
    repo = FakeTaskListRepository()

    language, items = classify_capture(
        {"text": "Buy milk"},
        llm=llm,
        task_repository=repo,
        work_tasklist="WRK",
    )

    assert language == "en"
    assert items == [{"type": "task", "title": "Buy milk", "description": ""}]
    assert len(llm.prompts) == 2


def test_classify_capture_english_project_uses_existing_projects() -> None:
    llm = FakeJsonLlm(
        [
            [{"type": "project", "text": "Book flights for the trip"}],
            {
                "type": "project",
                "title": "Plan trip",
                "description": "",
                "existing_project_title": "Plan trip",
                "subtasks": ["Book flights"],
            },
        ]
    )
    repo = FakeTaskListRepository(
        projects={"WRK": [{"id": "project-1", "title": "Plan trip"}]}
    )

    language, items = classify_capture(
        {"text": "Book flights for the trip"},
        llm=llm,
        task_repository=repo,
        work_tasklist="WRK",
    )

    assert language == "en"
    assert items[0]["existing_project_title"] == "Plan trip"
    assert items[0]["subtasks"] == ["Book flights"]
    assert "Plan trip" in llm.prompts[1]


def test_classify_capture_spanish_normalizes_to_personal_tasks() -> None:
    llm = FakeJsonLlm(
        [
            [
                {"tipo": "compra", "titulo": "Leche", "descripcion": ""},
                {"tipo": "tarea", "titulo": "Llamar al fontanero", "descripcion": ""},
            ]
        ]
    )
    repo = FakeTaskListRepository()

    language, items = classify_capture(
        {"text_es": "Comprar leche y llamar al fontanero"},
        llm=llm,
        task_repository=repo,
        work_tasklist="WRK",
    )

    assert language == "es"
    assert items == [
        {"type": "task", "title": "Leche", "description": ""},
        {"type": "task", "title": "Llamar al fontanero", "description": ""},
    ]
    assert len(llm.prompts) == 1
