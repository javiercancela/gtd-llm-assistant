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

# Spanish prompt emits only compra/tarea; both map to tasks on the Personal list.
SPANISH_TYPE_MAP: dict[str, str] = {
    "tarea": ITEM_KIND_TASK,
    "compra": ITEM_KIND_TASK,
}
