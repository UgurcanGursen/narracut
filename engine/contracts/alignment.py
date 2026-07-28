"""Canonical AlignmentRequest identity and pre-execution contract."""

from __future__ import annotations

import hashlib
import re
import unicodedata
import weakref
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from ._canonical_json import encode_canonical_json_bytes
from .audio import AudioArtifact, _is_materialized_artifact
from .narration import (
    CanonicalNarrationDocument,
    NarrationRevision,
    _is_materialized_narration_document,
    _is_materialized_narration_revision,
)
from .temporal import (
    CanonicalRawPackage,
    STABLE_ISSUE_CODE_SET,
    _is_materialized_raw_package,
)


_ALIGNMENT_REQUEST_V1 = "ALIGNMENT-REQUEST-V1"
_ALIGNMENT_REQUEST_HASH_V1 = "ALIGNMENT-REQUEST-HASH-V1"
_ADAPTER_CAPABILITY_V1 = "ADAPTER-CAPABILITY-V1"
_CANONICAL_NARRATION_SCOPE = "CANONICAL_NARRATION"

_HASH_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
_BARE_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
_STABLE_ID_PATTERN = re.compile(
    r"[a-z][a-z0-9]*_[a-z0-9][a-z0-9_-]{2,63}"
)
_ADAPTER_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_LANGUAGE_TAG_PATTERN = re.compile(r"[a-z]{2,3}(?:-[a-z0-9]{2,8})*")
_MEDIA_TYPE_PATTERN = re.compile(
    r"[a-z0-9][a-z0-9!#$&^_.+-]{0,63}/"
    r"[a-z0-9][a-z0-9!#$&^_.+-]{0,63}"
)
_REQUEST_REQUIRED = {
    "schema_version",
    "hash_scope_version",
    "alignment_request_id",
    "alignment_request_hash",
    "project_id",
    "document_id",
    "temporal_raw_package_hash",
    "narration_revision_id",
    "narration_revision_hash",
    "audio_artifact_id",
    "audio_artifact_hash",
    "mode",
    "adapter_capability",
    "transcript_reference",
}
_REQUEST_RESERVED = {"authorization_reference", "extensions"}
_REQUEST_ALLOWED_STAGE1 = _REQUEST_REQUIRED | _REQUEST_RESERVED
_CAPABILITY_REQUIRED = {
    "schema_version",
    "adapter_id",
    "adapter_version",
    "mode",
    "language_tag",
    "media_type",
    "confidence_output",
    "network_access",
    "license_class",
}
_TRANSCRIPT_REQUIRED = {
    "narration_revision_id",
    "narration_revision_hash",
    "text_scope",
}
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
_DRIVE_PREFIX_PATTERN = re.compile(r"^[A-Za-z]:")
_MATERIALIZED_ALIGNMENT_REQUESTS: dict[
    int, weakref.ReferenceType["AlignmentRequest"]
] = {}


class AlignmentRequestMode(str, Enum):
    LOCAL = "LOCAL"
    REPLAY = "REPLAY"
    FREE_API = "FREE_API"
    MANUAL_UI = "MANUAL_UI"


@dataclass(frozen=True)
class AdapterCapability:
    schema_version: str
    adapter_id: str
    adapter_version: str
    mode: str
    language_tag: str
    media_type: str
    confidence_output: str
    network_access: str
    license_class: str


@dataclass(frozen=True)
class CanonicalTranscriptReference:
    narration_revision_id: str
    narration_revision_hash: str
    text_scope: str


@dataclass(frozen=True)
class AlignmentRequest:
    schema_version: str
    hash_scope_version: str
    alignment_request_id: str
    alignment_request_hash: str
    project_id: str
    document_id: str
    temporal_raw_package_hash: str
    narration_revision_id: str
    narration_revision_hash: str
    audio_artifact_id: str
    audio_artifact_hash: str
    mode: AlignmentRequestMode
    adapter_capability: AdapterCapability
    transcript_reference: CanonicalTranscriptReference | None


class AlignmentRequestRejectionReason(str, Enum):
    STRUCTURE_INVALID = "STRUCTURE_INVALID"
    UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
    LINEAGE_MISMATCH = "LINEAGE_MISMATCH"
    MODE_PRESENCE_MISMATCH = "MODE_PRESENCE_MISMATCH"
    TRANSCRIPT_INVALID = "TRANSCRIPT_INVALID"
    AUTHORIZATION_FORBIDDEN = "AUTHORIZATION_FORBIDDEN"
    CAPABILITY_INVALID = "CAPABILITY_INVALID"
    MODE_CAPABILITY_MISMATCH = "MODE_CAPABILITY_MISMATCH"
    EXTENSIONS_FORBIDDEN = "EXTENSIONS_FORBIDDEN"
    SENSITIVE_DATA = "SENSITIVE_DATA"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    NOT_MATERIALIZED = "NOT_MATERIALIZED"


