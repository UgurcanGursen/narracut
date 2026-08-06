"""Replaceable application ports for project orchestration."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from .models import (
    DomainCommand,
    ProjectAggregate,
    ResolvedDomainSelection,
    ReviewSnapshotRecord,
    RenderInputSnapshotRecord,
    PreviewExecutionResult,
    PreviewJobEvent,
    PreviewJobRecord,
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

    def put_render_input(self, value: RenderInputSnapshotRecord) -> None: ...

    def get_render_input(
        self, project_id: str, sequence_id: str
    ) -> RenderInputSnapshotRecord | None: ...


class StudioRenderInputResolverPort(Protocol):
    def resolve(
        self, *, project_id: str, sequence_id: str, review_snapshot: ReviewSnapshotRecord
    ) -> RenderInputSnapshotRecord | None: ...


class PreviewExecutionPort(Protocol):
    def execute(self, snapshot: RenderInputSnapshotRecord, *, timestamp_utc: str) -> PreviewExecutionResult: ...


class RenderJobRepositoryPort(Protocol):
    def create_preview_job(self, job: PreviewJobRecord) -> None: ...
    def get_preview_job(self, job_id: str) -> PreviewJobRecord | None: ...
    def get_active_preview_job(self, request_hash: str) -> PreviewJobRecord | None: ...
    def next_preview_attempt(self, request_hash: str) -> int: ...
    def transition_preview_job(self, job_id: str, *, state: str, created_at: str, public_failure_code: str | None = None, receipt_hash: str | None = None, preview_manifest_hash: str | None = None, delivery_id: str | None = None) -> PreviewJobRecord: ...
    def list_preview_events(self, job_id: str, *, after: int) -> tuple[PreviewJobEvent, ...]: ...


class PreviewDeliveryPort(Protocol):
    def put(self, *, delivery_id: str, project_id: str, job_id: str, manifest: bytes, frames: Mapping[int, bytes]) -> None: ...
    def manifest(self, *, delivery_id: str, project_id: str, job_id: str) -> bytes | None: ...
    def frame(self, *, delivery_id: str, project_id: str, job_id: str, frame_index: int) -> bytes | None: ...
