"""Compatibility shim for Gemini client imports."""

import sys

from gtd_assistant.adapters.gemini import client as _module

sys.modules[__name__] = _module