class AlignmentRequestContractError(ValueError):
    """Fail-closed validation error with no request artifact output."""

    def __init__(
        self,
        pointer: str,
        reason: AlignmentRequestRejectionReason,
        message: str,
        *,
        issue_code: str | None = None,
    ):
        if type(pointer) is not str:
            raise TypeError("pointer must be an exact built-in string.")
        if not isinstance(reason, AlignmentRequestRejectionReason):
            raise TypeError("reason must be an AlignmentRequestRejectionReason.")
        if issue_code is not None and (
            type(issue_code) is not str
            or issue_code not in STABLE_ISSUE_CODE_SET
        ):
            raise ValueError("Unknown canonical issue code.")
        super().__init__(message)
        self.pointer = pointer
        self.reason = reason
        self.issue_code = issue_code


def _issue_metadata_row(
    *,
    reason: AlignmentRequestRejectionReason,
    stage: str,
) -> Mapping[str, str]:
    return MappingProxyType(
        {
            "category": "PRE_EXECUTION_CONTRACT_REJECTION",
            "default_severity": "FATAL",
            "producer": "ALIGNMENT_REQUEST_MATERIALIZER",
            "carried_by": "ALIGNMENT_REQUEST_CONTRACT_ERROR",
            "terminal_state_effect": "NO_EXECUTION_STATE",
            "escalation_effect": "NO_ESCALATION",
            "canonical_hash_behavior": "NO_ARTIFACT_OR_FAILURE_HASH",
            "reason": reason.value,
            "stage": stage,
        }
    )


_ALIGNMENT_REQUEST_ISSUE_METADATA = MappingProxyType(
    {
        "ALIGNMENT_REQUEST_WIRE_INVALID": _issue_metadata_row(
            reason=AlignmentRequestRejectionReason.STRUCTURE_INVALID,
            stage="1",
        ),
        "ALIGNMENT_REQUEST_UNSUPPORTED_VALUE": _issue_metadata_row(
            reason=AlignmentRequestRejectionReason.UNSUPPORTED_VALUE,
            stage="2 or 8",
        ),
        "ALIGNMENT_REQUEST_LINEAGE_MISMATCH": _issue_metadata_row(
            reason=AlignmentRequestRejectionReason.LINEAGE_MISMATCH,
            stage="3-7",
        ),
        "ALIGNMENT_REQUEST_MODE_PRESENCE_MISMATCH": _issue_metadata_row(
            reason=AlignmentRequestRejectionReason.MODE_PRESENCE_MISMATCH,
            stage="9 presence",
        ),
        "ALIGNMENT_REQUEST_TRANSCRIPT_INVALID": _issue_metadata_row(
            reason=AlignmentRequestRejectionReason.TRANSCRIPT_INVALID,
            stage="9 transcript content",
        ),
        "ALIGNMENT_REQUEST_AUTHORIZATION_FORBIDDEN": _issue_metadata_row(
            reason=AlignmentRequestRejectionReason.AUTHORIZATION_FORBIDDEN,
            stage="10",
        ),
        "ALIGNMENT_REQUEST_CAPABILITY_INVALID": _issue_metadata_row(
            reason=AlignmentRequestRejectionReason.CAPABILITY_INVALID,
            stage="11",
        ),
        "ALIGNMENT_REQUEST_MODE_CAPABILITY_MISMATCH": _issue_metadata_row(
            reason=AlignmentRequestRejectionReason.MODE_CAPABILITY_MISMATCH,
            stage="12",
        ),
        "ALIGNMENT_REQUEST_EXTENSIONS_FORBIDDEN": _issue_metadata_row(
            reason=AlignmentRequestRejectionReason.EXTENSIONS_FORBIDDEN,
            stage="13",
        ),
        "ALIGNMENT_REQUEST_SENSITIVE_DATA": _issue_metadata_row(
            reason=AlignmentRequestRejectionReason.SENSITIVE_DATA,
            stage="14",
        ),
        "ALIGNMENT_REQUEST_IDENTITY_MISMATCH": _issue_metadata_row(
            reason=AlignmentRequestRejectionReason.IDENTITY_MISMATCH,
            stage="15",
        ),
    }
)


@dataclass(frozen=True)
class _ParsedAlignmentRequest:
    schema_version: str
    hash_scope_version: str
    alignment_request_id: str
    alignment_request_hash: str
    project_id: str
    document_id: str
    temporal_raw_package_hash: str
    narration_revision_id: str
    narration_revision_hash: str
    audio_artifact_id: str
    audio_artifact_hash: str
    mode: str
    adapter_capability: Mapping[str, Any]
    transcript_reference: Mapping[str, Any] | None
    has_authorization_reference: bool
    has_extensions: bool
    raw: Mapping[str, Any]


