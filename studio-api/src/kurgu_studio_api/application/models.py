"""Immutable application-layer project models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping


@dataclass(frozen=True)
class CoreOnlyDomainCommand:
    resolution_mode: Literal["core_only"] = "core_only"


@dataclass(frozen=True)
class DomainProfileCommand:
    profile_id: str
    enabled_extensions: tuple[Mapping[str, Any], ...]
    policy_overrides: Mapping[str, Any]


@dataclass(frozen=True)
class DomainPackDomainCommand:
    domain_id: str
    domain_pack_version: str
    profile: DomainProfileCommand
    resolution_mode: Literal["domain_pack"] = "domain_pack"


DomainCommand = CoreOnlyDomainCommand | DomainPackDomainCommand


@dataclass(frozen=True)
class CreateProjectCommand:
    title: str
    domain: DomainCommand


@dataclass(frozen=True)
class ResolvedDomainSelection:
    resolution_mode: Literal["core_only", "domain_pack"]
    domain_id: str
    domain_pack_version: str
    profile_id: str
    policy_snapshot_id: str
    profile: Mapping[str, Any]
    policy_snapshot: Mapping[str, Any]


@dataclass(frozen=True)
class ProjectAggregate:
    project: Mapping[str, Any]
    domain: ResolvedDomainSelection
    artifacts: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True)
class ProjectCreatedView:
    project: Mapping[str, Any]
    domain: ResolvedDomainSelection
    persistence_scope: Literal["process_lifetime", "local_sqlite"] = "process_lifetime"


@dataclass(frozen=True)
class ProjectStatusView:
    project_id: str
    status: str
    updated_at: str
    version: int
    domain: ResolvedDomainSelection
    persistence_scope: Literal["process_lifetime", "local_sqlite"] = "process_lifetime"


@dataclass(frozen=True)
class ProjectListView:
    items: tuple[ProjectStatusView, ...]
    persistence_scope: Literal["process_lifetime", "local_sqlite"] = "process_lifetime"

    @property
    def count(self) -> int:
        return len(self.items)


@dataclass(frozen=True)
class ArtifactCollectionView:
    project_id: str
    items: tuple[Mapping[str, Any], ...]
    persistence_scope: Literal["process_lifetime", "local_sqlite"] = "process_lifetime"

    @property
    def count(self) -> int:
        return len(self.items)


@dataclass(frozen=True)
class StudioTaskRecord:
    task_id: str
    task_hash: str
    project_id: str
    policy_snapshot_id: str
    policy_snapshot_hash: str
    family: Literal["research", "planner"]
    task_type: str
    backend_mode: Literal["replay", "manual_ui"]
    prompt: str
    context_package: Mapping[str, Any]
    payload: Mapping[str, Any]
    parent_task_id: str | None
    attempt: int
    created_at: str


@dataclass(frozen=True)
class StudioTaskView:
    record: StudioTaskRecord
    status: Literal["waiting", "valid", "repair_required", "approved"]
    validation_issues: tuple[str, ...]
    response_hash: str | None


@dataclass(frozen=True)
class ReviewSnapshotRecord:
    snapshot_id: str
    snapshot_hash: str
    project_id: str
    policy_snapshot_id: str
    policy_snapshot_hash: str
    executable_plan: Mapping[str, Any]
    final_edl_bundle: Mapping[str, Any]
    created_at: str
