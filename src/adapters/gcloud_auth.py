"""Compatibility shim for Google Tasks auth."""

import sys

from gtd_assistant.adapters.google_tasks import auth as _module

sys.modules[__name__] = _module
