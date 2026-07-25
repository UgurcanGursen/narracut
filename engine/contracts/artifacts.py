"""Artifact lineage and retention invariants; this module is not a cleanup engine."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .models import ArtifactRecord, RetentionPolicy
from .validation import ValidationIssue, ValidationResult


PROTECTED_RETENTION_CLASSES = frozenset(
    {"approved", "final", "provenance", "baseline", "pinned"}
)
ALL_RETENTION_CLASSES = frozenset(
    {
        "ephemeral",
        "temporary",
        "cache",
        "review",
        "approved",
        "final",
        "provenance",
        "baseline",
        "pinned",
    }
)


def _record(value: ArtifactRecord | Mapping[str, Any]) -> ArtifactRecord:
    if isinstance(value, ArtifactRecord):
        return value
    return ArtifactRecord.from_dict(value)


def validate_artifact_graph(
    values: Iterable[ArtifactRecord | Mapping[str, Any]],
    *,
    source_file: str = "<artifact-manifest>",
    project_ids: set[str] | None = None,
    sequence_ids: set[str] | None = None,
) -> ValidationResult:
    records = tuple(_record(value) for value in values)
    issues: list[ValidationIssue] = []
    by_id: dict[str, ArtifactRecord] = {}

    for index, record in enumerate(records):
        pointer = f"/artifacts/{index}"
        if record.artifact_id in by_id:
            issues.append(
                ValidationIssue(
                    source_file,
                    f"{pointer}/artifact_id",
                    "ARTIFACT_DUPLICATE_ID",
                    f"Duplicate artifact_id: {record.artifact_id}",
                )
            )
        by_id[record.artifact_id] = record

        if record.size_bytes < 0:
            issues.append(
                ValidationIssue(
                    source_file,
                    f"{pointer}/size_bytes",
                    "ARTIFACT_NEGATIVE_SIZE",
                    "Artifact size_bytes cannot be negative.",
                )
            )
        if record.artifact_id in record.dependency_ids:
            issues.append(
                ValidationIssue(
                    source_file,
                    f"{pointer}/dependency_ids",
                    "ARTIFACT_SELF_DEPENDENCY",
                    f"{record.artifact_id} cannot depend on itself.",
                )
            )
        if project_ids is not None and record.project_id not in project_ids:
            issues.append(
                ValidationIssue(
                    source_file,
                    f"{pointer}/project_id",
                    "ORPHAN_ARTIFACT",
                    f"Unknown project reference: {record.project_id}",
                )
            )
        if (
            sequence_ids is not None
            and record.sequence_id is not None
            and record.sequence_id not in sequence_ids
        ):
            issues.append(
                ValidationIssue(
                    source_file,
                    f"{pointer}/sequence_id",
                    "ORPHAN_ARTIFACT",
                    f"Unknown sequence reference: {record.sequence_id}",
                )
            )
        if (
            record.artifact_type in {"output", "render", "final_video"}
            and not record.dependency_ids
        ):
            issues.append(
                ValidationIssue(
                    source_file,
                    f"{pointer}/dependency_ids",
                    "ORPHAN_OUTPUT",
                    "Output artifacts must declare at least one dependency.",
                )
            )
        if record.cleanup_candidate and (
            record.locked
            or record.pinned
            or record.approved
            or record.retention_class in PROTECTED_RETENTION_CLASSES
        ):
            issues.append(
                ValidationIssue(
                    source_file,
                    f"{pointer}/cleanup_candidate",
                    "ARTIFACT_PROTECTED_FROM_CLEANUP",
                    "Locked, pinned, approved, or protected-retention artifacts "
                    "cannot be cleanup candidates.",
                )
            )

    for index, record in enumerate(records):
        for dependency_id in record.dependency_ids:
            if dependency_id not in by_id:
                issues.append(
                    ValidationIssue(
                        source_file,
                        f"/artifacts/{index}/dependency_ids",
                        "ARTIFACT_MISSING_DEPENDENCY",
                        f"Missing artifact dependency: {dependency_id}",
                    )
                )

    visiting: set[str] = set()
    visited: set[str] = set()
    reported_cycles: set[tuple[str, ...]] = set()

    def visit(artifact_id: str, path: tuple[str, ...]) -> None:
        if artifact_id in visiting:
            start = path.index(artifact_id)
            cycle = path[start:] + (artifact_id,)
            if cycle not in reported_cycles:
                reported_cycles.add(cycle)
                issues.append(
                    ValidationIssue(
                        source_file,
                        "/artifacts",
                        "ARTIFACT_DEPENDENCY_CYCLE",
                        "Artifact dependency cycle: " + " -> ".join(cycle),
                    )
                )
            return
        if artifact_id in visited or artifact_id not in by_id:
            return
        visiting.add(artifact_id)
        record = by_id[artifact_id]
        for dependency_id in record.dependency_ids:
            if dependency_id != artifact_id:
                visit(dependency_id, path + (artifact_id,))
        visiting.remove(artifact_id)
        visited.add(artifact_id)

    for artifact_id in sorted(by_id):
        visit(artifact_id, ())

    return ValidationResult(tuple(issues))


def validate_retention_policy(
    value: RetentionPolicy | Mapping[str, Any],
    *,
    source_file: str = "<retention-policy>",
) -> ValidationResult:
    policy = value if isinstance(value, RetentionPolicy) else RetentionPolicy.from_dict(value)
    issues: list[ValidationIssue] = []
    seen: set[str] = set()

    for index, rule in enumerate(policy.rules):
        retention_class = rule["retention_class"]
        if retention_class in seen:
            issues.append(
                ValidationIssue(
                    source_file,
                    f"/rules/{index}/retention_class",
                    "RETENTION_DUPLICATE_CLASS",
                    f"Duplicate retention class: {retention_class}",
                )
            )
        seen.add(retention_class)
        if retention_class in PROTECTED_RETENTION_CLASSES and (
            rule["ttl_days"] is not None or rule["cleanup_eligible"]
        ):
            issues.append(
                ValidationIssue(
                    source_file,
                    f"/rules/{index}",
                    "RETENTION_PROTECTED_TTL",
                    f"{retention_class} must not be TTL-cleanable.",
                )
            )

    for missing in sorted(ALL_RETENTION_CLASSES - seen):
        issues.append(
            ValidationIssue(
                source_file,
                "/rules",
                "RETENTION_MISSING_CLASS",
                f"Missing retention class rule: {missing}",
            )
        )

    return ValidationResult(tuple(issues))
