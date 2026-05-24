"""Compatibility shim for the renamed inbox run logger."""

import sys

from gtd_assistant.infrastructure import inbox_run_log as _module

sys.modules[__name__] = _module