def materialize_alignment_request(
    value: Mapping[str, Any],
    *,
    temporal_raw_package: CanonicalRawPackage,
    narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision,
    audio_artifact: AudioArtifact,
) -> AlignmentRequest:
    _preflight_dependencies(
        temporal_raw_package,
        narration_document,
        narration_revision,
        audio_artifact,
    )
    data = _parse_alignment_request(value)
    _validate_versions(data)
    _validate_lineage(
        data,
        temporal_raw_package,
        narration_document,
        narration_revision,
        audio_artifact,
    )
    mode = _parse_mode(data.mode)
    transcript = _parse_transcript_reference(
        data.transcript_reference,
        mode,
        narration_revision,
    )
    if data.has_authorization_reference:
        _reject_alignment_request(
            "/authorization_reference",
            AlignmentRequestRejectionReason.AUTHORIZATION_FORBIDDEN,
            "Alignment request authorization reference is forbidden.",
            "ALIGNMENT_REQUEST_AUTHORIZATION_FORBIDDEN",
        )
    capability = _parse_adapter_capability(data.adapter_capability)
    _validate_mode_contract(mode, transcript)
    _validate_capability_compatibility(
        capability,
        mode,
        narration_document,
        audio_artifact,
    )
    if data.has_extensions:
        _reject_alignment_request(
            "/extensions",
            AlignmentRequestRejectionReason.EXTENSIONS_FORBIDDEN,
            "Alignment request extensions are forbidden.",
            "ALIGNMENT_REQUEST_EXTENSIONS_FORBIDDEN",
        )
    _scan_sensitive_data(data.raw)
    projection = _identity_projection(
        data,
        mode=mode,
        capability=capability,
        transcript=transcript,
    )
    projection_bytes = encode_canonical_json_bytes(projection)
    digest = hashlib.sha256(projection_bytes).hexdigest()
    if data.alignment_request_hash != digest:
        _reject_alignment_request(
            "/alignment_request_hash",
            AlignmentRequestRejectionReason.IDENTITY_MISMATCH,
            "Alignment request identity hash does not match.",
            "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
        )
    request_id = "arq_" + digest[:32]
    if data.alignment_request_id != request_id:
        _reject_alignment_request(
            "/alignment_request_id",
            AlignmentRequestRejectionReason.IDENTITY_MISMATCH,
            "Alignment request identity ID does not match.",
            "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
        )
    request = AlignmentRequest(
        schema_version=_ALIGNMENT_REQUEST_V1,
        hash_scope_version=_ALIGNMENT_REQUEST_HASH_V1,
        alignment_request_id=request_id,
        alignment_request_hash=digest,
        project_id=data.project_id,
        document_id=data.document_id,
        temporal_raw_package_hash=data.temporal_raw_package_hash,
        narration_revision_id=data.narration_revision_id,
        narration_revision_hash=data.narration_revision_hash,
        audio_artifact_id=data.audio_artifact_id,
        audio_artifact_hash=data.audio_artifact_hash,
        mode=mode,
        adapter_capability=capability,
        transcript_reference=transcript,
    )
    encode_canonical_json_bytes(_full_envelope(request))
    _register_materialized_alignment_request(request)
    return request


def serialize_alignment_request(
    request: AlignmentRequest,
) -> bytes:
    if not _is_materialized_alignment_request(request):
        _reject_alignment_request(
            "/",
            AlignmentRequestRejectionReason.NOT_MATERIALIZED,
            "Alignment request must be a materialized AlignmentRequest.",
            None,
        )
    return encode_canonical_json_bytes(_full_envelope(request))


def _register_materialized_alignment_request(value: AlignmentRequest) -> None:
    identity_key = id(value)

    def _remove(
        callback_reference: weakref.ReferenceType[AlignmentRequest],
    ) -> None:
        if _MATERIALIZED_ALIGNMENT_REQUESTS.get(identity_key) is callback_reference:
            del _MATERIALIZED_ALIGNMENT_REQUESTS[identity_key]

    registered_reference = weakref.ref(value, _remove)
    try:
        _MATERIALIZED_ALIGNMENT_REQUESTS[identity_key] = registered_reference
        verification = _is_materialized_alignment_request(value)
    except Exception:
        if (
            _MATERIALIZED_ALIGNMENT_REQUESTS.get(identity_key)
            is registered_reference
        ):
            del _MATERIALIZED_ALIGNMENT_REQUESTS[identity_key]
        raise
    if not verification:
        if (
            _MATERIALIZED_ALIGNMENT_REQUESTS.get(identity_key)
            is registered_reference
        ):
            del _MATERIALIZED_ALIGNMENT_REQUESTS[identity_key]
        raise RuntimeError("alignment request provenance registration failed")


