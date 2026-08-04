"""Canonical Phase 2 alignment-confidence report contract."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import weakref
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ._canonical_json import encode_canonical_json_bytes
from .alignment_execution import ConfidenceAvailability
from .alignment_result import (
    AlignmentResult,
    AlignmentResultContractError,
    AlignmentTimingSource,
    serialize_alignment_result,
)
from .caption_groups import (
    CaptionGroupsArtifact,
    CaptionGroupsContractError,
    serialize_caption_groups,
)
from .narration import (
    CanonicalNarrationDocument,
    NarrationRevision,
    _has_materialized_narration_document_identity,
    _has_materialized_narration_revision_identity,
    _is_materialized_narration_document,
    _is_materialized_narration_revision,
)
from .temporal import STABLE_ISSUE_CODE_SET


ALIGNMENT_REPORT_V1 = "ALIGNMENT-REPORT-V1"
ALIGNMENT_REPORT_HASH_V1 = "ALIGNMENT-REPORT-HASH-V1"
ALIGNMENT_REPORT_FINDING_V1 = "ALIGNMENT-REPORT-FINDING-V1"
ALIGNMENT_REPORT_FINDING_HASH_V1 = "ALIGNMENT-REPORT-FINDING-HASH-V1"
ALIGNMENT_REPORT_POLICY_V1 = "ALIGNMENT-REPORT-POLICY-V1"


class AlignmentReportStatus(str, Enum):
    PASS = "PASS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"
    CONFIDENCE_UNAVAILABLE = "CONFIDENCE_UNAVAILABLE"
    CONFIDENCE_NOT_APPLICABLE = "CONFIDENCE_NOT_APPLICABLE"


class AlignmentFindingSeverity(str, Enum):
    WARNING = "WARNING"
    BLOCKER = "BLOCKER"


class AlignmentFindingScope(str, Enum):
    WORD = "WORD"
    CAPTION_GROUP = "CAPTION_GROUP"
    REPORT = "REPORT"


class AlignmentReportRejectionReason(str, Enum):
    STRUCTURE_INVALID = "STRUCTURE_INVALID"
    UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
    DEPENDENCY_CONTENT_DRIFT = "DEPENDENCY_CONTENT_DRIFT"
    DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
    POLICY_INVALID = "POLICY_INVALID"
    CONFIDENCE_INVALID = "CONFIDENCE_INVALID"
    FINDING_INVALID = "FINDING_INVALID"
    NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    CONTENT_DRIFT = "CONTENT_DRIFT"
    NOT_MATERIALIZED = "NOT_MATERIALIZED"


@dataclass(frozen=True)
class AlignmentReportPolicy:
    policy_version: str
    individual_warning_below_millionths: int
    individual_blocker_below_millionths: int
    caption_group_warning_below_millionths: int
    caption_group_blocker_below_millionths: int
    low_confidence_ratio_warning_at_or_above_millionths: int
    low_confidence_ratio_blocker_at_or_above_millionths: int


@dataclass(frozen=True)
class AlignmentReportFinding:
    schema_version: str
    hash_scope_version: str
    alignment_report_finding_id: str
    alignment_report_finding_hash: str
    alignment_result_id: str
    caption_groups_id: str
    alignment_report_policy_snapshot_hash: str
    ordinal: int
    issue_code: str
    severity: AlignmentFindingSeverity
    scope: AlignmentFindingScope
    word_ordinal: int | None
    word_id: str | None
    caption_group_ordinal: int | None
    caption_group_id: str | None
    start_word_ordinal: int | None
    end_exclusive_word_ordinal: int | None
    observed_millionths: int | None
    threshold_millionths: int | None


@dataclass(frozen=True)
class AlignmentReport:
    schema_version: str
    hash_scope_version: str
    alignment_report_id: str
    alignment_report_hash: str
    project_id: str
    document_id: str
    temporal_raw_package_hash: str
    narration_revision_id: str
    narration_revision_hash: str
    audio_artifact_id: str
    audio_artifact_hash: str
    alignment_request_id: str
    alignment_request_hash: str
    adapter_execution_id: str
    adapter_execution_hash: str
    timing_origin_evidence_id: str
    timing_origin_evidence_hash: str
    alignment_result_id: str
    alignment_result_hash: str
    caption_groups_id: str
    caption_groups_hash: str
    timing_source: AlignmentTimingSource
    confidence_availability: ConfidenceAvailability
    alignment_report_policy: AlignmentReportPolicy
    alignment_report_policy_snapshot_hash: str
    word_count: int
    caption_group_count: int
    evaluated_word_confidence_count: int
    evaluated_caption_group_confidence_count: int
    minimum_word_confidence_millionths: int | None
    minimum_caption_group_confidence_millionths: int | None
    low_confidence_word_count: int
    low_confidence_caption_group_count: int
    low_confidence_word_ratio_millionths: int | None
    warning_finding_count: int
    blocker_finding_count: int
    status: AlignmentReportStatus
    findings: tuple[AlignmentReportFinding, ...]


_FIXED_POINTERS = frozenset({
    "/", "/narration_document", "/narration_revision", "/alignment_result",
    "/caption_groups", "/policy", "/alignment_report_policy", "/findings",
})
_INDEXED_POINTER = re.compile(r"/findings/(?:0|[1-9][0-9]*)")


class AlignmentReportContractError(ValueError):
    def __init__(self, pointer: str, reason: AlignmentReportRejectionReason, issue_code: str | None = None) -> None:
        if (
            type(pointer) is not str
            or (pointer not in _FIXED_POINTERS and _INDEXED_POINTER.fullmatch(pointer) is None)
            or type(reason) is not AlignmentReportRejectionReason
        ):
            raise TypeError("invalid alignment report error construction")
        if issue_code is not None and (
            type(issue_code) is not str or issue_code not in STABLE_ISSUE_CODE_SET
        ):
            raise TypeError("invalid alignment report issue code")
        super().__init__(f"Alignment report rejected: {reason.value}")
        self.pointer = pointer
        self.reason = reason
        self.issue_code = issue_code


_POLICY_FIELDS = (
    "policy_version", "individual_warning_below_millionths",
    "individual_blocker_below_millionths", "caption_group_warning_below_millionths",
    "caption_group_blocker_below_millionths",
    "low_confidence_ratio_warning_at_or_above_millionths",
    "low_confidence_ratio_blocker_at_or_above_millionths",
)
_FINDING_FIELDS = (
    "schema_version", "hash_scope_version", "alignment_report_finding_id",
    "alignment_report_finding_hash", "alignment_result_id", "caption_groups_id",
    "alignment_report_policy_snapshot_hash", "ordinal", "issue_code", "severity",
    "scope", "word_ordinal", "word_id", "caption_group_ordinal", "caption_group_id",
    "start_word_ordinal", "end_exclusive_word_ordinal", "observed_millionths",
    "threshold_millionths",
)
_ROOT_FIELDS = (
    "schema_version", "hash_scope_version", "alignment_report_id",
    "alignment_report_hash", "project_id", "document_id", "temporal_raw_package_hash",
    "narration_revision_id", "narration_revision_hash", "audio_artifact_id",
    "audio_artifact_hash", "alignment_request_id", "alignment_request_hash",
    "adapter_execution_id", "adapter_execution_hash", "timing_origin_evidence_id",
    "timing_origin_evidence_hash", "alignment_result_id", "alignment_result_hash",
    "caption_groups_id", "caption_groups_hash", "timing_source",
    "confidence_availability", "alignment_report_policy",
    "alignment_report_policy_snapshot_hash", "word_count", "caption_group_count",
    "evaluated_word_confidence_count", "evaluated_caption_group_confidence_count",
    "minimum_word_confidence_millionths", "minimum_caption_group_confidence_millionths",
    "low_confidence_word_count", "low_confidence_caption_group_count",
    "low_confidence_word_ratio_millionths", "warning_finding_count",
    "blocker_finding_count", "status", "findings",
)
_ROOT_INTEGER_FIELDS = frozenset({
    "word_count", "caption_group_count", "evaluated_word_confidence_count",
    "evaluated_caption_group_confidence_count", "low_confidence_word_count",
    "low_confidence_caption_group_count", "warning_finding_count",
    "blocker_finding_count",
})
_ROOT_NULLABLE_INTEGER_FIELDS = frozenset({
    "minimum_word_confidence_millionths",
    "minimum_caption_group_confidence_millionths",
    "low_confidence_word_ratio_millionths",
})
_ROOT_ENUM_TYPES = {
    "timing_source": AlignmentTimingSource,
    "confidence_availability": ConfidenceAvailability,
    "status": AlignmentReportStatus,
}
_FINDING_NULLABLE_INTEGER_FIELDS = frozenset({
    "word_ordinal", "caption_group_ordinal", "start_word_ordinal",
    "end_exclusive_word_ordinal", "observed_millionths", "threshold_millionths",
})
_FINDING_NULLABLE_STRING_FIELDS = frozenset({"word_id", "caption_group_id"})
_ISSUES = frozenset({
    "INDIVIDUAL_CONFIDENCE_WARNING", "INDIVIDUAL_CONFIDENCE_BLOCKER",
    "SEGMENT_CONFIDENCE_WARNING", "SEGMENT_CONFIDENCE_BLOCKER",
    "LOW_CONFIDENCE_RATIO_WARNING", "LOW_CONFIDENCE_RATIO_BLOCKER",
    "CONFIDENCE_UNAVAILABLE",
})

_MATERIALIZED_ALIGNMENT_REPORTS: dict[
    int, tuple[weakref.ReferenceType[AlignmentReport], bytes, tuple[Any, ...]]
] = {}
_OWNED_ALIGNMENT_REPORT_REFERENCES: dict[int, weakref.ReferenceType[AlignmentReport]] = {}


def _reject(pointer: str, reason: AlignmentReportRejectionReason, issue_code: str | None = None) -> None:
    raise AlignmentReportContractError(pointer, reason, issue_code)


def _digest(value: Any) -> str:
    return hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _policy_dict(value: AlignmentReportPolicy) -> dict[str, Any]:
    return {field: getattr(value, field) for field in _POLICY_FIELDS}


def _finding_dict(value: AlignmentReportFinding) -> dict[str, Any]:
    result = {field: getattr(value, field) for field in _FINDING_FIELDS}
    result["severity"] = value.severity.value
    result["scope"] = value.scope.value
    return result


def _finding_projection(value: AlignmentReportFinding) -> dict[str, Any]:
    result = _finding_dict(value)
    result.pop("alignment_report_finding_id")
    result.pop("alignment_report_finding_hash")
    return result


def _report_dict(value: AlignmentReport) -> dict[str, Any]:
    result = {field: getattr(value, field) for field in _ROOT_FIELDS}
    result["timing_source"] = value.timing_source.value
    result["confidence_availability"] = value.confidence_availability.value
    result["alignment_report_policy"] = _policy_dict(value.alignment_report_policy)
    result["status"] = value.status.value
    result["findings"] = [_finding_dict(item) for item in value.findings]
    return result


def _report_projection(value: AlignmentReport) -> dict[str, Any]:
    result = _report_dict(value)
    result.pop("alignment_report_id")
    result.pop("alignment_report_hash")
    return result


def _policy_signature(value: Any) -> tuple[Any, ...]:
    if type(value) is not AlignmentReportPolicy:
        raise TypeError
    fields: list[tuple[int, int, Any]] = []
    for index, field in enumerate(_POLICY_FIELDS):
        item = getattr(value, field)
        expected_type = str if index == 0 else int
        if type(item) is not expected_type:
            raise TypeError
        fields.append((id(type(item)), id(item), item))
    return (id(value), tuple(fields))


def _finding_signature(value: Any) -> tuple[Any, ...]:
    if type(value) is not AlignmentReportFinding:
        raise TypeError
    fields: list[tuple[int, int, Any]] = []
    for field in _FINDING_FIELDS:
        item = getattr(value, field)
        if field == "severity":
            valid = type(item) is AlignmentFindingSeverity
        elif field == "scope":
            valid = type(item) is AlignmentFindingScope
        elif field == "ordinal":
            valid = type(item) is int
        elif field in _FINDING_NULLABLE_INTEGER_FIELDS:
            valid = item is None or type(item) is int
        elif field in _FINDING_NULLABLE_STRING_FIELDS:
            valid = item is None or type(item) is str
        else:
            valid = type(item) is str
        if not valid:
            raise TypeError
        fields.append((id(type(item)), id(item), item))
    return (id(value), tuple(fields))


def _signature(value: Any) -> tuple[Any, ...]:
    if type(value) is not AlignmentReport:
        raise TypeError
    root_fields: list[tuple[Any, ...]] = []
    for field in _ROOT_FIELDS:
        item = getattr(value, field)
        if field == "alignment_report_policy":
            root_fields.append((id(AlignmentReportPolicy), id(item), _policy_signature(item)))
            continue
        if field == "findings":
            if type(item) is not tuple:
                raise TypeError
            root_fields.append((id(tuple), id(item), tuple(_finding_signature(finding) for finding in item)))
            continue
        if field in _ROOT_ENUM_TYPES:
            valid = type(item) is _ROOT_ENUM_TYPES[field]
        elif field in _ROOT_INTEGER_FIELDS:
            valid = type(item) is int
        elif field in _ROOT_NULLABLE_INTEGER_FIELDS:
            valid = item is None or type(item) is int
        else:
            valid = type(item) is str
        if not valid:
            raise TypeError
        root_fields.append((id(type(item)), id(item), item))
    return tuple(root_fields)


def _validate_policy(value: Any, pointer: str = "/policy") -> tuple[AlignmentReportPolicy, str]:
    if type(value) is not AlignmentReportPolicy:
        _reject(pointer, AlignmentReportRejectionReason.POLICY_INVALID)
    if type(value.policy_version) is not str:
        _reject(pointer, AlignmentReportRejectionReason.POLICY_INVALID)
    if value.policy_version != ALIGNMENT_REPORT_POLICY_V1:
        _reject(pointer, AlignmentReportRejectionReason.POLICY_INVALID, "UNSUPPORTED_CONTRACT_ENUM")
    numbers = [getattr(value, field) for field in _POLICY_FIELDS[1:]]
    if any(type(number) is not int or number < 0 or number > 1_000_000 for number in numbers):
        _reject(pointer, AlignmentReportRejectionReason.POLICY_INVALID)
    if not (
        value.individual_blocker_below_millionths < value.individual_warning_below_millionths
        and value.caption_group_blocker_below_millionths < value.caption_group_warning_below_millionths
        and value.low_confidence_ratio_warning_at_or_above_millionths
        < value.low_confidence_ratio_blocker_at_or_above_millionths
    ):
        _reject(pointer, AlignmentReportRejectionReason.POLICY_INVALID)
    owned = AlignmentReportPolicy(*(_policy_dict(value)[field] for field in _POLICY_FIELDS))
    return owned, "sha256:" + _digest(_policy_dict(owned))


def _dependency_drift(pointer: str, narration: bool = False) -> None:
    _reject(
        pointer, AlignmentReportRejectionReason.DEPENDENCY_CONTENT_DRIFT,
        "ALIGNMENT_REQUEST_IDENTITY_MISMATCH" if narration else "REPLAY_HASH_MISMATCH",
    )


def _preflight(
    narration_document: Any,
    narration_revision: Any,
    alignment_result: Any,
    caption_groups: Any,
) -> None:
    if type(narration_document) is not CanonicalNarrationDocument or not _has_materialized_narration_document_identity(narration_document):
        raise TypeError("narration_document must be a genuine canonical narration document")
    if not _is_materialized_narration_document(narration_document):
        _dependency_drift("/narration_document", True)
    if type(narration_revision) is not NarrationRevision or not _has_materialized_narration_revision_identity(narration_revision):
        raise TypeError("narration_revision must be a genuine narration revision")
    if not _is_materialized_narration_revision(narration_revision):
        _dependency_drift("/narration_revision", True)
    if type(alignment_result) is not AlignmentResult:
        raise TypeError("alignment_result must be a genuine alignment result")
    try:
        serialize_alignment_result(alignment_result)
    except AlignmentResultContractError as error:
        if error.reason.value == "NOT_MATERIALIZED":
            raise TypeError("alignment_result must be a genuine alignment result") from None
        _dependency_drift("/alignment_result")
    except Exception:
        raise RuntimeError("alignment report dependency validation failed") from None
    if type(caption_groups) is not CaptionGroupsArtifact:
        raise TypeError("caption_groups must be a genuine caption groups artifact")
    try:
        serialize_caption_groups(caption_groups)
    except CaptionGroupsContractError as error:
        if error.reason.value == "NOT_MATERIALIZED":
            raise TypeError("caption_groups must be a genuine caption groups artifact") from None
        _dependency_drift("/caption_groups")
    except Exception:
        raise RuntimeError("alignment report dependency validation failed") from None


def _bindings(
    document: CanonicalNarrationDocument,
    revision: NarrationRevision,
    result: AlignmentResult,
    groups: CaptionGroupsArtifact,
) -> None:
    if (
        document.current_revision_id != revision.revision_id
        or document.project_id != revision.project_id
        or document.document_id != revision.document_id
    ):
        _reject("/narration_revision", AlignmentReportRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    if (
        result.project_id != document.project_id or result.document_id != document.document_id
        or result.narration_revision_id != revision.revision_id
        or result.narration_revision_hash != revision.revision_hash
    ):
        _reject("/alignment_result", AlignmentReportRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    if (
        groups.project_id != document.project_id or groups.document_id != document.document_id
        or groups.narration_revision_id != revision.revision_id
        or groups.narration_revision_hash != revision.revision_hash
        or groups.alignment_result_id != result.alignment_result_id
        or groups.alignment_result_hash != result.alignment_result_hash
    ):
        _reject("/caption_groups", AlignmentReportRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    if groups.confidence_availability is not result.confidence_availability:
        _reject("/caption_groups", AlignmentReportRejectionReason.CONFIDENCE_INVALID, "ADAPTER_PRECISION_OVERSTATED")
    words = revision.canonical_words
    timings = result.word_timings
    if len(words) != len(timings) or any(word.ordinal != index or word.word_id != timings[index].word_id for index, word in enumerate(words)):
        _reject("/alignment_result", AlignmentReportRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    cursor = 0
    for index, group in enumerate(groups.caption_groups):
        if (
            group.ordinal != index or group.start_word_ordinal != cursor
            or group.end_exclusive_word_ordinal <= cursor
            or group.end_exclusive_word_ordinal > len(timings)
            or group.word_ids != tuple(item.word_id for item in timings[cursor:group.end_exclusive_word_ordinal])
            or group.start_ms != timings[cursor].start_ms
            or group.end_ms != timings[group.end_exclusive_word_ordinal - 1].end_ms
        ):
            _reject("/caption_groups", AlignmentReportRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
        cursor = group.end_exclusive_word_ordinal
    if cursor != len(timings):
        _reject("/caption_groups", AlignmentReportRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")


def _new_finding(
    *, result: AlignmentResult, groups: CaptionGroupsArtifact, policy_hash: str,
    ordinal: int, issue_code: str, severity: AlignmentFindingSeverity,
    scope: AlignmentFindingScope, word_ordinal: int | None = None,
    word_id: str | None = None, caption_group_ordinal: int | None = None,
    caption_group_id: str | None = None, start_word_ordinal: int | None = None,
    end_exclusive_word_ordinal: int | None = None,
    observed_millionths: int | None = None, threshold_millionths: int | None = None,
) -> AlignmentReportFinding:
    base = AlignmentReportFinding(
        ALIGNMENT_REPORT_FINDING_V1, ALIGNMENT_REPORT_FINDING_HASH_V1,
        "alrf_" + "0" * 32, "0" * 64, result.alignment_result_id,
        groups.caption_groups_id, policy_hash, ordinal, issue_code, severity, scope,
        word_ordinal, word_id, caption_group_ordinal, caption_group_id,
        start_word_ordinal, end_exclusive_word_ordinal, observed_millionths,
        threshold_millionths,
    )
    digest = _digest(_finding_projection(base))
    return AlignmentReportFinding(
        base.schema_version, base.hash_scope_version, "alrf_" + digest[:32], digest,
        *tuple(getattr(base, field) for field in _FINDING_FIELDS[4:]),
    )


def _derive(
    document: CanonicalNarrationDocument, revision: NarrationRevision,
    result: AlignmentResult, groups: CaptionGroupsArtifact,
    policy: AlignmentReportPolicy, policy_hash: str,
) -> AlignmentReport:
    availability = result.confidence_availability
    word_count = len(result.word_timings)
    group_count = len(groups.caption_groups)
    findings: list[AlignmentReportFinding] = []
    if availability is ConfidenceAvailability.AVAILABLE:
        word_values: list[int] = []
        group_values: list[int] = []
        for index, timing in enumerate(result.word_timings):
            value = timing.confidence_millionths
            if type(value) is not int or value < 0 or value > 1_000_000:
                issue = "CONFIDENCE_REQUIRED_UNAVAILABLE" if value is None else "ADAPTER_PRECISION_OVERSTATED"
                _reject("/alignment_result", AlignmentReportRejectionReason.CONFIDENCE_INVALID, issue)
            word_values.append(value)
            if value < policy.individual_blocker_below_millionths:
                code, severity, threshold = "INDIVIDUAL_CONFIDENCE_BLOCKER", AlignmentFindingSeverity.BLOCKER, policy.individual_blocker_below_millionths
            elif value < policy.individual_warning_below_millionths:
                code, severity, threshold = "INDIVIDUAL_CONFIDENCE_WARNING", AlignmentFindingSeverity.WARNING, policy.individual_warning_below_millionths
            else:
                continue
            findings.append(_new_finding(
                result=result, groups=groups, policy_hash=policy_hash, ordinal=len(findings),
                issue_code=code, severity=severity, scope=AlignmentFindingScope.WORD,
                word_ordinal=index, word_id=timing.word_id,
                observed_millionths=value, threshold_millionths=threshold,
            ))
        for group in groups.caption_groups:
            value = group.confidence_millionths
            if type(value) is not int or value < 0 or value > 1_000_000:
                issue = "CONFIDENCE_REQUIRED_UNAVAILABLE" if value is None else "ADAPTER_PRECISION_OVERSTATED"
                _reject("/caption_groups", AlignmentReportRejectionReason.CONFIDENCE_INVALID, issue)
            group_values.append(value)
            if value < policy.caption_group_blocker_below_millionths:
                code, severity, threshold = "SEGMENT_CONFIDENCE_BLOCKER", AlignmentFindingSeverity.BLOCKER, policy.caption_group_blocker_below_millionths
            elif value < policy.caption_group_warning_below_millionths:
                code, severity, threshold = "SEGMENT_CONFIDENCE_WARNING", AlignmentFindingSeverity.WARNING, policy.caption_group_warning_below_millionths
            else:
                continue
            findings.append(_new_finding(
                result=result, groups=groups, policy_hash=policy_hash, ordinal=len(findings),
                issue_code=code, severity=severity, scope=AlignmentFindingScope.CAPTION_GROUP,
                caption_group_ordinal=group.ordinal, caption_group_id=group.caption_group_id,
                start_word_ordinal=group.start_word_ordinal,
                end_exclusive_word_ordinal=group.end_exclusive_word_ordinal,
                observed_millionths=value, threshold_millionths=threshold,
            ))
        low_words = sum(value < policy.individual_warning_below_millionths for value in word_values)
        low_groups = sum(value < policy.caption_group_warning_below_millionths for value in group_values)
        ratio = (low_words * 1_000_000) // word_count
        if low_words * 1_000_000 >= policy.low_confidence_ratio_blocker_at_or_above_millionths * word_count:
            code, severity, threshold = "LOW_CONFIDENCE_RATIO_BLOCKER", AlignmentFindingSeverity.BLOCKER, policy.low_confidence_ratio_blocker_at_or_above_millionths
        elif low_words * 1_000_000 >= policy.low_confidence_ratio_warning_at_or_above_millionths * word_count:
            code, severity, threshold = "LOW_CONFIDENCE_RATIO_WARNING", AlignmentFindingSeverity.WARNING, policy.low_confidence_ratio_warning_at_or_above_millionths
        else:
            code = ""
        if code:
            findings.append(_new_finding(
                result=result, groups=groups, policy_hash=policy_hash, ordinal=len(findings),
                issue_code=code, severity=severity, scope=AlignmentFindingScope.REPORT,
                observed_millionths=ratio, threshold_millionths=threshold,
            ))
        evaluated_words, evaluated_groups = word_count, group_count
        minimum_word, minimum_group = min(word_values), min(group_values)
    else:
        for timing in result.word_timings:
            if timing.confidence_millionths is not None:
                _reject("/alignment_result", AlignmentReportRejectionReason.CONFIDENCE_INVALID, "ADAPTER_PRECISION_OVERSTATED")
        for group in groups.caption_groups:
            if group.confidence_millionths is not None:
                _reject("/caption_groups", AlignmentReportRejectionReason.CONFIDENCE_INVALID, "ADAPTER_PRECISION_OVERSTATED")
        evaluated_words = evaluated_groups = low_words = low_groups = 0
        minimum_word = minimum_group = ratio = None
        if availability is ConfidenceAvailability.UNAVAILABLE:
            findings.append(_new_finding(
                result=result, groups=groups, policy_hash=policy_hash, ordinal=0,
                issue_code="CONFIDENCE_UNAVAILABLE", severity=AlignmentFindingSeverity.WARNING,
                scope=AlignmentFindingScope.REPORT,
            ))
    warning_count = sum(item.severity is AlignmentFindingSeverity.WARNING for item in findings)
    blocker_count = sum(item.severity is AlignmentFindingSeverity.BLOCKER for item in findings)
    if availability is ConfidenceAvailability.UNAVAILABLE:
        status = AlignmentReportStatus.CONFIDENCE_UNAVAILABLE
    elif availability is ConfidenceAvailability.NOT_APPLICABLE:
        status = AlignmentReportStatus.CONFIDENCE_NOT_APPLICABLE
    elif blocker_count:
        status = AlignmentReportStatus.BLOCKED
    elif warning_count:
        status = AlignmentReportStatus.REVIEW_REQUIRED
    else:
        status = AlignmentReportStatus.PASS
    base = AlignmentReport(
        ALIGNMENT_REPORT_V1, ALIGNMENT_REPORT_HASH_V1, "alrep_" + "0" * 32,
        "0" * 64, document.project_id, document.document_id,
        result.temporal_raw_package_hash, revision.revision_id, revision.revision_hash,
        result.audio_artifact_id, result.audio_artifact_hash, result.alignment_request_id,
        result.alignment_request_hash, result.adapter_execution_id,
        result.adapter_execution_hash, result.timing_origin_evidence_id,
        result.timing_origin_evidence_hash, result.alignment_result_id,
        result.alignment_result_hash, groups.caption_groups_id, groups.caption_groups_hash,
        result.timing_source, availability, policy, policy_hash, word_count, group_count,
        evaluated_words, evaluated_groups, minimum_word, minimum_group, low_words,
        low_groups, ratio, warning_count, blocker_count, status, tuple(findings),
    )
    digest = _digest(_report_projection(base))
    return AlignmentReport(
        base.schema_version, base.hash_scope_version, "alrep_" + digest[:32], digest,
        *tuple(getattr(base, field) for field in _ROOT_FIELDS[4:]),
    )


def _register(report: AlignmentReport, envelope: bytes) -> None:
    key = id(report)
    existing = _MATERIALIZED_ALIGNMENT_REPORTS.get(key)
    if existing is not None and existing[0]() is not None and existing[0]() is not report:
        raise RuntimeError("alignment report provenance registration failed")
    def cleanup(reference: weakref.ReferenceType[AlignmentReport]) -> None:
        entry = _MATERIALIZED_ALIGNMENT_REPORTS.get(key)
        if entry is not None and entry[0] is reference:
            _MATERIALIZED_ALIGNMENT_REPORTS.pop(key, None)
        if _OWNED_ALIGNMENT_REPORT_REFERENCES.get(key) is reference:
            _OWNED_ALIGNMENT_REPORT_REFERENCES.pop(key, None)
    reference = weakref.ref(report, cleanup)
    entry = (reference, envelope, _signature(report))
    try:
        _MATERIALIZED_ALIGNMENT_REPORTS[key] = entry
        _OWNED_ALIGNMENT_REPORT_REFERENCES[key] = reference
        if _MATERIALIZED_ALIGNMENT_REPORTS.get(key) is not entry or reference() is not report:
            raise RuntimeError("alignment report provenance registration failed")
    except Exception:
        if _MATERIALIZED_ALIGNMENT_REPORTS.get(key) is entry:
            _MATERIALIZED_ALIGNMENT_REPORTS.pop(key, None)
        if _OWNED_ALIGNMENT_REPORT_REFERENCES.get(key) is reference:
            _OWNED_ALIGNMENT_REPORT_REFERENCES.pop(key, None)
        raise


def compile_alignment_report(
    *, narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision, alignment_result: AlignmentResult,
    caption_groups: CaptionGroupsArtifact, policy: AlignmentReportPolicy,
) -> AlignmentReport:
    _preflight(narration_document, narration_revision, alignment_result, caption_groups)
    _bindings(narration_document, narration_revision, alignment_result, caption_groups)
    owned_policy, policy_hash = _validate_policy(policy)
    report = _derive(narration_document, narration_revision, alignment_result, caption_groups, owned_policy, policy_hash)
    try:
        _register(report, encode_canonical_json_bytes(_report_dict(report)))
    except AlignmentReportContractError:
        raise
    except Exception:
        raise RuntimeError("alignment report construction failed") from None
    return report


class _Pairs(list):
    pass


def _parse(source: bytes) -> Any:
    if type(source) is not bytes:
        _reject("/", AlignmentReportRejectionReason.STRUCTURE_INVALID)
    try:
        text = source.decode("utf-8")
        value = json.loads(
            text, object_pairs_hook=_Pairs,
            parse_int=lambda token: (_raise_number() if token == "-0" else int(token)),
            parse_float=lambda _: (_ for _ in ()).throw(ValueError()),
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except Exception:
        _reject("/", AlignmentReportRejectionReason.NON_CANONICAL_SERIALIZATION)
    def convert(item: Any) -> Any:
        if type(item) is _Pairs:
            keys = [pair[0] for pair in item]
            if (
                any(type(key) is not str or unicodedata.normalize("NFC", key) != key for key in keys)
                or len(keys) != len(set(keys))
            ):
                _reject("/", AlignmentReportRejectionReason.NON_CANONICAL_SERIALIZATION)
            return {key: convert(val) for key, val in item}
        if type(item) is list:
            return [convert(val) for val in item]
        if type(item) is str and unicodedata.normalize("NFC", item) != item:
            _reject("/", AlignmentReportRejectionReason.NON_CANONICAL_SERIALIZATION)
        return item
    return convert(value)


def _raise_number() -> Any:
    raise ValueError("forbidden number")


def _exact_keys(value: Any, fields: tuple[str, ...], pointer: str) -> dict[str, Any]:
    if type(value) is not dict:
        _reject(pointer, AlignmentReportRejectionReason.STRUCTURE_INVALID)
    keys = set(value)
    if keys != set(fields):
        _reject(pointer, AlignmentReportRejectionReason.STRUCTURE_INVALID)
    return value


def _loaded_policy(value: Any) -> AlignmentReportPolicy:
    if type(value) is not dict or set(value) != set(_POLICY_FIELDS):
        _reject("/alignment_report_policy", AlignmentReportRejectionReason.POLICY_INVALID)
    data = value
    try:
        policy = AlignmentReportPolicy(*(data[field] for field in _POLICY_FIELDS))
    except Exception:
        _reject("/alignment_report_policy", AlignmentReportRejectionReason.POLICY_INVALID)
    return _validate_policy(policy, "/alignment_report_policy")[0]


def _loaded_root_types(root: dict[str, Any]) -> None:
    for field in _ROOT_FIELDS:
        value = root[field]
        if field in _ROOT_INTEGER_FIELDS:
            valid = type(value) is int and 0 <= value <= 2**32 - 1
        elif field in _ROOT_NULLABLE_INTEGER_FIELDS:
            valid = value is None or (
                type(value) is int and 0 <= value <= 1_000_000
            )
        elif field == "alignment_report_policy":
            valid = True
        elif field == "findings":
            valid = True
        else:
            valid = type(value) is str
        if not valid:
            _reject("/", AlignmentReportRejectionReason.STRUCTURE_INVALID)
    if type(root["findings"]) is not list:
        _reject("/findings", AlignmentReportRejectionReason.STRUCTURE_INVALID)


def _loaded_finding_types(data: dict[str, Any], pointer: str) -> None:
    for field in _FINDING_FIELDS:
        value = data[field]
        if field == "ordinal":
            valid = type(value) is int and 0 <= value <= 2**32 - 1
        elif field in _FINDING_NULLABLE_INTEGER_FIELDS:
            upper_bound = 1_000_000 if field in {"observed_millionths", "threshold_millionths"} else 2**32 - 1
            valid = value is None or (
                type(value) is int and 0 <= value <= upper_bound
            )
        elif field in _FINDING_NULLABLE_STRING_FIELDS:
            valid = value is None or type(value) is str
        else:
            valid = type(value) is str
        if not valid:
            _reject(pointer, AlignmentReportRejectionReason.STRUCTURE_INVALID)


def _loaded_enum(value: str, enum_type: type[Enum], pointer: str) -> Enum:
    try:
        return enum_type(value)
    except ValueError:
        _reject(
            pointer, AlignmentReportRejectionReason.UNSUPPORTED_VALUE,
            "UNSUPPORTED_CONTRACT_ENUM",
        )


def _root_difference(field: str) -> None:
    if field in {"project_id", "document_id"}:
        pointer = "/narration_document"
    elif field in {"narration_revision_id", "narration_revision_hash"}:
        pointer = "/narration_revision"
    elif field in {
        "caption_groups_id", "caption_groups_hash", "caption_group_count",
        "evaluated_caption_group_confidence_count",
        "minimum_caption_group_confidence_millionths",
        "low_confidence_caption_group_count",
    }:
        pointer = "/caption_groups"
    else:
        pointer = "/alignment_result"
    _reject(
        pointer, AlignmentReportRejectionReason.DEPENDENCY_BINDING_INVALID,
        "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
    )


def load_alignment_report(
    source: bytes, *, narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision, alignment_result: AlignmentResult,
    caption_groups: CaptionGroupsArtifact, policy: AlignmentReportPolicy,
) -> AlignmentReport:
    _preflight(narration_document, narration_revision, alignment_result, caption_groups)
    _bindings(narration_document, narration_revision, alignment_result, caption_groups)
    owned_policy, policy_hash = _validate_policy(policy)
    expected = _derive(narration_document, narration_revision, alignment_result, caption_groups, owned_policy, policy_hash)
    value = _parse(source)
    try:
        canonical = encode_canonical_json_bytes(value)
    except Exception:
        _reject("/", AlignmentReportRejectionReason.NON_CANONICAL_SERIALIZATION)
    if source != canonical:
        _reject("/", AlignmentReportRejectionReason.NON_CANONICAL_SERIALIZATION)
    root = _exact_keys(value, _ROOT_FIELDS, "/")
    _loaded_root_types(root)
    if root["schema_version"] != ALIGNMENT_REPORT_V1 or root["hash_scope_version"] != ALIGNMENT_REPORT_HASH_V1:
        _reject("/", AlignmentReportRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
    expected_dict = _report_dict(expected)
    declaration_fields = _ROOT_FIELDS[4:23]
    for field in declaration_fields:
        if field in _ROOT_ENUM_TYPES:
            _loaded_enum(root[field], _ROOT_ENUM_TYPES[field], "/")
        if root[field] != expected_dict[field]:
            _root_difference(field)
    loaded_policy = _loaded_policy(root["alignment_report_policy"])
    if _policy_dict(loaded_policy) != _policy_dict(expected.alignment_report_policy) or root["alignment_report_policy_snapshot_hash"] != expected.alignment_report_policy_snapshot_hash:
        _reject("/alignment_report_policy", AlignmentReportRejectionReason.POLICY_INVALID)
    metric_fields = _ROOT_FIELDS[25:37]
    for field in metric_fields:
        if field == "status":
            _loaded_enum(root[field], AlignmentReportStatus, "/")
        if root[field] != expected_dict[field]:
            _root_difference(field)
    findings = root["findings"]
    if type(findings) is not list or len(findings) != len(expected.findings):
        _reject("/findings", AlignmentReportRejectionReason.STRUCTURE_INVALID)
    for index, (actual, wanted) in enumerate(zip(findings, expected_dict["findings"])):
        pointer = f"/findings/{index}"
        data = _exact_keys(actual, _FINDING_FIELDS, pointer)
        _loaded_finding_types(data, pointer)
        if data["schema_version"] != ALIGNMENT_REPORT_FINDING_V1 or data["hash_scope_version"] != ALIGNMENT_REPORT_FINDING_HASH_V1:
            _reject(pointer, AlignmentReportRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
        if data["issue_code"] not in _ISSUES:
            _reject(pointer, AlignmentReportRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
        _loaded_enum(data["severity"], AlignmentFindingSeverity, pointer)
        _loaded_enum(data["scope"], AlignmentFindingScope, pointer)
        for field in _FINDING_FIELDS[4:]:
            if data[field] != wanted[field]:
                _reject(pointer, AlignmentReportRejectionReason.FINDING_INVALID, wanted["issue_code"] if wanted["issue_code"] in _ISSUES else None)
        projection = {field: data[field] for field in _FINDING_FIELDS if field not in {"alignment_report_finding_id", "alignment_report_finding_hash"}}
        digest = _digest(projection)
        if data["alignment_report_finding_hash"] != digest:
            _reject(pointer, AlignmentReportRejectionReason.IDENTITY_MISMATCH)
        if data["alignment_report_finding_id"] != "alrf_" + digest[:32]:
            _reject(pointer, AlignmentReportRejectionReason.IDENTITY_MISMATCH)
    projection = {field: root[field] for field in _ROOT_FIELDS if field not in {"alignment_report_id", "alignment_report_hash"}}
    digest = _digest(projection)
    if root["alignment_report_hash"] != digest:
        _reject("/", AlignmentReportRejectionReason.IDENTITY_MISMATCH)
    if root["alignment_report_id"] != "alrep_" + digest[:32]:
        _reject("/", AlignmentReportRejectionReason.IDENTITY_MISMATCH)
    envelope = encode_canonical_json_bytes(expected_dict)
    if source != envelope:
        _reject("/", AlignmentReportRejectionReason.NON_CANONICAL_SERIALIZATION)
    try:
        _register(expected, envelope)
    except Exception:
        raise RuntimeError("alignment report construction failed") from None
    return expected


def serialize_alignment_report(report: AlignmentReport) -> bytes:
    owner = _OWNED_ALIGNMENT_REPORT_REFERENCES.get(id(report))
    entry = _MATERIALIZED_ALIGNMENT_REPORTS.get(id(report))
    if type(report) is not AlignmentReport or owner is None or owner() is not report:
        _reject("/", AlignmentReportRejectionReason.NOT_MATERIALIZED)
    if entry is None or entry[0] is not owner or entry[0]() is not report:
        _reject("/", AlignmentReportRejectionReason.CONTENT_DRIFT)
    try:
        if entry[2] != _signature(report):
            raise ValueError
        if type(report.alignment_report_policy) is not AlignmentReportPolicy or type(report.findings) is not tuple:
            raise ValueError
        for finding in report.findings:
            if type(finding) is not AlignmentReportFinding or type(finding.severity) is not AlignmentFindingSeverity or type(finding.scope) is not AlignmentFindingScope:
                raise ValueError
            digest = _digest(_finding_projection(finding))
            if finding.alignment_report_finding_hash != digest or finding.alignment_report_finding_id != "alrf_" + digest[:32]:
                raise ValueError
        digest = _digest(_report_projection(report))
        if report.alignment_report_hash != digest or report.alignment_report_id != "alrep_" + digest[:32]:
            raise ValueError
        envelope = encode_canonical_json_bytes(_report_dict(report))
        if envelope != entry[1]:
            raise ValueError
    except Exception:
        _reject("/", AlignmentReportRejectionReason.CONTENT_DRIFT)
    return entry[1]
