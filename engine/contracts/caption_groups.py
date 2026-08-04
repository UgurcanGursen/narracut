"""Deterministic, fail-closed canonical caption-group contract."""

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
    AlignmentResultRejectionReason,
    WordTiming,
    _revision_projection,
    serialize_alignment_result,
)
from .narration import (
    CanonicalNarrationDocument,
    CanonicalTextToken,
    CanonicalWord,
    NarrationParagraph,
    NarrationRevision,
    NarrationSection,
    NarrationSentence,
    TokenKind,
    _document_to_dict,
    _has_materialized_narration_document_identity,
    _has_materialized_narration_revision_identity,
    _is_materialized_narration_document,
    _is_materialized_narration_revision,
)
from .temporal import STABLE_ISSUE_CODE_SET


CAPTION_GROUP_V1 = "CAPTION-GROUP-V1"
CAPTION_GROUP_HASH_V1 = "CAPTION-GROUP-HASH-V1"
CAPTION_GROUPS_V1 = "CAPTION-GROUPS-V1"
CAPTION_GROUPS_HASH_V1 = "CAPTION-GROUPS-HASH-V1"
PHRASE_GROUPING_POLICY_V1 = "PHRASE-GROUPING-POLICY-V1"

_HARD_BREAK_TOKEN_TEXTS = frozenset((".", "!", "?", "…", "...", "?!", "!?", ";", ":", "—", "–"))
_SOFT_BREAK_TOKEN_TEXTS = frozenset((",",))
_TARGET_WORD_COUNT = 6
_MIN_PREFERRED_WORD_COUNT = 4
_MAX_PREFERRED_WORD_COUNT = 9
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_INDEXED_POINTER = re.compile(r"^/caption_groups/(?:0|[1-9][0-9]*)$")
_FIXED_POINTERS = frozenset(
    {"/", "/narration_document", "/narration_revision", "/alignment_result", "/caption_groups"}
)


class CaptionGroupWordCountPolicy(str, Enum):
    PREFERRED_4_TO_9 = "PREFERRED_4_TO_9"
    SHORT_SENTENCE_1_TO_3 = "SHORT_SENTENCE_1_TO_3"


class CaptionGroupingRejectionReason(str, Enum):
    STRUCTURE_INVALID = "STRUCTURE_INVALID"
    UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
    DEPENDENCY_CONTENT_DRIFT = "DEPENDENCY_CONTENT_DRIFT"
    DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
    CANONICAL_COVERAGE_INVALID = "CANONICAL_COVERAGE_INVALID"
    GROUPING_POLICY_INVALID = "GROUPING_POLICY_INVALID"
    DISPLAY_TEXT_INVALID = "DISPLAY_TEXT_INVALID"
    TIMING_INVALID = "TIMING_INVALID"
    CONFIDENCE_INVALID = "CONFIDENCE_INVALID"
    NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    CONTENT_DRIFT = "CONTENT_DRIFT"
    NOT_MATERIALIZED = "NOT_MATERIALIZED"


@dataclass(frozen=True)
class CaptionGroup:
    schema_version: str
    hash_scope_version: str
    caption_group_id: str
    caption_group_hash: str
    narration_revision_id: str
    alignment_result_id: str
    grouping_policy_version: str
    ordinal: int
    sentence_id: str
    start_word_ordinal: int
    end_exclusive_word_ordinal: int
    start_word_id: str
    end_word_id: str
    word_ids: tuple[str, ...]
    word_count_policy: CaptionGroupWordCountPolicy
    display_text: str
    start_ms: int
    end_ms: int
    confidence_millionths: int | None


@dataclass(frozen=True)
class CaptionGroupsArtifact:
    schema_version: str
    hash_scope_version: str
    caption_groups_id: str
    caption_groups_hash: str
    project_id: str
    document_id: str
    narration_revision_id: str
    narration_revision_hash: str
    alignment_result_id: str
    alignment_result_hash: str
    grouping_policy_version: str
    confidence_availability: ConfidenceAvailability
    caption_groups: tuple[CaptionGroup, ...]


class CaptionGroupsContractError(ValueError):
    def __init__(
        self,
        pointer: str,
        reason: CaptionGroupingRejectionReason,
        issue_code: str | None = None,
    ) -> None:
        if (
            type(pointer) is not str
            or (pointer not in _FIXED_POINTERS and _INDEXED_POINTER.fullmatch(pointer) is None)
            or type(reason) is not CaptionGroupingRejectionReason
        ):
            raise TypeError("invalid caption groups error construction")
        if issue_code is not None and (
            type(issue_code) is not str or issue_code not in STABLE_ISSUE_CODE_SET
        ):
            raise TypeError("invalid caption groups issue code")
        super().__init__(f"Caption groups rejected: {reason.value}")
        self.pointer = pointer
        self.reason = reason
        self.issue_code = issue_code


_ROOT_FIELDS = (
    "schema_version", "hash_scope_version", "caption_groups_id",
    "caption_groups_hash", "project_id", "document_id",
    "narration_revision_id", "narration_revision_hash",
    "alignment_result_id", "alignment_result_hash",
    "grouping_policy_version", "confidence_availability", "caption_groups",
)
_GROUP_FIELDS = (
    "schema_version", "hash_scope_version", "caption_group_id",
    "caption_group_hash", "narration_revision_id", "alignment_result_id",
    "grouping_policy_version", "ordinal", "sentence_id",
    "start_word_ordinal", "end_exclusive_word_ordinal", "start_word_id",
    "end_word_id", "word_ids", "word_count_policy", "display_text",
    "start_ms", "end_ms", "confidence_millionths",
)