def _is_materialized_alignment_request(value: object) -> bool:
    if type(value) is not AlignmentRequest:
        return False

    registered_reference = _MATERIALIZED_ALIGNMENT_REQUESTS.get(id(value))

    return (
        registered_reference is not None
        and registered_reference() is value
    )


def _preflight_dependencies(
    temporal_raw_package: CanonicalRawPackage,
    narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision,
    audio_artifact: AudioArtifact,
) -> None:
    if type(temporal_raw_package) is not CanonicalRawPackage or not _is_materialized_raw_package(
        temporal_raw_package
    ):
        raise TypeError("temporal_raw_package must be genuine exact CanonicalRawPackage")
    if type(narration_document) is not CanonicalNarrationDocument or not _is_materialized_narration_document(
        narration_document
    ):
        raise TypeError(
            "narration_document must be genuine exact CanonicalNarrationDocument"
        )
    if type(narration_revision) is not NarrationRevision or not _is_materialized_narration_revision(
        narration_revision
    ):
        raise TypeError("narration_revision must be genuine exact NarrationRevision")
    if type(audio_artifact) is not AudioArtifact or not _is_materialized_artifact(
        audio_artifact
    ):
        raise TypeError("audio_artifact must be genuine exact AudioArtifact")


def _parse_alignment_request(value: Mapping[str, Any]) -> _ParsedAlignmentRequest:
    data = _require_mapping(value, "/")
    fields = _mapping_keys(data, "/")
    unknown = fields - _REQUEST_ALLOWED_STAGE1
    if unknown:
        _reject_alignment_request(
            "/" + _first_sorted(unknown),
            AlignmentRequestRejectionReason.STRUCTURE_INVALID,
            "Alignment request contains an unknown field.",
            "ALIGNMENT_REQUEST_WIRE_INVALID",
        )
    missing = _REQUEST_REQUIRED - fields
    if missing:
        _reject_alignment_request(
            "/",
            AlignmentRequestRejectionReason.STRUCTURE_INVALID,
            "Alignment request required fields are missing.",
            "ALIGNMENT_REQUEST_WIRE_INVALID",
        )
    parsed_strings: dict[str, str] = {}
    for field in (
        "schema_version",
        "hash_scope_version",
        "alignment_request_id",
        "alignment_request_hash",
        "project_id",
        "document_id",
        "temporal_raw_package_hash",
        "narration_revision_id",
        "narration_revision_hash",
        "audio_artifact_id",
        "audio_artifact_hash",
        "mode",
    ):
        parsed_strings[field] = _require_exact_nfc_string(
            _mapping_get(data, field, "/" + field),
            "/" + field,
            AlignmentRequestRejectionReason.STRUCTURE_INVALID,
            "ALIGNMENT_REQUEST_WIRE_INVALID",
        )
    capability = _require_mapping(
        _mapping_get(data, "adapter_capability", "/adapter_capability"),
        "/adapter_capability",
    )
    transcript_raw = _mapping_get(
        data,
        "transcript_reference",
        "/transcript_reference",
    )
    if transcript_raw is not None:
        transcript_raw = _require_mapping(
            transcript_raw,
            "/transcript_reference",
        )
    return _ParsedAlignmentRequest(
        adapter_capability=capability,
        transcript_reference=transcript_raw,
        has_authorization_reference="authorization_reference" in fields,
        has_extensions="extensions" in fields,
        raw=data,
        **parsed_strings,
    )


