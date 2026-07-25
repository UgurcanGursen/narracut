"""Typed views and deterministic helpers for canonical migration results."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

from engine.contracts import DomainPackRegistry, canonical_json


CLASSIFICATIONS = (
    "EXACT",
    "RENAMED",
    "NORMALIZED",
    "SPLIT",
    "MERGED",
    "DEFAULTED",
    "DERIVED",
    "PRESERVED_AS_EXTENSION",
    "DROPPED",
    "UNSUPPORTED",
    "AMBIGUOUS",
    "INVALID_SOURCE",
)
SEVERITIES = ("INFO", "WARNING", "ERROR")
BLOCKING_CLASSIFICATIONS = frozenset(
    {"AMBIGUOUS", "INVALID_SOURCE"}
)
STRICT_BLOCKING_CLASSIFICATIONS = frozenset(
    {"DROPPED", "UNSUPPORTED", "AMBIGUOUS", "INVALID_SOURCE"}
)


def canonical_fingerprint(value: Any) -> str:
    """Return one canonical SHA-256 fingerprint implementation."""
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def deterministic_token(prefix: str, *parts: Any, length: int = 20) -> str:
    payload = canonical_json(list(parts)).encode("utf-8")
    return prefix + hashlib.sha256(payload).hexdigest()[:length]


def source_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, Mapping):
        return "object"
    return "object"


@dataclass(frozen=True)
class MigrationOptions:
    mode: str = "permissive"
    resolution_mode: str = "core_only"
    source_path: str = "input_v2.json"
    target_path: str = "workspace.json"
    registry: DomainPackRegistry | None = None
    domain_id: str | None = None
    domain_pack_version: str | None = None
    profile: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.mode not in {"strict", "permissive"}:
            raise ValueError("mode must be 'strict' or 'permissive'")
        if self.resolution_mode not in {"core_only", "domain_pack"}:
            raise ValueError(
                "resolution_mode must be 'core_only' or 'domain_pack'"
            )
        for name, value in (
            ("source_path", self.source_path),
            ("target_path", self.target_path),
        ):
            normalized = value.replace("\\", "/")
            if (
                not value
                or normalized.startswith("/")
                or ":" in normalized.split("/")[0]
                or ".." in normalized.split("/")
            ):
                raise ValueError(f"{name} must be a safe relative path")


@dataclass(frozen=True)
class MigrationMapping:
    source_pointer: str
    source_field: str
    source_type: str
    source_semantics: str
    destination_pointer: str | None
    destination_concept: str
    classification: str
    transformation: str
    loss_severity: str = "NONE"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        mapping_id = deterministic_token(
            "map_",
            self.source_pointer,
            self.destination_pointer,
            self.classification,
            self.transformation,
        )
        return {
            "mapping_id": mapping_id,
            "source_pointer": self.source_pointer,
            "source_field": self.source_field,
            "source_type": self.source_type,
            "source_semantics": self.source_semantics,
            "destination_pointer": self.destination_pointer,
            "destination_concept": self.destination_concept,
            "classification": self.classification,
            "transformation": self.transformation,
            "loss_severity": self.loss_severity,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class MigrationIssue:
    severity: str
    code: str
    message: str
    source_pointer: str
    destination_pointer: str | None
    classification: str
    action: str
    details: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        issue_id = deterministic_token(
            "mig_",
            self.code,
            self.source_pointer,
            self.destination_pointer,
            self.message,
        )
        result: dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "source_path": self.source_pointer or "/",
            "issue_id": issue_id,
            "source_pointer": self.source_pointer,
            "destination_pointer": self.destination_pointer,
            "classification": self.classification,
            "action": self.action,
        }
        if self.details:
            result["details"] = dict(self.details)
        return result


@dataclass(frozen=True)
class MigrationOutcome:
    workspace: Mapping[str, Any] | None
    result: Mapping[str, Any]

    @property
    def status(self) -> str:
        return str(self.result["status"])

    @property
    def succeeded(self) -> bool:
        return self.status in {"SUCCESS", "SUCCESS_WITH_LOSS"}
