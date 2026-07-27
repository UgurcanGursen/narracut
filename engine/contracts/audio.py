"""Canonical AudioArtifact identity and secure audio-input boundary."""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Protocol
from urllib.parse import urlsplit

from ._canonical_json import encode_canonical_json_bytes
from .temporal import STABLE_ISSUE_CODE_SET


AUDIO_ARTIFACT_INPUT_V1 = "AUDIO-ARTIFACT-INPUT-V1"
SECURE_AUDIO_INPUT_V1 = "SECURE-AUDIO-INPUT-V1"
AUDIO_ARTIFACT_V1 = "AUDIO-ARTIFACT-V1"
AUDIO_ARTIFACT_HASH_V1 = "audio-artifact-hash-v1"

_HASH_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
_STABLE_ID_PATTERN = re.compile(
    r"[a-z][a-z0-9]*_[a-z0-9][a-z0-9_-]{2,63}"
)
_EXTENSION_KEY_PATTERN = re.compile(
    r"[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+/[a-z][a-z0-9_-]*"
)
_URI_LIKE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_DRIVE_PREFIX_PATTERN = re.compile(r"^[A-Za-z]:")
_UINT64_MAX = 2**64 - 1
_MAX_DATA_BYTE_LENGTH = 4_294_967_259
_MAX_WAVE_BYTE_LENGTH = 44 + _MAX_DATA_BYTE_LENGTH
_RESERVED_OPERANDS = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)
_SENSITIVE_EXTENSION_NAMES = frozenset(
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


class AudioArtifactRejectionReason(str, Enum):
    CONTAINMENT_FAILED = "containment_failed"
    DECODE_FAILED = "decode_failed"
    EMPTY = "empty"
    EXTENSION_INVALID = "extension_invalid"
    FORMAT_UNSUPPORTED = "format_unsupported"
    HASH_MISMATCH = "hash_mismatch"
    IDENTITY_CHANGED = "identity_changed"
    METADATA_MISMATCH = "metadata_mismatch"
    OPEN_FAILED = "open_failed"
    PATH_INVALID = "path_invalid"
    READ_FAILED = "read_failed"
    REVISION_MISMATCH = "revision_mismatch"
    SIZE_OUT_OF_BOUNDS = "size_out_of_bounds"
    STRUCTURE_INVALID = "structure_invalid"
    TRUNCATED = "truncated"
    UNSUPPORTED_ENUM = "unsupported_enum"
    URI_FORBIDDEN = "uri_forbidden"


class AudioArtifactContractError(ValueError):
    """Fail-closed validation error with no serialized artifact output."""

    def __init__(
        self,
        reason: AudioArtifactRejectionReason,
        pointer: str,
        message: str,
        *,
        issue_code: str | None = None,
        ordered_issue_codes: Sequence[str] | None = None,
    ):
        if not isinstance(reason, AudioArtifactRejectionReason):
            raise TypeError("reason must be an AudioArtifactRejectionReason.")
        if type(pointer) is not str:
            raise TypeError("pointer must be an exact built-in string.")
        if issue_code is not None:
            _validate_single_issue_code(issue_code)
        if ordered_issue_codes is None:
            ordered = () if issue_code is None else (issue_code,)
        else:
            ordered = tuple(ordered_issue_codes)
            _validate_ordered_issue_codes(ordered)
        if ordered:
            if issue_code is None or ordered[0] != issue_code:
                raise ValueError("ordered_issue_codes[0] must equal issue_code.")
        elif issue_code is not None:
            raise ValueError("issue_code requires a non-empty ordered set.")
        super().__init__(message)
        self.pointer = pointer
        self.reason = reason
        self.issue_code = issue_code
        self.ordered_issue_codes = ordered


@dataclass(frozen=True)
class SecureAudioInputReference:
    schema_version: str
    kind: str
    logical_path: str


@dataclass(frozen=True)
class AudioArtifactMaterializationInput:
    schema_version: str
    project_id: str
    document_id: str
    narration_revision_id: str
    narration_revision_hash: str
    logical_input: SecureAudioInputReference
    declared_media_byte_hash: str
    declared_sample_rate_hz: int
    declared_channel_count: int
    declared_sample_frame_count: int
    extensions: Mapping[str, Any]


@dataclass(frozen=True)
class DecodedAudioMetadata:
    container: str
    codec: str
    sample_format: str
    endianness: str
    sample_rate_hz: int
    channel_count: int
    sample_frame_count: int
    duration_us_numerator: int
    duration_us_denominator: int


@dataclass(frozen=True)
class AudioArtifact:
    schema_version: str
    hash_scope_version: str
    audio_artifact_id: str
    audio_artifact_hash: str
    project_id: str
    document_id: str
    narration_revision_id: str
    narration_revision_hash: str
    media_byte_hash: str
    logical_input: SecureAudioInputReference
    decoded_metadata: DecodedAudioMetadata
    extensions: Mapping[str, Any]


@dataclass(frozen=True)
class NarrationRevisionBinding:
    project_id: str
    document_id: str
    narration_revision_id: str
    narration_revision_hash: str

    def __post_init__(self) -> None:
        _require_stable_id(self.project_id, "$binding.project_id")
        _require_stable_id(self.document_id, "$binding.document_id")
        _require_stable_id(
            self.narration_revision_id,
            "$binding.narration_revision_id",
        )
        _require_hash(
            self.narration_revision_hash,
            "$binding.narration_revision_hash",
        )

    @classmethod
    def from_validated_revision(cls, revision: Any) -> NarrationRevisionBinding:
        if isinstance(revision, Mapping):
            raise TypeError("Validated narration revision object is required.")
        return cls(
            project_id=revision.project_id,
            document_id=revision.document_id,
            narration_revision_id=revision.revision_id,
            narration_revision_hash=revision.revision_hash,
        )


@dataclass(frozen=True)
class TrustedRootReference:
    canonical_absolute_root: str

    def __post_init__(self) -> None:
        _require_safe_nfc_string(
            self.canonical_absolute_root,
            "$runtime.trusted_root.canonical_absolute_root",
        )


class SecureAudioReader(Protocol):
    @property
    def access_count(self) -> int: ...

    @property
    def snapshot_read_count(self) -> int: ...

    @property
    def reverify_read_count(self) -> int: ...

    def open_snapshot(
        self,
        trusted_root: TrustedRootReference,
        validated_logical_segments: tuple[str, ...],
    ) -> "SecureAudioSnapshot": ...


@dataclass(frozen=True)
class AudioArtifactMaterializationRuntime:
    trusted_root: TrustedRootReference
    secure_reader: SecureAudioReader

    def __post_init__(self) -> None:
        if not isinstance(self.trusted_root, TrustedRootReference):
            raise TypeError("trusted_root must be a TrustedRootReference.")
        if not hasattr(self.secure_reader, "open_snapshot"):
            raise TypeError("secure_reader must implement open_snapshot.")
        for field in (
            "access_count",
            "snapshot_read_count",
            "reverify_read_count",
        ):
            _require_uint64(getattr(self.secure_reader, field), f"$runtime.{field}")


@dataclass(frozen=True)
class SecureOpenEvidence:
    initial_root_identity: str
    final_root_identity: str
    initial_file_identity: str
    final_file_identity: str
    initial_byte_length: int
    final_byte_length: int
    containment_before: bool
    containment_after: bool
    reparse_component_seen: bool
    snapshot_media_byte_hash: str
    final_same_object_media_byte_hash: str
    object_replacement_observed: bool
    final_read_byte_length: int

    def __post_init__(self) -> None:
        for field in (
            "initial_root_identity",
            "final_root_identity",
            "initial_file_identity",
            "final_file_identity",
        ):
            _require_safe_nfc_string(getattr(self, field), f"$evidence.{field}")
        for field in (
            "initial_byte_length",
            "final_byte_length",
            "final_read_byte_length",
        ):
            _require_uint64(getattr(self, field), f"$evidence.{field}")
        for field in (
            "containment_before",
            "containment_after",
            "reparse_component_seen",
            "object_replacement_observed",
        ):
            if type(getattr(self, field)) is not bool:
                raise TypeError(f"{field} must be an exact bool.")
        _require_hash(
            self.snapshot_media_byte_hash,
            "$evidence.snapshot_media_byte_hash",
        )
        _require_hash(
            self.final_same_object_media_byte_hash,
            "$evidence.final_same_object_media_byte_hash",
        )


@dataclass(frozen=True)
class SecureAudioSnapshot:
    exact_bytes: bytes
    open_evidence: SecureOpenEvidence
    reverify_evidence: SecureOpenEvidence

    def __post_init__(self) -> None:
        if not isinstance(self.exact_bytes, bytes):
            raise TypeError("exact_bytes must be bytes.")
        if not isinstance(self.open_evidence, SecureOpenEvidence):
            raise TypeError("open_evidence must be SecureOpenEvidence.")
        if not isinstance(self.reverify_evidence, SecureOpenEvidence):
            raise TypeError("reverify_evidence must be SecureOpenEvidence.")

    def reverify_same_object(self) -> SecureOpenEvidence:
        return self.reverify_evidence


def materialize_audio_artifact(
    value: Mapping[str, Any],
    *,
    narration_binding: NarrationRevisionBinding,
    runtime: AudioArtifactMaterializationRuntime,
) -> AudioArtifact:
    data = _parse_input(value)
    _validate_binding(data, narration_binding)
    logical_segments = _validate_logical_input(data.logical_input)
    snapshot = _open_snapshot(runtime, logical_segments)
    _validate_initial_evidence(snapshot)
    exact_bytes = snapshot.exact_bytes
    if len(exact_bytes) > _MAX_WAVE_BYTE_LENGTH:
        _reject(
            AudioArtifactRejectionReason.SIZE_OUT_OF_BOUNDS,
            "$.logical_input",
            "Audio input exceeds the WAVE byte bound.",
            issue_code="AUDIO_SIZE_OUT_OF_BOUNDS",
        )
    if exact_bytes == b"":
        _reject(
            AudioArtifactRejectionReason.EMPTY,
            "$.logical_input",
            "Audio input is empty.",
            issue_code="AUDIO_EMPTY",
        )

    media_byte_hash = "sha256:" + hashlib.sha256(exact_bytes).hexdigest()
    if media_byte_hash != data.declared_media_byte_hash:
        _reject(
            AudioArtifactRejectionReason.HASH_MISMATCH,
            "$.declared_media_byte_hash",
            "Declared audio byte hash does not match the snapshot bytes.",
            issue_code="AUDIO_BYTE_HASH_MISMATCH",
        )

    decoded = _decode_wave(exact_bytes)
    if decoded.sample_frame_count == 0:
        _reject(
            AudioArtifactRejectionReason.EMPTY,
            "$.logical_input",
            "Audio input contains zero sample frames.",
            issue_code="AUDIO_EMPTY",
        )
    _validate_declared_metadata(data, decoded)
    final_evidence = _reverify_snapshot(snapshot)
    _validate_final_evidence(final_evidence)

    projection = {
        "schema_version": AUDIO_ARTIFACT_V1,
        "hash_scope_version": AUDIO_ARTIFACT_HASH_V1,
        "project_id": data.project_id,
        "document_id": data.document_id,
        "narration_revision_id": data.narration_revision_id,
        "narration_revision_hash": data.narration_revision_hash,
        "media_byte_hash": media_byte_hash,
        "logical_input": _logical_input_to_dict(data.logical_input),
        "decoded_metadata": _decoded_metadata_to_dict(decoded),
    }
    projection_bytes = encode_canonical_json_bytes(projection)
    digest = hashlib.sha256(projection_bytes).hexdigest()
    return AudioArtifact(
        schema_version=AUDIO_ARTIFACT_V1,
        hash_scope_version=AUDIO_ARTIFACT_HASH_V1,
        audio_artifact_id="aud_" + digest[:20],
        audio_artifact_hash="sha256:" + digest,
        project_id=data.project_id,
        document_id=data.document_id,
        narration_revision_id=data.narration_revision_id,
        narration_revision_hash=data.narration_revision_hash,
        media_byte_hash=media_byte_hash,
        logical_input=data.logical_input,
        decoded_metadata=decoded,
        extensions=data.extensions,
    )


def serialize_audio_artifact(artifact: AudioArtifact) -> bytes:
    if not isinstance(artifact, AudioArtifact):
        raise TypeError("serialize_audio_artifact requires an AudioArtifact.")
    return encode_canonical_json_bytes(_artifact_to_dict(artifact))


def _parse_input(value: Mapping[str, Any]) -> AudioArtifactMaterializationInput:
    data = _require_mapping(value, "$")
    required = {
        "schema_version",
        "project_id",
        "document_id",
        "narration_revision_id",
        "narration_revision_hash",
        "logical_input",
        "declared_media_byte_hash",
        "declared_sample_rate_hz",
        "declared_channel_count",
        "declared_sample_frame_count",
        "extensions",
    }
    _require_closed_fields(data, required, required, "$")
    if data["schema_version"] != AUDIO_ARTIFACT_INPUT_V1:
        _reject(
            AudioArtifactRejectionReason.UNSUPPORTED_ENUM,
            "$.schema_version",
            "Unsupported audio artifact input schema.",
            issue_code="UNSUPPORTED_CONTRACT_ENUM",
        )
    logical_input = _parse_secure_reference(data["logical_input"])
    extensions = _validate_extensions(data["extensions"], "$.extensions")
    return AudioArtifactMaterializationInput(
        schema_version=AUDIO_ARTIFACT_INPUT_V1,
        project_id=_require_stable_id(data["project_id"], "$.project_id"),
        document_id=_require_stable_id(data["document_id"], "$.document_id"),
        narration_revision_id=_require_stable_id(
            data["narration_revision_id"],
            "$.narration_revision_id",
        ),
        narration_revision_hash=_require_hash(
            data["narration_revision_hash"],
            "$.narration_revision_hash",
        ),
        logical_input=logical_input,
        declared_media_byte_hash=_require_hash(
            data["declared_media_byte_hash"],
            "$.declared_media_byte_hash",
        ),
        declared_sample_rate_hz=_require_positive_int(
            data["declared_sample_rate_hz"],
            "$.declared_sample_rate_hz",
        ),
        declared_channel_count=_require_positive_int(
            data["declared_channel_count"],
            "$.declared_channel_count",
        ),
        declared_sample_frame_count=_require_nonnegative_int(
            data["declared_sample_frame_count"],
            "$.declared_sample_frame_count",
        ),
        extensions=extensions,
    )


def _parse_secure_reference(value: Any) -> SecureAudioInputReference:
    data = _require_mapping(value, "$.logical_input")
    required = {"schema_version", "kind", "logical_path"}
    _require_closed_fields(data, required, required, "$.logical_input")
    if data["schema_version"] != SECURE_AUDIO_INPUT_V1:
        _reject(
            AudioArtifactRejectionReason.UNSUPPORTED_ENUM,
            "$.logical_input.schema_version",
            "Unsupported secure audio input schema.",
            issue_code="UNSUPPORTED_CONTRACT_ENUM",
        )
    kind = _require_exact_string(data["kind"], "$.logical_input.kind")
    if kind != "LOCAL_FILE":
        _reject(
            AudioArtifactRejectionReason.UNSUPPORTED_ENUM,
            "$.logical_input.kind",
            "Unsupported secure audio input kind.",
            issue_code="UNSUPPORTED_CONTRACT_ENUM",
        )
    return SecureAudioInputReference(
        schema_version=SECURE_AUDIO_INPUT_V1,
        kind=kind,
        logical_path=_require_exact_string_without_nfc(
            data["logical_path"],
            "$.logical_input.logical_path",
        ),
    )


def _validate_binding(
    data: AudioArtifactMaterializationInput,
    binding: NarrationRevisionBinding,
) -> None:
    if not isinstance(binding, NarrationRevisionBinding):
        raise TypeError("narration_binding must be NarrationRevisionBinding.")
    if (
        data.project_id != binding.project_id
        or data.document_id != binding.document_id
        or data.narration_revision_id != binding.narration_revision_id
        or data.narration_revision_hash != binding.narration_revision_hash
    ):
        _reject(
            AudioArtifactRejectionReason.REVISION_MISMATCH,
            "$.narration_revision_id",
            "Audio input does not match the typed narration revision binding.",
            issue_code="AUDIO_REVISION_MISMATCH",
        )


def _validate_logical_input(
    logical_input: SecureAudioInputReference,
) -> tuple[str, ...]:
    path = logical_input.logical_path
    pointer = "$.logical_input.logical_path"
    if len(path) < 1 or len(path) > 1024:
        _path_reject("PATH_SYNTAX_INVALID", pointer)
    if path.startswith("\\\\?\\") or path.startswith("\\\\.\\"):
        _path_reject("PATH_DEVICE_FORBIDDEN", pointer)
    if path.startswith("//?/") or path.startswith("//./"):
        _path_reject("PATH_DEVICE_FORBIDDEN", pointer)
    if path.startswith("\\\\") or path.startswith("//"):
        _path_reject("PATH_UNC_FORBIDDEN", pointer)
    if _DRIVE_PREFIX_PATTERN.match(path):
        _path_reject("PATH_TRAVERSAL", pointer)
    if _URI_LIKE_PATTERN.match(path):
        return _reject_uri(path, pointer)
    if path.startswith("/"):
        _path_reject("PATH_TRAVERSAL", pointer)
    if "\\" in path or "//" in path:
        _path_reject("PATH_SYNTAX_INVALID", pointer)
    if any(ord(character) == 0 or ord(character) < 0x20 or ord(character) == 0x7F for character in path):
        _path_reject("PATH_SYNTAX_INVALID", pointer)
    if unicodedata.normalize("NFC", path) != path:
        _path_reject("PATH_SYNTAX_INVALID", pointer)
    segments = tuple(path.split("/"))
    for segment in segments:
        if segment == "":
            _path_reject("PATH_SYNTAX_INVALID", pointer)
        if segment in {".", ".."}:
            _path_reject("PATH_TRAVERSAL", pointer)
        if ":" in segment:
            _path_reject("PATH_ADS_FORBIDDEN", pointer)
        if segment.endswith(".") or segment.endswith(" "):
            _path_reject("PATH_RESERVED_NAME", pointer)
        operand = segment.split(".", 1)[0].upper()
        if operand in _RESERVED_OPERANDS:
            _path_reject("PATH_RESERVED_NAME", pointer)
    return segments


def _reject_uri(path: str, pointer: str) -> tuple[str, ...]:
    parsed = urlsplit(path)
    codes: list[str] = []
    if "@" in parsed.netloc.rsplit("]", 1)[-1]:
        codes.append("URI_USER_INFO")
    if parsed.query or parsed.fragment:
        codes.append("URI_SENSITIVE_COMPONENT")
    if not codes:
        codes.append("AUDIO_INPUT_URI_FORBIDDEN")
    _reject(
        AudioArtifactRejectionReason.URI_FORBIDDEN,
        pointer,
        "URI-like audio input references are forbidden.",
        issue_code=codes[0],
        ordered_issue_codes=tuple(codes),
    )


def _open_snapshot(
    runtime: AudioArtifactMaterializationRuntime,
    logical_segments: tuple[str, ...],
) -> SecureAudioSnapshot:
    try:
        snapshot = runtime.secure_reader.open_snapshot(
            runtime.trusted_root,
            logical_segments,
        )
    except AudioArtifactContractError:
        raise
    except Exception as exc:
        raise AudioArtifactContractError(
            AudioArtifactRejectionReason.OPEN_FAILED,
            "$.logical_input",
            "Secure audio input open failed.",
            issue_code="AUDIO_INPUT_OPEN_FAILED",
        ) from exc
    if not isinstance(snapshot, SecureAudioSnapshot):
        _reject(
            AudioArtifactRejectionReason.READ_FAILED,
            "$.logical_input",
            "Secure reader returned an invalid snapshot.",
            issue_code="AUDIO_INPUT_READ_FAILED",
        )
    return snapshot


def _validate_initial_evidence(snapshot: SecureAudioSnapshot) -> None:
    evidence = snapshot.open_evidence
    if evidence.reparse_component_seen or not evidence.containment_before:
        _reject(
            AudioArtifactRejectionReason.CONTAINMENT_FAILED,
            "$.logical_input",
            "Secure input containment validation failed.",
            issue_code="SECURE_INPUT_CONTAINMENT_FAILED",
        )
    actual_length = len(snapshot.exact_bytes)
    actual_hash = "sha256:" + hashlib.sha256(snapshot.exact_bytes).hexdigest()
    if (
        evidence.initial_byte_length != actual_length
        or evidence.snapshot_media_byte_hash != actual_hash
    ):
        _reject(
            AudioArtifactRejectionReason.READ_FAILED,
            "$.logical_input",
            "Secure input snapshot evidence does not match the read bytes.",
            issue_code="AUDIO_INPUT_READ_FAILED",
        )


def _reverify_snapshot(snapshot: SecureAudioSnapshot) -> SecureOpenEvidence:
    try:
        return snapshot.reverify_same_object()
    except AudioArtifactContractError:
        raise
    except Exception as exc:
        raise AudioArtifactContractError(
            AudioArtifactRejectionReason.READ_FAILED,
            "$.logical_input",
            "Secure audio input second read failed.",
            issue_code="AUDIO_INPUT_READ_FAILED",
        ) from exc


def _validate_final_evidence(evidence: SecureOpenEvidence) -> None:
    if evidence.final_read_byte_length != evidence.final_byte_length:
        _reject(
            AudioArtifactRejectionReason.READ_FAILED,
            "$.logical_input",
            "Secure audio input second read was incomplete.",
            issue_code="AUDIO_INPUT_READ_FAILED",
        )
    containment_failed = (
        evidence.reparse_component_seen
        or not evidence.containment_before
        or not evidence.containment_after
        or evidence.initial_root_identity != evidence.final_root_identity
    )
    if containment_failed:
        _reject(
            AudioArtifactRejectionReason.CONTAINMENT_FAILED,
            "$.logical_input",
            "Secure input containment validation failed.",
            issue_code="SECURE_INPUT_CONTAINMENT_FAILED",
        )
    identity_changed = (
        evidence.initial_file_identity != evidence.final_file_identity
        or evidence.initial_byte_length != evidence.final_byte_length
        or evidence.snapshot_media_byte_hash
        != evidence.final_same_object_media_byte_hash
        or evidence.object_replacement_observed
    )
    if identity_changed:
        _reject(
            AudioArtifactRejectionReason.IDENTITY_CHANGED,
            "$.logical_input",
            "Secure input identity changed during materialization.",
            issue_code="SECURE_INPUT_IDENTITY_CHANGED",
        )


def _decode_wave(source: bytes) -> DecodedAudioMetadata:
    def fail() -> None:
        _reject(
            AudioArtifactRejectionReason.DECODE_FAILED,
            "$.logical_input",
            "Audio input is not exact strict WAVE PCM.",
            issue_code="AUDIO_DECODE_FAILED",
        )

    if len(source) < 44:
        fail()
    if source[0:4] != b"RIFF" or source[8:12] != b"WAVE":
        fail()
    riff_size = _u32le(source, 4)
    if riff_size != len(source) - 8:
        fail()
    if source[12:16] != b"fmt " or _u32le(source, 16) != 16:
        fail()
    audio_format_tag = _u16le(source, 20)
    channel_count = _u16le(source, 22)
    sample_rate_hz = _u32le(source, 24)
    byte_rate = _u32le(source, 28)
    block_align = _u16le(source, 32)
    bits_per_sample = _u16le(source, 34)
    if source[36:40] != b"data":
        fail()
    data_byte_length = _u32le(source, 40)
    if data_byte_length > _MAX_DATA_BYTE_LENGTH:
        _reject(
            AudioArtifactRejectionReason.SIZE_OUT_OF_BOUNDS,
            "$.logical_input",
            "Audio data exceeds the WAVE data bound.",
            issue_code="AUDIO_SIZE_OUT_OF_BOUNDS",
        )
    if len(source) != 44 + data_byte_length:
        fail()
    if block_align == 0 or data_byte_length % block_align != 0:
        fail()
    sample_frame_count = data_byte_length // block_align
    if sample_frame_count == 0:
        return _decoded_metadata(
            sample_rate_hz,
            channel_count,
            sample_frame_count,
        )
    if (
        audio_format_tag != 1
        or channel_count not in {1, 2}
        or sample_rate_hz < 8000
        or sample_rate_hz > 192000
        or bits_per_sample != 16
        or block_align != channel_count * 2
        or byte_rate != sample_rate_hz * block_align
    ):
        _reject(
            AudioArtifactRejectionReason.FORMAT_UNSUPPORTED,
            "$.logical_input",
            "Readable WAVE input uses an unsupported audio format.",
            issue_code="AUDIO_FORMAT_UNSUPPORTED",
        )
    expected_data_length = sample_frame_count * channel_count * 2
    if data_byte_length != expected_data_length:
        fail()
    if riff_size != 36 + data_byte_length:
        fail()
    return _decoded_metadata(sample_rate_hz, channel_count, sample_frame_count)


def _decoded_metadata(
    sample_rate_hz: int,
    channel_count: int,
    sample_frame_count: int,
) -> DecodedAudioMetadata:
    raw_numerator = sample_frame_count * 1_000_000
    raw_denominator = sample_rate_hz
    if raw_denominator <= 0:
        _reject(
            AudioArtifactRejectionReason.DECODE_FAILED,
            "$.logical_input",
            "Decoded sample rate must be positive.",
            issue_code="AUDIO_DECODE_FAILED",
        )
    divisor = math.gcd(raw_numerator, raw_denominator)
    return DecodedAudioMetadata(
        container="WAVE",
        codec="PCM",
        sample_format="S16",
        endianness="LITTLE",
        sample_rate_hz=sample_rate_hz,
        channel_count=channel_count,
        sample_frame_count=sample_frame_count,
        duration_us_numerator=raw_numerator // divisor,
        duration_us_denominator=raw_denominator // divisor,
    )


def _validate_declared_metadata(
    data: AudioArtifactMaterializationInput,
    decoded: DecodedAudioMetadata,
) -> None:
    rate_mismatch = data.declared_sample_rate_hz != decoded.sample_rate_hz
    channel_mismatch = data.declared_channel_count != decoded.channel_count
    shorter = data.declared_sample_frame_count < decoded.sample_frame_count
    if rate_mismatch or channel_mismatch or shorter:
        _reject(
            AudioArtifactRejectionReason.METADATA_MISMATCH,
            "$.declared_sample_frame_count",
            "Declared audio metadata does not match decoded WAVE metadata.",
            issue_code="AUDIO_METADATA_MISMATCH",
        )
    truncated = data.declared_sample_frame_count > decoded.sample_frame_count
    if truncated:
        _reject(
            AudioArtifactRejectionReason.TRUNCATED,
            "$.declared_sample_frame_count",
            "Declared frame count exceeds decoded WAVE frame count.",
            issue_code="AUDIO_TRUNCATED",
        )


def _u16le(source: bytes, offset: int) -> int:
    if offset + 2 > len(source):
        _reject(
            AudioArtifactRejectionReason.DECODE_FAILED,
            "$.logical_input",
            "WAVE integer read exceeds input bytes.",
            issue_code="AUDIO_DECODE_FAILED",
        )
    return int.from_bytes(source[offset : offset + 2], "little")


def _u32le(source: bytes, offset: int) -> int:
    if offset + 4 > len(source):
        _reject(
            AudioArtifactRejectionReason.DECODE_FAILED,
            "$.logical_input",
            "WAVE integer read exceeds input bytes.",
            issue_code="AUDIO_DECODE_FAILED",
        )
    return int.from_bytes(source[offset : offset + 4], "little")


def _require_mapping(value: Any, pointer: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _reject(
            AudioArtifactRejectionReason.STRUCTURE_INVALID,
            pointer,
            "Expected an object.",
        )
    if any(type(key) is not str for key in value):
        _reject(
            AudioArtifactRejectionReason.STRUCTURE_INVALID,
            pointer,
            "Object keys must be exact built-in strings.",
        )
    return value


def _require_closed_fields(
    data: Mapping[str, Any],
    required: set[str],
    allowed: set[str],
    pointer: str,
) -> None:
    unknown = set(data) - allowed
    if unknown:
        _reject(
            AudioArtifactRejectionReason.STRUCTURE_INVALID,
            pointer,
            "Unknown fields are forbidden.",
        )
    missing = required - set(data)
    if missing:
        _reject(
            AudioArtifactRejectionReason.STRUCTURE_INVALID,
            pointer,
            "Required fields are missing.",
        )
    for field in required:
        if data[field] is None:
            _reject(
                AudioArtifactRejectionReason.STRUCTURE_INVALID,
                f"{pointer}.{field}" if pointer != "$" else f"$.{field}",
                "Required fields cannot be null.",
            )


def _require_exact_string(value: Any, pointer: str) -> str:
    if type(value) is not str:
        _reject(
            AudioArtifactRejectionReason.STRUCTURE_INVALID,
            pointer,
            "Expected an exact built-in string.",
        )
    _validate_unicode(value, pointer)
    if unicodedata.normalize("NFC", value) != value:
        _reject(
            AudioArtifactRejectionReason.STRUCTURE_INVALID,
            pointer,
            "String must be NFC.",
        )
    return value


def _require_exact_string_without_nfc(value: Any, pointer: str) -> str:
    if type(value) is not str:
        _reject(
            AudioArtifactRejectionReason.STRUCTURE_INVALID,
            pointer,
            "Expected an exact built-in string.",
        )
    _validate_unicode(value, pointer)
    return value


def _require_safe_nfc_string(value: Any, pointer: str) -> str:
    text = _require_exact_string(value, pointer)
    if any(ord(character) == 0 or ord(character) < 0x20 or ord(character) == 0x7F for character in text):
        raise TypeError("NUL/control characters are forbidden.")
    return text


def _require_stable_id(value: Any, pointer: str) -> str:
    text = _require_exact_string(value, pointer)
    if _STABLE_ID_PATTERN.fullmatch(text) is None:
        _reject(
            AudioArtifactRejectionReason.STRUCTURE_INVALID,
            pointer,
            "Value is not a canonical stable ID.",
        )
    return text


def _require_hash(value: Any, pointer: str) -> str:
    text = _require_exact_string(value, pointer)
    if _HASH_PATTERN.fullmatch(text) is None:
        _reject(
            AudioArtifactRejectionReason.STRUCTURE_INVALID,
            pointer,
            "Hash must be sha256:<64 lowercase hex>.",
        )
    return text


def _require_nonnegative_int(value: Any, pointer: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _reject(
            AudioArtifactRejectionReason.STRUCTURE_INVALID,
            pointer,
            "Expected a non-negative integer.",
        )
    return value


def _require_positive_int(value: Any, pointer: str) -> int:
    integer = _require_nonnegative_int(value, pointer)
    if integer == 0:
        _reject(
            AudioArtifactRejectionReason.STRUCTURE_INVALID,
            pointer,
            "Expected a positive integer.",
        )
    return integer


def _require_uint64(value: Any, pointer: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > _UINT64_MAX:
        raise TypeError(f"{pointer} must be an unsigned uint64 integer.")
    return value


def _validate_unicode(value: str, pointer: str) -> None:
    for character in value:
        codepoint = ord(character)
        if (
            0xD800 <= codepoint <= 0xDFFF
            or 0xFDD0 <= codepoint <= 0xFDEF
            or codepoint & 0xFFFF in {0xFFFE, 0xFFFF}
        ):
            _reject(
                AudioArtifactRejectionReason.STRUCTURE_INVALID,
                pointer,
                "Unicode surrogate/noncharacter is forbidden.",
            )


def _validate_extensions(value: Any, pointer: str) -> Mapping[str, Any]:
    data = _require_mapping(value, pointer)
    for key, item in data.items():
        if _EXTENSION_KEY_PATTERN.fullmatch(key) is None:
            _reject(
                AudioArtifactRejectionReason.EXTENSION_INVALID,
                pointer,
                "Extension keys must use the V1 dotted namespace form.",
                issue_code="AUDIO_EXTENSION_SECURITY_VIOLATION",
            )
        _scan_extension_name(key.rsplit("/", 1)[-1], f"{pointer}.{key}")
        _validate_json_extension_value(item, f"{pointer}.{key}")
    return _freeze_json(data)


def _validate_json_extension_value(value: Any, pointer: str) -> None:
    if value is None or type(value) is bool:
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    if isinstance(value, float):
        _extension_reject(pointer)
    if type(value) is str:
        _validate_unicode(value, pointer)
        if _extension_string_violates(value):
            _extension_reject(pointer)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_extension_value(item, f"{pointer}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if type(key) is not str:
                _extension_reject(pointer)
            _scan_extension_name(key, f"{pointer}.{key}")
            _validate_json_extension_value(item, f"{pointer}.{key}")
        return
    _extension_reject(pointer)


def _scan_extension_name(name: str, pointer: str) -> None:
    if name.lower() in _SENSITIVE_EXTENSION_NAMES:
        _extension_reject(pointer)


def _extension_string_violates(value: str) -> bool:
    return (
        "://" in value
        or value.startswith("/")
        or value.startswith("\\")
        or _DRIVE_PREFIX_PATTERN.match(value) is not None
        or any(ord(character) == 0 or ord(character) < 0x20 or ord(character) == 0x7F for character in value)
    )


def _extension_reject(pointer: str) -> None:
    _reject(
        AudioArtifactRejectionReason.EXTENSION_INVALID,
        pointer,
        "Audio extension security validation failed.",
        issue_code="AUDIO_EXTENSION_SECURITY_VIOLATION",
    )


def _path_reject(issue_code: str, pointer: str) -> None:
    _reject(
        AudioArtifactRejectionReason.PATH_INVALID,
        pointer,
        "Audio logical path validation failed.",
        issue_code=issue_code,
    )


def _validate_single_issue_code(code: str) -> None:
    if type(code) is not str or code not in STABLE_ISSUE_CODE_SET:
        raise ValueError("Unknown canonical issue code.")


def _validate_ordered_issue_codes(codes: tuple[str, ...]) -> None:
    seen: set[str] = set()
    for code in codes:
        _validate_single_issue_code(code)
        if code in seen:
            raise ValueError("Duplicate ordered issue code.")
        seen.add(code)


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _logical_input_to_dict(value: SecureAudioInputReference) -> dict[str, Any]:
    return {
        "schema_version": value.schema_version,
        "kind": value.kind,
        "logical_path": value.logical_path,
    }


def _decoded_metadata_to_dict(value: DecodedAudioMetadata) -> dict[str, Any]:
    return {
        field: getattr(value, field)
        for field in DecodedAudioMetadata.__dataclass_fields__
    }


def _artifact_to_dict(value: AudioArtifact) -> dict[str, Any]:
    return {
        "schema_version": value.schema_version,
        "hash_scope_version": value.hash_scope_version,
        "audio_artifact_id": value.audio_artifact_id,
        "audio_artifact_hash": value.audio_artifact_hash,
        "project_id": value.project_id,
        "document_id": value.document_id,
        "narration_revision_id": value.narration_revision_id,
        "narration_revision_hash": value.narration_revision_hash,
        "media_byte_hash": value.media_byte_hash,
        "logical_input": _logical_input_to_dict(value.logical_input),
        "decoded_metadata": _decoded_metadata_to_dict(value.decoded_metadata),
        "extensions": _thaw_json(value.extensions),
    }


def _reject(
    reason: AudioArtifactRejectionReason,
    pointer: str,
    message: str,
    *,
    issue_code: str | None = None,
    ordered_issue_codes: Sequence[str] | None = None,
) -> None:
    raise AudioArtifactContractError(
        reason,
        pointer,
        message,
        issue_code=issue_code,
        ordered_issue_codes=ordered_issue_codes,
    )
