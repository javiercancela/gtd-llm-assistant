"""Compatibility shim for inbox run use case."""

import sys

from gtd_assistant.application import process_inbox_run as _module

sys.modules[__name__] = _module
