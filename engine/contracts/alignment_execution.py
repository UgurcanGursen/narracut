"""Canonical immutable AdapterExecution provenance contract."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import weakref
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ._canonical_json import encode_canonical_json_bytes
from .alignment import (
    AlignmentRequest,
    AlignmentRequestMode,
    _is_materialized_alignment_request,
)
from .temporal import STABLE_ISSUE_CODE_SET


ADAPTER_EXECUTION_V1 = "ADAPTER-EXECUTION-V1"
ADAPTER_EXECUTION_HASH_V1 = "ADAPTER-EXECUTION-HASH-V1"
PAID_FALLBACK_AUTHORIZATION_EVIDENCE_V1 = (
    "PAID-FALLBACK-AUTHORIZATION-EVIDENCE-V1"
)
REPLAY_EVIDENCE_V1 = "REPLAY-EVIDENCE-V1"
CONFIDENCE_AVAILABILITY_EVIDENCE_V1 = (
    "CONFIDENCE-AVAILABILITY-EVIDENCE-V1"
)

_ROOT_FIELDS = (
    "schema_version",
    "hash_scope_version",
    "adapter_execution_id",
    "adapter_execution_hash",
    "alignment_request_id",
    "alignment_request_hash",
    "adapter_id",
    "adapter_version",
    "mode",
    "status",
    "paid_fallback_authorization_evidence",
    "replay_evidence",
    "confidence_availability_evidence",
)
_PAID_FIELDS = (
    "schema_version",
    "authorization_id",
    "source",
    "decision",
    "alignment_request_id",
    "alignment_request_hash",
)
_REPLAY_FIELDS = (
    "schema_version",
    "source_adapter_execution_id",
    "source_adapter_execution_hash",
    "source_alignment_request_id",
    "source_alignment_request_hash",
)
_CONFIDENCE_FIELDS = ("schema_version", "availability")
_ROOT_STRING_FIELDS = _ROOT_FIELDS[:10]

_EXECUTION_ID_PATTERN = re.compile(r"aex_[0-9a-f]{32}")
_REQUEST_ID_PATTERN = re.compile(r"arq_[0-9a-f]{32}")
_BARE_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
_AUTHORIZATION_ID_PATTERN = re.compile(r"pfa_[a-z0-9][a-z0-9_-]{2,63}")
_DRIVE_PREFIX_PATTERN = re.compile(r"^[A-Za-z]:")
_SENSITIVE_LOCAL_NAMES = frozenset(
    {
        "host_path",
        "absolute_path",
        "credential",
        "credentials",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "authorization",
        "password",
        "signed_url",
        "uri",
    }
)


class AdapterExecutionMode(str, Enum):
    LOCAL = "LOCAL"
    REPLAY = "REPLAY"
    FREE_API = "FREE_API"
    PAID_API = "PAID_API"
    MANUAL_UI = "MANUAL_UI"


class AdapterExecutionStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class PaidFallbackAuthorizationSource(str, Enum):
    USER_EXPLICIT = "USER_EXPLICIT"


class PaidFallbackAuthorizationDecision(str, Enum):
    APPROVED = "APPROVED"
    DENIED = "DENIED"


class ConfidenceAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AdapterExecutionRejectionReason(str, Enum):
    STRUCTURE_INVALID = "STRUCTURE_INVALID"
    UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
    REQUEST_BINDING_INVALID = "REQUEST_BINDING_INVALID"
    MODE_STATUS_INVALID = "MODE_STATUS_INVALID"
    EVIDENCE_PRESENCE_INVALID = "EVIDENCE_PRESENCE_INVALID"
    PAID_FALLBACK_AUTHORIZATION_INVALID = "PAID_FALLBACK_AUTHORIZATION_INVALID"
    REPLAY_EVIDENCE_INVALID = "REPLAY_EVIDENCE_INVALID"
    REPLAY_LINEAGE_INVALID = "REPLAY_LINEAGE_INVALID"
    CONFIDENCE_AVAILABILITY_INVALID = "CONFIDENCE_AVAILABILITY_INVALID"
    NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    NOT_MATERIALIZED = "NOT_MATERIALIZED"


@dataclass(frozen=True)
class PaidFallbackAuthorizationEvidence:
    schema_version: str
    authorization_id: str
    source: PaidFallbackAuthorizationSource
    decision: PaidFallbackAuthorizationDecision
    alignment_request_id: str
    alignment_request_hash: str


@dataclass(frozen=True)
class ReplayEvidence:
    schema_version: str
    source_adapter_execution_id: str
    source_adapter_execution_hash: str
    source_alignment_request_id: str
    source_alignment_request_hash: str


@dataclass(frozen=True)
class ConfidenceAvailabilityEvidence:
    schema_version: str
    availability: ConfidenceAvailability


@dataclass(frozen=True)
class AdapterExecution:
    schema_version: str
    hash_scope_version: str
    adapter_execution_id: str
    adapter_execution_hash: str
    alignment_request_id: str
    alignment_request_hash: str
    adapter_id: str
    adapter_version: str
    mode: AdapterExecutionMode
    status: AdapterExecutionStatus
    paid_fallback_authorization_evidence: PaidFallbackAuthorizationEvidence | None
    replay_evidence: ReplayEvidence | None
    confidence_availability_evidence: ConfidenceAvailabilityEvidence | None


class AdapterExecutionContractError(ValueError):
    """Fail-closed AdapterExecution validation error."""

    def __init__(
        self,
        pointer: str,
        reason: AdapterExecutionRejectionReason,
        issue_code: str | None = None,
    ) -> None:
        if type(pointer) is not str:
            raise TypeError("pointer must be an exact built-in string")
        if type(reason) is not AdapterExecutionRejectionReason:
            raise TypeError("reason must be an AdapterExecutionRejectionReason")
        if issue_code is not None and (
            type(issue_code) is not str or issue_code not in STABLE_ISSUE_CODE_SET
        ):
            raise ValueError("Unknown canonical issue code")
        super().__init__(f"Adapter execution rejected: {reason.value}")
        self.pointer = pointer
        self.reason = reason
        self.issue_code = issue_code


_MATERIALIZED_ADAPTER_EXECUTIONS: dict[
    int, weakref.ReferenceType[AdapterExecution]
] = {}


class _ObjectPairs(list[tuple[str, Any]]):
    pass


def materialize_adapter_execution(
    value: Mapping[str, Any],
    *,
    alignment_request: AlignmentRequest,
    source_alignment_request: AlignmentRequest | None = None,
    source_execution: AdapterExecution | None = None,
) -> AdapterExecution:
    return _materialize(
        value,
        alignment_request=alignment_request,
        source_alignment_request=source_alignment_request,
        source_execution=source_execution,
        source_bytes=None,
    )


def load_adapter_execution(
    source: bytes,
    *,
    alignment_request: AlignmentRequest,
    source_alignment_request: AlignmentRequest | None = None,
    source_execution: AdapterExecution | None = None,
) -> AdapterExecution:
    _preflight_dependencies(
        alignment_request,
        source_alignment_request,
        source_execution,
    )
    if type(source) is not bytes:
        _reject("/", AdapterExecutionRejectionReason.STRUCTURE_INVALID)
    if source.startswith(b"\xef\xbb\xbf"):
        _reject("/", AdapterExecutionRejectionReason.NON_CANONICAL_SERIALIZATION)
    try:
        text = source.decode("utf-8")
        parsed = json.loads(
            text,
            object_pairs_hook=_ObjectPairs,
        )
        value = _convert_pairs(parsed, "/")
    except AdapterExecutionContractError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
        _reject("/", AdapterExecutionRejectionReason.STRUCTURE_INVALID)
    return _materialize(
        value,
        alignment_request=alignment_request,
        source_alignment_request=source_alignment_request,
        source_execution=source_execution,
        source_bytes=source,
        preflight_complete=True,
    )


def serialize_adapter_execution(execution: AdapterExecution) -> bytes:
    if not _is_materialized_adapter_execution(execution):
        _reject("/", AdapterExecutionRejectionReason.NOT_MATERIALIZED)
    return encode_canonical_json_bytes(_envelope(execution))


def _materialize(
    value: Mapping[str, Any],
    *,
    alignment_request: AlignmentRequest,
    source_alignment_request: AlignmentRequest | None,
    source_execution: AdapterExecution | None,
    source_bytes: bytes | None,
    preflight_complete: bool = False,
) -> AdapterExecution:
    if not preflight_complete:
        _preflight_dependencies(
            alignment_request,
            source_alignment_request,
            source_execution,
        )
    data = _validate_root_shape(value)
    if data["schema_version"] != ADAPTER_EXECUTION_V1:
        _reject("/schema_version", AdapterExecutionRejectionReason.UNSUPPORTED_VALUE)
    if data["hash_scope_version"] != ADAPTER_EXECUTION_HASH_V1:
        _reject(
            "/hash_scope_version",
            AdapterExecutionRejectionReason.UNSUPPORTED_VALUE,
        )
    mode = _parse_root_enum(
        data["mode"], AdapterExecutionMode, "/mode"
    )
    status = _parse_root_enum(
        data["status"], AdapterExecutionStatus, "/status"
    )
    _validate_dependency_presence(
        mode,
        source_alignment_request,
        source_execution,
    )
    _validate_current_binding(data, alignment_request, mode)
    _validate_mode_status(mode, status)
    _validate_evidence_presence(data, mode, status)
    paid = _parse_paid(data["paid_fallback_authorization_evidence"], alignment_request, status)
    replay = _parse_replay(
        data["replay_evidence"],
        data,
        alignment_request,
        source_alignment_request,
        source_execution,
    )
    confidence = _parse_confidence(
        data["confidence_availability_evidence"],
        alignment_request,
        status,
    )
    _scan_sensitive_data(data)
    projection = _projection_from_parts(
        data,
        mode=mode,
        status=status,
        paid=paid,
        replay=replay,
        confidence=confidence,
    )
    digest = hashlib.sha256(encode_canonical_json_bytes(projection)).hexdigest()
    if data["adapter_execution_hash"] != digest:
        _reject(
            "/adapter_execution_hash",
            AdapterExecutionRejectionReason.IDENTITY_MISMATCH,
        )
    execution_id = "aex_" + digest[:32]
    if data["adapter_execution_id"] != execution_id:
        _reject(
            "/adapter_execution_id",
            AdapterExecutionRejectionReason.IDENTITY_MISMATCH,
        )
    envelope = dict(projection)
    envelope["adapter_execution_id"] = execution_id
    envelope["adapter_execution_hash"] = digest
    canonical_envelope = encode_canonical_json_bytes(envelope)
    if source_bytes is not None and source_bytes != canonical_envelope:
        _reject(
            "/",
            AdapterExecutionRejectionReason.NON_CANONICAL_SERIALIZATION,
        )
    execution = AdapterExecution(
        schema_version=ADAPTER_EXECUTION_V1,
        hash_scope_version=ADAPTER_EXECUTION_HASH_V1,
        adapter_execution_id=execution_id,
        adapter_execution_hash=digest,
        alignment_request_id=data["alignment_request_id"],
        alignment_request_hash=data["alignment_request_hash"],
        adapter_id=data["adapter_id"],
        adapter_version=data["adapter_version"],
        mode=mode,
        status=status,
        paid_fallback_authorization_evidence=paid,
        replay_evidence=replay,
        confidence_availability_evidence=confidence,
    )
    if encode_canonical_json_bytes(_envelope(execution)) != canonical_envelope:
        raise RuntimeError("adapter execution canonical envelope verification failed")
    _register_materialized_adapter_execution(execution)
    return execution


def _preflight_dependencies(
    alignment_request: AlignmentRequest,
    source_alignment_request: AlignmentRequest | None,
    source_execution: AdapterExecution | None,
) -> None:
    if (
        type(alignment_request) is not AlignmentRequest
        or not _is_materialized_alignment_request(alignment_request)
    ):
        raise TypeError("alignment_request must be genuine exact AlignmentRequest")
    if source_alignment_request is not None and (
        type(source_alignment_request) is not AlignmentRequest
        or not _is_materialized_alignment_request(source_alignment_request)
    ):
        _reject(
            "/source_alignment_request",
            AdapterExecutionRejectionReason.NOT_MATERIALIZED,
        )
    if source_execution is not None and (
        type(source_execution) is not AdapterExecution
        or not _is_materialized_adapter_execution(source_execution)
    ):
        _reject(
            "/source_execution",
            AdapterExecutionRejectionReason.NOT_MATERIALIZED,
        )


def _validate_root_shape(value: Any) -> Mapping[str, Any]:
    data = _require_mapping(value, "/")
    _require_exact_key_set(data, _ROOT_FIELDS, "/")
    for field in _ROOT_STRING_FIELDS:
        raw = _mapping_get(data, field, f"/{field}")
        if type(raw) is not str:
            _reject(f"/{field}", AdapterExecutionRejectionReason.STRUCTURE_INVALID)
    for field in (
        "paid_fallback_authorization_evidence",
        "replay_evidence",
        "confidence_availability_evidence",
    ):
        raw = _mapping_get(data, field, f"/{field}")
        if raw is not None and not isinstance(raw, Mapping):
            _reject(f"/{field}", AdapterExecutionRejectionReason.STRUCTURE_INVALID)
    return data


def _parse_root_enum(value: str, enum_type: type[Enum], pointer: str):
    try:
        return enum_type(value)
    except ValueError:
        _reject(
            pointer,
            AdapterExecutionRejectionReason.UNSUPPORTED_VALUE,
            "UNSUPPORTED_CONTRACT_ENUM",
        )


def _validate_dependency_presence(
    mode: AdapterExecutionMode,
    source_alignment_request: AlignmentRequest | None,
    source_execution: AdapterExecution | None,
) -> None:
    required = mode is AdapterExecutionMode.REPLAY
    if (source_alignment_request is None) == required:
        _reject(
            "/source_alignment_request",
            AdapterExecutionRejectionReason.REPLAY_EVIDENCE_INVALID,
            "REPLAY_INPUT_MISMATCH",
        )
    if (source_execution is None) == required:
        _reject(
            "/source_execution",
            AdapterExecutionRejectionReason.REPLAY_EVIDENCE_INVALID,
            "REPLAY_INPUT_MISMATCH",
        )


def _validate_current_binding(
    data: Mapping[str, Any],
    request: AlignmentRequest,
    mode: AdapterExecutionMode,
) -> None:
    if _REQUEST_ID_PATTERN.fullmatch(data["alignment_request_id"]) is None or data[
        "alignment_request_id"
    ] != request.alignment_request_id:
        _binding_reject("/alignment_request_id", "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    if _BARE_HASH_PATTERN.fullmatch(data["alignment_request_hash"]) is None or data[
        "alignment_request_hash"
    ] != request.alignment_request_hash:
        _binding_reject("/alignment_request_hash", "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    if data["adapter_id"] != request.adapter_capability.adapter_id:
        _binding_reject("/adapter_id", "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    if data["adapter_version"] != request.adapter_capability.adapter_version:
        _binding_reject("/adapter_version", "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    if not _mode_matches_request(mode, request.mode):
        _binding_reject("/mode", None)


def _mode_matches_request(
    execution_mode: AdapterExecutionMode,
    request_mode: AlignmentRequestMode,
) -> bool:
    if execution_mode is AdapterExecutionMode.PAID_API:
        return request_mode is AlignmentRequestMode.FREE_API
    return execution_mode.value == request_mode.value


def _validate_mode_status(
    mode: AdapterExecutionMode,
    status: AdapterExecutionStatus,
) -> None:
    if status is AdapterExecutionStatus.BLOCKED and mode in {
        AdapterExecutionMode.LOCAL,
        AdapterExecutionMode.REPLAY,
    }:
        _reject("/status", AdapterExecutionRejectionReason.MODE_STATUS_INVALID)


def _validate_evidence_presence(
    data: Mapping[str, Any],
    mode: AdapterExecutionMode,
    status: AdapterExecutionStatus,
) -> None:
    paid_present = data["paid_fallback_authorization_evidence"] is not None
    if paid_present != (mode is AdapterExecutionMode.PAID_API):
        _reject(
            "/paid_fallback_authorization_evidence",
            AdapterExecutionRejectionReason.EVIDENCE_PRESENCE_INVALID,
            "PAID_FALLBACK_UNAUTHORIZED",
        )
    replay_present = data["replay_evidence"] is not None
    if replay_present != (mode is AdapterExecutionMode.REPLAY):
        _reject(
            "/replay_evidence",
            AdapterExecutionRejectionReason.EVIDENCE_PRESENCE_INVALID,
            "REPLAY_INPUT_MISMATCH",
        )
    confidence_present = data["confidence_availability_evidence"] is not None
    if confidence_present != (status is not AdapterExecutionStatus.BLOCKED):
        _reject(
            "/confidence_availability_evidence",
            AdapterExecutionRejectionReason.EVIDENCE_PRESENCE_INVALID,
        )


def _parse_paid(
    value: Mapping[str, Any] | None,
    request: AlignmentRequest,
    status: AdapterExecutionStatus,
) -> PaidFallbackAuthorizationEvidence | None:
    if value is None:
        return None
    pointer = "/paid_fallback_authorization_evidence"
    data = _require_mapping(value, pointer)
    _require_exact_key_set(data, _PAID_FIELDS, pointer)
    issue = "PAID_FALLBACK_UNAUTHORIZED"
    schema = _nested_string(data, "schema_version", pointer, AdapterExecutionRejectionReason.PAID_FALLBACK_AUTHORIZATION_INVALID, issue)
    if schema != PAID_FALLBACK_AUTHORIZATION_EVIDENCE_V1:
        _reject(f"{pointer}/schema_version", AdapterExecutionRejectionReason.PAID_FALLBACK_AUTHORIZATION_INVALID, issue)
    authorization_id = _nested_string(data, "authorization_id", pointer, AdapterExecutionRejectionReason.PAID_FALLBACK_AUTHORIZATION_INVALID, issue)
    if _AUTHORIZATION_ID_PATTERN.fullmatch(authorization_id) is None:
        _reject(f"{pointer}/authorization_id", AdapterExecutionRejectionReason.PAID_FALLBACK_AUTHORIZATION_INVALID, issue)
    source_raw = _nested_string(data, "source", pointer, AdapterExecutionRejectionReason.PAID_FALLBACK_AUTHORIZATION_INVALID, issue)
    source = _parse_nested_enum(source_raw, PaidFallbackAuthorizationSource, f"{pointer}/source", AdapterExecutionRejectionReason.PAID_FALLBACK_AUTHORIZATION_INVALID, issue)
    decision_raw = _nested_string(data, "decision", pointer, AdapterExecutionRejectionReason.PAID_FALLBACK_AUTHORIZATION_INVALID, issue)
    decision = _parse_nested_enum(decision_raw, PaidFallbackAuthorizationDecision, f"{pointer}/decision", AdapterExecutionRejectionReason.PAID_FALLBACK_AUTHORIZATION_INVALID, issue)
    request_id = _nested_string(data, "alignment_request_id", pointer, AdapterExecutionRejectionReason.PAID_FALLBACK_AUTHORIZATION_INVALID, issue)
    if _REQUEST_ID_PATTERN.fullmatch(request_id) is None or request_id != request.alignment_request_id:
        _reject(f"{pointer}/alignment_request_id", AdapterExecutionRejectionReason.PAID_FALLBACK_AUTHORIZATION_INVALID, issue)
    request_hash = _nested_string(data, "alignment_request_hash", pointer, AdapterExecutionRejectionReason.PAID_FALLBACK_AUTHORIZATION_INVALID, issue)
    if _BARE_HASH_PATTERN.fullmatch(request_hash) is None or request_hash != request.alignment_request_hash:
        _reject(f"{pointer}/alignment_request_hash", AdapterExecutionRejectionReason.PAID_FALLBACK_AUTHORIZATION_INVALID, issue)
    expected = (
        PaidFallbackAuthorizationDecision.DENIED
        if status is AdapterExecutionStatus.BLOCKED
        else PaidFallbackAuthorizationDecision.APPROVED
    )
    if decision is not expected:
        _reject(f"{pointer}/decision", AdapterExecutionRejectionReason.PAID_FALLBACK_AUTHORIZATION_INVALID, issue)
    return PaidFallbackAuthorizationEvidence(
        schema, authorization_id, source, decision, request_id, request_hash
    )


def _parse_replay(
    value: Mapping[str, Any] | None,
    root: Mapping[str, Any],
    current_request: AlignmentRequest,
    source_request: AlignmentRequest | None,
    source_execution: AdapterExecution | None,
) -> ReplayEvidence | None:
    if value is None:
        return None
    assert source_request is not None and source_execution is not None
    pointer = "/replay_evidence"
    data = _require_mapping(value, pointer)
    _require_exact_key_set(data, _REPLAY_FIELDS, pointer)
    reason = AdapterExecutionRejectionReason.REPLAY_EVIDENCE_INVALID
    input_issue = "REPLAY_INPUT_MISMATCH"
    schema = _nested_string(data, "schema_version", pointer, reason, input_issue)
    if schema != REPLAY_EVIDENCE_V1:
        _reject(f"{pointer}/schema_version", reason, input_issue)
    source_execution_id = _nested_string(data, "source_adapter_execution_id", pointer, reason, input_issue)
    if _EXECUTION_ID_PATTERN.fullmatch(source_execution_id) is None:
        _reject(f"{pointer}/source_adapter_execution_id", reason, input_issue)
    source_execution_hash = _nested_string(data, "source_adapter_execution_hash", pointer, reason, input_issue)
    if _BARE_HASH_PATTERN.fullmatch(source_execution_hash) is None:
        _reject(f"{pointer}/source_adapter_execution_hash", reason, "REPLAY_HASH_MISMATCH")
    source_request_id = _nested_string(data, "source_alignment_request_id", pointer, reason, input_issue)
    if _REQUEST_ID_PATTERN.fullmatch(source_request_id) is None:
        _reject(f"{pointer}/source_alignment_request_id", reason, input_issue)
    source_request_hash = _nested_string(data, "source_alignment_request_hash", pointer, reason, input_issue)
    if _BARE_HASH_PATTERN.fullmatch(source_request_hash) is None:
        _reject(f"{pointer}/source_alignment_request_hash", reason, input_issue)
    if source_request.mode is AlignmentRequestMode.REPLAY:
        _lineage_reject("/source_alignment_request/mode")
    if source_execution.status is not AdapterExecutionStatus.SUCCEEDED:
        _lineage_reject("/source_execution/status")
    if source_execution.mode is AdapterExecutionMode.REPLAY:
        _lineage_reject("/source_execution/mode")
    if not _mode_matches_request(source_execution.mode, source_request.mode):
        _replay_reject("/source_execution/mode", input_issue)
    if source_execution.alignment_request_id != source_request.alignment_request_id:
        _replay_reject("/source_execution/alignment_request_id", input_issue)
    if source_execution.alignment_request_hash != source_request.alignment_request_hash:
        _replay_reject("/source_execution/alignment_request_hash", input_issue)
    if source_request_id != source_request.alignment_request_id:
        _replay_reject(f"{pointer}/source_alignment_request_id", input_issue)
    if source_request_hash != source_request.alignment_request_hash:
        _replay_reject(f"{pointer}/source_alignment_request_hash", input_issue)
    if source_request.alignment_request_id == current_request.alignment_request_id:
        _lineage_reject("/source_alignment_request/alignment_request_id")
    if source_request.alignment_request_hash == current_request.alignment_request_hash:
        _lineage_reject("/source_alignment_request/alignment_request_hash")
    if source_execution_id != source_execution.adapter_execution_id:
        _replay_reject(f"{pointer}/source_adapter_execution_id", input_issue)
    if source_execution_hash != source_execution.adapter_execution_hash:
        _replay_reject(f"{pointer}/source_adapter_execution_hash", "REPLAY_HASH_MISMATCH")
    if source_execution_id == root["adapter_execution_id"]:
        _lineage_reject(f"{pointer}/source_adapter_execution_id")
    return ReplayEvidence(
        schema,
        source_execution_id,
        source_execution_hash,
        source_request_id,
        source_request_hash,
    )


def _parse_confidence(
    value: Mapping[str, Any] | None,
    request: AlignmentRequest,
    status: AdapterExecutionStatus,
) -> ConfidenceAvailabilityEvidence | None:
    if value is None:
        return None
    pointer = "/confidence_availability_evidence"
    data = _require_mapping(value, pointer)
    _require_exact_key_set(data, _CONFIDENCE_FIELDS, pointer)
    reason = AdapterExecutionRejectionReason.CONFIDENCE_AVAILABILITY_INVALID
    schema = _nested_string(data, "schema_version", pointer, reason, None)
    if schema != CONFIDENCE_AVAILABILITY_EVIDENCE_V1:
        _reject(f"{pointer}/schema_version", reason)
    availability_raw = _nested_string(data, "availability", pointer, reason, None)
    availability = _parse_nested_enum(
        availability_raw,
        ConfidenceAvailability,
        f"{pointer}/availability",
        reason,
        None,
    )
    capability = request.adapter_capability.confidence_output
    if status is AdapterExecutionStatus.FAILED:
        valid = availability is ConfidenceAvailability.NOT_APPLICABLE
    elif capability == "SUPPORTED":
        valid = availability in {
            ConfidenceAvailability.AVAILABLE,
            ConfidenceAvailability.UNAVAILABLE,
        }
    else:
        valid = availability is ConfidenceAvailability.NOT_APPLICABLE
    if not valid:
        _reject(f"{pointer}/availability", reason)
    return ConfidenceAvailabilityEvidence(schema, availability)


def _nested_string(
    data: Mapping[str, Any],
    field: str,
    base_pointer: str,
    reason: AdapterExecutionRejectionReason,
    issue_code: str | None,
) -> str:
    pointer = f"{base_pointer}/{field}"
    value = _mapping_get(data, field, pointer)
    if type(value) is not str:
        _reject(pointer, reason, issue_code)
    return value


def _parse_nested_enum(
    value: str,
    enum_type: type[Enum],
    pointer: str,
    reason: AdapterExecutionRejectionReason,
    issue_code: str | None,
):
    try:
        return enum_type(value)
    except ValueError:
        _reject(pointer, reason, issue_code)


def _projection_from_parts(
    data: Mapping[str, Any],
    *,
    mode: AdapterExecutionMode,
    status: AdapterExecutionStatus,
    paid: PaidFallbackAuthorizationEvidence | None,
    replay: ReplayEvidence | None,
    confidence: ConfidenceAvailabilityEvidence | None,
) -> dict[str, Any]:
    return {
        "adapter_id": data["adapter_id"],
        "adapter_version": data["adapter_version"],
        "alignment_request_hash": data["alignment_request_hash"],
        "alignment_request_id": data["alignment_request_id"],
        "confidence_availability_evidence": _confidence_dict(confidence),
        "hash_scope_version": data["hash_scope_version"],
        "mode": mode.value,
        "paid_fallback_authorization_evidence": _paid_dict(paid),
        "replay_evidence": _replay_dict(replay),
        "schema_version": data["schema_version"],
        "status": status.value,
    }


def _envelope(execution: AdapterExecution) -> dict[str, Any]:
    projection = {
        "adapter_id": execution.adapter_id,
        "adapter_version": execution.adapter_version,
        "alignment_request_hash": execution.alignment_request_hash,
        "alignment_request_id": execution.alignment_request_id,
        "confidence_availability_evidence": _confidence_dict(
            execution.confidence_availability_evidence
        ),
        "hash_scope_version": execution.hash_scope_version,
        "mode": execution.mode.value,
        "paid_fallback_authorization_evidence": _paid_dict(
            execution.paid_fallback_authorization_evidence
        ),
        "replay_evidence": _replay_dict(execution.replay_evidence),
        "schema_version": execution.schema_version,
        "status": execution.status.value,
    }
    projection["adapter_execution_id"] = execution.adapter_execution_id
    projection["adapter_execution_hash"] = execution.adapter_execution_hash
    return projection


def _paid_dict(value: PaidFallbackAuthorizationEvidence | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "alignment_request_hash": value.alignment_request_hash,
        "alignment_request_id": value.alignment_request_id,
        "authorization_id": value.authorization_id,
        "decision": value.decision.value,
        "schema_version": value.schema_version,
        "source": value.source.value,
    }


def _replay_dict(value: ReplayEvidence | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "schema_version": value.schema_version,
        "source_adapter_execution_hash": value.source_adapter_execution_hash,
        "source_adapter_execution_id": value.source_adapter_execution_id,
        "source_alignment_request_hash": value.source_alignment_request_hash,
        "source_alignment_request_id": value.source_alignment_request_id,
    }


def _confidence_dict(value: ConfidenceAvailabilityEvidence | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "availability": value.availability.value,
        "schema_version": value.schema_version,
    }


def _register_materialized_adapter_execution(value: AdapterExecution) -> None:
    identity_key = id(value)

    def _remove(reference: weakref.ReferenceType[AdapterExecution]) -> None:
        if _MATERIALIZED_ADAPTER_EXECUTIONS.get(identity_key) is reference:
            del _MATERIALIZED_ADAPTER_EXECUTIONS[identity_key]

    registered_reference = weakref.ref(value, _remove)
    try:
        _MATERIALIZED_ADAPTER_EXECUTIONS[identity_key] = registered_reference
        verification = _is_materialized_adapter_execution(value)
    except Exception:
        if _MATERIALIZED_ADAPTER_EXECUTIONS.get(identity_key) is registered_reference:
            del _MATERIALIZED_ADAPTER_EXECUTIONS[identity_key]
        raise
    if not verification:
        if _MATERIALIZED_ADAPTER_EXECUTIONS.get(identity_key) is registered_reference:
            del _MATERIALIZED_ADAPTER_EXECUTIONS[identity_key]
        raise RuntimeError("adapter execution provenance registration failed")


def _is_materialized_adapter_execution(value: object) -> bool:
    if type(value) is not AdapterExecution:
        return False
    reference = _MATERIALIZED_ADAPTER_EXECUTIONS.get(id(value))
    return reference is not None and reference() is value


def _require_mapping(value: Any, pointer: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _reject(pointer, AdapterExecutionRejectionReason.STRUCTURE_INVALID)
    try:
        keys = list(value.keys())
    except Exception:
        _reject(pointer, AdapterExecutionRejectionReason.STRUCTURE_INVALID)
    if any(type(key) is not str for key in keys):
        _reject(pointer, AdapterExecutionRejectionReason.STRUCTURE_INVALID)
    return value


def _require_exact_key_set(
    data: Mapping[str, Any],
    required_order: tuple[str, ...],
    pointer: str,
) -> None:
    try:
        keys = list(data.keys())
    except Exception:
        _reject(pointer, AdapterExecutionRejectionReason.STRUCTURE_INVALID)
    if any(type(key) is not str for key in keys):
        _reject(pointer, AdapterExecutionRejectionReason.STRUCTURE_INVALID)
    required = set(required_order)
    unknown = sorted(set(keys) - required)
    if unknown:
        key = unknown[0]
        selected = (
            _join_pointer(pointer, key) if _safe_dynamic_key(key) else pointer
        )
        _reject(selected, AdapterExecutionRejectionReason.STRUCTURE_INVALID)
    present = set(keys)
    for field in required_order:
        if field not in present:
            _reject(
                _join_pointer(pointer, field),
                AdapterExecutionRejectionReason.STRUCTURE_INVALID,
            )


def _mapping_get(data: Mapping[str, Any], key: str, pointer: str) -> Any:
    try:
        return data[key]
    except Exception:
        _reject(pointer, AdapterExecutionRejectionReason.STRUCTURE_INVALID)


def _reject_json_number(_: str) -> Any:
    raise ValueError("numbers are forbidden")


def _convert_pairs(value: Any, pointer: str) -> Any:
    if isinstance(value, _ObjectPairs):
        keys = [pair[0] for pair in value]
        if len(keys) != len(set(keys)):
            _reject(pointer, AdapterExecutionRejectionReason.STRUCTURE_INVALID)
        result: dict[str, Any] = {}
        for key, nested in value:
            child_pointer = (
                _join_pointer(pointer, key) if _safe_dynamic_key(key) else pointer
            )
            result[key] = _convert_pairs(nested, child_pointer)
        return result
    if isinstance(value, list):
        return [_convert_pairs(item, pointer) for item in value]
    return value


def _scan_sensitive_data(value: Any) -> None:
    seen: set[int] = set()

    def scan(item: Any, pointer: str) -> None:
        if isinstance(item, Mapping):
            identity = id(item)
            if identity in seen:
                _reject(pointer, AdapterExecutionRejectionReason.STRUCTURE_INVALID)
            seen.add(identity)
            try:
                keys = sorted(item.keys())
            except Exception:
                _reject(pointer, AdapterExecutionRejectionReason.STRUCTURE_INVALID)
            for key in keys:
                if not _safe_dynamic_key(key):
                    _reject(pointer, AdapterExecutionRejectionReason.STRUCTURE_INVALID)
                child = _join_pointer(pointer, key)
                scan(_mapping_get(item, key, child), child)
            seen.remove(identity)
        elif type(item) is str and _unsafe_string(item):
            _reject(pointer, AdapterExecutionRejectionReason.STRUCTURE_INVALID)

    scan(value, "/")


def _safe_dynamic_key(value: Any) -> bool:
    return (
        type(value) is str
        and unicodedata.normalize("NFC", value) == value
        and not _invalid_unicode(value)
        and value.rsplit("/", 1)[-1].lower() not in _SENSITIVE_LOCAL_NAMES
        and not _unsafe_string(value)
    )


def _unsafe_string(value: str) -> bool:
    return (
        unicodedata.normalize("NFC", value) != value
        or _invalid_unicode(value)
        or "://" in value
        or value.startswith("/")
        or value.startswith("\\")
        or _DRIVE_PREFIX_PATTERN.match(value) is not None
        or any(ord(character) < 0x20 or 0x7F <= ord(character) <= 0x9F for character in value)
    )


def _invalid_unicode(value: str) -> bool:
    return any(
        0xD800 <= ord(character) <= 0xDFFF
        or 0xFDD0 <= ord(character) <= 0xFDEF
        or ord(character) & 0xFFFF in {0xFFFE, 0xFFFF}
        for character in value
    )


def _join_pointer(base: str, key: str) -> str:
    escaped = key.replace("~", "~0").replace("/", "~1")
    return f"/{escaped}" if base == "/" else f"{base}/{escaped}"


def _binding_reject(pointer: str, issue_code: str | None) -> None:
    _reject(
        pointer,
        AdapterExecutionRejectionReason.REQUEST_BINDING_INVALID,
        issue_code,
    )


def _replay_reject(pointer: str, issue_code: str) -> None:
    _reject(
        pointer,
        AdapterExecutionRejectionReason.REPLAY_EVIDENCE_INVALID,
        issue_code,
    )


def _lineage_reject(pointer: str) -> None:
    _reject(
        pointer,
        AdapterExecutionRejectionReason.REPLAY_LINEAGE_INVALID,
        "REPLAY_INPUT_MISMATCH",
    )


def _reject(
    pointer: str,
    reason: AdapterExecutionRejectionReason,
    issue_code: str | None = None,
) -> None:
    raise AdapterExecutionContractError(pointer, reason, issue_code)