def _parse_adapter_capability(value: Mapping[str, Any]) -> AdapterCapability:
    fields = _mapping_keys(value, "/adapter_capability")
    if fields != _CAPABILITY_REQUIRED:
        _reject_alignment_request(
            "/adapter_capability",
            AlignmentRequestRejectionReason.CAPABILITY_INVALID,
            "Adapter capability fields are invalid.",
            "ALIGNMENT_REQUEST_CAPABILITY_INVALID",
        )
    parsed = {
        field: _require_exact_nfc_string(
            _mapping_get(value, field, f"/adapter_capability/{field}"),
            f"/adapter_capability/{field}",
            AlignmentRequestRejectionReason.CAPABILITY_INVALID,
            "ALIGNMENT_REQUEST_CAPABILITY_INVALID",
        )
        for field in _CAPABILITY_REQUIRED
    }
    if parsed["schema_version"] != _ADAPTER_CAPABILITY_V1:
        _capability_reject("/adapter_capability/schema_version")
    for field in ("adapter_id", "adapter_version"):
        if _ADAPTER_TOKEN_PATTERN.fullmatch(parsed[field]) is None:
            _capability_reject(f"/adapter_capability/{field}")
    if _LANGUAGE_TAG_PATTERN.fullmatch(parsed["language_tag"]) is None:
        _capability_reject("/adapter_capability/language_tag")
    if _MEDIA_TYPE_PATTERN.fullmatch(parsed["media_type"]) is None:
        _capability_reject("/adapter_capability/media_type")
    if parsed["confidence_output"] not in {"SUPPORTED", "UNSUPPORTED"}:
        _capability_reject("/adapter_capability/confidence_output")
    if parsed["network_access"] not in {"FORBIDDEN", "REQUIRED"}:
        _capability_reject("/adapter_capability/network_access")
    if parsed["license_class"] not in {"LOCAL", "REPLAY", "FREE", "MANUAL"}:
        _capability_reject("/adapter_capability/license_class")
    if parsed["mode"] not in {mode.value for mode in AlignmentRequestMode}:
        _capability_reject("/adapter_capability/mode")
    return AdapterCapability(**parsed)


def _parse_transcript_reference(
    value: Mapping[str, Any] | None,
    mode: AlignmentRequestMode,
    narration_revision: NarrationRevision,
) -> CanonicalTranscriptReference | None:
    required = mode is not AlignmentRequestMode.FREE_API
    if required and value is None:
        _reject_alignment_request(
            "/transcript_reference",
            AlignmentRequestRejectionReason.MODE_PRESENCE_MISMATCH,
            "Transcript reference is required for this mode.",
            "ALIGNMENT_REQUEST_MODE_PRESENCE_MISMATCH",
        )
    if not required and value is not None:
        _reject_alignment_request(
            "/transcript_reference",
            AlignmentRequestRejectionReason.MODE_PRESENCE_MISMATCH,
            "Transcript reference is forbidden for this mode.",
            "ALIGNMENT_REQUEST_MODE_PRESENCE_MISMATCH",
        )
    if value is None:
        return None
    fields = _mapping_keys(value, "/transcript_reference")
    if fields != _TRANSCRIPT_REQUIRED:
        _transcript_reject("/transcript_reference")
    revision_id = _require_exact_nfc_string(
        _mapping_get(value, "narration_revision_id", "/transcript_reference/narration_revision_id"),
        "/transcript_reference/narration_revision_id",
        AlignmentRequestRejectionReason.TRANSCRIPT_INVALID,
        "ALIGNMENT_REQUEST_TRANSCRIPT_INVALID",
    )
    revision_hash = _require_exact_nfc_string(
        _mapping_get(value, "narration_revision_hash", "/transcript_reference/narration_revision_hash"),
        "/transcript_reference/narration_revision_hash",
        AlignmentRequestRejectionReason.TRANSCRIPT_INVALID,
        "ALIGNMENT_REQUEST_TRANSCRIPT_INVALID",
    )
    text_scope = _require_exact_nfc_string(
        _mapping_get(value, "text_scope", "/transcript_reference/text_scope"),
        "/transcript_reference/text_scope",
        AlignmentRequestRejectionReason.TRANSCRIPT_INVALID,
        "ALIGNMENT_REQUEST_TRANSCRIPT_INVALID",
    )
    if text_scope != _CANONICAL_NARRATION_SCOPE:
        _transcript_reject("/transcript_reference/text_scope")
    if revision_id != narration_revision.revision_id:
        _transcript_reject("/transcript_reference/narration_revision_id")
    if revision_hash != narration_revision.revision_hash:
        _transcript_reject("/transcript_reference/narration_revision_hash")
    return CanonicalTranscriptReference(
        narration_revision_id=revision_id,
        narration_revision_hash=revision_hash,
        text_scope=text_scope,
    )


def _validate_lineage(
    data: _ParsedAlignmentRequest,
    temporal_raw_package: CanonicalRawPackage,
    narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision,
    audio_artifact: AudioArtifact,
) -> None:
    if data.temporal_raw_package_hash != temporal_raw_package.canonical_hash:
        _lineage_reject("/temporal_raw_package_hash")
    if narration_document.current_revision_id != narration_revision.revision_id:
        _lineage_reject("/narration_revision_id")
    if (
        data.project_id != narration_document.project_id
        or data.project_id != narration_revision.project_id
        or data.project_id != audio_artifact.project_id
    ):
        _lineage_reject("/project_id")
    if (
        data.document_id != narration_document.document_id
        or data.document_id != narration_revision.document_id
        or data.document_id != audio_artifact.document_id
    ):
        _lineage_reject("/document_id")
    if audio_artifact.narration_revision_id != narration_revision.revision_id:
        _lineage_reject("/narration_revision_id")
    if audio_artifact.narration_revision_hash != narration_revision.revision_hash:
        _lineage_reject("/narration_revision_hash")
    if data.narration_revision_id != narration_revision.revision_id:
        _lineage_reject("/narration_revision_id")
    if data.narration_revision_hash != narration_revision.revision_hash:
        _lineage_reject("/narration_revision_hash")
    if data.audio_artifact_id != audio_artifact.audio_artifact_id:
        _lineage_reject("/audio_artifact_id")
    if data.audio_artifact_hash != audio_artifact.audio_artifact_hash:
        _lineage_reject("/audio_artifact_hash")


