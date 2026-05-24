"""Compatibility shim for Gemini response parser imports."""

import sys

from gtd_assistant.adapters.gemini import response_parser as _module

sys.modules[__name__] = _module
