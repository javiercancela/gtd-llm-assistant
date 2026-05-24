"""Compatibility shim for Google Tasks helpers."""

import sys

from gtd_assistant.adapters.google_tasks import repository as _module

sys.modules[__name__] = _module
