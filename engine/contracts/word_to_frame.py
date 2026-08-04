"""Deterministic, fail-closed Phase 2 word-to-frame compilation contract."""

from __future__ import annotations

import hashlib
import json
import math
import re
import weakref
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ._canonical_json import encode_canonical_json_bytes
from .alignment_execution import ConfidenceAvailability
from .alignment_result import (
    AlignmentResult,
    AlignmentResultContractError,
    AlignmentResultRejectionReason,
    WordTiming,
    serialize_alignment_result,
)
from .caption_groups import (
    CaptionGroup,
    CaptionGroupsArtifact,
    CaptionGroupsContractError,
    CaptionGroupingRejectionReason,
    serialize_caption_groups,
)
from .emphasis_events import (
    EmphasisEvent,
    EmphasisEventsArtifact,
    EmphasisEventsContractError,
    EmphasisEventsRejectionReason,
    serialize_emphasis_events,
)
from .temporal import STABLE_ISSUE_CODE_SET


WORD_TO_FRAME_V1 = "WORD-TO-FRAME-V1"
WORD_TO_FRAME_HASH_V1 = "WORD-TO-FRAME-HASH-V1"
WORD_TO_FRAME_POLICY_V1 = "WORD-TO-FRAME-POLICY-V1"

_UINT32_MAX = 2**32 - 1
_JS_SAFE_INTEGER_MAX = 2**53 - 1
_INDEXED_POINTER = re.compile(
    r"^/(?:word_frames|caption_frames|emphasis_frames)/(?:0|[1-9][0-9]*)$"
)
_FIXED_POINTERS = frozenset(
    {
        "/",
        "/alignment_result",
        "/caption_groups",
        "/emphasis_events",
        "/frame_rate",
        "/word_frames",
        "/caption_frames",
        "/emphasis_frames",
    }
)


class TemporalFrameSpanKind(str, Enum):
    WORD = "WORD"
    CAPTION_GROUP = "CAPTION_GROUP"
    EMPHASIS_EVENT = "EMPHASIS_EVENT"


class WordToFrameRejectionReason(str, Enum):
    STRUCTURE_INVALID = "STRUCTURE_INVALID"
    UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
    DEPENDENCY_CONTENT_DRIFT = "DEPENDENCY_CONTENT_DRIFT"
    DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
    FRAME_RATE_INVALID = "FRAME_RATE_INVALID"
    SOURCE_RANGE_INVALID = "SOURCE_RANGE_INVALID"
    TIMING_INVALID = "TIMING_INVALID"
    FRAME_MAPPING_INVALID = "FRAME_MAPPING_INVALID"
    NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    CONTENT_DRIFT = "CONTENT_DRIFT"
    NOT_MATERIALIZED = "NOT_MATERIALIZED"


@dataclass(frozen=True)
class TemporalFrameRate:
    numerator: int
    denominator: int


@dataclass(frozen=True)
class TemporalCompiledFrameSpan:
    source_kind: TemporalFrameSpanKind
    source_id: str
    ordinal: int
    start_word_ordinal: int
    end_exclusive_word_ordinal: int
    start_word_id: str
    end_word_id: str
    start_ms: int
    end_ms: int
    start_frame: int
    end_exclusive_frame: int


@dataclass(frozen=True)
class WordToFrameArtifact:
    schema_version: str
    hash_scope_version: str
    word_to_frame_id: str
    word_to_frame_hash: str
    project_id: str
    document_id: str
    narration_revision_id: str
    narration_revision_hash: str
    alignment_result_id: str
    alignment_result_hash: str
    caption_groups_id: str
    caption_groups_hash: str
    emphasis_events_id: str
    emphasis_events_hash: str
    confidence_availability: ConfidenceAvailability
    mapping_policy_version: str
    frame_rate: TemporalFrameRate
    word_frames: tuple[TemporalCompiledFrameSpan, ...]
    caption_frames: tuple[TemporalCompiledFrameSpan, ...]
    emphasis_frames: tuple[TemporalCompiledFrameSpan, ...]


class WordToFrameContractError(ValueError):
    def __init__(
        self,
        pointer: str,
        reason: WordToFrameRejectionReason,
        issue_code: str | None = None,
    ) -> None:
        if (
            type(pointer) is not str
            or (
                pointer not in _FIXED_POINTERS
                and _INDEXED_POINTER.fullmatch(pointer) is None
            )
            or type(reason) is not WordToFrameRejectionReason
        ):
            raise TypeError("invalid word-to-frame error construction")
        if issue_code is not None and (
            type(issue_code) is not str
            or issue_code not in STABLE_ISSUE_CODE_SET
        ):
            raise TypeError("invalid word-to-frame issue code")
        super().__init__(f"Word-to-frame artifact rejected: {reason.value}")
        self.pointer = pointer
        self.reason = reason
        self.issue_code = issue_code


