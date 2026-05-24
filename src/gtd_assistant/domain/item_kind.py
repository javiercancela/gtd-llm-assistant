"""GTD item kinds and the Spanish label map used by the LLM output.

The canonical kind is the value of the `type` field on a classified item.
"""

from __future__ import annotations

ITEM_KIND_TASK = "task"
ITEM_KIND_PROJECT = "project"
ITEM_KIND_REFERENCE = "reference"
ITEM_KIND_WAITING_FOR = "waiting_for"

VALID_ITEM_KINDS: frozenset[str] = frozenset(
    {ITEM_KIND_TASK, ITEM_KIND_PROJECT, ITEM_KIND_REFERENCE, ITEM_KIND_WAITING_FOR}
)

# Spanish prompt emits these labels; map them onto the canonical kinds.
SPANISH_TYPE_MAP: dict[str, str] = {
    "tarea": ITEM_KIND_TASK,
    "proyecto": ITEM_KIND_PROJECT,
    "referencia": ITEM_KIND_REFERENCE,
    "esperando": ITEM_KIND_WAITING_FOR,
    "compra": ITEM_KIND_TASK,
}
