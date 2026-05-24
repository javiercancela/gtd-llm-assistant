"""Compatibility shim for run logger port."""

import sys

from gtd_assistant.ports import run_logger as _module

sys.modules[__name__] = _module
