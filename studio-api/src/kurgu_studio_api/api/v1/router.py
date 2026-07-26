"""Deterministic v1 route registration."""

from __future__ import annotations

from fastapi import APIRouter

from ...application.project_service import ProjectApplicationService
from .projects import create_projects_router


def create_v1_router(service: ProjectApplicationService) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    router.include_router(create_projects_router(service))
    return router
