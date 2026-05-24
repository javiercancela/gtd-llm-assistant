"""Compatibility shim for capture reader port."""

import sys

from gtd_assistant.ports import capture_reader as _module

sys.modules[__name__] = _module
