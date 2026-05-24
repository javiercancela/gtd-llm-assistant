"""Compatibility shim for domain item kind constants."""

import sys

from gtd_assistant.domain import item_kind as _module

sys.modules[__name__] = _module