def _validate_versions(data: _ParsedAlignmentRequest) -> None:
    if data.schema_version != _ALIGNMENT_REQUEST_V1:
        _reject_alignment_request(
            "/schema_version",
            AlignmentRequestRejectionReason.UNSUPPORTED_VALUE,
            "Unsupported alignment request schema version.",
            "ALIGNMENT_REQUEST_UNSUPPORTED_VALUE",
        )
    if data.hash_scope_version != _ALIGNMENT_REQUEST_HASH_V1:
        _reject_alignment_request(
            "/hash_scope_version",
            AlignmentRequestRejectionReason.UNSUPPORTED_VALUE,
            "Unsupported alignment request hash scope.",
            "ALIGNMENT_REQUEST_UNSUPPORTED_VALUE",
        )


def _parse_mode(value: str) -> AlignmentRequestMode:
    try:
        return AlignmentRequestMode(value)
    except ValueError as exc:
        raise AlignmentRequestContractError(
            "/mode",
            AlignmentRequestRejectionReason.UNSUPPORTED_VALUE,
            "Unsupported alignment request mode.",
            issue_code="ALIGNMENT_REQUEST_UNSUPPORTED_VALUE",
        ) from exc


def _validate_mode_contract(
    mode: AlignmentRequestMode,
    transcript: CanonicalTranscriptReference | None,
) -> None:
    if mode is AlignmentRequestMode.FREE_API and transcript is not None:
        _reject_alignment_request(
            "/transcript_reference",
            AlignmentRequestRejectionReason.MODE_PRESENCE_MISMATCH,
            "Transcript reference is forbidden for this mode.",
            "ALIGNMENT_REQUEST_MODE_PRESENCE_MISMATCH",
        )
    if mode is not AlignmentRequestMode.FREE_API and transcript is None:
        _reject_alignment_request(
            "/transcript_reference",
            AlignmentRequestRejectionReason.MODE_PRESENCE_MISMATCH,
            "Transcript reference is required for this mode.",
            "ALIGNMENT_REQUEST_MODE_PRESENCE_MISMATCH",
        )


def _validate_capability_compatibility(
    capability: AdapterCapability,
    mode: AlignmentRequestMode,
    narration_document: CanonicalNarrationDocument,
    audio_artifact: AudioArtifact,
) -> None:
    expected = {
        AlignmentRequestMode.LOCAL: ("LOCAL", "FORBIDDEN", "LOCAL"),
        AlignmentRequestMode.REPLAY: ("REPLAY", "FORBIDDEN", "REPLAY"),
        AlignmentRequestMode.FREE_API: ("FREE_API", "REQUIRED", "FREE"),
        AlignmentRequestMode.MANUAL_UI: ("MANUAL_UI", "FORBIDDEN", "MANUAL"),
    }[mode]
    actual = (
        capability.mode,
        capability.network_access,
        capability.license_class,
    )
    if actual != expected:
        _mode_capability_reject("/adapter_capability/mode")
    if capability.language_tag != narration_document.language:
        _mode_capability_reject("/adapter_capability/language_tag")
    if capability.media_type != "audio/wav":
        _mode_capability_reject("/adapter_capability/media_type")
    decoded = audio_artifact.decoded_metadata
    if (
        decoded.container != "WAVE"
        or decoded.codec != "PCM"
        or decoded.sample_format != "S16"
        or decoded.endianness != "LITTLE"
    ):
        _mode_capability_reject("/adapter_capability/media_type")


