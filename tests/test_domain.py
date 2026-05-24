import pytest

from gtd_assistant.domain.classified_item import normalize_spanish_item
from gtd_assistant.domain.dedupe import IDEMPOTENCY_MARKER_PREFIX, dedupe_marker, notes_with_marker
from gtd_assistant.domain.language import detect_language_from_capture
from gtd_assistant.domain.routing import gtd_list_for

_TASKLISTS = {
    "personal": "PER",
    "work": "WRK",
    "waiting_for": "WAIT",
    "reference": "REF",
}


def test_detect_language_falls_back_to_english() -> None:
    assert detect_language_from_capture({"text": "Plain English sentence."}) == "en"


def test_detect_language_uses_spanish_hint_heuristic() -> None:
    assert detect_language_from_capture({"text": "comprar leche para la cena"}) == "es"


def test_normalize_spanish_item_maps_compra_to_task() -> None:
    normalized = normalize_spanish_item(
        {"tipo": "compra", "titulo": "Leche", "descripcion": ""}
    )
    assert normalized == {"type": "task", "title": "Leche", "description": ""}


def test_normalize_spanish_item_maps_tarea_to_task() -> None:
    normalized = normalize_spanish_item(
        {"tipo": "tarea", "titulo": "Llamar al fontanero", "descripcion": "Fuga en cocina"}
    )
    assert normalized == {
        "type": "task",
        "title": "Llamar al fontanero",
        "description": "Fuga en cocina",
    }


@pytest.mark.parametrize(
    "tipo",
    ["proyecto", "referencia", "esperando", "desconocido"],
)
def test_normalize_spanish_item_non_task_types_become_task(tipo: str) -> None:
    normalized = normalize_spanish_item(
        {"tipo": tipo, "titulo": "X", "descripcion": "Y"}
    )
    assert normalized == {"type": "task", "title": "X", "description": "Y"}


def test_gtd_list_for_spanish_always_routes_to_personal() -> None:
    assert gtd_list_for("project", "es", tasklists=_TASKLISTS) == "PER"


def test_gtd_list_for_english_routes_by_kind() -> None:
    assert gtd_list_for("task", "en", tasklists=_TASKLISTS) == "WRK"
    assert gtd_list_for("project", "en", tasklists=_TASKLISTS) == "WRK"
    assert gtd_list_for("reference", "en", tasklists=_TASKLISTS) == "REF"
    assert gtd_list_for("waiting_for", "en", tasklists=_TASKLISTS) == "WAIT"


def test_dedupe_marker_is_stable_and_short() -> None:
    item = {"type": "task", "title": "T", "description": "D"}
    marker = dedupe_marker("inbox.json", item)
    assert marker == dedupe_marker("inbox.json", item)
    assert len(marker) == 16
    assert all(c in "0123456789abcdef" for c in marker)


def test_dedupe_marker_differs_when_source_or_content_differs() -> None:
    item = {"type": "task", "title": "T", "description": "D"}
    assert dedupe_marker("a.json", item) != dedupe_marker("b.json", item)
    other = {"type": "task", "title": "T", "description": "D2"}
    assert dedupe_marker("a.json", item) != dedupe_marker("a.json", other)


def test_notes_with_marker_appends_when_notes_present() -> None:
    out = notes_with_marker("hello", "abc")
    assert out == f"hello\n\n{IDEMPOTENCY_MARKER_PREFIX}abc"


def test_notes_with_marker_empty_when_notes_empty() -> None:
    assert notes_with_marker("", "abc") == ""