_MATERIALIZED_CAPTION_GROUPS: dict[
    int, tuple[weakref.ReferenceType[CaptionGroupsArtifact], bytes]
] = {}
_OWNED_CAPTION_GROUP_REFERENCES: dict[
    int, weakref.ReferenceType[CaptionGroupsArtifact]
] = {}


def _reject(
    pointer: str,
    reason: CaptionGroupingRejectionReason,
    issue_code: str | None = None,
) -> None:
    raise CaptionGroupsContractError(pointer, reason, issue_code)


def _hash(value: Any) -> str:
    return hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _safe_text(value: Any, *, allow_empty: bool = False) -> str:
    if type(value) is not str or (not allow_empty and not value):
        raise ValueError
    if unicodedata.normalize("NFC", value) != value:
        raise ValueError
    for character in value:
        code = ord(character)
        if (
            0xD800 <= code <= 0xDFFF
            or 0xFDD0 <= code <= 0xFDEF
            or (code & 0xFFFF) in {0xFFFE, 0xFFFF}
            or code < 0x20
            or 0x7F <= code <= 0x9F
        ):
            raise ValueError
    return value


def _stable_id(value: Any) -> str:
    value = _safe_text(value)
    if _SAFE_ID.fullmatch(value) is None:
        raise ValueError
    return value


def _dependency_drift(pointer: str, issue_code: str) -> None:
    _reject(pointer, CaptionGroupingRejectionReason.DEPENDENCY_CONTENT_DRIFT, issue_code)


@dataclass(frozen=True)
class _Preflight:
    result_bytes: bytes
    result_value: dict[str, Any]
    revision_hash: str