def _scan_sensitive_data(value: Any) -> None:
    seen: set[int] = set()

    def scan(item: Any, pointer: str) -> None:
        identity = id(item)
        if isinstance(item, (Mapping, Sequence)) and not isinstance(
            item,
            (str, bytes, bytearray),
        ):
            if identity in seen:
                _sensitive_reject()
            seen.add(identity)
        if isinstance(item, Mapping):
            try:
                keys = list(item.keys())
            except Exception:
                _sensitive_reject()
            for key in sorted(keys, key=lambda raw: raw if type(raw) is str else ""):
                if type(key) is not str:
                    _sensitive_reject()
                if _sensitive_key_violates(key):
                    _sensitive_reject()
                try:
                    nested = item[key]
                except Exception:
                    _sensitive_reject()
                scan(nested, pointer + "/" + key if pointer != "/" else "/" + key)
            seen.discard(identity)
            return
        if isinstance(item, Sequence) and not isinstance(
            item,
            (str, bytes, bytearray),
        ):
            for index, nested in enumerate(item):
                scan(nested, f"{pointer}/{index}")
            seen.discard(identity)
            return
        if type(item) is str and _sensitive_string_violates(item):
            _sensitive_reject()

    scan(value, "/")


def _identity_projection(
    data: _ParsedAlignmentRequest,
    *,
    mode: AlignmentRequestMode,
    capability: AdapterCapability,
    transcript: CanonicalTranscriptReference | None,
) -> dict[str, Any]:
    return {
        "adapter_capability": _capability_to_dict(capability),
        "audio_artifact_hash": data.audio_artifact_hash,
        "audio_artifact_id": data.audio_artifact_id,
        "document_id": data.document_id,
        "hash_scope_version": data.hash_scope_version,
        "mode": mode.value,
        "narration_revision_hash": data.narration_revision_hash,
        "narration_revision_id": data.narration_revision_id,
        "project_id": data.project_id,
        "schema_version": data.schema_version,
        "temporal_raw_package_hash": data.temporal_raw_package_hash,
        "transcript_reference": (
            _transcript_to_dict(transcript) if transcript is not None else None
        ),
    }


def _full_envelope(value: AlignmentRequest) -> dict[str, Any]:
    return {
        "adapter_capability": _capability_to_dict(value.adapter_capability),
        "alignment_request_hash": value.alignment_request_hash,
        "alignment_request_id": value.alignment_request_id,
        "audio_artifact_hash": value.audio_artifact_hash,
        "audio_artifact_id": value.audio_artifact_id,
        "document_id": value.document_id,
        "hash_scope_version": value.hash_scope_version,
        "mode": value.mode.value,
        "narration_revision_hash": value.narration_revision_hash,
        "narration_revision_id": value.narration_revision_id,
        "project_id": value.project_id,
        "schema_version": value.schema_version,
        "temporal_raw_package_hash": value.temporal_raw_package_hash,
        "transcript_reference": (
            _transcript_to_dict(value.transcript_reference)
            if value.transcript_reference is not None
            else None
        ),
    }


def _reject_alignment_request(
    pointer: str,
    reason: AlignmentRequestRejectionReason,
    message: str,
    issue_code: str | None,
) -> None:
    raise AlignmentRequestContractError(
        pointer,
        reason,
        message,
        issue_code=issue_code,
    )


