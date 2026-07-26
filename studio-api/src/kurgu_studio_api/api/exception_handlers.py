"""Centralized sanitized exception handling."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..application.errors import ApplicationError
from .errors import ERROR_STATUS


def _pointer(location: tuple[Any, ...]) -> str:
    parts = [str(part) for part in location if part not in {"body", "path"}]
    if len(parts) > 1 and parts[0] == "domain" and parts[1] in {
        "core_only",
        "domain_pack",
    }:
        parts.pop(1)
    escaped = [part.replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(escaped) if escaped else ""


def _validation_message(error_type: str) -> str:
    if error_type == "missing":
        return "A required field is missing."
    if error_type == "extra_forbidden":
        return "An unexpected field is not allowed."
    if error_type == "union_tag_invalid":
        return "The discriminator has an unsupported value."
    return "The request field is invalid."


def _error_payload(
    code: str,
    message: str,
    issues: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "issues": issues,
        }
    }


def register_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        del request
        errors = exc.errors()
        domain_configuration_missing = bool(errors) and all(
            error["type"] == "missing"
            and _pointer(tuple(error["loc"])).startswith("/domain")
            for error in errors
        )
        code = (
            "DOMAIN_CONFIGURATION_REQUIRED"
            if domain_configuration_missing
            else "REQUEST_VALIDATION_FAILED"
        )
        message = (
            "A complete domain configuration is required."
            if domain_configuration_missing
            else "The request did not pass validation."
        )
        issues = [
            {
                "code": code,
                "json_pointer": _pointer(tuple(error["loc"])),
                "message": _validation_message(error["type"]),
            }
            for error in errors
        ]
        return JSONResponse(
            status_code=422,
            content=_error_payload(code, message, issues),
        )

    @application.exception_handler(ApplicationError)
    async def application_error_handler(
        request: Request,
        exc: ApplicationError,
    ) -> JSONResponse:
        del request
        return JSONResponse(
            status_code=ERROR_STATUS[exc.code],
            content=_error_payload(
                exc.code,
                exc.message,
                [
                    {
                        "code": issue.code,
                        "json_pointer": issue.json_pointer,
                        "message": issue.message,
                    }
                    for issue in exc.issues
                ],
            ),
        )

    @application.exception_handler(Exception)
    async def internal_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        del request, exc
        code = "INTERNAL_ERROR"
        message = "An internal error occurred."
        return JSONResponse(
            status_code=500,
            content=_error_payload(
                code,
                message,
                [
                    {
                        "code": code,
                        "json_pointer": "",
                        "message": message,
                    }
                ],
            ),
        )
