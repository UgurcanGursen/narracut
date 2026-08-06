"""Strict request and explicit response DTOs for project contracts."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictRequestDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ExtensionReferenceDTO(StrictRequestDTO):
    namespace: str
    name: str
    version: str


class DomainProfileCreateDTO(StrictRequestDTO):
    profile_id: str
    enabled_extensions: list[ExtensionReferenceDTO]
    policy_overrides: dict[str, Any]


class CoreOnlyDomainCreateDTO(StrictRequestDTO):
    resolution_mode: Literal["core_only"]


class DomainPackDomainCreateDTO(StrictRequestDTO):
    resolution_mode: Literal["domain_pack"]
    domain_id: str
    domain_pack_version: str
    profile: DomainProfileCreateDTO


DomainCreateDTO = Annotated[
    CoreOnlyDomainCreateDTO | DomainPackDomainCreateDTO,
    Field(discriminator="resolution_mode"),
]


class ProjectCreateRequestDTO(StrictRequestDTO):
    title: str = Field(min_length=1, max_length=240)
    domain: DomainCreateDTO


class ProjectDocumentDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    project_id: str
    title: str
    created_at: str
    updated_at: str
    domain_id: str
    domain_pack_version: str
    policy_snapshot_id: str
    status: str
    version: int


class ResolvedDomainDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution_mode: Literal["core_only", "domain_pack"]
    domain_id: str
    domain_pack_version: str
    profile_id: str
    policy_snapshot_id: str


class ProjectCreateResponseDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: ProjectDocumentDTO
    domain: ResolvedDomainDTO
    persistence_scope: Literal["process_lifetime", "local_sqlite"]


class ProjectStatusResponseDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    status: str
    updated_at: str
    version: int
    domain: ResolvedDomainDTO
    persistence_scope: Literal["process_lifetime", "local_sqlite"]


class ProjectListResponseDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ProjectStatusResponseDTO]
    count: int
    persistence_scope: Literal["process_lifetime", "local_sqlite"]


class ArtifactDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    artifact_id: str
    artifact_type: str
    project_id: str
    sequence_id: str | None
    created_at: str
    last_accessed_at: str
    content_hash: str
    size_bytes: int
    retention_class: str
    dependency_ids: list[str]
    locked: bool
    pinned: bool
    approved: bool
    cleanup_candidate: bool
    producer: str
    producer_version: str
    job_id: str | None
    status: str
    version: int


class ProjectArtifactsResponseDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    items: list[ArtifactDTO]
    count: int
    persistence_scope: Literal["process_lifetime", "local_sqlite"]


class StudioTaskCreateRequestDTO(StrictRequestDTO):
    family: Literal["research", "planner"]
    task_type: Literal["source_discovery", "outline"]
    backend_mode: Literal["replay", "manual_ui"]
    topic: str = Field(min_length=1, max_length=500)


class StudioTaskResponseSubmitDTO(StrictRequestDTO):
    payload: dict[str, Any]


class StudioTaskDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    task_hash: str
    project_id: str
    policy_snapshot_id: str
    policy_snapshot_hash: str
    family: Literal["research", "planner"]
    task_type: str
    backend_mode: Literal["replay", "manual_ui"]
    prompt: str
    context_package: dict[str, Any]
    parent_task_id: str | None
    attempt: int
    created_at: str
    status: Literal["waiting", "valid", "repair_required", "approved"]
    validation_issues: list[str]
    response_hash: str | None


class StudioTaskCollectionDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    items: list[StudioTaskDTO]
    count: int


class ReviewSnapshotCreateDTO(StrictRequestDTO):
    executable_plan: dict[str, Any]
    final_edl_bundle: dict[str, Any]


class ReviewSnapshotDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    snapshot_hash: str
    project_id: str
    policy_snapshot_id: str
    policy_snapshot_hash: str
    created_at: str


class ReviewDecisionRequestDTO(StrictRequestDTO):
    action: Literal["approve", "replacement_requested"]
    replacement_kind: Literal["asset_change", "replan"] | None = None


class SequenceReviewDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    snapshot_hash: str
    sequence: dict[str, Any]
    edl_binding: dict[str, Any]
    decision: dict[str, Any] | None


class ProjectReviewDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["available", "unavailable"]
    project_id: str
    snapshot_id: str | None
    snapshot_hash: str | None
    sequence_ids: list[str]


class ReviewDecisionDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str
    decision_hash: str
    project_id: str
    sequence_id: str
    snapshot_id: str
    snapshot_hash: str
    executable_sequence_hash: str
    video_edl_hash: str
    audio_edl_hash: str
    action: Literal["approve", "replacement_requested"]
    replacement_kind: Literal["asset_change", "replan"] | None
    created_at: str
    producer: str
    producer_version: str


class PreviewJobDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str
    preview_request_id: str
    preview_request_hash: str
    attempt_ordinal: int
    project_id: str
    sequence_id: str
    snapshot_id: str
    snapshot_hash: str
    state: Literal["requested", "admitted", "running", "succeeded", "failed", "cancelled", "rejected_pre_admission"]
    created_at: str
    updated_at: str
    public_failure_code: str | None
    receipt_hash: str | None
    preview_manifest_hash: str | None
    delivery_id: str | None


class PreviewEventDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ordinal: int
    event_id: str
    state: str
    created_at: str
    public_code: str | None


class PreviewEventCollectionDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str
    items: list[PreviewEventDTO]
    count: int
