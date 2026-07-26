"""Minimal, deterministic FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI


APPLICATION_TITLE = "Kurgu Studio API"
APPLICATION_VERSION = "0.1.0"
APPLICATION_DESCRIPTION = (
    "Phase 1 control-plane contract generation foundation. "
    "No application endpoints are exposed in this slice."
)
OPENAPI_VERSION = "3.1.0"


def create_app() -> FastAPI:
    """Return a fresh routes-free application with fixed contract metadata."""
    application = FastAPI(
        title=APPLICATION_TITLE,
        version=APPLICATION_VERSION,
        description=APPLICATION_DESCRIPTION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.openapi_version = OPENAPI_VERSION
    return application
