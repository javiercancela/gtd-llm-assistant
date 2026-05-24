"""Compatibility shim for domain classified item helpers."""

import sys

from gtd_assistant.domain import classified_item as _module

sys.modules[__name__] = _module
