"""Stable public error response models and HTTP mappings."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ErrorIssueDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    json_pointer: str
    message: str


class ErrorBodyDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    issues: list[ErrorIssueDTO]


class ErrorEnvelopeDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorBodyDTO


ERROR_STATUS = {
    "REQUEST_VALIDATION_FAILED": 422,
    "CONTRACT_VALIDATION_FAILED": 422,
    "DOMAIN_CONFIGURATION_REQUIRED": 422,
    "DOMAIN_UNKNOWN": 422,
    "DOMAIN_PROFILE_MISMATCH": 422,
    "PROJECT_NOT_FOUND": 404,
    "PROJECT_ID_COLLISION": 409,
    "TASK_NOT_FOUND": 404,
    "TASK_PROJECT_MISMATCH": 409,
    "TASK_STATE_INVALID": 409,
    "TASK_NOT_VALID": 409,
    "TASK_UNAVAILABLE": 422,
    "REPAIR_NOT_REQUIRED": 409,
    "REVIEW_SNAPSHOT_NOT_FOUND": 404,
    "REVIEW_SEQUENCE_NOT_FOUND": 404,
    "REVIEW_SNAPSHOT_INVALID": 422,
    "REVIEW_SEQUENCE_LOCKED": 409,
    "REVIEW_DECISION_INVALID": 422,
    "INTERNAL_ERROR": 500,
}
