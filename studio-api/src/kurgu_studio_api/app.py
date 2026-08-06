"""FastAPI application factory for the local durable Studio control plane."""

from __future__ import annotations

from fastapi import FastAPI

from .api.exception_handlers import register_exception_handlers
from .api.v1 import create_v1_router
from .infrastructure.runtime import Runtime, build_runtime


APPLICATION_TITLE = "Kurgu Studio API"
APPLICATION_VERSION = "0.1.0"
APPLICATION_DESCRIPTION = (
    "Phase 13 local Studio API with SQLite project persistence."
)
OPENAPI_VERSION = "3.1.0"


def create_app(runtime: Runtime | None = None) -> FastAPI:
    """Return an application with a supplied or local durable runtime."""
    active_runtime = runtime or build_runtime()
    application = FastAPI(
        title=APPLICATION_TITLE,
        version=APPLICATION_VERSION,
        description=APPLICATION_DESCRIPTION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.openapi_version = OPENAPI_VERSION
    application.state.runtime = active_runtime
    register_exception_handlers(application)
    application.include_router(
        create_v1_router(
            active_runtime.project_service,
            getattr(active_runtime, "workflow_service", None),
        )
    )
    return application
