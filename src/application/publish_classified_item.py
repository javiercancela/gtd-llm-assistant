"""Compatibility shim for publishing use case."""

import sys

from gtd_assistant.application import publish_classified_item as _module

sys.modules[__name__] = _module
