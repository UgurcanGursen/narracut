"""Replaceable application ports for project orchestration."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from .models import (
    DomainCommand,
    ProjectAggregate,
    ResolvedDomainSelection,
    ReviewSnapshotRecord,
    StudioTaskRecord,
    StudioTaskView,
)


class RepositoryCollisionError(RuntimeError):
    """The repository already contains the requested stable ID."""


class ProjectRepository(Protocol):
    persistence_scope: str

    def create(self, aggregate: ProjectAggregate) -> None: ...

    def get(self, project_id: str) -> ProjectAggregate | None: ...

    def list_projects(self) -> tuple[ProjectAggregate, ...]: ...

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


class ManualTaskFactoryPort(Protocol):
    def create(
        self,
        *,
        project: ProjectAggregate,
        family: str,
        task_type: str,
        backend_mode: str,
        topic: str,
        created_at: str,
        parent: StudioTaskRecord | None = None,
    ) -> StudioTaskRecord: ...

    def validate_response(
        self,
        *,
        task: StudioTaskRecord,
        payload: Mapping[str, Any],
    ) -> tuple[bool, tuple[str, ...], str]: ...


class StudioWorkflowRepository(Protocol):
    def put_task(self, task: StudioTaskRecord) -> None: ...

    def get_task(self, task_id: str) -> StudioTaskView | None: ...

    def list_tasks(self, project_id: str) -> tuple[StudioTaskView, ...]: ...

    def record_task_result(
        self,
        *,
        task_id: str,
        status: str,
        response_hash: str | None,
        validation_issues: tuple[str, ...],
        created_at: str,
    ) -> None: ...

    def put_review_snapshot(self, snapshot: ReviewSnapshotRecord) -> None: ...

    def get_review_snapshot(
        self,
        project_id: str,
    ) -> ReviewSnapshotRecord | None: ...

    def get_review_decision(
        self,
        *,
        project_id: str,
        sequence_id: str,
    ) -> Mapping[str, Any] | None: ...

    def put_review_decision(self, value: Mapping[str, Any]) -> None: ...
