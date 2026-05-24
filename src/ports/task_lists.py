"""Compatibility shim for task list repository port."""

import sys

from gtd_assistant.ports import task_lists as _module

sys.modules[__name__] = _module
