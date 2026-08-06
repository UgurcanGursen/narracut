"""Thin project HTTP routes and DTO/application mapping."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Response, status

from ...application.models import (
    CoreOnlyDomainCommand,
    CreateProjectCommand,
    DomainPackDomainCommand,
    DomainProfileCommand,
    ResolvedDomainSelection,
)
from ...application.project_service import ProjectApplicationService
from ..errors import ErrorEnvelopeDTO
from .dto import (
    CoreOnlyDomainCreateDTO,
    DomainPackDomainCreateDTO,
    ProjectArtifactsResponseDTO,
    ProjectCreateRequestDTO,
    ProjectCreateResponseDTO,
    ProjectListResponseDTO,
    ProjectStatusResponseDTO,
    ResolvedDomainDTO,
)


PROJECT_ID_PATTERN = r"^prj_[a-z0-9][a-z0-9_-]{2,63}$"
ProjectIdPath = Annotated[str, Path(pattern=PROJECT_ID_PATTERN)]


def _resolved_domain_dto(
    domain: ResolvedDomainSelection,
) -> ResolvedDomainDTO:
    return ResolvedDomainDTO(
        resolution_mode=domain.resolution_mode,
        domain_id=domain.domain_id,
        domain_pack_version=domain.domain_pack_version,
        profile_id=domain.profile_id,
        policy_snapshot_id=domain.policy_snapshot_id,
    )


def _command(request: ProjectCreateRequestDTO) -> CreateProjectCommand:
    if isinstance(request.domain, CoreOnlyDomainCreateDTO):
        domain = CoreOnlyDomainCommand()
    elif isinstance(request.domain, DomainPackDomainCreateDTO):
        domain = DomainPackDomainCommand(
            domain_id=request.domain.domain_id,
            domain_pack_version=request.domain.domain_pack_version,
            profile=DomainProfileCommand(
                profile_id=request.domain.profile.profile_id,
                enabled_extensions=tuple(
                    item.model_dump(mode="python")
                    for item in request.domain.profile.enabled_extensions
                ),
                policy_overrides=request.domain.profile.policy_overrides,
            ),
        )
    else:  # pragma: no cover - Pydantic discriminator closes this branch.
        raise TypeError("Unsupported domain request variant.")
    return CreateProjectCommand(title=request.title, domain=domain)


def create_projects_router(
    service: ProjectApplicationService,
) -> APIRouter:
    router = APIRouter(prefix="/projects", tags=["projects"])

    @router.get(
        "",
        operation_id="listProjects",
        response_model=ProjectListResponseDTO,
        responses={500: {"model": ErrorEnvelopeDTO}},
    )
    def list_projects() -> ProjectListResponseDTO:
        view = service.list_projects()
        return ProjectListResponseDTO(
            items=[
                ProjectStatusResponseDTO(
                    project_id=item.project_id,
                    status=item.status,
                    updated_at=item.updated_at,
                    version=item.version,
                    domain=_resolved_domain_dto(item.domain),
                    persistence_scope=item.persistence_scope,
                )
                for item in view.items
            ],
            count=view.count,
            persistence_scope=view.persistence_scope,
        )

    @router.post(
        "",
        operation_id="createProject",
        status_code=status.HTTP_201_CREATED,
        response_model=ProjectCreateResponseDTO,
        responses={
            409: {"model": ErrorEnvelopeDTO},
            422: {"model": ErrorEnvelopeDTO},
            500: {"model": ErrorEnvelopeDTO},
        },
    )
    def create_project(
        request: ProjectCreateRequestDTO,
        response: Response,
    ) -> ProjectCreateResponseDTO:
        created = service.create_project(_command(request))
        response.headers["Location"] = (
            f"/api/v1/projects/{created.project['project_id']}/status"
        )
        return ProjectCreateResponseDTO(
            project=created.project,
            domain=_resolved_domain_dto(created.domain),
            persistence_scope=created.persistence_scope,
        )

    @router.get(
        "/{project_id}/status",
        operation_id="getProjectStatus",
        response_model=ProjectStatusResponseDTO,
        responses={
            404: {"model": ErrorEnvelopeDTO},
            422: {"model": ErrorEnvelopeDTO},
            500: {"model": ErrorEnvelopeDTO},
        },
    )
    def get_project_status(
        project_id: ProjectIdPath,
    ) -> ProjectStatusResponseDTO:
        view = service.get_project_status(project_id)
        return ProjectStatusResponseDTO(
            project_id=view.project_id,
            status=view.status,
            updated_at=view.updated_at,
            version=view.version,
            domain=_resolved_domain_dto(view.domain),
            persistence_scope=view.persistence_scope,
        )

    @router.get(
        "/{project_id}/artifacts",
        operation_id="listProjectArtifacts",
        response_model=ProjectArtifactsResponseDTO,
        responses={
            404: {"model": ErrorEnvelopeDTO},
            422: {"model": ErrorEnvelopeDTO},
            500: {"model": ErrorEnvelopeDTO},
        },
    )
    def list_project_artifacts(
        project_id: ProjectIdPath,
    ) -> ProjectArtifactsResponseDTO:
        view = service.list_project_artifacts(project_id)
        return ProjectArtifactsResponseDTO(
            project_id=view.project_id,
            items=list(view.items),
            count=view.count,
            persistence_scope=view.persistence_scope,
        )

    return router
