"""Artifact lineage and retention invariants; this module is not a cleanup engine."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .models import ArtifactRecord, RetentionPolicy
from .validation import SchemaCatalog, ValidationIssue, ValidationResult


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


def _prefixed_schema_issues(
    result: ValidationResult,
    pointer_prefix: str,
) -> tuple[ValidationIssue, ...]:
    return tuple(
        ValidationIssue(
            issue.source_file,
            pointer_prefix + issue.json_pointer,
            issue.code,
            issue.message,
        )
        for issue in result.issues
    )


def _raw_catalog_required(api_name: str) -> TypeError:
    return TypeError(
        f"{api_name} requires catalog=SchemaCatalog(...) for raw Mapping "
        "input; schema validation cannot be bypassed."
    )


def validate_artifact_graph(
    values: Iterable[ArtifactRecord | Mapping[str, Any]],
    *,
    catalog: SchemaCatalog | None = None,
    source_file: str = "<artifact-manifest>",
    project_ids: set[str] | None = None,
    sequence_ids: set[str] | None = None,
) -> ValidationResult:
    """Validate schema first for raw mappings, then artifact graph invariants.

    ArtifactRecord inputs are treated as already schema-validated typed views.
    Raw Mapping inputs require the caller's explicit SchemaCatalog dependency.
    """
    raw_values = tuple(values)
    schema_issues: list[ValidationIssue] = []
    for index, value in enumerate(raw_values):
        if isinstance(value, ArtifactRecord):
            continue
        if not isinstance(value, Mapping):
            raise TypeError(
                "validate_artifact_graph accepts only ArtifactRecord or "
                "Mapping values."
            )
        if catalog is None:
            raise _raw_catalog_required("validate_artifact_graph")
        result = catalog.validate(value, "artifact.schema.json", source_file)
        schema_issues.extend(
            _prefixed_schema_issues(result, f"/artifacts/{index}")
        )
    if schema_issues:
        return ValidationResult(tuple(schema_issues))

    try:
        records = tuple(
            value
            if isinstance(value, ArtifactRecord)
            else ArtifactRecord._from_validated_dict(value)
            for value in raw_values
        )
    except (KeyError, TypeError, ValueError) as exc:
        return ValidationResult(
            (
                ValidationIssue(
                    source_file,
                    "/artifacts",
                    "CONTRACT_CONSTRUCTION_ERROR",
                    f"Schema-valid artifact construction failed: {exc}",
                ),
            )
        )
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
    catalog: SchemaCatalog | None = None,
    source_file: str = "<retention-policy>",
) -> ValidationResult:
    """Validate schema first for a raw mapping, then retention invariants.

    RetentionPolicy input is treated as an already schema-validated typed view.
    Raw Mapping input requires the caller's explicit SchemaCatalog dependency.
    """
    if not isinstance(value, (RetentionPolicy, Mapping)):
        raise TypeError(
            "validate_retention_policy accepts only RetentionPolicy or "
            "Mapping input."
        )
    if isinstance(value, Mapping):
        if catalog is None:
            raise _raw_catalog_required("validate_retention_policy")
        schema_result = catalog.validate(
            value,
            "retention_policy.schema.json",
            source_file,
        )
        if not schema_result.is_valid:
            return schema_result
        try:
            policy = RetentionPolicy._from_validated_dict(value)
        except (KeyError, TypeError, ValueError) as exc:
            return ValidationResult(
                (
                    ValidationIssue(
                        source_file,
                        "",
                        "CONTRACT_CONSTRUCTION_ERROR",
                        f"Schema-valid retention policy construction failed: {exc}",
                    ),
                )
            )
    else:
        policy = value
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
