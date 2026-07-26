"""Instance-local, process-lifetime project repository."""

from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any, Mapping

from ..application.models import ProjectAggregate
from ..application.ports import RepositoryCollisionError


class InMemoryProjectRepository:
    def __init__(self):
        self._projects: dict[str, ProjectAggregate] = {}
        self._lock = RLock()

    def create(self, aggregate: ProjectAggregate) -> None:
        project_id = aggregate.project["project_id"]
        with self._lock:
            if project_id in self._projects:
                raise RepositoryCollisionError(project_id)
            self._projects[project_id] = deepcopy(aggregate)

    def get(self, project_id: str) -> ProjectAggregate | None:
        with self._lock:
            aggregate = self._projects.get(project_id)
            return deepcopy(aggregate) if aggregate is not None else None

    def list_artifacts(
        self,
        project_id: str,
    ) -> tuple[Mapping[str, Any], ...] | None:
        with self._lock:
            aggregate = self._projects.get(project_id)
            if aggregate is None:
                return None
            return deepcopy(aggregate.artifacts)
