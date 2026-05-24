"""Compatibility shim for the renamed iCloud hydration adapter."""

import sys

from gtd_assistant.adapters.icloud import hydrate as _module

sys.modules[__name__] = _module