def _preflight(
    narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision,
    alignment_result: AlignmentResult,
) -> _Preflight:
    identity_checks = (
        (
            narration_document,
            CanonicalNarrationDocument,
            _has_materialized_narration_document_identity,
            "narration_document",
        ),
        (
            narration_revision,
            NarrationRevision,
            _has_materialized_narration_revision_identity,
            "narration_revision",
        ),
    )
    for value, exact_type, has_identity, name in identity_checks:
        if type(value) is not exact_type or not has_identity(value):
            raise TypeError(f"{name} must be a genuine exact dependency")
    document_current = _is_materialized_narration_document(narration_document)
    revision_current = _is_materialized_narration_revision(narration_revision)
    if type(alignment_result) is not AlignmentResult:
        raise TypeError("alignment_result must be a genuine exact dependency")

    try:
        document_value = _document_to_dict(narration_document)
        if type(document_value) is not dict or type(document_value.get("extensions")) is not dict:
            raise ValueError
        for field in (
            "schema_version", "project_id", "document_id", "current_revision_id",
            "language", "locale",
        ):
            _safe_text(document_value[field])
        for field in ("project_id", "document_id", "current_revision_id"):
            _stable_id(document_value[field])
        if document_value["title"] is not None:
            _safe_text(document_value["title"])
        encode_canonical_json_bytes(document_value)
        document_binding = (
            narration_document.project_id,
            narration_document.document_id,
            narration_document.current_revision_id,
        )
        revision_binding = (
            narration_revision.project_id,
            narration_revision.document_id,
            narration_revision.revision_id,
        )
        if not document_current and document_binding == revision_binding:
            raise ValueError
    except Exception:
        _dependency_drift("/narration_document", "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    try:
        projection = _revision_projection(narration_revision)
        revision_hash = "sha256:" + _hash(projection)
        if (
            narration_revision.revision_hash != revision_hash
            or narration_revision.revision_id != "narrev_" + revision_hash[7:27]
            or not revision_current
        ):
            raise ValueError
    except CaptionGroupsContractError:
        raise
    except Exception:
        _dependency_drift("/narration_revision", "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    try:
        result_bytes = serialize_alignment_result(alignment_result)
        result_value = json.loads(result_bytes)
        if type(result_value) is not dict:
            raise ValueError
    except AlignmentResultContractError as error:
        if error.reason is AlignmentResultRejectionReason.NOT_MATERIALIZED:
            raise TypeError("alignment_result must be a genuine exact dependency") from None
        _dependency_drift("/alignment_result", "REPLAY_HASH_MISMATCH")
    except Exception:
        _dependency_drift("/alignment_result", "REPLAY_HASH_MISMATCH")
    return _Preflight(bytes(result_bytes), result_value, revision_hash)


def _validate_bindings(
    document: CanonicalNarrationDocument,
    revision: NarrationRevision,
    result: AlignmentResult,
    preflight: _Preflight,
) -> None:
    expected = (revision.project_id, revision.document_id, revision.revision_id)
    document_actual = (document.project_id, document.document_id, document.current_revision_id)
    if document_actual[0] != expected[0] or document_actual[1] != expected[1] or document_actual[2] != expected[2]:
        _reject(
            "/narration_document",
            CaptionGroupingRejectionReason.DEPENDENCY_BINDING_INVALID,
            "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
        )
    result_actual = (
        result.project_id,
        result.document_id,
        result.narration_revision_id,
        result.narration_revision_hash,
    )
    if result_actual != expected + (preflight.revision_hash,):
        _reject(
            "/alignment_result",
            CaptionGroupingRejectionReason.DEPENDENCY_BINDING_INVALID,
            "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
        )


@dataclass(frozen=True)
class _Inventory:
    words: tuple[CanonicalWord, ...]
    timings: tuple[WordTiming, ...]
    sentence_ids: tuple[str, ...]
    sentence_ranges: tuple[tuple[str, int, int], ...]
    tokens_by_sentence: dict[str, tuple[CanonicalTextToken, ...]]
    token_position_by_id: dict[str, int]
    boundary_rank_after_word: dict[int, int]


def _coverage_invalid(issue: str = "CANONICAL_COVERAGE_BLOCKER") -> None:
    _reject(
        "/narration_revision",
        CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID,
        issue,
    )


def _inventory(revision: NarrationRevision, result: AlignmentResult) -> _Inventory:
    words = revision.canonical_words
    tokens = revision.text_tokens
    if type(words) is not tuple or not words or type(tokens) is not tuple:
        _coverage_invalid()
    if any(type(word) is not CanonicalWord for word in words):
        _coverage_invalid()
    if any(type(token) is not CanonicalTextToken for token in tokens):
        _coverage_invalid()

    token_by_id: dict[str, CanonicalTextToken] = {}
    tokens_by_sentence_mut: dict[str, list[CanonicalTextToken]] = {}
    token_position_by_id: dict[str, int] = {}
    previous_text_order = -1
    for token in tokens:
        try:
            _stable_id(token.token_id)
            _stable_id(token.sentence_id)
        except ValueError:
            _coverage_invalid()
        if token.token_id in token_by_id or type(token.text_order) is not int or isinstance(token.text_order, bool):
            _coverage_invalid()
        if token.text_order <= previous_text_order:
            _coverage_invalid("CANONICAL_WORD_ORDER_INVALID")
        previous_text_order = token.text_order
        token_by_id[token.token_id] = token
        sentence_tokens = tokens_by_sentence_mut.setdefault(token.sentence_id, [])
        token_position_by_id[token.token_id] = len(sentence_tokens)
        sentence_tokens.append(token)

    word_ids: set[str] = set()
    word_token_orders: list[int] = []
    for index, word in enumerate(words):
        try:
            _stable_id(word.word_id)
            _stable_id(word.token_id)
            _stable_id(word.sentence_id)
        except ValueError:
            _coverage_invalid()
        if word.word_id in word_ids or type(word.ordinal) is not int or isinstance(word.ordinal, bool):
            _coverage_invalid()
        if word.ordinal != index:
            _coverage_invalid("CANONICAL_WORD_ORDER_INVALID")
        word_ids.add(word.word_id)
        token = token_by_id.get(word.token_id)
        if (
            token is None
            or token.kind is not TokenKind.SPOKEN
            or token.canonical_word_ordinal != index
            or (
                token.text_order,
                token.display_text,
                token.source_start,
                token.source_end,
                token.section_id,
                token.paragraph_id,
                token.sentence_id,
            )
            != (
                word.text_order,
                word.display_text,
                word.source_start,
                word.source_end,
                word.section_id,
                word.paragraph_id,
                word.sentence_id,
            )
        ):
            _coverage_invalid()
        word_token_orders.append(word.text_order)
    if word_token_orders != sorted(word_token_orders) or len(set(word_token_orders)) != len(words):
        _coverage_invalid("CANONICAL_WORD_ORDER_INVALID")

    sentence_ids: list[str] = []
    seen_sentence_ids: set[str] = set()
    if type(revision.sections) is not tuple:
        _coverage_invalid()
    for section_index, section in enumerate(revision.sections):
        if type(section) is not NarrationSection or section.order != section_index or type(section.paragraphs) is not tuple:
            _coverage_invalid()
        for paragraph_index, paragraph in enumerate(section.paragraphs):
            if type(paragraph) is not NarrationParagraph or paragraph.order != paragraph_index or type(paragraph.sentences) is not tuple:
                _coverage_invalid()
            for sentence_index, sentence in enumerate(paragraph.sentences):
                if type(sentence) is not NarrationSentence or sentence.order != sentence_index:
                    _coverage_invalid()
                if sentence.sentence_id in seen_sentence_ids:
                    _coverage_invalid()
                sentence_ids.append(sentence.sentence_id)
                seen_sentence_ids.add(sentence.sentence_id)

    sentence_ranges: list[tuple[str, int, int]] = []
    cursor = 0
    for sentence_id in sentence_ids:
        start = cursor
        while cursor < len(words) and words[cursor].sentence_id == sentence_id:
            cursor += 1
        if cursor > start:
            sentence_ranges.append((sentence_id, start, cursor))
    if cursor != len(words):
        _coverage_invalid()

    timings = result.word_timings
    if type(timings) is not tuple or len(timings) != len(words):
        _reject(
            "/alignment_result",
            CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID,
            "CANONICAL_COVERAGE_BLOCKER",
        )
    for index, (word, timing) in enumerate(zip(words, timings)):
        if type(timing) is not WordTiming or timing.word_id != word.word_id:
            _reject(
                "/alignment_result",
                CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID,
                "CANONICAL_WORD_ORDER_INVALID",
            )
        if (
            type(timing.start_ms) is not int
            or isinstance(timing.start_ms, bool)
            or type(timing.end_ms) is not int
            or isinstance(timing.end_ms, bool)
        ):
            _reject("/alignment_result", CaptionGroupingRejectionReason.TIMING_INVALID, "TIMESTAMP_NON_MONOTONIC")
        if timing.start_ms < 0:
            _reject("/alignment_result", CaptionGroupingRejectionReason.TIMING_INVALID, "TIMESTAMP_OUT_OF_BOUNDS")
        if timing.start_ms == timing.end_ms:
            _reject("/alignment_result", CaptionGroupingRejectionReason.TIMING_INVALID, "ZERO_DURATION_WORD")
        if timing.start_ms > timing.end_ms:
            _reject("/alignment_result", CaptionGroupingRejectionReason.TIMING_INVALID, "TIMESTAMP_NON_MONOTONIC")
        if index and timing.start_ms < timings[index - 1].end_ms:
            _reject("/alignment_result", CaptionGroupingRejectionReason.TIMING_INVALID, "TIMESTAMP_OVERLAP")

    availability = result.confidence_availability
    if type(availability) is not ConfidenceAvailability:
        _reject("/alignment_result", CaptionGroupingRejectionReason.CONFIDENCE_INVALID, "ADAPTER_PRECISION_OVERSTATED")
    for timing in timings:
        confidence = timing.confidence_millionths
        if availability is ConfidenceAvailability.AVAILABLE:
            if confidence is None:
                _reject("/alignment_result", CaptionGroupingRejectionReason.CONFIDENCE_INVALID, "CONFIDENCE_REQUIRED_UNAVAILABLE")
            if type(confidence) is not int or isinstance(confidence, bool) or not 0 <= confidence <= 1_000_000:
                _reject("/alignment_result", CaptionGroupingRejectionReason.CONFIDENCE_INVALID, "ADAPTER_PRECISION_OVERSTATED")
        elif confidence is not None:
            _reject("/alignment_result", CaptionGroupingRejectionReason.CONFIDENCE_INVALID, "ADAPTER_PRECISION_OVERSTATED")

    tokens_by_sentence = {
        key: tuple(value) for key, value in tokens_by_sentence_mut.items()
    }
    boundary_rank_after_word: dict[int, int] = {}
    for _sentence_id, start, end in sentence_ranges:
        sentence_tokens = tokens_by_sentence.get(words[start].sentence_id, ())
        previous_word_ordinal: int | None = None
        pending_rank = 2
        for token in sentence_tokens:
            if token.kind is TokenKind.SPOKEN:
                if previous_word_ordinal is not None:
                    boundary_rank_after_word[previous_word_ordinal] = pending_rank
                previous_word_ordinal = token.canonical_word_ordinal
                pending_rank = 2
            elif token.kind is TokenKind.PUNCTUATION and previous_word_ordinal is not None:
                if token.display_text in _HARD_BREAK_TOKEN_TEXTS:
                    pending_rank = 0
                elif token.display_text in _SOFT_BREAK_TOKEN_TEXTS and pending_rank > 1:
                    pending_rank = 1
    return _Inventory(
        words,
        timings,
        tuple(sentence_ids),
        tuple(sentence_ranges),
        tokens_by_sentence,
        token_position_by_id,
        boundary_rank_after_word,
    )


def _partition_sizes(length: int, start_ordinal: int, ranks: dict[int, int]) -> tuple[int, ...]:
    if type(length) is not int or isinstance(length, bool) or length <= 0:
        raise ValueError("sentence length must be positive")
    if length <= 3:
        return (length,)
    sizes: list[int] = []
    consumed = 0
    while consumed < length:
        remaining = length - consumed
        if _MIN_PREFERRED_WORD_COUNT <= remaining <= _MAX_PREFERRED_WORD_COUNT:
            sizes.append(remaining)
            break
        candidates = [
            size
            for size in range(_MIN_PREFERRED_WORD_COUNT, _MAX_PREFERRED_WORD_COUNT + 1)
            if remaining - size == 0 or remaining - size >= _MIN_PREFERRED_WORD_COUNT
        ]
        size = min(
            candidates,
            key=lambda item: (
                ranks.get(start_ordinal + consumed + item - 1, 2),
                abs(item - _TARGET_WORD_COUNT),
                -item,
            ),
        )
        sizes.append(size)
        consumed += size
    return tuple(sizes)


def _display_text(
    inventory: _Inventory,
    source_text: str,
    start: int,
    end: int,
    sentence_start: int,
    sentence_end: int,
) -> str:
    words = inventory.words
    sentence_tokens = inventory.tokens_by_sentence.get(words[start].sentence_id, ())
    lower = 0 if start == sentence_start else inventory.token_position_by_id[words[start].token_id]
    upper = (
        inventory.token_position_by_id[words[end].token_id]
        if end < sentence_end
        else len(sentence_tokens)
    )
    retained = tuple(
        token
        for token in sentence_tokens[lower:upper]
        if token.kind in {TokenKind.SPOKEN, TokenKind.PUNCTUATION}
    )
    expected_spoken = tuple(word.token_id for word in words[start:end])
    actual_spoken = tuple(token.token_id for token in retained if token.kind is TokenKind.SPOKEN)
    if actual_spoken != expected_spoken or not retained:
        _reject(
            "/caption_groups",
            CaptionGroupingRejectionReason.DISPLAY_TEXT_INVALID,
            "CANONICAL_COVERAGE_BLOCKER",
        )
    text = retained[0].display_text
    for previous, current in zip(retained, retained[1:]):
        gap = ""
        if previous.source_end < current.source_start:
            gap = source_text[previous.source_end:current.source_start]
        if any(character in "\t\n\r " for character in gap):
            text += " "
        text += current.display_text
    try:
        return _safe_text(text)
    except ValueError:
        _reject("/caption_groups", CaptionGroupingRejectionReason.DISPLAY_TEXT_INVALID)


def _group_projection(group: CaptionGroup) -> dict[str, Any]:
    value = _group_envelope(group)
    value.pop("caption_group_id")
    value.pop("caption_group_hash")
    return value


def _group_envelope(group: CaptionGroup) -> dict[str, Any]:
    return {
        "schema_version": group.schema_version,
        "hash_scope_version": group.hash_scope_version,
        "caption_group_id": group.caption_group_id,
        "caption_group_hash": group.caption_group_hash,
        "narration_revision_id": group.narration_revision_id,
        "alignment_result_id": group.alignment_result_id,
        "grouping_policy_version": group.grouping_policy_version,
        "ordinal": group.ordinal,
        "sentence_id": group.sentence_id,
        "start_word_ordinal": group.start_word_ordinal,
        "end_exclusive_word_ordinal": group.end_exclusive_word_ordinal,
        "start_word_id": group.start_word_id,
        "end_word_id": group.end_word_id,
        "word_ids": list(group.word_ids),
        "word_count_policy": group.word_count_policy.value,
        "display_text": group.display_text,
        "start_ms": group.start_ms,
        "end_ms": group.end_ms,
        "confidence_millionths": group.confidence_millionths,
    }


def _artifact_envelope(artifact: CaptionGroupsArtifact) -> dict[str, Any]:
    return {
        "schema_version": artifact.schema_version,
        "hash_scope_version": artifact.hash_scope_version,
        "caption_groups_id": artifact.caption_groups_id,
        "caption_groups_hash": artifact.caption_groups_hash,
        "project_id": artifact.project_id,
        "document_id": artifact.document_id,
        "narration_revision_id": artifact.narration_revision_id,
        "narration_revision_hash": artifact.narration_revision_hash,
        "alignment_result_id": artifact.alignment_result_id,
        "alignment_result_hash": artifact.alignment_result_hash,
        "grouping_policy_version": artifact.grouping_policy_version,
        "confidence_availability": artifact.confidence_availability.value,
        "caption_groups": [_group_envelope(group) for group in artifact.caption_groups],
    }


def _artifact_projection(artifact: CaptionGroupsArtifact) -> dict[str, Any]:
    value = _artifact_envelope(artifact)
    value.pop("caption_groups_id")
    value.pop("caption_groups_hash")
    return value


def _derive(
    document: CanonicalNarrationDocument,
    revision: NarrationRevision,
    result: AlignmentResult,
    preflight: _Preflight,
) -> CaptionGroupsArtifact:
    _validate_bindings(document, revision, result, preflight)
    inventory = _inventory(revision, result)
    groups: list[CaptionGroup] = []
    for sentence_id, sentence_start, sentence_end in inventory.sentence_ranges:
        length = sentence_end - sentence_start
        cursor = sentence_start
        for size in _partition_sizes(length, sentence_start, inventory.boundary_rank_after_word):
            end = cursor + size
            timings = inventory.timings[cursor:end]
            confidence = (
                min(item.confidence_millionths for item in timings if item.confidence_millionths is not None)
                if result.confidence_availability is ConfidenceAvailability.AVAILABLE
                else None
            )
            group = CaptionGroup(
                CAPTION_GROUP_V1,
                CAPTION_GROUP_HASH_V1,
                "",
                "",
                revision.revision_id,
                result.alignment_result_id,
                PHRASE_GROUPING_POLICY_V1,
                len(groups),
                sentence_id,
                cursor,
                end,
                inventory.words[cursor].word_id,
                inventory.words[end - 1].word_id,
                tuple(word.word_id for word in inventory.words[cursor:end]),
                (
                    CaptionGroupWordCountPolicy.SHORT_SENTENCE_1_TO_3
                    if length <= 3
                    else CaptionGroupWordCountPolicy.PREFERRED_4_TO_9
                ),
                _display_text(
                    inventory,
                    revision.source_text,
                    cursor,
                    end,
                    sentence_start,
                    sentence_end,
                ),
                timings[0].start_ms,
                timings[-1].end_ms,
                confidence,
            )
            digest = _hash(_group_projection(group))
            group = CaptionGroup(
                group.schema_version,
                group.hash_scope_version,
                "cgrp_" + digest[:32],
                digest,
                *tuple(getattr(group, field) for field in _GROUP_FIELDS[4:]),
            )
            groups.append(group)
            cursor = end

    artifact = CaptionGroupsArtifact(
        CAPTION_GROUPS_V1,
        CAPTION_GROUPS_HASH_V1,
        "",
        "",
        revision.project_id,
        revision.document_id,
        revision.revision_id,
        preflight.revision_hash,
        result.alignment_result_id,
        result.alignment_result_hash,
        PHRASE_GROUPING_POLICY_V1,
        result.confidence_availability,
        tuple(groups),
    )
    digest = _hash(_artifact_projection(artifact))
    return CaptionGroupsArtifact(
        artifact.schema_version,
        artifact.hash_scope_version,
        "cgs_" + digest[:32],
        digest,
        *tuple(getattr(artifact, field) for field in _ROOT_FIELDS[4:]),
    )


class _Pairs(list):
    pass


def _raise_number() -> Any:
    raise ValueError("forbidden number")


def _pairs_to_value(value: Any) -> Any:
    if type(value) is _Pairs:
        result: dict[str, Any] = {}
        for key, item in value:
            if type(key) is not str or key in result:
                raise ValueError("duplicate or invalid key")
            result[key] = _pairs_to_value(item)
        return result
    if type(value) is list:
        return [_pairs_to_value(item) for item in value]
    return value


def _parse_source(source: bytes) -> Any:
    if type(source) is not bytes:
        raise TypeError("source must be exact bytes")
    try:
        if source.startswith(b"\xef\xbb\xbf"):
            raise ValueError
        value = json.loads(
            source.decode("utf-8", errors="strict"),
            object_pairs_hook=_Pairs,
            parse_int=lambda token: (_raise_number() if token == "-0" else int(token)),
            parse_float=lambda _token: _raise_number(),
            parse_constant=lambda _token: _raise_number(),
        )
        value = _pairs_to_value(value)
        canonical = encode_canonical_json_bytes(value)
        if canonical != source:
            raise ValueError
        return value
    except CaptionGroupsContractError:
        raise
    except Exception:
        _reject("/", CaptionGroupingRejectionReason.NON_CANONICAL_SERIALIZATION)


def _exact_keys(value: Any, fields: tuple[str, ...], pointer: str) -> dict[str, Any]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        _reject(pointer, CaptionGroupingRejectionReason.STRUCTURE_INVALID)
    if any(key not in fields for key in value) or any(key not in value for key in fields):
        _reject(pointer, CaptionGroupingRejectionReason.STRUCTURE_INVALID)
    return value


def _validate_loaded_shape(value: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = _exact_keys(value, _ROOT_FIELDS, "/")
    root_string_fields = _ROOT_FIELDS[:12]
    for field in root_string_fields:
        if field == "confidence_availability":
            continue
        if type(root[field]) is not str:
            _reject("/", CaptionGroupingRejectionReason.STRUCTURE_INVALID)
        try:
            _safe_text(root[field])
        except ValueError:
            _reject("/", CaptionGroupingRejectionReason.STRUCTURE_INVALID)
    if type(root["confidence_availability"]) is not str:
        _reject("/", CaptionGroupingRejectionReason.STRUCTURE_INVALID)
    if type(root["caption_groups"]) is not list:
        _reject("/caption_groups", CaptionGroupingRejectionReason.STRUCTURE_INVALID)
    try:
        if (
            re.fullmatch(r"^cgs_[0-9a-f]{32}$", root["caption_groups_id"]) is None
            or _HEX64.fullmatch(root["caption_groups_hash"]) is None
            or _SHA256.fullmatch(root["narration_revision_hash"]) is None
            or _HEX64.fullmatch(root["alignment_result_hash"]) is None
        ):
            raise ValueError
        for field in ("project_id", "document_id", "narration_revision_id", "alignment_result_id"):
            _stable_id(root[field])
    except ValueError:
        _reject("/", CaptionGroupingRejectionReason.STRUCTURE_INVALID)
    groups: list[dict[str, Any]] = []
    for index, raw in enumerate(root["caption_groups"]):
        pointer = f"/caption_groups/{index}"
        group = _exact_keys(raw, _GROUP_FIELDS, pointer)
        string_fields = (
            "schema_version", "hash_scope_version", "caption_group_id",
            "caption_group_hash", "narration_revision_id", "alignment_result_id",
            "grouping_policy_version", "sentence_id", "start_word_id", "end_word_id",
            "word_count_policy", "display_text",
        )
        if any(type(group[field]) is not str for field in string_fields):
            _reject(pointer, CaptionGroupingRejectionReason.STRUCTURE_INVALID)
        int_fields = ("ordinal", "start_word_ordinal", "end_exclusive_word_ordinal", "start_ms", "end_ms")
        if any(type(group[field]) is not int or isinstance(group[field], bool) for field in int_fields):
            _reject(pointer, CaptionGroupingRejectionReason.STRUCTURE_INVALID)
        if type(group["word_ids"]) is not list or any(type(item) is not str for item in group["word_ids"]):
            _reject(pointer, CaptionGroupingRejectionReason.STRUCTURE_INVALID)
        confidence = group["confidence_millionths"]
        if confidence is not None and (type(confidence) is not int or isinstance(confidence, bool)):
            _reject(pointer, CaptionGroupingRejectionReason.STRUCTURE_INVALID)
        for field in string_fields:
            if field == "display_text":
                continue
            try:
                _safe_text(group[field])
            except ValueError:
                _reject(pointer, CaptionGroupingRejectionReason.STRUCTURE_INVALID)
        for item in group["word_ids"]:
            try:
                _stable_id(item)
            except ValueError:
                _reject(pointer, CaptionGroupingRejectionReason.STRUCTURE_INVALID)
        try:
            if (
                re.fullmatch(r"^cgrp_[0-9a-f]{32}$", group["caption_group_id"]) is None
                or _HEX64.fullmatch(group["caption_group_hash"]) is None
            ):
                raise ValueError
            for field in (
                "narration_revision_id", "alignment_result_id", "sentence_id",
                "start_word_id", "end_word_id",
            ):
                _stable_id(group[field])
        except ValueError:
            _reject(pointer, CaptionGroupingRejectionReason.STRUCTURE_INVALID)
        try:
            _safe_text(group["display_text"])
        except ValueError:
            _reject(pointer, CaptionGroupingRejectionReason.DISPLAY_TEXT_INVALID)
        groups.append(group)
    return root, groups


def _validate_loaded_semantics(
    root: dict[str, Any],
    groups: list[dict[str, Any]],
    expected: CaptionGroupsArtifact,
) -> None:
    if (
        root["schema_version"] != CAPTION_GROUPS_V1
        or root["hash_scope_version"] != CAPTION_GROUPS_HASH_V1
        or root["grouping_policy_version"] != PHRASE_GROUPING_POLICY_V1
    ):
        _reject("/", CaptionGroupingRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
    try:
        availability = ConfidenceAvailability(root["confidence_availability"])
    except ValueError:
        _reject("/", CaptionGroupingRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
    dependency_fields = (
        "project_id", "document_id", "narration_revision_id",
        "narration_revision_hash", "alignment_result_id", "alignment_result_hash",
    )
    expected_root = _artifact_envelope(expected)
    if any(root[field] != expected_root[field] for field in dependency_fields):
        _reject("/", CaptionGroupingRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    if availability is not expected.confidence_availability:
        _reject("/", CaptionGroupingRejectionReason.CONFIDENCE_INVALID, "ADAPTER_PRECISION_OVERSTATED")
    if len(groups) != len(expected.caption_groups):
        _reject("/caption_groups", CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_COVERAGE_BLOCKER")

    previous_end: int | None = None
    canonical_word_ids = tuple(
        word_id for group in expected.caption_groups for word_id in group.word_ids
    )
    word_count = len(canonical_word_ids)
    for index, (actual, expected_group) in enumerate(zip(groups, expected.caption_groups)):
        pointer = f"/caption_groups/{index}"
        if (
            actual["schema_version"] != CAPTION_GROUP_V1
            or actual["hash_scope_version"] != CAPTION_GROUP_HASH_V1
            or actual["grouping_policy_version"] != PHRASE_GROUPING_POLICY_V1
        ):
            _reject(pointer, CaptionGroupingRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
        try:
            policy = CaptionGroupWordCountPolicy(actual["word_count_policy"])
        except ValueError:
            _reject(pointer, CaptionGroupingRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
        if (
            actual["narration_revision_id"] != expected.narration_revision_id
            or actual["alignment_result_id"] != expected.alignment_result_id
            or actual["grouping_policy_version"] != expected.grouping_policy_version
        ):
            _reject(pointer, CaptionGroupingRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
        if actual["ordinal"] != index:
            _reject(pointer, CaptionGroupingRejectionReason.GROUPING_POLICY_INVALID, "CANONICAL_WORD_ORDER_INVALID")
        start = actual["start_word_ordinal"]
        end = actual["end_exclusive_word_ordinal"]
        if start > end:
            _reject(pointer, CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "WORD_RANGE_REVERSED")
        if start < 0 or start == end or end > word_count:
            _reject(pointer, CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "WORD_RANGE_OUT_OF_BOUNDS")
        if index == 0 and start != 0:
            _reject(pointer, CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_COVERAGE_BLOCKER")
        if previous_end is not None and start != previous_end:
            _reject(pointer, CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_COVERAGE_BLOCKER")
        if index == len(groups) - 1 and end != word_count:
            _reject(pointer, CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_COVERAGE_BLOCKER")
        previous_end = end
        expected_word_ids = list(canonical_word_ids[start:end])
        if len(actual["word_ids"]) != end - start:
            _reject(pointer, CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_COVERAGE_BLOCKER")
        if actual["start_word_id"] != expected_word_ids[0] or actual["end_word_id"] != expected_word_ids[-1]:
            _reject(pointer, CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_COVERAGE_BLOCKER")
        if actual["word_ids"] != expected_word_ids:
            issue = (
                "CANONICAL_WORD_ORDER_INVALID"
                if len(set(actual["word_ids"])) == len(expected_word_ids)
                and set(actual["word_ids"]) == set(expected_word_ids)
                else "CANONICAL_COVERAGE_BLOCKER"
            )
            _reject(pointer, CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, issue)
        if actual["sentence_id"] != expected_group.sentence_id:
            _reject(pointer, CaptionGroupingRejectionReason.GROUPING_POLICY_INVALID, "CANONICAL_COVERAGE_BLOCKER")
        count = end - start
        if policy is CaptionGroupWordCountPolicy.PREFERRED_4_TO_9 and count > 9:
            _reject(pointer, CaptionGroupingRejectionReason.GROUPING_POLICY_INVALID, "WORD_RANGE_OUT_OF_BOUNDS")
        if policy is CaptionGroupWordCountPolicy.SHORT_SENTENCE_1_TO_3 and not 1 <= count <= 3:
            _reject(pointer, CaptionGroupingRejectionReason.GROUPING_POLICY_INVALID, "CANONICAL_COVERAGE_BLOCKER")
        if policy is CaptionGroupWordCountPolicy.PREFERRED_4_TO_9 and count <= 3:
            _reject(pointer, CaptionGroupingRejectionReason.GROUPING_POLICY_INVALID, "CANONICAL_COVERAGE_BLOCKER")
        if (start, end, policy) != (
            expected_group.start_word_ordinal,
            expected_group.end_exclusive_word_ordinal,
            expected_group.word_count_policy,
        ):
            _reject(pointer, CaptionGroupingRejectionReason.GROUPING_POLICY_INVALID, "CANONICAL_COVERAGE_BLOCKER")
        if actual["display_text"] != expected_group.display_text:
            _reject(pointer, CaptionGroupingRejectionReason.DISPLAY_TEXT_INVALID)
        if actual["start_ms"] != expected_group.start_ms:
            _reject(pointer, CaptionGroupingRejectionReason.TIMING_INVALID, "TIMESTAMP_NON_MONOTONIC")
        if actual["end_ms"] != expected_group.end_ms:
            _reject(pointer, CaptionGroupingRejectionReason.TIMING_INVALID, "TIMESTAMP_NON_MONOTONIC")
        if actual["confidence_millionths"] != expected_group.confidence_millionths:
            issue = (
                "CONFIDENCE_REQUIRED_UNAVAILABLE"
                if expected.confidence_availability is ConfidenceAvailability.AVAILABLE
                and actual["confidence_millionths"] is None
                else "ADAPTER_PRECISION_OVERSTATED"
            )
            _reject(pointer, CaptionGroupingRejectionReason.CONFIDENCE_INVALID, issue)
        expected_group_value = _group_envelope(expected_group)
        actual_projection = {key: item for key, item in actual.items() if key not in {"caption_group_id", "caption_group_hash"}}
        digest = _hash(actual_projection)
        if actual["caption_group_hash"] != digest or digest != expected_group.caption_group_hash:
            _reject(pointer, CaptionGroupingRejectionReason.IDENTITY_MISMATCH)
        if actual["caption_group_id"] != "cgrp_" + digest[:32] or actual["caption_group_id"] != expected_group_value["caption_group_id"]:
            _reject(pointer, CaptionGroupingRejectionReason.IDENTITY_MISMATCH)

    projection = {key: item for key, item in root.items() if key not in {"caption_groups_id", "caption_groups_hash"}}
    digest = _hash(projection)
    if root["caption_groups_hash"] != digest or digest != expected.caption_groups_hash:
        _reject("/", CaptionGroupingRejectionReason.IDENTITY_MISMATCH)
    if root["caption_groups_id"] != "cgs_" + digest[:32] or root["caption_groups_id"] != expected.caption_groups_id:
        _reject("/", CaptionGroupingRejectionReason.IDENTITY_MISMATCH)


def _register(artifact: CaptionGroupsArtifact, envelope: bytes) -> None:
    key = id(artifact)
    old = _MATERIALIZED_CAPTION_GROUPS.get(key)
    if old is not None and old[0]() is not None:
        raise RuntimeError("caption groups provenance collision")

    def forget(reference: weakref.ReferenceType[CaptionGroupsArtifact]) -> None:
        current = _MATERIALIZED_CAPTION_GROUPS.get(key)
        if current is not None and current[0] is reference:
            _MATERIALIZED_CAPTION_GROUPS.pop(key, None)
        if _OWNED_CAPTION_GROUP_REFERENCES.get(key) is reference:
            _OWNED_CAPTION_GROUP_REFERENCES.pop(key, None)

    reference = weakref.ref(artifact, forget)
    entry = (reference, bytes(envelope))
    try:
        _OWNED_CAPTION_GROUP_REFERENCES[key] = reference
        _MATERIALIZED_CAPTION_GROUPS[key] = entry
        if (
            _OWNED_CAPTION_GROUP_REFERENCES.get(key) is not reference
            or _MATERIALIZED_CAPTION_GROUPS.get(key) is not entry
            or reference() is not artifact
        ):
            raise RuntimeError("caption groups provenance registration failed")
    except Exception:
        if _MATERIALIZED_CAPTION_GROUPS.get(key) is entry:
            _MATERIALIZED_CAPTION_GROUPS.pop(key, None)
        if _OWNED_CAPTION_GROUP_REFERENCES.get(key) is reference:
            _OWNED_CAPTION_GROUP_REFERENCES.pop(key, None)
        raise


def compile_caption_groups(
    *,
    narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision,
    alignment_result: AlignmentResult,
) -> CaptionGroupsArtifact:
    preflight = _preflight(narration_document, narration_revision, alignment_result)
    artifact = _derive(narration_document, narration_revision, alignment_result, preflight)
    try:
        envelope = encode_canonical_json_bytes(_artifact_envelope(artifact))
        _register(artifact, envelope)
    except CaptionGroupsContractError:
        raise
    except Exception as error:
        raise RuntimeError("caption groups construction failed") from error
    return artifact


def load_caption_groups(
    source: bytes,
    *,
    narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision,
    alignment_result: AlignmentResult,
) -> CaptionGroupsArtifact:
    preflight = _preflight(narration_document, narration_revision, alignment_result)
    value = _parse_source(source)
    expected = _derive(narration_document, narration_revision, alignment_result, preflight)
    root, groups = _validate_loaded_shape(value)
    _validate_loaded_semantics(root, groups, expected)
    envelope = encode_canonical_json_bytes(_artifact_envelope(expected))
    if source != envelope:
        _reject("/", CaptionGroupingRejectionReason.NON_CANONICAL_SERIALIZATION)
    try:
        _register(expected, envelope)
    except Exception as error:
        raise RuntimeError("caption groups construction failed") from error
    return expected


def serialize_caption_groups(artifact: CaptionGroupsArtifact) -> bytes:
    entry = _MATERIALIZED_CAPTION_GROUPS.get(id(artifact))
    owner = _OWNED_CAPTION_GROUP_REFERENCES.get(id(artifact))
    if type(artifact) is not CaptionGroupsArtifact or owner is None or owner() is not artifact:
        _reject("/", CaptionGroupingRejectionReason.NOT_MATERIALIZED)
    if entry is None or entry[0] is not owner or type(entry[1]) is not bytes:
        _reject("/", CaptionGroupingRejectionReason.CONTENT_DRIFT)
    try:
        if type(artifact.confidence_availability) is not ConfidenceAvailability or type(artifact.caption_groups) is not tuple:
            raise ValueError
        if any(type(group) is not CaptionGroup or type(group.word_ids) is not tuple or type(group.word_count_policy) is not CaptionGroupWordCountPolicy for group in artifact.caption_groups):
            raise ValueError
        for group in artifact.caption_groups:
            digest = _hash(_group_projection(group))
            if group.caption_group_hash != digest or group.caption_group_id != "cgrp_" + digest[:32]:
                raise ValueError
        digest = _hash(_artifact_projection(artifact))
        if artifact.caption_groups_hash != digest or artifact.caption_groups_id != "cgs_" + digest[:32]:
            raise ValueError
        envelope = encode_canonical_json_bytes(_artifact_envelope(artifact))
        if envelope != entry[1]:
            raise ValueError
    except Exception:
        _reject("/", CaptionGroupingRejectionReason.CONTENT_DRIFT)
    return bytes(entry[1])