_ROOT_FIELDS = tuple(WordToFrameArtifact.__dataclass_fields__)
_RATE_FIELDS = tuple(TemporalFrameRate.__dataclass_fields__)
_SPAN_FIELDS = tuple(TemporalCompiledFrameSpan.__dataclass_fields__)
_ROOT_STRING_FIELDS = tuple(
    field
    for field in _ROOT_FIELDS
    if field
    not in {
        "confidence_availability",
        "frame_rate",
        "word_frames",
        "caption_frames",
        "emphasis_frames",
    }
)
_ROOT_DECLARATION_FIELDS = tuple(
    field
    for field in _ROOT_FIELDS
    if field
    not in {
        "schema_version",
        "hash_scope_version",
        "word_to_frame_id",
        "word_to_frame_hash",
        "mapping_policy_version",
        "frame_rate",
        "word_frames",
        "caption_frames",
        "emphasis_frames",
    }
)
_SPAN_STRING_FIELDS = (
    "source_kind",
    "source_id",
    "start_word_id",
    "end_word_id",
)
_SPAN_INTEGER_FIELDS = (
    "ordinal",
    "start_word_ordinal",
    "end_exclusive_word_ordinal",
    "start_ms",
    "end_ms",
    "start_frame",
    "end_exclusive_frame",
)
_SPAN_COLLECTIONS = (
    ("word_frames", TemporalFrameSpanKind.WORD),
    ("caption_frames", TemporalFrameSpanKind.CAPTION_GROUP),
    ("emphasis_frames", TemporalFrameSpanKind.EMPHASIS_EVENT),
)

_MATERIALIZED: dict[
    int,
    tuple[
        weakref.ReferenceType[WordToFrameArtifact],
        bytes,
        tuple[int, ...],
    ],
] = {}


def _reject(
    pointer: str,
    reason: WordToFrameRejectionReason,
    issue_code: str | None = None,
) -> None:
    raise WordToFrameContractError(pointer, reason, issue_code)


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _rate_dict(value: TemporalFrameRate) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _span_dict(value: TemporalCompiledFrameSpan) -> dict[str, Any]:
    return {
        "source_kind": value.source_kind.value,
        "source_id": value.source_id,
        "ordinal": value.ordinal,
        "start_word_ordinal": value.start_word_ordinal,
        "end_exclusive_word_ordinal": value.end_exclusive_word_ordinal,
        "start_word_id": value.start_word_id,
        "end_word_id": value.end_word_id,
        "start_ms": value.start_ms,
        "end_ms": value.end_ms,
        "start_frame": value.start_frame,
        "end_exclusive_frame": value.end_exclusive_frame,
    }


def _artifact_dict(value: WordToFrameArtifact) -> dict[str, Any]:
    return {
        "schema_version": value.schema_version,
        "hash_scope_version": value.hash_scope_version,
        "word_to_frame_id": value.word_to_frame_id,
        "word_to_frame_hash": value.word_to_frame_hash,
        "project_id": value.project_id,
        "document_id": value.document_id,
        "narration_revision_id": value.narration_revision_id,
        "narration_revision_hash": value.narration_revision_hash,
        "alignment_result_id": value.alignment_result_id,
        "alignment_result_hash": value.alignment_result_hash,
        "caption_groups_id": value.caption_groups_id,
        "caption_groups_hash": value.caption_groups_hash,
        "emphasis_events_id": value.emphasis_events_id,
        "emphasis_events_hash": value.emphasis_events_hash,
        "confidence_availability": value.confidence_availability.value,
        "mapping_policy_version": value.mapping_policy_version,
        "frame_rate": _rate_dict(value.frame_rate),
        "word_frames": [_span_dict(span) for span in value.word_frames],
        "caption_frames": [_span_dict(span) for span in value.caption_frames],
        "emphasis_frames": [_span_dict(span) for span in value.emphasis_frames],
    }


def _artifact_projection(value: WordToFrameArtifact) -> dict[str, Any]:
    result = _artifact_dict(value)
    result.pop("word_to_frame_id")
    result.pop("word_to_frame_hash")
    return result


def _identity_signature(value: WordToFrameArtifact) -> tuple[int, ...]:
    signature: list[int] = []

    def visit(item: Any) -> None:
        signature.extend((id(item), id(type(item))))
        if type(item) is WordToFrameArtifact:
            for field in _ROOT_FIELDS:
                visit(getattr(item, field))
        elif type(item) is TemporalFrameRate:
            for field in _RATE_FIELDS:
                visit(getattr(item, field))
        elif type(item) is TemporalCompiledFrameSpan:
            for field in _SPAN_FIELDS:
                visit(getattr(item, field))
        elif type(item) is tuple:
            for nested in item:
                visit(nested)

    visit(value)
    return tuple(signature)


