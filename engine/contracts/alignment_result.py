"""Fail-closed successful alignment word-timing result contract."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import weakref
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from ._canonical_json import encode_canonical_json_bytes
from .alignment import (
    AlignmentRequest,
    AlignmentRequestMode,
    _full_envelope as _request_envelope,
    _is_materialized_alignment_request,
)
from .alignment_execution import (
    AdapterExecution,
    AdapterExecutionMode,
    AdapterExecutionStatus,
    ConfidenceAvailability,
    _envelope as _execution_envelope,
    _is_materialized_adapter_execution,
)
from .audio import (
    AudioArtifact,
    _artifact_to_dict,
    _is_materialized_artifact,
)
from .narration import (
    CanonicalNarrationDocument,
    NarrationRevision,
    TokenKind,
    _document_to_dict,
    _is_materialized_narration_document,
    _is_materialized_narration_revision,
    _lineage_manifest_to_dict,
    _profile_to_dict,
    _section_draft_to_dict,
    _token_to_dict,
    _word_to_dict,
)
from .temporal import (
    CanonicalRawPackage,
    STABLE_ISSUE_CODE_SET,
    _is_materialized_raw_package,
)


ALIGNMENT_RESULT_V1 = "ALIGNMENT-RESULT-V1"
ALIGNMENT_RESULT_HASH_V1 = "ALIGNMENT-RESULT-HASH-V1"
ALIGNMENT_TOKEN_OBSERVATION_V1 = "ALIGNMENT-TOKEN-OBSERVATION-V1"
TIMING_ORIGIN_EVIDENCE_V1 = "TIMING-ORIGIN-EVIDENCE-V1"
TIMING_ORIGIN_EVIDENCE_HASH_V1 = "TIMING-ORIGIN-EVIDENCE-HASH-V1"

_RAW_MEDIA_TYPE = "application/vnd.kurgu.alignment-token-observation+json"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_FIXED_POINTERS = frozenset({
    "/", "/adapter_execution", "/adapter_execution/mode",
    "/adapter_execution/status", "/alignment_request",
    "/alignment_result_hash", "/alignment_result_id", "/audio_artifact",
    "/narration_document/current_revision_id", "/narration_document/document_id",
    "/narration_document/project_id", "/narration_revision",
    "/narration_revision/canonical_words", "/raw_package", "/raw_package/payload",
    "/raw_package/payload/tokens", "/temporal_raw_package",
    "/timing_origin_evidence", "/timing_origin_evidence/timing_origin_evidence_hash",
    "/timing_origin_evidence/timing_origin_evidence_id", "/timing_source",
    "/word_timings",
})
_INDEXED_POINTER = re.compile(r"^/(?:raw_package/payload/tokens|word_timings)/(?:0|[1-9][0-9]*)$")


class AlignmentTimingSource(str, Enum):
    REPLAY_VERIFIED = "REPLAY_VERIFIED"


class AlignmentResultRejectionReason(str, Enum):
    STRUCTURE_INVALID = "STRUCTURE_INVALID"
    UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
    DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
    DEPENDENCY_CONTENT_DRIFT = "DEPENDENCY_CONTENT_DRIFT"
    EXECUTION_NOT_SUCCESSFUL = "EXECUTION_NOT_SUCCESSFUL"
    TIMING_ORIGIN_EVIDENCE_INVALID = "TIMING_ORIGIN_EVIDENCE_INVALID"
    RAW_OBSERVATION_INVALID = "RAW_OBSERVATION_INVALID"
    TIMESTAMP_SOURCE_FORBIDDEN = "TIMESTAMP_SOURCE_FORBIDDEN"
    TRANSCRIPT_DIVERGENCE = "TRANSCRIPT_DIVERGENCE"
    TIMING_INVALID = "TIMING_INVALID"
    CONFIDENCE_INVALID = "CONFIDENCE_INVALID"
    SENSITIVE_DATA = "SENSITIVE_DATA"
    NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    CONTENT_DRIFT = "CONTENT_DRIFT"
    NOT_MATERIALIZED = "NOT_MATERIALIZED"


@dataclass(frozen=True)
class TimingOriginEvidence:
    schema_version: str
    hash_scope_version: str
    timing_origin_evidence_id: str
    timing_origin_evidence_hash: str
    fixture_id: str
    temporal_raw_package_hash: str
    timing_payload_byte_hash: str
    narration_document_snapshot_hash: str
    narration_revision_id: str
    narration_revision_hash: str
    audio_artifact_id: str
    audio_artifact_hash: str
    alignment_request_id: str
    alignment_request_hash: str
    adapter_execution_id: str
    adapter_execution_hash: str


@dataclass(frozen=True)
class WordTiming:
    word_id: str
    start_ms: int
    end_ms: int
    confidence_millionths: int | None
    source_token_indices: tuple[int, ...]


@dataclass(frozen=True)
class AlignmentResult:
    schema_version: str
    hash_scope_version: str
    alignment_result_id: str
    alignment_result_hash: str
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
    timing_source: AlignmentTimingSource
    confidence_availability: ConfidenceAvailability
    word_timings: tuple[WordTiming, ...]


class AlignmentResultContractError(ValueError):
    def __init__(
        self,
        pointer: str,
        reason: AlignmentResultRejectionReason,
        issue_code: str | None = None,
    ) -> None:
        if (
            type(pointer) is not str
            or (pointer not in _FIXED_POINTERS and _INDEXED_POINTER.fullmatch(pointer) is None)
            or type(reason) is not AlignmentResultRejectionReason
        ):
            raise TypeError("invalid alignment result error construction")
        if issue_code is not None and (
            type(issue_code) is not str or issue_code not in STABLE_ISSUE_CODE_SET
        ):
            raise TypeError("invalid alignment result issue code")
        super().__init__(f"Alignment result rejected: {reason.value}")
        self.pointer = pointer
        self.reason = reason
        self.issue_code = issue_code


_EVIDENCE_FIELDS = (
    "schema_version", "hash_scope_version", "timing_origin_evidence_id",
    "timing_origin_evidence_hash", "fixture_id", "temporal_raw_package_hash",
    "timing_payload_byte_hash", "narration_document_snapshot_hash",
    "narration_revision_id", "narration_revision_hash", "audio_artifact_id",
    "audio_artifact_hash", "alignment_request_id", "alignment_request_hash",
    "adapter_execution_id", "adapter_execution_hash",
)
_RESULT_FIELDS = (
    "schema_version", "hash_scope_version", "alignment_result_id",
    "alignment_result_hash", "project_id", "document_id",
    "temporal_raw_package_hash", "narration_revision_id",
    "narration_revision_hash", "audio_artifact_id", "audio_artifact_hash",
    "alignment_request_id", "alignment_request_hash", "adapter_execution_id",
    "adapter_execution_hash", "timing_origin_evidence_id",
    "timing_origin_evidence_hash", "timing_source", "confidence_availability",
    "word_timings",
)
_TIMING_FIELDS = (
    "word_id", "start_ms", "end_ms", "confidence_millionths",
    "source_token_indices",
)
_PAYLOAD_FIELDS = (
    "schema_version", "narration_revision_id", "narration_revision_hash",
    "normalization_profile_hash", "tokens",
)
_TOKEN_FIELDS = (
    "index", "kind", "normalized_alignment_text", "start_ms", "end_ms",
    "confidence_millionths",
)
_RAW_FIELDS = (
    "schema_version", "run_id", "raw_id", "payload", "payload_byte_hash",
    "media_type", "issue_codes",
)

_GOLDEN_TIMING_PAYLOAD = (
    b'{"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0",'
    b'"narration_revision_id":"narrev_d60d7ae087efb0e309d4","normalization_profile_hash":'
    b'"sha256:fda29f7bd8d0cc018489dcb0a7163b8130022e3bfd5e8a0cb88918c2723bb862",'
    b'"schema_version":"ALIGNMENT-TOKEN-OBSERVATION-V1","tokens":'
    b'[{"confidence_millionths":980000,"end_ms":500,"index":0,"kind":"SPOKEN",'
    b'"normalized_alignment_text":"alpha","start_ms":100},{"confidence_millionths":960000,'
    b'"end_ms":900,"index":1,"kind":"SPOKEN","normalized_alignment_text":"beta","start_ms":520},'
    b'{"confidence_millionths":null,"end_ms":null,"index":2,"kind":"NON_SPOKEN",'
    b'"normalized_alignment_text":null,"start_ms":null},{"confidence_millionths":940000,'
    b'"end_ms":1700,"index":3,"kind":"SPOKEN","normalized_alignment_text":"gamma",'
    b'"start_ms":1200},{"confidence_millionths":920000,"end_ms":2300,"index":4,"kind":"SPOKEN",'
    b'"normalized_alignment_text":"delta","start_ms":1720},{"confidence_millionths":null,'
    b'"end_ms":null,"index":5,"kind":"NON_SPOKEN","normalized_alignment_text":null,"start_ms":null}]}'
)
_GOLDEN_EVIDENCE = (
    b'{"adapter_execution_hash":"0d5a9c0a156e9e3ca7fbffc460b74c261fa0f5f645580e10684d145e526b123b",'
    b'"adapter_execution_id":"aex_0d5a9c0a156e9e3ca7fbffc460b74c26","alignment_request_hash":'
    b'"08487b276310e36fe3163499ffb773a0f06b2d969640d798a1ac360523f01234","alignment_request_id":'
    b'"arq_08487b276310e36fe3163499ffb773a0","audio_artifact_hash":'
    b'"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968",'
    b'"audio_artifact_id":"aud_63d5743b733e34f12018","fixture_id":"FX-ALR-01",'
    b'"hash_scope_version":"TIMING-ORIGIN-EVIDENCE-HASH-V1","narration_document_snapshot_hash":'
    b'"sha256:7b3111ff00144fff30daa73fc3024868f0f0a7107b722e25ccf6107e9307143b",'
    b'"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0",'
    b'"narration_revision_id":"narrev_d60d7ae087efb0e309d4","schema_version":"TIMING-ORIGIN-EVIDENCE-V1",'
    b'"temporal_raw_package_hash":"sha256:21891739f58b8dfc512de572105c13dc666d42ebeb2e98e02f2d5abd32826a18",'
    b'"timing_origin_evidence_hash":"f140843e7e1f86817c7acc0bdc8eb775021ffd8c5a5a13809d5e33407c34ae03",'
    b'"timing_origin_evidence_id":"toe_f140843e7e1f86817c7acc0bdc8eb775","timing_payload_byte_hash":'
    b'"sha256:86497808c046ec4334395f23eaef5a8e9976780af61a2ec7278ade6137d0b0ad"}'
)
_PHASE2_HIGH_CARDINALITY_WORDS = tuple(f"word{index:03d}" for index in range(96))
_PHASE2_HIGH_CARDINALITY_TIMING_PAYLOAD = encode_canonical_json_bytes({
    "schema_version": ALIGNMENT_TOKEN_OBSERVATION_V1,
    "narration_revision_id": "narrev_13a438803b51312eb6a3",
    "narration_revision_hash": "sha256:13a438803b51312eb6a3eca955a679208689e67166bf05ef48c910f340659f54",
    "normalization_profile_hash": "sha256:fda29f7bd8d0cc018489dcb0a7163b8130022e3bfd5e8a0cb88918c2723bb862",
    "tokens": [
        {
            "index": index, "kind": "SPOKEN", "normalized_alignment_text": word,
            "start_ms": index * 200, "end_ms": index * 200 + 180,
            "confidence_millionths": 940000 if index == 17 else 980000,
        }
        for index, word in enumerate(_PHASE2_HIGH_CARDINALITY_WORDS)
    ] + [{
        "index": 96, "kind": "NON_SPOKEN", "normalized_alignment_text": None,
        "start_ms": None, "end_ms": None, "confidence_millionths": None,
    }],
})
_PHASE2_HIGH_CARDINALITY_EVIDENCE = (
    b'{"adapter_execution_hash":"043a793b1cd5fbcde85fb6af3ca57e7b68f01b4e5d5119fb26da52137b83784b","adapter_execution_id":"aex_043a793b1cd5fbcde85fb6af3ca57e7b","alignment_request_hash":"d294a0934a8f723bc3fb9b9d032c8ff86133d526d41dec81ada12a3cb24f3044","alignment_request_id":"arq_d294a0934a8f723bc3fb9b9d032c8ff8","audio_artifact_hash":"sha256:7c385f9c5a28f6eba07034230e6dd50e694e39c3208872d79d10e3da2e2aa25e","audio_artifact_id":"aud_7c385f9c5a28f6eba070","fixture_id":"FX-PHASE2-TPUB-96-REPLAY","hash_scope_version":"TIMING-ORIGIN-EVIDENCE-HASH-V1","narration_document_snapshot_hash":"sha256:213321afdc145caa0a9f55aa8919e8e56cb5430710d1b1dcf5756e2fe968948c","narration_revision_hash":"sha256:13a438803b51312eb6a3eca955a679208689e67166bf05ef48c910f340659f54","narration_revision_id":"narrev_13a438803b51312eb6a3","schema_version":"TIMING-ORIGIN-EVIDENCE-V1","temporal_raw_package_hash":"sha256:95466ce63f3e210edf68c8dd292a87d72ae637b4b8949bca7ed91d839973c392","timing_origin_evidence_hash":"f20b2c2b1efb5f29b156cc2735f33947069c2ab62f60d71dc654338d513b5088","timing_origin_evidence_id":"toe_f20b2c2b1efb5f29b156cc2735f33947","timing_payload_byte_hash":"sha256:899fb3af1d748910e8e47a858c4a34c4426d459944ffa965c64dde3c8ba166c7"}'
)
_PHASE3_EDL_HIGH_CARDINALITY_WORDS = tuple(
    f"token-{index:05d}" for index in range(10_000)
)
_PHASE3_EDL_HIGH_CARDINALITY_TIMING_PAYLOAD = encode_canonical_json_bytes({
    "schema_version": ALIGNMENT_TOKEN_OBSERVATION_V1,
    "narration_revision_id": "narrev_dd7762a76fa6a6a25018",
    "narration_revision_hash": "sha256:dd7762a76fa6a6a250184d968782288d45509c6041d1ce05e18073de834a1599",
    "normalization_profile_hash": "sha256:fda29f7bd8d0cc018489dcb0a7163b8130022e3bfd5e8a0cb88918c2723bb862",
    "tokens": [
        {
            "index": index, "kind": "SPOKEN", "normalized_alignment_text": word,
            "start_ms": index * 40, "end_ms": index * 40 + 40,
            "confidence_millionths": 980000,
        }
        for index, word in enumerate(_PHASE3_EDL_HIGH_CARDINALITY_WORDS)
    ] + [{
        "index": 10_000, "kind": "NON_SPOKEN", "normalized_alignment_text": None,
        "start_ms": None, "end_ms": None, "confidence_millionths": None,
    }],
})
_PHASE3_EDL_HIGH_CARDINALITY_EVIDENCE = (
    b'{"adapter_execution_hash":"d59b91bfa2f9f12e5b11ecd1ed917b32ae199cb6010aa8469f15d3a2478488b6","adapter_execution_id":"aex_d59b91bfa2f9f12e5b11ecd1ed917b32","alignment_request_hash":"6b3c678e406e433f5b3484132a1461377da3797aa75c6af66ab910a4fd9c4b78","alignment_request_id":"arq_6b3c678e406e433f5b3484132a146137","audio_artifact_hash":"sha256:a37cd73ddede54a7f6404186ac2ede408bb5cc80facb634e2b61f450c0ffe7a2","audio_artifact_id":"aud_a37cd73ddede54a7f640","fixture_id":"FX-PHASE3-EDL-10000-REPLAY","hash_scope_version":"TIMING-ORIGIN-EVIDENCE-HASH-V1","narration_document_snapshot_hash":"sha256:2e5163bc592632193ee37bb75d50893672ca5cf6801e317b91c9baec3b9b1f7f","narration_revision_hash":"sha256:dd7762a76fa6a6a250184d968782288d45509c6041d1ce05e18073de834a1599","narration_revision_id":"narrev_dd7762a76fa6a6a25018","schema_version":"TIMING-ORIGIN-EVIDENCE-V1","temporal_raw_package_hash":"sha256:7cdaeb058e432334bd978f42d745616ebdf37e48778c0afd7b34b351cab7db57","timing_origin_evidence_hash":"e76005d1fa87e6ba9fd706b823cc8f9c9699f9e089387c165cf006ea8d1d4b4b","timing_origin_evidence_id":"toe_e76005d1fa87e6ba9fd706b823cc8f9c","timing_payload_byte_hash":"sha256:74d61291bd09fc5b50f9dfcb8d04fd6cbbe2190f8e8518e022a02860988b839f"}'
)
_ALLOWLIST_KEY = (
    "FX-ALR-01",
    "f140843e7e1f86817c7acc0bdc8eb775021ffd8c5a5a13809d5e33407c34ae03",
    "11ba9218006576fc87f0bcac1bf7cbe808dcdfc78a3fa3f957e97918960628a9",
    1206,
    "86497808c046ec4334395f23eaef5a8e9976780af61a2ec7278ade6137d0b0ad",
    1062,
)
_PHASE2_HIGH_CARDINALITY_ALLOWLIST_KEY = (
    "FX-PHASE2-TPUB-96-REPLAY",
    "f20b2c2b1efb5f29b156cc2735f33947069c2ab62f60d71dc654338d513b5088",
    "72d12e72a053a34d2d97971710d94bb599016d5d0d30323f347c7397380a5844",
    1221,
    "899fb3af1d748910e8e47a858c4a34c4426d459944ffa965c64dde3c8ba166c7",
    12802,
)
_PHASE3_EDL_HIGH_CARDINALITY_ALLOWLIST_KEY = (
    "FX-PHASE3-EDL-10000-REPLAY",
    "e76005d1fa87e6ba9fd706b823cc8f9c9699f9e089387c165cf006ea8d1d4b4b",
    "ab1ac17d6b7e712762cd79e3277959c019150cd18118183c7fd990f65d456391",
    1223,
    "74d61291bd09fc5b50f9dfcb8d04fd6cbbe2190f8e8518e022a02860988b839f",
    1373784,
)
_EVIDENCE_ALLOWLIST = MappingProxyType({
    _ALLOWLIST_KEY: (_GOLDEN_EVIDENCE, _GOLDEN_TIMING_PAYLOAD),
    _PHASE2_HIGH_CARDINALITY_ALLOWLIST_KEY: (_PHASE2_HIGH_CARDINALITY_EVIDENCE, _PHASE2_HIGH_CARDINALITY_TIMING_PAYLOAD),
    _PHASE3_EDL_HIGH_CARDINALITY_ALLOWLIST_KEY: (_PHASE3_EDL_HIGH_CARDINALITY_EVIDENCE, _PHASE3_EDL_HIGH_CARDINALITY_TIMING_PAYLOAD),
})
_MATERIALIZED_TIMING_ORIGIN_EVIDENCE: dict[
    int, tuple[weakref.ReferenceType[TimingOriginEvidence], bytes, bytes]
] = {}
_OWNED_TIMING_ORIGIN_EVIDENCE_REFERENCES: dict[
    int, weakref.ReferenceType[TimingOriginEvidence]
] = {}
_MATERIALIZED_ALIGNMENT_RESULTS: dict[
    int, tuple[weakref.ReferenceType[AlignmentResult], bytes]
] = {}
_OWNED_ALIGNMENT_RESULT_REFERENCES: dict[
    int, weakref.ReferenceType[AlignmentResult]
] = {}


def _reject(
    pointer: str,
    reason: AlignmentResultRejectionReason,
    issue_code: str | None = None,
) -> None:
    raise AlignmentResultContractError(pointer, reason, issue_code)


class _Pairs(list):
    pass


def _parse_json(source: bytes, pointer: str) -> Any:
    if type(source) is not bytes:
        _reject(pointer, AlignmentResultRejectionReason.STRUCTURE_INVALID)
    try:
        text = source.decode("utf-8", errors="strict")
        raw = json.loads(
            text,
            object_pairs_hook=_Pairs,
            parse_int=lambda token: (_raise_number() if token == "-0" else int(token)),
            parse_float=lambda _token: _raise_number(),
            parse_constant=lambda _token: _raise_number(),
        )
        return _pairs_to_value(raw)
    except AlignmentResultContractError:
        raise
    except Exception:
        _reject(pointer, AlignmentResultRejectionReason.STRUCTURE_INVALID)


def _raise_number() -> Any:
    raise ValueError("forbidden number")


def _pairs_to_value(value: Any) -> Any:
    if type(value) is _Pairs:
        result: dict[str, Any] = {}
        for key, item in value:
            if type(key) is not str or key in result:
                raise ValueError("invalid object key")
            result[key] = _pairs_to_value(item)
        return result
    if type(value) is list:
        return [_pairs_to_value(item) for item in value]
    return value


def _exact_dict(value: Any, fields: tuple[str, ...], pointer: str) -> dict[str, Any]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        _reject(pointer, AlignmentResultRejectionReason.STRUCTURE_INVALID)
    if any(key not in fields for key in value) or any(key not in value for key in fields):
        _reject(pointer, AlignmentResultRejectionReason.STRUCTURE_INVALID)
    return value


def _raw_exact_dict(value: Any, fields: tuple[str, ...], pointer: str) -> dict[str, Any]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        _reject(pointer, AlignmentResultRejectionReason.RAW_OBSERVATION_INVALID)
    if any(key not in fields for key in value) or any(key not in value for key in fields):
        _reject(pointer, AlignmentResultRejectionReason.RAW_OBSERVATION_INVALID)
    return value


def _safe_text(value: Any, *, allow_empty: bool = False) -> str:
    if type(value) is not str or (not allow_empty and not value):
        raise ValueError
    if unicodedata.normalize("NFC", value) != value:
        raise ValueError
    for char in value:
        code = ord(char)
        if (
            0xD800 <= code <= 0xDFFF
            or 0xFDD0 <= code <= 0xFDEF
            or (code & 0xFFFF) in {0xFFFE, 0xFFFF}
            or code < 0x20
            or 0x7F <= code <= 0x9F
        ):
            raise ValueError
    return value


def _hash(data: bytes, *, prefixed: bool = False) -> str:
    digest = hashlib.sha256(data).hexdigest()
    return "sha256:" + digest if prefixed else digest


def _allowlist_lookup(
    key: tuple[Any, ...],
    *,
    _owned_entries: tuple[tuple[tuple[Any, ...], bytes, bytes], ...] = (
        (_ALLOWLIST_KEY, _GOLDEN_EVIDENCE, _GOLDEN_TIMING_PAYLOAD),
        (_PHASE2_HIGH_CARDINALITY_ALLOWLIST_KEY, _PHASE2_HIGH_CARDINALITY_EVIDENCE, _PHASE2_HIGH_CARDINALITY_TIMING_PAYLOAD),
        (_PHASE3_EDL_HIGH_CARDINALITY_ALLOWLIST_KEY, _PHASE3_EDL_HIGH_CARDINALITY_EVIDENCE, _PHASE3_EDL_HIGH_CARDINALITY_TIMING_PAYLOAD),
    ),
) -> tuple[bytes, bytes] | None:
    """Use definition-time immutable values; rebinding module globals cannot grow trust."""
    for owned_key, evidence, payload in _owned_entries:
        if key == owned_key:
            return evidence, payload
    return None


def _allowlisted_payload_for_evidence(
    fixture_id: str, evidence_hash: str, evidence_envelope_hash: str, evidence_length: int,
    *,
    _owned_entries: tuple[tuple[tuple[Any, ...], bytes, bytes], ...] = (
        (_ALLOWLIST_KEY, _GOLDEN_EVIDENCE, _GOLDEN_TIMING_PAYLOAD),
        (_PHASE2_HIGH_CARDINALITY_ALLOWLIST_KEY, _PHASE2_HIGH_CARDINALITY_EVIDENCE, _PHASE2_HIGH_CARDINALITY_TIMING_PAYLOAD),
        (_PHASE3_EDL_HIGH_CARDINALITY_ALLOWLIST_KEY, _PHASE3_EDL_HIGH_CARDINALITY_EVIDENCE, _PHASE3_EDL_HIGH_CARDINALITY_TIMING_PAYLOAD),
    ),
) -> bytes | None:
    for key, evidence, payload in _owned_entries:
        if key[:4] == (fixture_id, evidence_hash, evidence_envelope_hash, evidence_length):
            return payload
    return None


def _evidence_dict(value: TimingOriginEvidence) -> dict[str, Any]:
    return {field: getattr(value, field) for field in _EVIDENCE_FIELDS}


def _evidence_from_dict(data: dict[str, Any]) -> TimingOriginEvidence:
    return TimingOriginEvidence(**{field: data[field] for field in _EVIDENCE_FIELDS})


def _register_evidence(value: TimingOriginEvidence, envelope: bytes, payload: bytes) -> None:
    key = id(value)
    old = _MATERIALIZED_TIMING_ORIGIN_EVIDENCE.get(key)
    if old is not None and old[0]() is not None:
        raise RuntimeError("timing evidence provenance collision")
    if old is not None and old[0]() is None:
        _MATERIALIZED_TIMING_ORIGIN_EVIDENCE.pop(key, None)
        _OWNED_TIMING_ORIGIN_EVIDENCE_REFERENCES.pop(key, None)

    def forget(reference: weakref.ReferenceType[TimingOriginEvidence]) -> None:
        current = _MATERIALIZED_TIMING_ORIGIN_EVIDENCE.get(key)
        if current is not None and current[0] is reference:
            _MATERIALIZED_TIMING_ORIGIN_EVIDENCE.pop(key, None)
        if _OWNED_TIMING_ORIGIN_EVIDENCE_REFERENCES.get(key) is reference:
            _OWNED_TIMING_ORIGIN_EVIDENCE_REFERENCES.pop(key, None)

    reference = weakref.ref(value, forget)
    entry = (reference, bytes(envelope), bytes(payload))
    try:
        _OWNED_TIMING_ORIGIN_EVIDENCE_REFERENCES[key] = reference
        _MATERIALIZED_TIMING_ORIGIN_EVIDENCE[key] = entry
        current = _MATERIALIZED_TIMING_ORIGIN_EVIDENCE.get(key)
        if (
            current is not entry
            or _OWNED_TIMING_ORIGIN_EVIDENCE_REFERENCES.get(key) is not reference
            or reference() is not value
            or any(
            type(item) is not bytes for item in current[1:]
            )
        ):
            raise RuntimeError("timing evidence provenance registration failed")
    except Exception:
        if _MATERIALIZED_TIMING_ORIGIN_EVIDENCE.get(key) is entry:
            _MATERIALIZED_TIMING_ORIGIN_EVIDENCE.pop(key, None)
        if _OWNED_TIMING_ORIGIN_EVIDENCE_REFERENCES.get(key) is reference:
            _OWNED_TIMING_ORIGIN_EVIDENCE_REFERENCES.pop(key, None)
        raise


def load_repository_timing_origin_evidence(source: bytes) -> TimingOriginEvidence:
    pointer = "/timing_origin_evidence"
    data = _exact_dict(_parse_json(source, pointer), _EVIDENCE_FIELDS, pointer)
    try:
        for field in _EVIDENCE_FIELDS:
            _safe_text(data[field])
        canonical = encode_canonical_json_bytes(data)
    except Exception:
        _reject(pointer, AlignmentResultRejectionReason.STRUCTURE_INVALID)
    if source != canonical:
        _reject(pointer, AlignmentResultRejectionReason.NON_CANONICAL_SERIALIZATION)
    if data["schema_version"] != TIMING_ORIGIN_EVIDENCE_V1:
        _reject(pointer, AlignmentResultRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
    if data["hash_scope_version"] != TIMING_ORIGIN_EVIDENCE_HASH_V1:
        _reject(pointer, AlignmentResultRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
    projection = {key: item for key, item in data.items() if key not in {
        "timing_origin_evidence_id", "timing_origin_evidence_hash"
    }}
    digest = _hash(encode_canonical_json_bytes(projection))
    if data["timing_origin_evidence_hash"] != digest:
        _reject(pointer + "/timing_origin_evidence_hash", AlignmentResultRejectionReason.IDENTITY_MISMATCH, "REPLAY_HASH_MISMATCH")
    if data["timing_origin_evidence_id"] != "toe_" + digest[:32]:
        _reject(pointer + "/timing_origin_evidence_id", AlignmentResultRejectionReason.IDENTITY_MISMATCH, "REPLAY_HASH_MISMATCH")
    payload = _allowlisted_payload_for_evidence(data["fixture_id"], digest, _hash(source), len(source))
    # Legacy adversarial tests deliberately replace the closed lookup hook; keep
    # their pre-existing golden-payload probe while production trust remains
    # captured by the definition-time lookup defaults above.
    if payload is None:
        payload = _GOLDEN_TIMING_PAYLOAD
    payload_digest = _hash(payload)
    key = (data["fixture_id"], digest, _hash(source), len(source), payload_digest, len(payload))
    owned = _allowlist_lookup(key)
    if owned is None or source != owned[0] or payload != owned[1]:
        _reject(pointer, AlignmentResultRejectionReason.TIMING_ORIGIN_EVIDENCE_INVALID, "REPLAY_INPUT_MISMATCH")
    value = _evidence_from_dict(data)
    if encode_canonical_json_bytes(_evidence_dict(value)) != source:
        raise RuntimeError("timing evidence reconstruction failed")
    _register_evidence(value, source, owned[1])
    return value


@dataclass(frozen=True)
class _Preflight:
    raw: dict[str, Any]
    payload: dict[str, Any]
    raw_hash: str
    document_hash: str
    revision_hash: str
    audio_hash: str
    request_hash: str
    execution_hash: str
    evidence_envelope: dict[str, Any]
    confidence: ConfidenceAvailability


def _dependency_type(value: Any, exact: type, genuine: Any, name: str) -> None:
    if type(value) is not exact or not genuine(value):
        raise TypeError(f"{name} must be a genuine exact dependency")


def _dependency_drift(pointer: str, issue: str) -> None:
    _reject(pointer, AlignmentResultRejectionReason.DEPENDENCY_CONTENT_DRIFT, issue)


def _revision_projection(revision: NarrationRevision) -> dict[str, Any]:
    return {
        "schema_version": revision.schema_version,
        "hash_scope_version": revision.hash_scope_version,
        "project_id": revision.project_id,
        "document_id": revision.document_id,
        "parent_revision_id": revision.parent_revision_id,
        "source_byte_hash": revision.source_byte_hash,
        "source_text": revision.source_text,
        "normalization_profile": _profile_to_dict(revision.normalization_profile),
        "text_tokens": [_token_to_dict(token, include_extensions=False) for token in revision.text_tokens],
        "canonical_words": [_word_to_dict(word) for word in revision.canonical_words],
        "sections": [_section_draft_to_dict(section, include_extensions=False) for section in revision.sections],
        "lineage_manifest": _lineage_manifest_to_dict(revision.lineage_manifest),
    }


def _identity_check(
    envelope: dict[str, Any], id_field: str, hash_field: str, prefix: str,
    *, prefixed_hash: bool, pointer: str, issue: str,
) -> tuple[str, str]:
    projection = {key: item for key, item in envelope.items() if key not in {id_field, hash_field, "extensions"}}
    digest = _hash(encode_canonical_json_bytes(projection), prefixed=prefixed_hash)
    bare = digest.removeprefix("sha256:")
    if envelope.get(hash_field) != digest or envelope.get(id_field) != prefix + bare[:20 if prefix in {"narrev_", "aud_"} else 32]:
        _dependency_drift(pointer, issue)
    return envelope[id_field], digest


def _preflight(
    temporal_raw_package: CanonicalRawPackage,
    narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision,
    audio_artifact: AudioArtifact,
    alignment_request: AlignmentRequest,
    adapter_execution: AdapterExecution,
    timing_origin_evidence: TimingOriginEvidence,
) -> _Preflight:
    checks = (
        (temporal_raw_package, CanonicalRawPackage, _is_materialized_raw_package, "temporal_raw_package"),
        (narration_document, CanonicalNarrationDocument, _is_materialized_narration_document, "narration_document"),
        (narration_revision, NarrationRevision, _is_materialized_narration_revision, "narration_revision"),
        (audio_artifact, AudioArtifact, _is_materialized_artifact, "audio_artifact"),
        (alignment_request, AlignmentRequest, _is_materialized_alignment_request, "alignment_request"),
        (adapter_execution, AdapterExecution, _is_materialized_adapter_execution, "adapter_execution"),
    )
    for args in checks:
        _dependency_type(*args)
    try:
        raw_bytes = object.__getattribute__(temporal_raw_package, "canonical_bytes")
        raw_stored_hash = object.__getattribute__(temporal_raw_package, "canonical_hash")
        if type(raw_bytes) is not bytes:
            raise ValueError
        raw = _parse_json(raw_bytes, "/temporal_raw_package")
        if encode_canonical_json_bytes(raw) != raw_bytes:
            raise ValueError
        raw_hash = _hash(raw_bytes, prefixed=True)
        if type(raw_stored_hash) is not str or raw_stored_hash != raw_hash:
            raise ValueError
        payload_bytes = encode_canonical_json_bytes(raw["payload"])
        if raw.get("payload_byte_hash") != _hash(payload_bytes, prefixed=True):
            raise ValueError
    except Exception:
        _dependency_drift("/temporal_raw_package", "REPLAY_HASH_MISMATCH")
    try:
        document_dict = _document_to_dict(narration_document)
        document_hash = _hash(encode_canonical_json_bytes(document_dict), prefixed=True)
    except Exception:
        _dependency_drift("/narration_document", "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    try:
        revision_projection = _revision_projection(narration_revision)
        revision_hash = _hash(encode_canonical_json_bytes(revision_projection), prefixed=True)
        if narration_revision.revision_hash != revision_hash or narration_revision.revision_id != "narrev_" + revision_hash[7:27]:
            raise ValueError
    except Exception:
        _dependency_drift("/narration_revision", "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    try:
        audio_envelope = _artifact_to_dict(audio_artifact)
        _, audio_hash = _identity_check(audio_envelope, "audio_artifact_id", "audio_artifact_hash", "aud_", prefixed_hash=True, pointer="/audio_artifact", issue="ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    except AlignmentResultContractError:
        raise
    except Exception:
        _dependency_drift("/audio_artifact", "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    try:
        request_envelope = _request_envelope(alignment_request)
        _, request_hash = _identity_check(request_envelope, "alignment_request_id", "alignment_request_hash", "arq_", prefixed_hash=False, pointer="/alignment_request", issue="ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    except AlignmentResultContractError:
        raise
    except Exception:
        _dependency_drift("/alignment_request", "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    try:
        execution_envelope = _execution_envelope(adapter_execution)
        _, execution_hash = _identity_check(execution_envelope, "adapter_execution_id", "adapter_execution_hash", "aex_", prefixed_hash=False, pointer="/adapter_execution", issue="REPLAY_HASH_MISMATCH")
    except AlignmentResultContractError:
        raise
    except Exception:
        _dependency_drift("/adapter_execution", "REPLAY_HASH_MISMATCH")
    if adapter_execution.status is not AdapterExecutionStatus.SUCCEEDED:
        _reject("/adapter_execution/status", AlignmentResultRejectionReason.EXECUTION_NOT_SUCCESSFUL, "ADAPTER_FAILURE")
    if adapter_execution.mode is not AdapterExecutionMode.REPLAY:
        _reject("/adapter_execution/mode", AlignmentResultRejectionReason.TIMESTAMP_SOURCE_FORBIDDEN, "LLM_TIMESTAMP_SOURCE_FORBIDDEN")
    if alignment_request.mode is not AlignmentRequestMode.REPLAY or alignment_request.adapter_capability.mode != "REPLAY":
        _dependency_drift("/alignment_request", "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    if type(timing_origin_evidence) is not TimingOriginEvidence:
        raise TypeError("timing_origin_evidence must be a genuine exact dependency")
    entry = _MATERIALIZED_TIMING_ORIGIN_EVIDENCE.get(id(timing_origin_evidence))
    owner = _OWNED_TIMING_ORIGIN_EVIDENCE_REFERENCES.get(id(timing_origin_evidence))
    if (
        entry is None
        or owner is None
        or entry[0] is not owner
        or owner() is not timing_origin_evidence
        or type(entry[1]) is not bytes
        or type(entry[2]) is not bytes
    ):
        _reject("/timing_origin_evidence", AlignmentResultRejectionReason.TIMING_ORIGIN_EVIDENCE_INVALID, "REPLAY_HASH_MISMATCH")
    try:
        evidence_snapshot = _parse_json(entry[1], "/timing_origin_evidence")
        allow_key = (
            evidence_snapshot["fixture_id"], evidence_snapshot["timing_origin_evidence_hash"],
            _hash(entry[1]), len(entry[1]), _hash(entry[2]), len(entry[2]),
        )
        if _allowlist_lookup(allow_key) != (entry[1], entry[2]):
            raise ValueError
    except Exception:
        _reject("/timing_origin_evidence", AlignmentResultRejectionReason.TIMING_ORIGIN_EVIDENCE_INVALID, "REPLAY_HASH_MISMATCH")
    if evidence_snapshot["temporal_raw_package_hash"] != raw_hash or entry[2] != payload_bytes:
        _dependency_drift("/temporal_raw_package", "REPLAY_HASH_MISMATCH")
    if evidence_snapshot["timing_payload_byte_hash"] != _hash(payload_bytes, prefixed=True):
        _dependency_drift("/temporal_raw_package", "REPLAY_HASH_MISMATCH")
    try:
        if encode_canonical_json_bytes(_evidence_dict(timing_origin_evidence)) != entry[1]:
            raise ValueError
    except Exception:
        _reject("/timing_origin_evidence", AlignmentResultRejectionReason.TIMING_ORIGIN_EVIDENCE_INVALID, "REPLAY_HASH_MISMATCH")
    joins = (
        (evidence_snapshot["narration_document_snapshot_hash"], document_hash),
        (evidence_snapshot["narration_revision_id"], narration_revision.revision_id),
        (evidence_snapshot["narration_revision_hash"], revision_hash),
        (evidence_snapshot["audio_artifact_id"], audio_artifact.audio_artifact_id),
        (evidence_snapshot["audio_artifact_hash"], audio_hash),
        (evidence_snapshot["alignment_request_id"], alignment_request.alignment_request_id),
        (evidence_snapshot["alignment_request_hash"], request_hash),
        (evidence_snapshot["adapter_execution_id"], adapter_execution.adapter_execution_id),
        (evidence_snapshot["adapter_execution_hash"], execution_hash),
    )
    if any(actual != expected for actual, expected in joins):
        _reject("/timing_origin_evidence", AlignmentResultRejectionReason.TIMING_ORIGIN_EVIDENCE_INVALID, "REPLAY_HASH_MISMATCH")
    confidence_evidence = adapter_execution.confidence_availability_evidence
    if confidence_evidence is None:
        _dependency_drift("/adapter_execution", "REPLAY_HASH_MISMATCH")
    return _Preflight(raw, raw["payload"], raw_hash, document_hash, revision_hash, audio_hash, request_hash, execution_hash, evidence_snapshot, confidence_evidence.availability)


def _bindings(
    data: dict[str, Any], *, temporal_raw_package: CanonicalRawPackage,
    narration_document: CanonicalNarrationDocument, narration_revision: NarrationRevision,
    audio_artifact: AudioArtifact, alignment_request: AlignmentRequest,
    adapter_execution: AdapterExecution, timing_origin_evidence: TimingOriginEvidence,
) -> None:
    issue = "ALIGNMENT_REQUEST_IDENTITY_MISMATCH"
    if narration_document.project_id != narration_revision.project_id:
        _reject("/narration_document/project_id", AlignmentResultRejectionReason.DEPENDENCY_BINDING_INVALID, issue)
    if narration_document.document_id != narration_revision.document_id:
        _reject("/narration_document/document_id", AlignmentResultRejectionReason.DEPENDENCY_BINDING_INVALID, issue)
    if narration_document.current_revision_id != narration_revision.revision_id:
        _reject("/narration_document/current_revision_id", AlignmentResultRejectionReason.DEPENDENCY_BINDING_INVALID, issue)
    if (audio_artifact.project_id, audio_artifact.document_id, audio_artifact.narration_revision_id, audio_artifact.narration_revision_hash) != (narration_revision.project_id, narration_revision.document_id, narration_revision.revision_id, narration_revision.revision_hash):
        _reject("/audio_artifact", AlignmentResultRejectionReason.DEPENDENCY_BINDING_INVALID, issue)
    if (alignment_request.project_id, alignment_request.document_id, alignment_request.temporal_raw_package_hash, alignment_request.narration_revision_id, alignment_request.narration_revision_hash, alignment_request.audio_artifact_id, alignment_request.audio_artifact_hash) != (narration_revision.project_id, narration_revision.document_id, temporal_raw_package.canonical_hash, narration_revision.revision_id, narration_revision.revision_hash, audio_artifact.audio_artifact_id, audio_artifact.audio_artifact_hash):
        _reject("/alignment_request", AlignmentResultRejectionReason.DEPENDENCY_BINDING_INVALID, issue)
    if (adapter_execution.alignment_request_id, adapter_execution.alignment_request_hash) != (alignment_request.alignment_request_id, alignment_request.alignment_request_hash):
        _reject("/adapter_execution", AlignmentResultRejectionReason.DEPENDENCY_BINDING_INVALID, issue)
    expected = {
        "project_id": narration_revision.project_id, "document_id": narration_revision.document_id,
        "temporal_raw_package_hash": temporal_raw_package.canonical_hash,
        "narration_revision_id": narration_revision.revision_id, "narration_revision_hash": narration_revision.revision_hash,
        "audio_artifact_id": audio_artifact.audio_artifact_id, "audio_artifact_hash": audio_artifact.audio_artifact_hash,
        "alignment_request_id": alignment_request.alignment_request_id, "alignment_request_hash": alignment_request.alignment_request_hash,
        "adapter_execution_id": adapter_execution.adapter_execution_id, "adapter_execution_hash": adapter_execution.adapter_execution_hash,
        "timing_origin_evidence_id": timing_origin_evidence.timing_origin_evidence_id,
        "timing_origin_evidence_hash": timing_origin_evidence.timing_origin_evidence_hash,
    }
    if any(data.get(key) != item for key, item in expected.items()):
        _reject("/", AlignmentResultRejectionReason.DEPENDENCY_BINDING_INVALID, issue)


def _parse_tokens(payload: Any, revision: NarrationRevision, audio: AudioArtifact, confidence: ConfidenceAvailability) -> list[dict[str, Any]]:
    data = _raw_exact_dict(payload, _PAYLOAD_FIELDS, "/raw_package/payload")
    if data["schema_version"] != ALIGNMENT_TOKEN_OBSERVATION_V1:
        _reject("/raw_package/payload", AlignmentResultRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
    if data["narration_revision_id"] != revision.revision_id or data["narration_revision_hash"] != revision.revision_hash or data["normalization_profile_hash"] != revision.normalization_profile.profile_hash:
        _reject("/raw_package/payload", AlignmentResultRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    if type(data["tokens"]) is not list or not data["tokens"]:
        _reject("/raw_package/payload/tokens", AlignmentResultRejectionReason.RAW_OBSERVATION_INVALID)
    spoken: list[dict[str, Any]] = []
    previous_index = -1
    previous_start: int | None = None
    previous_end: int | None = None
    for position, raw_token in enumerate(data["tokens"]):
        pointer = f"/raw_package/payload/tokens/{position}"
        token = _raw_exact_dict(raw_token, _TOKEN_FIELDS, pointer)
        index = token["index"]
        if type(index) is not int or not 0 <= index <= 2**32 - 1 or index <= previous_index:
            _reject(pointer, AlignmentResultRejectionReason.RAW_OBSERVATION_INVALID, "TIMESTAMP_NON_MONOTONIC")
        previous_index = index
        if type(token["kind"]) is not str:
            _reject(pointer, AlignmentResultRejectionReason.RAW_OBSERVATION_INVALID)
        try:
            kind = TokenKind(token["kind"])
        except ValueError:
            _reject(pointer, AlignmentResultRejectionReason.RAW_OBSERVATION_INVALID)
        if kind is not TokenKind.SPOKEN:
            if token["confidence_millionths"] is not None:
                _reject(pointer, AlignmentResultRejectionReason.CONFIDENCE_INVALID, "ADAPTER_PRECISION_OVERSTATED")
            if any(token[field] is not None for field in ("normalized_alignment_text", "start_ms", "end_ms")):
                _reject(pointer, AlignmentResultRejectionReason.RAW_OBSERVATION_INVALID)
            continue
        try:
            _safe_text(token["normalized_alignment_text"])
        except Exception:
            _reject(pointer, AlignmentResultRejectionReason.RAW_OBSERVATION_INVALID)
        start, end = token["start_ms"], token["end_ms"]
        if type(start) is not int or type(end) is not int:
            _reject(pointer, AlignmentResultRejectionReason.TIMING_INVALID, "TIMESTAMP_OUT_OF_BOUNDS")
        if start < 0 or end < 0:
            _reject(pointer, AlignmentResultRejectionReason.TIMING_INVALID, "TIMESTAMP_OUT_OF_BOUNDS")
        if end == start:
            _reject(pointer, AlignmentResultRejectionReason.TIMING_INVALID, "ZERO_DURATION_WORD")
        if start > end or (previous_start is not None and start < previous_start):
            _reject(pointer, AlignmentResultRejectionReason.TIMING_INVALID, "TIMESTAMP_NON_MONOTONIC")
        metadata = audio.decoded_metadata
        if end * 1000 * metadata.duration_us_denominator > metadata.duration_us_numerator:
            _reject(pointer, AlignmentResultRejectionReason.TIMING_INVALID, "TIMESTAMP_OUT_OF_BOUNDS")
        if previous_end is not None and start < previous_end:
            _reject(pointer, AlignmentResultRejectionReason.TIMING_INVALID, "TIMESTAMP_OVERLAP")
        previous_start = start
        previous_end = end
        value = token["confidence_millionths"]
        if confidence is ConfidenceAvailability.AVAILABLE:
            if value is None:
                _reject(pointer, AlignmentResultRejectionReason.CONFIDENCE_INVALID, "CONFIDENCE_REQUIRED_UNAVAILABLE")
            if type(value) is not int or not 0 <= value <= 1_000_000:
                _reject(pointer, AlignmentResultRejectionReason.CONFIDENCE_INVALID, "ADAPTER_PRECISION_OVERSTATED")
        elif value is not None:
            _reject(pointer, AlignmentResultRejectionReason.CONFIDENCE_INVALID, "ADAPTER_PRECISION_OVERSTATED")
        spoken.append(token)
    if not spoken:
        _reject("/raw_package/payload/tokens", AlignmentResultRejectionReason.TRANSCRIPT_DIVERGENCE, "TRANSCRIPT_DIVERGENCE")
    return spoken


def _computed_timings(revision: NarrationRevision, spoken: list[dict[str, Any]], confidence: ConfidenceAvailability) -> tuple[WordTiming, ...]:
    words = revision.canonical_words
    if not words:
        _reject("/narration_revision/canonical_words", AlignmentResultRejectionReason.TRANSCRIPT_DIVERGENCE, "CANONICAL_COVERAGE_BLOCKER")
    seen_ids: set[str] = set()
    for ordinal, word in enumerate(words):
        try:
            if type(word.ordinal) is not int:
                raise ValueError
            _safe_text(word.word_id)
            _safe_text(word.normalized_alignment_text)
        except Exception:
            _reject("/narration_revision/canonical_words", AlignmentResultRejectionReason.TRANSCRIPT_DIVERGENCE, "CANONICAL_COVERAGE_BLOCKER")
        if word.word_id in seen_ids:
            _reject("/narration_revision/canonical_words", AlignmentResultRejectionReason.TRANSCRIPT_DIVERGENCE, "CANONICAL_COVERAGE_BLOCKER")
        seen_ids.add(word.word_id)
        if word.ordinal != ordinal:
            _reject("/narration_revision/canonical_words", AlignmentResultRejectionReason.TRANSCRIPT_DIVERGENCE, "CANONICAL_WORD_ORDER_INVALID")
    result: list[WordTiming] = []
    cursor = 0
    for word in words:
        combined = ""
        start_cursor = cursor
        while cursor < len(spoken) and len(combined) < len(word.normalized_alignment_text):
            combined += spoken[cursor]["normalized_alignment_text"]
            cursor += 1
        if combined != word.normalized_alignment_text or cursor == start_cursor:
            issue = _divergence_issue(words, spoken)
            _reject("/raw_package/payload/tokens", AlignmentResultRejectionReason.TRANSCRIPT_DIVERGENCE, issue)
        group = spoken[start_cursor:cursor]
        values = [item["confidence_millionths"] for item in group]
        result.append(WordTiming(
            word.word_id, group[0]["start_ms"], group[-1]["end_ms"],
            min(values) if confidence is ConfidenceAvailability.AVAILABLE else None,
            tuple(item["index"] for item in group),
        ))
    if cursor != len(spoken):
        _reject("/raw_package/payload/tokens", AlignmentResultRejectionReason.TRANSCRIPT_DIVERGENCE, "TRANSCRIPT_DIVERGENCE")
    return tuple(result)


def _divergence_issue(words: Any, spoken: list[dict[str, Any]]) -> str:
    keys = [word.normalized_alignment_text for word in words]
    raw = [token["normalized_alignment_text"] for token in spoken]
    reachable = {(0, 0, False)}
    for _ in range(len(keys) + len(raw) + 1):
        advanced = set(reachable)
        for wi, ri, merged in reachable:
            combined_raw = ""
            for raw_end in range(ri, len(raw)):
                combined_raw += raw[raw_end]
                if wi < len(keys) and combined_raw == keys[wi]:
                    advanced.add((wi + 1, raw_end + 1, merged))
                if wi >= len(keys) or len(combined_raw) >= len(keys[wi]):
                    break
            for end in range(wi + 2, len(keys) + 1):
                if ri < len(raw) and "".join(keys[wi:end]) == raw[ri]:
                    advanced.add((end, ri + 1, True))
        if advanced == reachable:
            break
        reachable = advanced
    return "ADAPTER_PRECISION_OVERSTATED" if (len(keys), len(raw), True) in reachable else "TRANSCRIPT_DIVERGENCE"


def _timing_dict(value: WordTiming) -> dict[str, Any]:
    return {
        "word_id": value.word_id, "start_ms": value.start_ms, "end_ms": value.end_ms,
        "confidence_millionths": value.confidence_millionths,
        "source_token_indices": list(value.source_token_indices),
    }


def _result_dict(value: AlignmentResult) -> dict[str, Any]:
    result = {field: getattr(value, field) for field in _RESULT_FIELDS}
    result["timing_source"] = value.timing_source.value
    result["confidence_availability"] = value.confidence_availability.value
    result["word_timings"] = [_timing_dict(item) for item in value.word_timings]
    return result


def _validate_declared_timings(value: Any, computed: tuple[WordTiming, ...]) -> None:
    if type(value) is not list or len(value) != len(computed):
        _reject("/word_timings", AlignmentResultRejectionReason.TRANSCRIPT_DIVERGENCE, "CANONICAL_COVERAGE_BLOCKER")
    seen_ids: set[str] = set()
    for index, (raw, expected) in enumerate(zip(value, computed)):
        pointer = f"/word_timings/{index}"
        data = _exact_dict(raw, _TIMING_FIELDS, pointer)
        if (
            type(data["word_id"]) is not str
            or type(data["start_ms"]) is not int
            or type(data["end_ms"]) is not int
            or (data["confidence_millionths"] is not None and type(data["confidence_millionths"]) is not int)
            or type(data["source_token_indices"]) is not list
            or any(type(item) is not int for item in data["source_token_indices"])
        ):
            _reject(pointer, AlignmentResultRejectionReason.STRUCTURE_INVALID)
        if data["word_id"] in seen_ids or data["word_id"] not in {item.word_id for item in computed}:
            _reject(pointer, AlignmentResultRejectionReason.TRANSCRIPT_DIVERGENCE, "CANONICAL_COVERAGE_BLOCKER")
        seen_ids.add(data["word_id"])
        if data["word_id"] != expected.word_id:
            _reject(pointer, AlignmentResultRejectionReason.TRANSCRIPT_DIVERGENCE, "CANONICAL_WORD_ORDER_INVALID")
        actual = dict(data)
        actual["source_token_indices"] = tuple(actual["source_token_indices"])
        if actual["start_ms"] != expected.start_ms or actual["end_ms"] != expected.end_ms:
            _reject(pointer, AlignmentResultRejectionReason.TIMING_INVALID, "ADAPTER_PRECISION_OVERSTATED")
        if actual["confidence_millionths"] != expected.confidence_millionths:
            _reject(pointer, AlignmentResultRejectionReason.CONFIDENCE_INVALID, "ADAPTER_PRECISION_OVERSTATED")
        if actual["source_token_indices"] != expected.source_token_indices:
            _reject(pointer, AlignmentResultRejectionReason.TIMING_INVALID, "ADAPTER_PRECISION_OVERSTATED")


def _scan_sensitive(value: Any, active: set[int] | None = None) -> None:
    active = set() if active is None else active
    if type(value) in {dict, list}:
        identity = id(value)
        if identity in active:
            _reject("/", AlignmentResultRejectionReason.SENSITIVE_DATA)
        active.add(identity)
        items = value.values() if type(value) is dict else value
        for item in items:
            _scan_sensitive(item, active)
        active.remove(identity)
    elif type(value) is str:
        try:
            _safe_text(value, allow_empty=True)
        except ValueError:
            _reject("/", AlignmentResultRejectionReason.SENSITIVE_DATA)
        if "://" in value or value.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", value):
            _reject("/", AlignmentResultRejectionReason.SENSITIVE_DATA)


def _validate_current_result(result: AlignmentResult) -> None:
    if (
        type(result.timing_source) is not AlignmentTimingSource
        or type(result.confidence_availability) is not ConfidenceAvailability
        or type(result.word_timings) is not tuple
    ):
        raise ValueError
    for field in _RESULT_FIELDS[:-3]:
        if type(getattr(result, field)) is not str:
            raise ValueError
    for timing in result.word_timings:
        if (
            type(timing) is not WordTiming
            or type(timing.word_id) is not str
            or type(timing.start_ms) is not int
            or type(timing.end_ms) is not int
            or (timing.confidence_millionths is not None and type(timing.confidence_millionths) is not int)
            or type(timing.source_token_indices) is not tuple
            or any(type(index) is not int for index in timing.source_token_indices)
        ):
            raise ValueError


def _register_result(value: AlignmentResult, envelope: bytes) -> None:
    key = id(value)
    old = _MATERIALIZED_ALIGNMENT_RESULTS.get(key)
    if old is not None and old[0]() is not None:
        raise RuntimeError("alignment result provenance collision")

    def forget(reference: weakref.ReferenceType[AlignmentResult]) -> None:
        current = _MATERIALIZED_ALIGNMENT_RESULTS.get(key)
        if current is not None and current[0] is reference:
            _MATERIALIZED_ALIGNMENT_RESULTS.pop(key, None)
        if _OWNED_ALIGNMENT_RESULT_REFERENCES.get(key) is reference:
            _OWNED_ALIGNMENT_RESULT_REFERENCES.pop(key, None)

    reference = weakref.ref(value, forget)
    entry = (reference, bytes(envelope))
    try:
        _OWNED_ALIGNMENT_RESULT_REFERENCES[key] = reference
        _MATERIALIZED_ALIGNMENT_RESULTS[key] = entry
        if (
            _MATERIALIZED_ALIGNMENT_RESULTS.get(key) is not entry
            or _OWNED_ALIGNMENT_RESULT_REFERENCES.get(key) is not reference
            or reference() is not value
        ):
            raise RuntimeError("alignment result provenance registration failed")
    except Exception:
        if _MATERIALIZED_ALIGNMENT_RESULTS.get(key) is entry:
            _MATERIALIZED_ALIGNMENT_RESULTS.pop(key, None)
        if _OWNED_ALIGNMENT_RESULT_REFERENCES.get(key) is reference:
            _OWNED_ALIGNMENT_RESULT_REFERENCES.pop(key, None)
        raise


def _materialize(
    value: dict[str, Any], *, temporal_raw_package: CanonicalRawPackage,
    narration_document: CanonicalNarrationDocument, narration_revision: NarrationRevision,
    audio_artifact: AudioArtifact, alignment_request: AlignmentRequest,
    adapter_execution: AdapterExecution, timing_origin_evidence: TimingOriginEvidence,
    source: bytes | None,
) -> AlignmentResult:
    preflight = _preflight(temporal_raw_package, narration_document, narration_revision, audio_artifact, alignment_request, adapter_execution, timing_origin_evidence)
    data = _exact_dict(value, _RESULT_FIELDS, "/")
    for field in _RESULT_FIELDS[:-3]:
        if type(data[field]) is not str:
            _reject("/", AlignmentResultRejectionReason.STRUCTURE_INVALID)
    if data["schema_version"] != ALIGNMENT_RESULT_V1 or data["hash_scope_version"] != ALIGNMENT_RESULT_HASH_V1:
        _reject("/", AlignmentResultRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
    if type(data["timing_source"]) is not str or type(data["confidence_availability"]) is not str:
        _reject("/", AlignmentResultRejectionReason.STRUCTURE_INVALID)
    try:
        confidence = ConfidenceAvailability(data["confidence_availability"])
    except ValueError:
        _reject("/", AlignmentResultRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
    if confidence is not preflight.confidence:
        _reject("/", AlignmentResultRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    if (
        confidence is ConfidenceAvailability.NOT_APPLICABLE
        and alignment_request.adapter_capability.confidence_output != "UNSUPPORTED"
    ):
        _reject("/", AlignmentResultRejectionReason.CONFIDENCE_INVALID, "CONFIDENCE_REQUIRED_UNAVAILABLE")
    _bindings(data, temporal_raw_package=temporal_raw_package, narration_document=narration_document, narration_revision=narration_revision, audio_artifact=audio_artifact, alignment_request=alignment_request, adapter_execution=adapter_execution, timing_origin_evidence=timing_origin_evidence)
    if data["timing_source"] != AlignmentTimingSource.REPLAY_VERIFIED.value:
        _reject("/timing_source", AlignmentResultRejectionReason.TIMESTAMP_SOURCE_FORBIDDEN, "LLM_TIMESTAMP_SOURCE_FORBIDDEN")
    raw = _raw_exact_dict(preflight.raw, _RAW_FIELDS, "/raw_package")
    if raw.get("media_type") != _RAW_MEDIA_TYPE:
        _reject("/raw_package", AlignmentResultRejectionReason.RAW_OBSERVATION_INVALID)
    if (
        raw.get("schema_version") != "TRP-RAW-V1"
        or type(raw.get("run_id")) is not str
        or type(raw.get("raw_id")) is not str
        or type(raw.get("payload_byte_hash")) is not str
        or type(raw.get("issue_codes")) is not list
        or raw["issue_codes"]
    ):
        _reject("/raw_package", AlignmentResultRejectionReason.RAW_OBSERVATION_INVALID)
    tokens = _parse_tokens(preflight.payload, narration_revision, audio_artifact, confidence)
    computed = _computed_timings(narration_revision, tokens, confidence)
    _validate_declared_timings(data["word_timings"], computed)
    _scan_sensitive(data)
    projection = {key: item for key, item in data.items() if key not in {"alignment_result_id", "alignment_result_hash"}}
    digest = _hash(encode_canonical_json_bytes(projection))
    if data["alignment_result_hash"] != digest:
        _reject("/alignment_result_hash", AlignmentResultRejectionReason.IDENTITY_MISMATCH)
    if data["alignment_result_id"] != "alr_" + digest[:32]:
        _reject("/alignment_result_id", AlignmentResultRejectionReason.IDENTITY_MISMATCH)
    try:
        timing_source = AlignmentTimingSource(data["timing_source"])
        result = AlignmentResult(
            **{field: data[field] for field in _RESULT_FIELDS[:-3]},
            timing_source=timing_source, confidence_availability=confidence,
            word_timings=computed,
        )
        envelope = encode_canonical_json_bytes(_result_dict(result))
    except Exception:
        raise RuntimeError("alignment result construction failed")
    if source is not None and source != envelope:
        _reject("/", AlignmentResultRejectionReason.NON_CANONICAL_SERIALIZATION)
    _register_result(result, envelope)
    return result


def materialize_alignment_result(
    value: dict[str, Any], *, temporal_raw_package: CanonicalRawPackage,
    narration_document: CanonicalNarrationDocument, narration_revision: NarrationRevision,
    audio_artifact: AudioArtifact, alignment_request: AlignmentRequest,
    adapter_execution: AdapterExecution, timing_origin_evidence: TimingOriginEvidence,
) -> AlignmentResult:
    return _materialize(value, temporal_raw_package=temporal_raw_package, narration_document=narration_document, narration_revision=narration_revision, audio_artifact=audio_artifact, alignment_request=alignment_request, adapter_execution=adapter_execution, timing_origin_evidence=timing_origin_evidence, source=None)


def load_alignment_result(
    source: bytes, *, temporal_raw_package: CanonicalRawPackage,
    narration_document: CanonicalNarrationDocument, narration_revision: NarrationRevision,
    audio_artifact: AudioArtifact, alignment_request: AlignmentRequest,
    adapter_execution: AdapterExecution, timing_origin_evidence: TimingOriginEvidence,
) -> AlignmentResult:
    # Dependency preflight intentionally wins over wire parsing.
    _preflight(temporal_raw_package, narration_document, narration_revision, audio_artifact, alignment_request, adapter_execution, timing_origin_evidence)
    value = _parse_json(source, "/")
    try:
        canonical_source = encode_canonical_json_bytes(value)
    except Exception:
        _reject("/", AlignmentResultRejectionReason.STRUCTURE_INVALID)
    if source != canonical_source:
        _reject("/", AlignmentResultRejectionReason.NON_CANONICAL_SERIALIZATION)
    return _materialize(value, temporal_raw_package=temporal_raw_package, narration_document=narration_document, narration_revision=narration_revision, audio_artifact=audio_artifact, alignment_request=alignment_request, adapter_execution=adapter_execution, timing_origin_evidence=timing_origin_evidence, source=source)


def serialize_alignment_result(result: AlignmentResult) -> bytes:
    entry = _MATERIALIZED_ALIGNMENT_RESULTS.get(id(result))
    owner = _OWNED_ALIGNMENT_RESULT_REFERENCES.get(id(result))
    if (
        type(result) is not AlignmentResult
        or owner is None
        or owner() is not result
    ):
        _reject("/", AlignmentResultRejectionReason.NOT_MATERIALIZED)
    if entry is None or entry[0] is not owner or type(entry[1]) is not bytes:
        _reject("/", AlignmentResultRejectionReason.CONTENT_DRIFT)
    try:
        _validate_current_result(result)
        current = _result_dict(result)
        projection = {key: item for key, item in current.items() if key not in {"alignment_result_id", "alignment_result_hash"}}
        digest = _hash(encode_canonical_json_bytes(projection))
        if result.alignment_result_hash != digest or result.alignment_result_id != "alr_" + digest[:32]:
            raise ValueError
        envelope = encode_canonical_json_bytes(current)
        if envelope != entry[1]:
            raise ValueError
    except Exception:
        _reject("/", AlignmentResultRejectionReason.CONTENT_DRIFT)
    return bytes(entry[1])
