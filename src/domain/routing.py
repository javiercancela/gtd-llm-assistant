"""Compatibility shim for domain routing helpers."""

import sys

from gtd_assistant.domain import routing as _module

sys.modules[__name__] = _module
