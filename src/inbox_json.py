"""Compatibility shim for the renamed iCloud JSON reader."""

import sys

from gtd_assistant.adapters.icloud import json_reader as _module

sys.modules[__name__] = _module
