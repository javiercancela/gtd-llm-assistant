from __future__ import annotations

from collections import defaultdict
from typing import Any


class FakeTaskListRepository:
    def __init__(
        self,
        *,
        tasks: dict[str, list[dict[str, Any]]] | None = None,
        projects: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        self.tasks: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        self.projects: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for tasklist, task_items in (tasks or {}).items():
            self.tasks[tasklist].extend(dict(item) for item in task_items)
        for tasklist, project_items in (projects or {}).items():
            self.projects[tasklist].extend(dict(item) for item in project_items)

        self.created_tasks: list[dict[str, Any]] = []
        self.created_projects: list[dict[str, Any]] = []
        self.added_subtasks: list[dict[str, Any]] = []

    def list_tasks(self, tasklist: str) -> list[dict[str, Any]]:
        return list(self.tasks[tasklist])

    def list_projects(self, tasklist: str) -> list[dict[str, Any]]:
        return list(self.projects[tasklist])

    def create_task(
        self,
        *,
        tasklist: str,
        title: str,
        notes: str | None = None,
        url: str | None = None,
    ) -> dict[str, Any]:
        task = {
            "id": f"task-{len(self.created_tasks) + 1}",
            "tasklist": tasklist,
            "title": title,
            "notes": notes,
            "url": url,
        }
        self.created_tasks.append(task)
        self.tasks[tasklist].append(task)
        return task

    def create_project(
        self,
        *,
        tasklist: str,
        title: str,
        notes: str | None = None,
        url: str | None = None,
    ) -> dict[str, Any]:
        project = {
            "id": f"project-{len(self.created_projects) + 1}",
            "tasklist": tasklist,
            "title": title,
            "notes": notes,
            "url": url,
        }
        self.created_projects.append(project)
        self.projects[tasklist].append(project)
        self.tasks[tasklist].append(project)
        return project

    def add_task_to_project(
        self,
        *,
        tasklist: str,
        project_id: str,
        title: str,
    ) -> dict[str, Any]:
        subtask = {
            "id": f"subtask-{len(self.added_subtasks) + 1}",
            "tasklist": tasklist,
            "project_id": project_id,
            "title": title,
        }
        self.added_subtasks.append(subtask)
        self.tasks[tasklist].append({**subtask, "parent": project_id})
        return subtask
