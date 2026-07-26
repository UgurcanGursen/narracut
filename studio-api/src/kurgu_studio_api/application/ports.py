"""Replaceable application ports for project orchestration."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from .models import (
    DomainCommand,
    ProjectAggregate,
    ResolvedDomainSelection,
)


class RepositoryCollisionError(RuntimeError):
    """The repository already contains the requested stable ID."""


class ProjectRepository(Protocol):
    def create(self, aggregate: ProjectAggregate) -> None: ...

    def get(self, project_id: str) -> ProjectAggregate | None: ...

    def list_artifacts(
        self, project_id: str
    ) -> tuple[Mapping[str, Any], ...] | None: ...


class ContractValidationPort(Protocol):
    def validate_project(self, value: Mapping[str, Any]) -> None: ...

    def validate_profile(self, value: Mapping[str, Any]) -> None: ...

    def validate_policy_snapshot(self, value: Mapping[str, Any]) -> None: ...

    def validate_artifacts(
        self,
        values: tuple[Mapping[str, Any], ...],
        *,
        project_id: str,
    ) -> None: ...


class DomainResolutionPort(Protocol):
    def resolve(
        self,
        command: DomainCommand,
        *,
        created_at: str,
    ) -> ResolvedDomainSelection: ...


class ProjectIdFactory(Protocol):
    def new_project_id(self) -> str: ...


class Clock(Protocol):
    def now_utc(self) -> str: ...