def _artifact_has_exact_shape(value: WordToFrameArtifact) -> bool:
    if (
        type(value) is not WordToFrameArtifact
        or any(type(getattr(value, field)) is not str for field in _ROOT_STRING_FIELDS)
        or type(value.confidence_availability) is not ConfidenceAvailability
        or type(value.frame_rate) is not TemporalFrameRate
        or type(value.frame_rate.numerator) is not int
        or type(value.frame_rate.denominator) is not int
    ):
        return False
    for collection in (
        value.word_frames,
        value.caption_frames,
        value.emphasis_frames,
    ):
        if type(collection) is not tuple:
            return False
        for span in collection:
            if (
                type(span) is not TemporalCompiledFrameSpan
                or type(span.source_kind) is not TemporalFrameSpanKind
                or any(
                    type(getattr(span, field)) is not str
                    for field in ("source_id", "start_word_id", "end_word_id")
                )
                or any(
                    type(getattr(span, field)) is not int
                    for field in _SPAN_INTEGER_FIELDS
                )
            ):
                return False
    return True


def _dependency_error(pointer: str) -> None:
    _reject(
        pointer,
        WordToFrameRejectionReason.DEPENDENCY_CONTENT_DRIFT,
        "REPLAY_HASH_MISMATCH",
    )


def _alignment_bytes(value: AlignmentResult) -> bytes:
    if type(value) is not AlignmentResult:
        raise TypeError("alignment_result must be a genuine exact dependency")
    try:
        return bytes(serialize_alignment_result(value))
    except AlignmentResultContractError as error:
        if error.reason is AlignmentResultRejectionReason.NOT_MATERIALIZED:
            raise TypeError(
                "alignment_result must be a genuine exact dependency"
            ) from None
        _dependency_error("/alignment_result")
    except TypeError:
        raise
    except Exception:
        _dependency_error("/alignment_result")


def _caption_bytes(value: CaptionGroupsArtifact) -> bytes:
    if type(value) is not CaptionGroupsArtifact:
        raise TypeError("caption_groups must be a genuine exact dependency")
    try:
        return bytes(serialize_caption_groups(value))
    except CaptionGroupsContractError as error:
        if error.reason is CaptionGroupingRejectionReason.NOT_MATERIALIZED:
            raise TypeError(
                "caption_groups must be a genuine exact dependency"
            ) from None
        _dependency_error("/caption_groups")
    except TypeError:
        raise
    except Exception:
        _dependency_error("/caption_groups")


def _emphasis_bytes(value: EmphasisEventsArtifact) -> bytes:
    if type(value) is not EmphasisEventsArtifact:
        raise TypeError("emphasis_events must be a genuine exact dependency")
    try:
        return bytes(serialize_emphasis_events(value))
    except EmphasisEventsContractError as error:
        if error.reason is EmphasisEventsRejectionReason.NOT_MATERIALIZED:
            raise TypeError(
                "emphasis_events must be a genuine exact dependency"
            ) from None
        _dependency_error("/emphasis_events")
    except TypeError:
        raise
    except Exception:
        _dependency_error("/emphasis_events")


def _validate_dependency_bindings(
    result: AlignmentResult,
    groups: CaptionGroupsArtifact,
    emphasis: EmphasisEventsArtifact,
) -> None:
    baseline = (
        result.project_id,
        result.document_id,
        result.narration_revision_id,
        result.narration_revision_hash,
    )
    group_lineage = (
        groups.project_id,
        groups.document_id,
        groups.narration_revision_id,
        groups.narration_revision_hash,
    )
    if group_lineage != baseline or (
        groups.alignment_result_id,
        groups.alignment_result_hash,
    ) != (result.alignment_result_id, result.alignment_result_hash):
        _reject(
            "/caption_groups",
            WordToFrameRejectionReason.DEPENDENCY_BINDING_INVALID,
            "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
        )
    emphasis_lineage = (
        emphasis.project_id,
        emphasis.document_id,
        emphasis.narration_revision_id,
        emphasis.narration_revision_hash,
    )
    if emphasis_lineage != baseline or (
        emphasis.alignment_result_id,
        emphasis.alignment_result_hash,
    ) != (result.alignment_result_id, result.alignment_result_hash) or (
        emphasis.caption_groups_id,
        emphasis.caption_groups_hash,
    ) != (groups.caption_groups_id, groups.caption_groups_hash):
        _reject(
            "/emphasis_events",
            WordToFrameRejectionReason.DEPENDENCY_BINDING_INVALID,
            "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
        )
    if groups.confidence_availability is not result.confidence_availability:
        _reject(
            "/caption_groups",
            WordToFrameRejectionReason.DEPENDENCY_BINDING_INVALID,
            "ADAPTER_PRECISION_OVERSTATED",
        )
    if emphasis.confidence_availability is not result.confidence_availability:
        _reject(
            "/emphasis_events",
            WordToFrameRejectionReason.DEPENDENCY_BINDING_INVALID,
            "ADAPTER_PRECISION_OVERSTATED",
        )


