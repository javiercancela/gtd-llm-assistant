"""Compatibility shim for domain language helpers."""

import sys

from gtd_assistant.domain import language as _module

sys.modules[__name__] = _module