def _require_mapping(value: Any, pointer: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _reject_alignment_request(
            pointer,
            AlignmentRequestRejectionReason.STRUCTURE_INVALID,
            "Expected an object.",
            "ALIGNMENT_REQUEST_WIRE_INVALID",
        )
    try:
        if any(type(key) is not str for key in value.keys()):
            _reject_alignment_request(
                pointer,
                AlignmentRequestRejectionReason.STRUCTURE_INVALID,
                "Object keys must be exact built-in strings.",
                "ALIGNMENT_REQUEST_WIRE_INVALID",
            )
    except AlignmentRequestContractError:
        raise
    except Exception:
        _reject_alignment_request(
            pointer,
            AlignmentRequestRejectionReason.STRUCTURE_INVALID,
            "Object keys are invalid.",
            "ALIGNMENT_REQUEST_WIRE_INVALID",
        )
    return value


def _mapping_keys(data: Mapping[str, Any], pointer: str) -> set[str]:
    try:
        keys = set(data.keys())
    except Exception:
        _reject_alignment_request(
            pointer,
            AlignmentRequestRejectionReason.STRUCTURE_INVALID,
            "Object keys are invalid.",
            "ALIGNMENT_REQUEST_WIRE_INVALID",
        )
    if any(type(key) is not str for key in keys):
        _reject_alignment_request(
            pointer,
            AlignmentRequestRejectionReason.STRUCTURE_INVALID,
            "Object keys must be exact built-in strings.",
            "ALIGNMENT_REQUEST_WIRE_INVALID",
        )
    return keys


def _mapping_get(data: Mapping[str, Any], key: str, pointer: str) -> Any:
    try:
        return data[key]
    except KeyError:
        _reject_alignment_request(
            pointer,
            AlignmentRequestRejectionReason.STRUCTURE_INVALID,
            "Required field is missing.",
            "ALIGNMENT_REQUEST_WIRE_INVALID",
        )
    except Exception:
        _reject_alignment_request(
            pointer,
            AlignmentRequestRejectionReason.STRUCTURE_INVALID,
            "Field access failed.",
            "ALIGNMENT_REQUEST_WIRE_INVALID",
        )


def _require_exact_nfc_string(
    value: Any,
    pointer: str,
    reason: AlignmentRequestRejectionReason,
    issue_code: str,
) -> str:
    if type(value) is not str:
        _reject_alignment_request(
            pointer,
            reason,
            "Expected an exact built-in string.",
            issue_code,
        )
    _validate_unicode(value, pointer, reason, issue_code)
    if unicodedata.normalize("NFC", value) != value:
        _reject_alignment_request(
            pointer,
            reason,
            "String must be NFC.",
            issue_code,
        )
    return value


def _validate_unicode(
    value: str,
    pointer: str,
    reason: AlignmentRequestRejectionReason,
    issue_code: str,
) -> None:
    for character in value:
        codepoint = ord(character)
        if (
            0xD800 <= codepoint <= 0xDFFF
            or 0xFDD0 <= codepoint <= 0xFDEF
            or codepoint & 0xFFFF in {0xFFFE, 0xFFFF}
        ):
            _reject_alignment_request(
                pointer,
                reason,
                "Unicode surrogate/noncharacter is forbidden.",
                issue_code,
            )


def _require_stable_id_for_content(value: str, pointer: str) -> None:
    if _STABLE_ID_PATTERN.fullmatch(value) is None:
        _transcript_reject(pointer)


def _require_hash_for_content(value: str, pointer: str) -> None:
    if _HASH_PATTERN.fullmatch(value) is None:
        _transcript_reject(pointer)


def _capability_reject(pointer: str) -> None:
    _reject_alignment_request(
        pointer,
        AlignmentRequestRejectionReason.CAPABILITY_INVALID,
        "Adapter capability is invalid.",
        "ALIGNMENT_REQUEST_CAPABILITY_INVALID",
    )


def _transcript_reject(pointer: str) -> None:
    _reject_alignment_request(
        pointer,
        AlignmentRequestRejectionReason.TRANSCRIPT_INVALID,
        "Transcript reference is invalid.",
        "ALIGNMENT_REQUEST_TRANSCRIPT_INVALID",
    )


def _lineage_reject(pointer: str) -> None:
    _reject_alignment_request(
        pointer,
        AlignmentRequestRejectionReason.LINEAGE_MISMATCH,
        "Alignment request lineage binding failed.",
        "ALIGNMENT_REQUEST_LINEAGE_MISMATCH",
    )


def _mode_capability_reject(pointer: str) -> None:
    _reject_alignment_request(
        pointer,
        AlignmentRequestRejectionReason.MODE_CAPABILITY_MISMATCH,
        "Alignment request mode and adapter capability are incompatible.",
        "ALIGNMENT_REQUEST_MODE_CAPABILITY_MISMATCH",
    )


def _sensitive_reject() -> None:
    _reject_alignment_request(
        "/",
        AlignmentRequestRejectionReason.SENSITIVE_DATA,
        "Alignment request contains forbidden sensitive input material.",
        "ALIGNMENT_REQUEST_SENSITIVE_DATA",
    )


def _first_sorted(values: set[str]) -> str:
    return sorted(values)[0]


def _sensitive_key_violates(key: str) -> bool:
    local_name = key.rsplit("/", 1)[-1]
    normalized = "".join(
        chr(ord(character) + 32) if "A" <= character <= "Z" else character
        for character in local_name
    )
    return normalized in _SENSITIVE_LOCAL_NAMES or _sensitive_string_violates(key)


def _sensitive_string_violates(value: str) -> bool:
    return (
        "://" in value
        or value.startswith("/")
        or value.startswith("\\")
        or _DRIVE_PREFIX_PATTERN.match(value) is not None
        or any(
            ord(character) == 0
            or ord(character) < 0x20
            or ord(character) == 0x7F
            for character in value
        )
    )


def _capability_to_dict(value: AdapterCapability) -> dict[str, Any]:
    return {
        "adapter_id": value.adapter_id,
        "adapter_version": value.adapter_version,
        "confidence_output": value.confidence_output,
        "language_tag": value.language_tag,
        "license_class": value.license_class,
        "media_type": value.media_type,
        "mode": value.mode,
        "network_access": value.network_access,
        "schema_version": value.schema_version,
    }


def _transcript_to_dict(
    value: CanonicalTranscriptReference,
) -> dict[str, Any]:
    return {
        "narration_revision_hash": value.narration_revision_hash,
        "narration_revision_id": value.narration_revision_id,
        "text_scope": value.text_scope,
    }
