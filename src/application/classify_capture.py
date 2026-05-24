"""Compatibility shim for classification use case."""

import sys

from gtd_assistant.application import classify_capture as _module

sys.modules[__name__] = _module