def _source_range_invalid(
    pointer: str, issue_code: str = "CANONICAL_COVERAGE_BLOCKER"
) -> None:
    _reject(
        pointer,
        WordToFrameRejectionReason.SOURCE_RANGE_INVALID,
        issue_code,
    )


def _source_timing_invalid(pointer: str) -> None:
    _reject(
        pointer,
        WordToFrameRejectionReason.TIMING_INVALID,
        "ADAPTER_PRECISION_OVERSTATED",
    )


def _validate_source_inventory(
    result: AlignmentResult,
    groups: CaptionGroupsArtifact,
    emphasis: EmphasisEventsArtifact,
) -> None:
    timings = result.word_timings
    if type(timings) is not tuple or not timings:
        _source_range_invalid("/word_frames")
    seen_word_ids: set[str] = set()
    previous_end: int | None = None
    for ordinal, timing in enumerate(timings):
        pointer = f"/word_frames/{ordinal}"
        if type(timing) is not WordTiming or type(timing.word_id) is not str:
            _source_range_invalid(pointer)
        if timing.word_id in seen_word_ids:
            _source_range_invalid(pointer)
        seen_word_ids.add(timing.word_id)
        if (
            type(timing.start_ms) is not int
            or type(timing.end_ms) is not int
            or timing.start_ms < 0
            or timing.end_ms <= timing.start_ms
            or (previous_end is not None and timing.start_ms < previous_end)
        ):
            _source_timing_invalid(pointer)
        confidence = timing.confidence_millionths
        if result.confidence_availability is ConfidenceAvailability.AVAILABLE:
            if type(confidence) is not int or not 0 <= confidence <= 1_000_000:
                _dependency_error("/alignment_result")
        elif confidence is not None:
            _dependency_error("/alignment_result")
        previous_end = timing.end_ms

    source_groups = groups.caption_groups
    if type(source_groups) is not tuple or not source_groups:
        _source_range_invalid("/caption_frames")
    cursor = 0
    seen_group_ids: set[str] = set()
    group_by_id: dict[str, CaptionGroup] = {}
    for index, group in enumerate(source_groups):
        pointer = f"/caption_frames/{index}"
        if type(group) is not CaptionGroup:
            _source_range_invalid(pointer)
        if type(group.ordinal) is not int or group.ordinal != index:
            _source_range_invalid(pointer, "CANONICAL_WORD_ORDER_INVALID")
        if type(group.caption_group_id) is not str or group.caption_group_id in seen_group_ids:
            _source_range_invalid(pointer)
        seen_group_ids.add(group.caption_group_id)
        if (
            type(group.start_word_ordinal) is not int
            or type(group.end_exclusive_word_ordinal) is not int
            or group.start_word_ordinal != cursor
            or not group.start_word_ordinal < group.end_exclusive_word_ordinal
            or group.end_exclusive_word_ordinal > len(timings)
        ):
            _source_range_invalid(pointer)
        selected = timings[
            group.start_word_ordinal : group.end_exclusive_word_ordinal
        ]
        expected_ids = tuple(timing.word_id for timing in selected)
        if (
            type(group.word_ids) is not tuple
            or any(type(word_id) is not str for word_id in group.word_ids)
            or group.word_ids != expected_ids
            or type(group.start_word_id) is not str
            or type(group.end_word_id) is not str
            or group.start_word_id != expected_ids[0]
            or group.end_word_id != expected_ids[-1]
            or group.alignment_result_id != result.alignment_result_id
            or group.narration_revision_id != result.narration_revision_id
        ):
            _source_range_invalid(pointer)
        if (
            group.start_ms != selected[0].start_ms
            or group.end_ms != selected[-1].end_ms
        ):
            _source_timing_invalid(pointer)
        group_by_id[group.caption_group_id] = group
        cursor = group.end_exclusive_word_ordinal
    if cursor != len(timings):
        _source_range_invalid("/caption_frames")

    source_events = emphasis.emphasis_events
    if type(source_events) is not tuple:
        _source_range_invalid("/emphasis_frames")
    seen_event_ids: set[str] = set()
    previous_event_end = 0
    for index, event in enumerate(source_events):
        pointer = f"/emphasis_frames/{index}"
        if type(event) is not EmphasisEvent:
            _source_range_invalid(pointer)
        if type(event.ordinal) is not int or event.ordinal != index:
            _source_range_invalid(pointer, "CANONICAL_WORD_ORDER_INVALID")
        if type(event.emphasis_event_id) is not str or event.emphasis_event_id in seen_event_ids:
            _source_range_invalid(pointer)
        seen_event_ids.add(event.emphasis_event_id)
        if (
            type(event.start_word_ordinal) is not int
            or type(event.end_exclusive_word_ordinal) is not int
            or event.start_word_ordinal < previous_event_end
            or not event.start_word_ordinal < event.end_exclusive_word_ordinal
            or event.end_exclusive_word_ordinal > len(timings)
        ):
            _source_range_invalid(pointer)
        selected = timings[
            event.start_word_ordinal : event.end_exclusive_word_ordinal
        ]
        expected_ids = tuple(timing.word_id for timing in selected)
        containing_group = group_by_id.get(event.caption_group_id)
        if (
            type(event.word_ids) is not tuple
            or any(type(word_id) is not str for word_id in event.word_ids)
            or event.word_ids != expected_ids
            or type(event.start_word_id) is not str
            or type(event.end_word_id) is not str
            or event.start_word_id != expected_ids[0]
            or event.end_word_id != expected_ids[-1]
            or event.narration_revision_id != result.narration_revision_id
            or event.alignment_result_id != result.alignment_result_id
            or event.caption_groups_id != groups.caption_groups_id
            or containing_group is None
            or not (
                containing_group.start_word_ordinal
                <= event.start_word_ordinal
                < event.end_exclusive_word_ordinal
                <= containing_group.end_exclusive_word_ordinal
            )
        ):
            _source_range_invalid(pointer)
        if (
            event.start_ms != selected[0].start_ms
            or event.end_ms != selected[-1].end_ms
        ):
            _source_timing_invalid(pointer)
        previous_event_end = event.end_exclusive_word_ordinal


