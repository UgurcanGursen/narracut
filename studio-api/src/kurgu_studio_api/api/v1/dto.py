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
    persistence_scope: Literal["process_lifetime"]


class ProjectStatusResponseDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    status: str
    updated_at: str
    version: int
    domain: ResolvedDomainDTO
    persistence_scope: Literal["process_lifetime"]


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
    persistence_scope: Literal["process_lifetime"]
