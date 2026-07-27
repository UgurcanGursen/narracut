"""Canonical TRP-RAW-V1 serialization and issue-code validation."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any


TRP_RAW_V1 = "TRP-RAW-V1"

STABLE_ISSUE_CODES = (
    "ADAPTER_FAILURE",
    "ADAPTER_PRECISION_OVERSTATED",
    "ADAPTER_UNSUPPORTED_LANGUAGE",
    "AUDIO_REVISION_MISMATCH",
    "AUDIO_TRUNCATED",
    "AUTO_OVERLAP_REPAIR",
    "CANONICAL_COVERAGE_BLOCKER",
    "CANONICAL_WORD_ORDER_INVALID",
    "CONFIDENCE_REQUIRED_UNAVAILABLE",
    "CONFIDENCE_UNAVAILABLE",
    "CONTIGUOUS_UNALIGNED",
    "CONTIGUOUS_UNALIGNED_BLOCKER",
    "CORRECTION_PRECONDITION_CONFLICT",
    "DIVERGENCE_AMBIGUOUS",
    "DOWNSTREAM_UNALIGNED_REFERENCE",
    "DURATION_GAP_BLOCKER",
    "DURATION_GAP_WARNING",
    "FRAME_BOUNDARY_DRIFT_EXCEEDED",
    "FRAME_BOUNDARY_TOLERANCE_WARNING",
    "FRAME_RATE_INVALID",
    "HASH_DEPENDENCY_CYCLE",
    "HIERARCHY_COVERAGE_BLOCKER",
    "HIERARCHY_COVERAGE_WARNING",
    "INDIVIDUAL_CONFIDENCE_BLOCKER",
    "INDIVIDUAL_CONFIDENCE_WARNING",
    "INPUT_TEXT_INVALID_UTF8",
    "LLM_TIMESTAMP_SOURCE_FORBIDDEN",
    "LOW_CONFIDENCE_RATIO_BLOCKER",
    "LOW_CONFIDENCE_RATIO_WARNING",
    "MANUAL_CORRECTION_RATIO_BLOCKER",
    "MANUAL_CORRECTION_RATIO_WARNING",
    "MANUAL_CORRECTION_REVIEWED",
    "NEGATIVE_NARRATION_OFFSET",
    "PAID_CANDIDATE_COST_WARNING",
    "PAID_FALLBACK_UNAUTHORIZED",
    "PATH_ADS_FORBIDDEN",
    "PATH_DEVICE_FORBIDDEN",
    "PATH_RESERVED_NAME",
    "PATH_TRAVERSAL",
    "PATH_UNC_FORBIDDEN",
    "PROVIDER_METADATA_INCOMPLETE",
    "REPLAY_HASH_MISMATCH",
    "REPLAY_INPUT_MISMATCH",
    "SECURE_INPUT_CONTAINMENT_FAILED",
    "SECURE_INPUT_IDENTITY_CHANGED",
    "SEGMENT_CONFIDENCE_BLOCKER",
    "SEGMENT_CONFIDENCE_WARNING",
    "TIMESTAMP_NON_MONOTONIC",
    "TIMESTAMP_OUT_OF_BOUNDS",
    "TIMESTAMP_OVERLAP",
    "TRANSCRIPT_CER_BLOCKER",
    "TRANSCRIPT_CER_WARNING",
    "TRANSCRIPT_DIVERGENCE",
    "TRANSCRIPT_WER_BLOCKER",
    "TRANSCRIPT_WER_WARNING",
    "UNALIGNED_COVERAGE",
    "UNALIGNED_DURATION_BLOCKER",
    "UNALIGNED_DURATION_WARNING",
    "UNSUPPORTED_CONTRACT_ENUM",
    "URI_SENSITIVE_COMPONENT",
    "URI_USER_INFO",
    "WORD_RANGE_OUT_OF_BOUNDS",
    "WORD_RANGE_REVERSED",
    "WORD_RANGE_REVISION_MISMATCH",
    "ZERO_DURATION_WORD",
)
STABLE_ISSUE_CODE_SET = frozenset(STABLE_ISSUE_CODES)


class RawPackageRejectionReason(str, Enum):
    BOM_FORBIDDEN = "bom_forbidden"
    DUPLICATE_KEY = "duplicate_key"
    FLOAT_FORBIDDEN = "float_forbidden"
    INVALID_JSON = "invalid_json"
    INVALID_UTF8 = "invalid_utf8"
    INVALID_UNICODE = "invalid_unicode"
    NEGATIVE_ZERO_FORBIDDEN = "negative_zero_forbidden"
    NORMALIZED_KEY_COLLISION = "normalized_key_collision"
    STRUCTURE_INVALID = "structure_invalid"
    TOKEN_ORDER_INVALID = "token_order_invalid"
    UNKNOWN_ISSUE_CODE = "unknown_issue_code"
    UNSUPPORTED_VALUE = "unsupported_value"


class TemporalRawPackageError(ValueError):
    """Fail-closed rejection with no canonical payload or hash."""

    def __init__(
        self,
        reason: RawPackageRejectionReason,
        pointer: str,
        message: str,
    ):
        super().__init__(message)
        self.reason = reason
        self.pointer = pointer


@dataclass(frozen=True)
class CanonicalRawPackage:
    canonical_bytes: bytes
    canonical_hash: str


class _DuplicateKeyError(ValueError):
    pass


class _NumberSyntaxError(ValueError):
    pass


def validate_issue_codes(codes: Sequence[str]) -> tuple[str, ...]:
    """Validate exact canonical membership while preserving declared order."""
    if isinstance(codes, (str, bytes, bytearray)) or not isinstance(
        codes, Sequence
    ):
        _reject(
            RawPackageRejectionReason.STRUCTURE_INVALID,
            "$.issue_codes",
            "issue_codes must be an ordered array.",
        )

    validated: list[str] = []
    seen: set[str] = set()
    for index, code in enumerate(codes):
        pointer = f"$.issue_codes[{index}]"
        if not isinstance(code, str) or code not in STABLE_ISSUE_CODE_SET:
            _reject(
                RawPackageRejectionReason.UNKNOWN_ISSUE_CODE,
                pointer,
                "Issue code is not an exact canonical inventory member.",
            )
        if code in seen:
            _reject(
                RawPackageRejectionReason.STRUCTURE_INVALID,
                pointer,
                "Ordered issue-code sets cannot contain duplicates.",
            )
        seen.add(code)
        validated.append(code)
    return tuple(validated)


def canonicalize_temporal_raw_package(
    value: Mapping[str, Any],
) -> CanonicalRawPackage:
    """Validate and materialize one logical TRP-RAW-V1 package."""
    normalized = _normalize_value(value, "$")
    _validate_package_structure(normalized)
    canonical_bytes = _encode_value(normalized).encode("utf-8")
    digest = hashlib.sha256(canonical_bytes).hexdigest()
    return CanonicalRawPackage(canonical_bytes, f"sha256:{digest}")


def load_temporal_raw_package(source: bytes) -> CanonicalRawPackage:
    """Parse UTF-8 JSON bytes, then use the logical materialization path."""
    if not isinstance(source, bytes):
        _reject(
            RawPackageRejectionReason.UNSUPPORTED_VALUE,
            "$",
            "Raw package input must be bytes.",
        )
    if source.startswith(b"\xef\xbb\xbf"):
        _reject(
            RawPackageRejectionReason.BOM_FORBIDDEN,
            "$",
            "UTF-8 BOM is forbidden.",
        )
    try:
        text = source.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise TemporalRawPackageError(
            RawPackageRejectionReason.INVALID_UTF8,
            "$",
            "Raw package is not valid UTF-8.",
        ) from exc

    try:
        value = json.loads(
            text,
            object_pairs_hook=_mapping_from_pairs,
            parse_int=_parse_integer,
            parse_float=_reject_float_literal,
            parse_constant=_reject_float_literal,
        )
    except _DuplicateKeyError as exc:
        raise TemporalRawPackageError(
            RawPackageRejectionReason.DUPLICATE_KEY,
            "$",
            "Duplicate object keys are forbidden.",
        ) from exc
    except _NumberSyntaxError as exc:
        reason = (
            RawPackageRejectionReason.NEGATIVE_ZERO_FORBIDDEN
            if str(exc) == "-0"
            else RawPackageRejectionReason.FLOAT_FORBIDDEN
        )
        raise TemporalRawPackageError(
            reason,
            "$",
            "JSON number is forbidden by TRP-RAW-V1.",
        ) from exc
    except json.JSONDecodeError as exc:
        raise TemporalRawPackageError(
            RawPackageRejectionReason.INVALID_JSON,
            "$",
            "Raw package is not valid JSON.",
        ) from exc

    return canonicalize_temporal_raw_package(value)


def _mapping_from_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError
        result[key] = value
    return result


def _parse_integer(token: str) -> int:
    if token == "-0":
        raise _NumberSyntaxError(token)
    return int(token)


def _reject_float_literal(token: str) -> float:
    raise _NumberSyntaxError(token)


def _normalize_value(value: Any, pointer: str) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        _reject(
            RawPackageRejectionReason.FLOAT_FORBIDDEN,
            pointer,
            "Floating-point values are forbidden.",
        )
    if isinstance(value, str):
        return _normalize_text(value, pointer)
    if isinstance(value, list):
        return [
            _normalize_value(item, f"{pointer}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                _reject(
                    RawPackageRejectionReason.UNSUPPORTED_VALUE,
                    pointer,
                    "Object keys must be strings.",
                )
            normalized_key = _normalize_text(key, pointer)
            if normalized_key in normalized:
                _reject(
                    RawPackageRejectionReason.NORMALIZED_KEY_COLLISION,
                    pointer,
                    "Object keys collide after NFC normalization.",
                )
            normalized[normalized_key] = _normalize_value(
                item, f"{pointer}.{normalized_key}"
            )
        return normalized
    _reject(
        RawPackageRejectionReason.UNSUPPORTED_VALUE,
        pointer,
        "Value is not representable by TRP-RAW-V1.",
    )


def _normalize_text(value: str, pointer: str) -> str:
    _validate_unicode(value, pointer)
    normalized = unicodedata.normalize("NFC", value)
    _validate_unicode(normalized, pointer)
    return normalized


def _validate_unicode(value: str, pointer: str) -> None:
    for character in value:
        codepoint = ord(character)
        is_surrogate = 0xD800 <= codepoint <= 0xDFFF
        is_noncharacter = (
            0xFDD0 <= codepoint <= 0xFDEF
            or codepoint & 0xFFFF in {0xFFFE, 0xFFFF}
        )
        if is_surrogate or is_noncharacter:
            _reject(
                RawPackageRejectionReason.INVALID_UNICODE,
                pointer,
                "Unpaired surrogates and Unicode noncharacters are forbidden.",
            )


def _validate_package_structure(value: Any) -> None:
    if not isinstance(value, dict):
        _reject(
            RawPackageRejectionReason.STRUCTURE_INVALID,
            "$",
            "TRP-RAW-V1 root must be an object.",
        )

    required = {
        "issue_codes",
        "media_type",
        "payload",
        "raw_id",
        "run_id",
        "schema_version",
    }
    if not required.issubset(value):
        _reject(
            RawPackageRejectionReason.STRUCTURE_INVALID,
            "$",
            "TRP-RAW-V1 required fields are missing.",
        )
    if value["schema_version"] != TRP_RAW_V1:
        _reject(
            RawPackageRejectionReason.STRUCTURE_INVALID,
            "$.schema_version",
            "schema_version must be TRP-RAW-V1.",
        )
    for field in ("raw_id", "run_id", "media_type"):
        if not isinstance(value[field], str) or not value[field]:
            _reject(
                RawPackageRejectionReason.STRUCTURE_INVALID,
                f"$.{field}",
                f"{field} must be a non-empty string.",
            )
    if not isinstance(value["payload"], dict):
        _reject(
            RawPackageRejectionReason.STRUCTURE_INVALID,
            "$.payload",
            "payload must be an object.",
        )
    if not isinstance(value["issue_codes"], list):
        _reject(
            RawPackageRejectionReason.STRUCTURE_INVALID,
            "$.issue_codes",
            "issue_codes must be an ordered array.",
        )
    validate_issue_codes(value["issue_codes"])
    _validate_token_arrays(value, "$")


def _validate_token_arrays(value: Any, pointer: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            item_pointer = f"{pointer}.{key}"
            if key == "tokens":
                if not isinstance(item, list):
                    _reject(
                        RawPackageRejectionReason.TOKEN_ORDER_INVALID,
                        item_pointer,
                        "Token collections must be arrays.",
                    )
                indices: list[int] = []
                for index, token in enumerate(item):
                    if (
                        not isinstance(token, dict)
                        or isinstance(token.get("index"), bool)
                        or not isinstance(token.get("index"), int)
                    ):
                        _reject(
                            RawPackageRejectionReason.TOKEN_ORDER_INVALID,
                            f"{item_pointer}[{index}]",
                            "Every token must have an integer index.",
                        )
                    indices.append(token["index"])
                if any(
                    current >= following
                    for current, following in zip(indices, indices[1:])
                ):
                    _reject(
                        RawPackageRejectionReason.TOKEN_ORDER_INVALID,
                        item_pointer,
                        "Token arrays must use strictly ascending indices.",
                    )
            _validate_token_arrays(item, item_pointer)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_token_arrays(item, f"{pointer}[{index}]")


def _encode_value(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return _encode_string(value)
    if isinstance(value, list):
        return "[" + ",".join(_encode_value(item) for item in value) + "]"
    return (
        "{"
        + ",".join(
            f"{_encode_string(key)}:{_encode_value(value[key])}"
            for key in sorted(value)
        )
        + "}"
    )


def _encode_string(value: str) -> str:
    encoded = ['"']
    for character in value:
        codepoint = ord(character)
        if character == '"':
            encoded.append('\\"')
        elif character == "\\":
            encoded.append("\\\\")
        elif codepoint <= 0x1F:
            encoded.append(f"\\u{codepoint:04x}")
        else:
            encoded.append(character)
    encoded.append('"')
    return "".join(encoded)


def _reject(
    reason: RawPackageRejectionReason,
    pointer: str,
    message: str,
) -> None:
    raise TemporalRawPackageError(reason, pointer, message)