def _validate_frame_rate(value: TemporalFrameRate) -> TemporalFrameRate:
    if type(value) is not TemporalFrameRate:
        raise TypeError("frame_rate must be exact TemporalFrameRate")
    numerator = value.numerator
    denominator = value.denominator
    if (
        type(numerator) is not int
        or type(denominator) is not int
        or not 1 <= numerator <= _UINT32_MAX
        or not 1 <= denominator <= _UINT32_MAX
        or math.gcd(numerator, denominator) != 1
        or numerator < denominator
        or numerator > 240 * denominator
    ):
        _reject(
            "/frame_rate",
            WordToFrameRejectionReason.FRAME_RATE_INVALID,
            "FRAME_RATE_INVALID",
        )
    return TemporalFrameRate(numerator, denominator)


def _frames(
    start_ms: int,
    end_ms: int,
    rate: TemporalFrameRate,
    pointer: str,
) -> tuple[int, int]:
    if (
        type(start_ms) is not int
        or type(end_ms) is not int
        or start_ms < 0
        or end_ms <= start_ms
    ):
        _reject(
            pointer,
            WordToFrameRejectionReason.TIMING_INVALID,
            "TIMESTAMP_NON_MONOTONIC",
        )
    scale = 1000 * rate.denominator
    start = (start_ms * rate.numerator) // scale
    end = (end_ms * rate.numerator + scale - 1) // scale
    if (
        start < 0
        or end <= start
        or start > _JS_SAFE_INTEGER_MAX
        or end > _JS_SAFE_INTEGER_MAX
    ):
        _reject(
            pointer,
            WordToFrameRejectionReason.FRAME_MAPPING_INVALID,
        )
    if (
        abs(start * scale - start_ms * rate.numerator) >= scale
        or abs(end * scale - end_ms * rate.numerator) >= scale
    ):
        _reject(
            pointer,
            WordToFrameRejectionReason.FRAME_MAPPING_INVALID,
            "FRAME_BOUNDARY_DRIFT_EXCEEDED",
        )
    return start, end


def _span(
    kind: TemporalFrameSpanKind,
    source_id: str,
    ordinal: int,
    start_word_ordinal: int,
    end_exclusive_word_ordinal: int,
    start_word_id: str,
    end_word_id: str,
    start_ms: int,
    end_ms: int,
    rate: TemporalFrameRate,
    pointer: str,
) -> TemporalCompiledFrameSpan:
    start_frame, end_frame = _frames(start_ms, end_ms, rate, pointer)
    return TemporalCompiledFrameSpan(
        kind,
        source_id,
        ordinal,
        start_word_ordinal,
        end_exclusive_word_ordinal,
        start_word_id,
        end_word_id,
        start_ms,
        end_ms,
        start_frame,
        end_frame,
    )


