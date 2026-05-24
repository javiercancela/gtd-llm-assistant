"""Compatibility shim for domain dedupe helpers."""

import sys

from gtd_assistant.domain import dedupe as _module

sys.modules[__name__] = _module
