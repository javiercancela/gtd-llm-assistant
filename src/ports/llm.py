"""Compatibility shim for LLM port."""

import sys

from gtd_assistant.ports import llm as _module

sys.modules[__name__] = _module
