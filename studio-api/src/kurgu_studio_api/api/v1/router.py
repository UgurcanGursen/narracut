"""Deterministic v1 route registration."""

from __future__ import annotations

from fastapi import APIRouter

from ...application.project_service import ProjectApplicationService
from ...application.studio_workflow_service import StudioWorkflowService
from .projects import create_projects_router
from .studio_workflow import create_studio_workflow_router


def create_v1_router(
    service: ProjectApplicationService,
    workflow_service: StudioWorkflowService | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    router.include_router(create_projects_router(service))
    if workflow_service is not None:
        router.include_router(create_studio_workflow_router(workflow_service))
    return router