def _compile(
    *,
    alignment_result: AlignmentResult,
    caption_groups: CaptionGroupsArtifact,
    emphasis_events: EmphasisEventsArtifact,
    frame_rate: TemporalFrameRate,
) -> WordToFrameArtifact:
    _alignment_bytes(alignment_result)
    _caption_bytes(caption_groups)
    _emphasis_bytes(emphasis_events)
    _validate_dependency_bindings(
        alignment_result, caption_groups, emphasis_events
    )
    _validate_source_inventory(
        alignment_result, caption_groups, emphasis_events
    )
    rate = _validate_frame_rate(frame_rate)

    word_frames = tuple(
        _span(
            TemporalFrameSpanKind.WORD,
            timing.word_id,
            ordinal,
            ordinal,
            ordinal + 1,
            timing.word_id,
            timing.word_id,
            timing.start_ms,
            timing.end_ms,
            rate,
            f"/word_frames/{ordinal}",
        )
        for ordinal, timing in enumerate(alignment_result.word_timings)
    )
    caption_frames = tuple(
        _span(
            TemporalFrameSpanKind.CAPTION_GROUP,
            group.caption_group_id,
            group.ordinal,
            group.start_word_ordinal,
            group.end_exclusive_word_ordinal,
            group.start_word_id,
            group.end_word_id,
            group.start_ms,
            group.end_ms,
            rate,
            f"/caption_frames/{index}",
        )
        for index, group in enumerate(caption_groups.caption_groups)
    )
    emphasis_frames = tuple(
        _span(
            TemporalFrameSpanKind.EMPHASIS_EVENT,
            event.emphasis_event_id,
            event.ordinal,
            event.start_word_ordinal,
            event.end_exclusive_word_ordinal,
            event.start_word_id,
            event.end_word_id,
            event.start_ms,
            event.end_ms,
            rate,
            f"/emphasis_frames/{index}",
        )
        for index, event in enumerate(emphasis_events.emphasis_events)
    )

    base = WordToFrameArtifact(
        WORD_TO_FRAME_V1,
        WORD_TO_FRAME_HASH_V1,
        "",
        "",
        alignment_result.project_id,
        alignment_result.document_id,
        alignment_result.narration_revision_id,
        alignment_result.narration_revision_hash,
        alignment_result.alignment_result_id,
        alignment_result.alignment_result_hash,
        caption_groups.caption_groups_id,
        caption_groups.caption_groups_hash,
        emphasis_events.emphasis_events_id,
        emphasis_events.emphasis_events_hash,
        alignment_result.confidence_availability,
        WORD_TO_FRAME_POLICY_V1,
        rate,
        word_frames,
        caption_frames,
        emphasis_frames,
    )
    artifact_hash = _digest(
        encode_canonical_json_bytes(_artifact_projection(base))
    )
    return WordToFrameArtifact(
        base.schema_version,
        base.hash_scope_version,
        "w2f_" + artifact_hash[:32],
        artifact_hash,
        *tuple(
            getattr(base, field)
            for field in list(base.__dataclass_fields__)[4:]
        ),
    )


def _register(artifact: WordToFrameArtifact, envelope: bytes) -> None:
    key = id(artifact)
    old = _MATERIALIZED.get(key)
    if old is not None and old[0]() is not None:
        raise RuntimeError("word-to-frame registry collision")

    def forget(reference: weakref.ReferenceType[WordToFrameArtifact]) -> None:
        current = _MATERIALIZED.get(key)
        if current is not None and current[0] is reference:
            _MATERIALIZED.pop(key, None)

    reference = weakref.ref(artifact, forget)
    entry = (reference, bytes(envelope), _identity_signature(artifact))
    try:
        _MATERIALIZED[key] = entry
        if _MATERIALIZED.get(key) is not entry:
            raise RuntimeError
    except Exception:
        if _MATERIALIZED.get(key) is entry:
            _MATERIALIZED.pop(key, None)
        raise RuntimeError("word-to-frame registration failed") from None


def compile_word_to_frame(
    *,
    alignment_result: AlignmentResult,
    caption_groups: CaptionGroupsArtifact,
    emphasis_events: EmphasisEventsArtifact,
    frame_rate: TemporalFrameRate,
) -> WordToFrameArtifact:
    artifact = _compile(
        alignment_result=alignment_result,
        caption_groups=caption_groups,
        emphasis_events=emphasis_events,
        frame_rate=frame_rate,
    )
    envelope = encode_canonical_json_bytes(_artifact_dict(artifact))
    _register(artifact, envelope)
    return artifact


class _Pairs(list):
    pass


