"""Port for publishing GTD items to task lists.

Application code depends on this protocol instead of importing the Google
Tasks adapter directly.
"""

from __future__ import annotations

from typing import Any, Protocol


class TaskListRepository(Protocol):
    """Narrow task-list operations needed by GTD publishing."""

    def list_tasks(self, tasklist: str) -> list[dict[str, Any]]:
        """Return tasks from `tasklist`, including notes used for dedupe."""

    def list_projects(self, tasklist: str) -> list[dict[str, Any]]:
        """Return parent tasks that can receive project subtasks."""

    def create_task(
        self,
        *,
        tasklist: str,
        title: str,
        notes: str | None = None,
        url: str | None = None,
    ) -> dict[str, Any]:
        """Create a regular task."""

    def create_project(
        self,
        *,
        tasklist: str,
        title: str,
        notes: str | None = None,
        url: str | None = None,
    ) -> dict[str, Any]:
        """Create a task intended to act as a project parent."""

    def add_task_to_project(
        self,
        *,
        tasklist: str,
        project_id: str,
        title: str,
    ) -> dict[str, Any]:
        """Create a subtask under `project_id`."""
