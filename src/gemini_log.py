"""Compatibility shim for the renamed Gemini exchange logger."""

import sys

from gtd_assistant.infrastructure import gemini_exchange_log as _module

sys.modules[__name__] = _module