def _parse_source(source: bytes) -> Any:
    if type(source) is not bytes:
        raise TypeError("source must be exact bytes")
    try:
        if source.startswith(b"\xef\xbb\xbf"):
            raise ValueError
        value = json.loads(
            source.decode("utf-8"),
            object_pairs_hook=_Pairs,
            parse_float=lambda _: (_ for _ in ()).throw(ValueError()),
            parse_int=lambda text: (
                int(text)
                if text == str(int(text))
                else (_ for _ in ()).throw(ValueError())
            ),
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except Exception:
        _reject(
            "/", WordToFrameRejectionReason.NON_CANONICAL_SERIALIZATION
        )

    def convert(item: Any) -> Any:
        if type(item) is _Pairs:
            keys = [key for key, _ in item]
            if len(keys) != len(set(keys)):
                _reject(
                    "/",
                    WordToFrameRejectionReason.NON_CANONICAL_SERIALIZATION,
                )
            return {key: convert(nested) for key, nested in item}
        if type(item) is list:
            return [convert(nested) for nested in item]
        return item

    return convert(value)


def _require_exact_keys(
    value: dict[str, Any], fields: tuple[str, ...], pointer: str
) -> None:
    allowed = frozenset(fields)
    if any(type(key) is not str or key not in allowed for key in value):
        _reject(pointer, WordToFrameRejectionReason.STRUCTURE_INVALID)
    for field in fields:
        if field not in value:
            _reject(pointer, WordToFrameRejectionReason.STRUCTURE_INVALID)


def _root_declaration_difference(field: str) -> None:
    if field in {"caption_groups_id", "caption_groups_hash"}:
        pointer = "/caption_groups"
    elif field in {"emphasis_events_id", "emphasis_events_hash"}:
        pointer = "/emphasis_events"
    else:
        pointer = "/alignment_result"
    issue = (
        "ADAPTER_PRECISION_OVERSTATED"
        if field == "confidence_availability"
        else "ALIGNMENT_REQUEST_IDENTITY_MISMATCH"
    )
    _reject(
        pointer,
        WordToFrameRejectionReason.DEPENDENCY_BINDING_INVALID,
        issue,
    )


def _validate_loaded_rate(
    value: Any,
    expected: TemporalFrameRate,
) -> None:
    if type(value) is not dict:
        _reject("/frame_rate", WordToFrameRejectionReason.STRUCTURE_INVALID)
    _require_exact_keys(value, _RATE_FIELDS, "/frame_rate")
    if any(type(value[field]) is not int for field in _RATE_FIELDS):
        _reject("/frame_rate", WordToFrameRejectionReason.STRUCTURE_INVALID)
    candidate = TemporalFrameRate(value["numerator"], value["denominator"])
    _validate_frame_rate(candidate)
    if candidate != expected:
        _reject(
            "/frame_rate",
            WordToFrameRejectionReason.FRAME_RATE_INVALID,
            "FRAME_RATE_INVALID",
        )


def _frame_issue(
    actual: int,
    timestamp_ms: int,
    rate: TemporalFrameRate,
) -> str | None:
    scale = 1000 * rate.denominator
    if abs(actual * scale - timestamp_ms * rate.numerator) >= scale:
        return "FRAME_BOUNDARY_DRIFT_EXCEEDED"
    return None


def _span_difference(
    field: str,
    actual: dict[str, Any],
    expected: dict[str, Any],
    pointer: str,
    rate: TemporalFrameRate,
) -> None:
    if field == "ordinal":
        _reject(
            pointer,
            WordToFrameRejectionReason.SOURCE_RANGE_INVALID,
            "CANONICAL_WORD_ORDER_INVALID",
        )
    if field in {
        "source_kind",
        "source_id",
        "start_word_ordinal",
        "end_exclusive_word_ordinal",
        "start_word_id",
        "end_word_id",
    }:
        _reject(
            pointer,
            WordToFrameRejectionReason.SOURCE_RANGE_INVALID,
            "CANONICAL_COVERAGE_BLOCKER",
        )
    if field in {"start_ms", "end_ms"}:
        _reject(
            pointer,
            WordToFrameRejectionReason.TIMING_INVALID,
            "ADAPTER_PRECISION_OVERSTATED",
        )
    if field == "start_frame":
        _reject(
            pointer,
            WordToFrameRejectionReason.FRAME_MAPPING_INVALID,
            _frame_issue(actual[field], expected["start_ms"], rate),
        )
    if field == "end_exclusive_frame":
        _reject(
            pointer,
            WordToFrameRejectionReason.FRAME_MAPPING_INVALID,
            _frame_issue(actual[field], expected["end_ms"], rate),
        )
    _reject(pointer, WordToFrameRejectionReason.STRUCTURE_INVALID)


def _validate_loaded_spans(
    value: Any,
    expected: tuple[TemporalCompiledFrameSpan, ...],
    field: str,
    kind: TemporalFrameSpanKind,
    rate: TemporalFrameRate,
) -> None:
    base_pointer = f"/{field}"
    if type(value) is not list:
        _reject(base_pointer, WordToFrameRejectionReason.STRUCTURE_INVALID)
    if len(value) != len(expected):
        _reject(
            base_pointer,
            WordToFrameRejectionReason.SOURCE_RANGE_INVALID,
            "CANONICAL_COVERAGE_BLOCKER",
        )
    for index, (actual, expected_span) in enumerate(zip(value, expected)):
        pointer = f"/{field}/{index}"
        if type(actual) is not dict:
            _reject(pointer, WordToFrameRejectionReason.STRUCTURE_INVALID)
        _require_exact_keys(actual, _SPAN_FIELDS, pointer)
        if any(type(actual[name]) is not str for name in _SPAN_STRING_FIELDS):
            _reject(pointer, WordToFrameRejectionReason.STRUCTURE_INVALID)
        if any(type(actual[name]) is not int for name in _SPAN_INTEGER_FIELDS):
            _reject(pointer, WordToFrameRejectionReason.STRUCTURE_INVALID)
        if actual["source_kind"] not in {
            item.value for item in TemporalFrameSpanKind
        }:
            _reject(
                pointer,
                WordToFrameRejectionReason.UNSUPPORTED_VALUE,
                "UNSUPPORTED_CONTRACT_ENUM",
            )
        wanted = _span_dict(expected_span)
        if actual["source_kind"] != kind.value:
            _span_difference("source_kind", actual, wanted, pointer, rate)
        for name in _SPAN_FIELDS:
            if actual[name] != wanted[name]:
                _span_difference(name, actual, wanted, pointer, rate)


def load_word_to_frame(
    source: bytes,
    *,
    alignment_result: AlignmentResult,
    caption_groups: CaptionGroupsArtifact,
    emphasis_events: EmphasisEventsArtifact,
    frame_rate: TemporalFrameRate,
) -> WordToFrameArtifact:
    expected = _compile(
        alignment_result=alignment_result,
        caption_groups=caption_groups,
        emphasis_events=emphasis_events,
        frame_rate=frame_rate,
    )
    value = _parse_source(source)
    if type(value) is not dict:
        _reject("/", WordToFrameRejectionReason.STRUCTURE_INVALID)
    _require_exact_keys(value, _ROOT_FIELDS, "/")
    if any(type(value[field]) is not str for field in _ROOT_STRING_FIELDS):
        _reject("/", WordToFrameRejectionReason.STRUCTURE_INVALID)
    for field, literal in (
        ("schema_version", WORD_TO_FRAME_V1),
        ("hash_scope_version", WORD_TO_FRAME_HASH_V1),
        ("mapping_policy_version", WORD_TO_FRAME_POLICY_V1),
    ):
        if value[field] != literal:
            _reject(
                "/",
                WordToFrameRejectionReason.UNSUPPORTED_VALUE,
                "UNSUPPORTED_CONTRACT_ENUM",
            )
    if type(value["confidence_availability"]) is not str:
        _reject("/", WordToFrameRejectionReason.STRUCTURE_INVALID)
    if value["confidence_availability"] not in {
        item.value for item in ConfidenceAvailability
    }:
        _reject(
            "/",
            WordToFrameRejectionReason.UNSUPPORTED_VALUE,
            "UNSUPPORTED_CONTRACT_ENUM",
        )

    expected_value = _artifact_dict(expected)
    for field in _ROOT_DECLARATION_FIELDS:
        if value[field] != expected_value[field]:
            _root_declaration_difference(field)
    _validate_loaded_rate(value["frame_rate"], expected.frame_rate)
    for field, kind in _SPAN_COLLECTIONS:
        _validate_loaded_spans(
            value[field], getattr(expected, field), field, kind, expected.frame_rate
        )

    projection = {
        field: value[field]
        for field in _ROOT_FIELDS
        if field not in {"word_to_frame_id", "word_to_frame_hash"}
    }
    artifact_hash = _digest(encode_canonical_json_bytes(projection))
    if value["word_to_frame_hash"] != artifact_hash:
        _reject("/", WordToFrameRejectionReason.IDENTITY_MISMATCH)
    if value["word_to_frame_id"] != "w2f_" + artifact_hash[:32]:
        _reject("/", WordToFrameRejectionReason.IDENTITY_MISMATCH)
    try:
        canonical = encode_canonical_json_bytes(value)
    except Exception:
        _reject(
            "/", WordToFrameRejectionReason.NON_CANONICAL_SERIALIZATION
        )
    if canonical != source:
        _reject(
            "/", WordToFrameRejectionReason.NON_CANONICAL_SERIALIZATION
        )
    expected_envelope = encode_canonical_json_bytes(expected_value)
    if canonical != expected_envelope:
        _reject("/", WordToFrameRejectionReason.FRAME_MAPPING_INVALID)
    _register(expected, expected_envelope)
    return expected


def serialize_word_to_frame(artifact: WordToFrameArtifact) -> bytes:
    if type(artifact) is not WordToFrameArtifact:
        raise TypeError("artifact must be exact WordToFrameArtifact")
    entry = _MATERIALIZED.get(id(artifact))
    if entry is None or entry[0]() is not artifact:
        _reject("/", WordToFrameRejectionReason.NOT_MATERIALIZED)
    if _identity_signature(artifact) != entry[2]:
        _reject("/", WordToFrameRejectionReason.CONTENT_DRIFT)
    if not _artifact_has_exact_shape(artifact):
        _reject("/", WordToFrameRejectionReason.CONTENT_DRIFT)
    try:
        current = encode_canonical_json_bytes(_artifact_dict(artifact))
        projection_hash = _digest(
            encode_canonical_json_bytes(_artifact_projection(artifact))
        )
    except Exception:
        _reject("/", WordToFrameRejectionReason.CONTENT_DRIFT)
    if (
        projection_hash != artifact.word_to_frame_hash
        or artifact.word_to_frame_id != "w2f_" + projection_hash[:32]
        or current != entry[1]
    ):
        _reject("/", WordToFrameRejectionReason.CONTENT_DRIFT)
    return entry[1]
