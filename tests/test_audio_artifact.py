from __future__ import annotations

import copy
import gc
import hashlib
import struct
import weakref
from dataclasses import FrozenInstanceError, replace
from enum import Enum
from types import MappingProxyType

import pytest

from engine.contracts import (
    AUDIO_ARTIFACT_HASH_V1,
    AUDIO_ARTIFACT_INPUT_V1,
    AUDIO_ARTIFACT_V1,
    SECURE_AUDIO_INPUT_V1,
    AudioArtifact,
    AudioArtifactContractError,
    AudioArtifactMaterializationRuntime,
    NarrationRevisionBinding,
    SecureAudioInputReference,
    SecureAudioSnapshot,
    SecureOpenEvidence,
    TrustedRootReference,
    materialize_audio_artifact,
    serialize_audio_artifact,
)


FX29_MEDIA_HASH = (
    "sha256:e99281ba3d343314e961f4de365be1f7f226094229bf403e2e902aa709a7b35d"
)
FX29_ARTIFACT_HASH = (
    "sha256:ca80b625935f012e179849bba321cf070ce34f31d41119f6541a6370b337ce2f"
)
FX29_ARTIFACT_ID = "aud_ca80b625935f012e1798"
FX14_MEDIA_HASH = (
    "sha256:7f8301c17450092a2649c727c88807297ad056b8189a6ecd5344577ebc907e91"
)
REVISION_A = "narrev_11111111111111111111"
REVISION_HASH_A = "sha256:" + "1" * 64
REVISION_B = "narrev_22222222222222222222"
REVISION_HASH_B = "sha256:" + "2" * 64
FX29_CANONICAL_BYTES = (
    b'{"audio_artifact_hash":"sha256:ca80b625935f012e179849bba321cf070ce34f31d41119f6541a6370b337ce2f",'
    b'"audio_artifact_id":"aud_ca80b625935f012e1798","decoded_metadata":'
    b'{"channel_count":1,"codec":"PCM","container":"WAVE","duration_us_denominator":1,'
    b'"duration_us_numerator":1000,"endianness":"LITTLE","sample_format":"S16",'
    b'"sample_frame_count":8,"sample_rate_hz":8000},"document_id":"nardoc_audiofx",'
    b'"extensions":{},"hash_scope_version":"audio-artifact-hash-v1","logical_input":'
    b'{"kind":"LOCAL_FILE","logical_path":"audio/narration.wav",'
    b'"schema_version":"SECURE-AUDIO-INPUT-V1"},"media_byte_hash":'
    b'"sha256:e99281ba3d343314e961f4de365be1f7f226094229bf403e2e902aa709a7b35d",'
    b'"narration_revision_hash":"sha256:1111111111111111111111111111111111111111111111111111111111111111",'
    b'"narration_revision_id":"narrev_11111111111111111111","project_id":"prj_audiofx",'
    b'"schema_version":"AUDIO-ARTIFACT-V1"}'
)


class CustomString(str):
    pass


class StringEnum(str, Enum):
    LOCAL = "LOCAL_FILE"


class ArbitraryEnum(Enum):
    LOCAL = "LOCAL_FILE"


def wave_bytes(
    *,
    sample_rate_hz: int,
    channel_count: int,
    sample_frame_count: int,
    audio_format_tag: int = 1,
    bits_per_sample: int = 16,
    extra_chunk: bytes = b"",
) -> bytes:
    data = bytearray()
    for frame in range(sample_frame_count):
        sample = ((frame * 257 + 12345) % 65536) - 32768
        for _channel in range(channel_count):
            data += struct.pack("<h", sample)
    block_align = channel_count * 2
    byte_rate = sample_rate_hz * block_align
    header = (
        b"RIFF"
        + struct.pack("<I", 36 + len(data) + len(extra_chunk))
        + b"WAVEfmt "
        + struct.pack(
            "<IHHIIHH",
            16,
            audio_format_tag,
            channel_count,
            sample_rate_hz,
            byte_rate,
            block_align,
            bits_per_sample,
        )
        + extra_chunk
        + b"data"
        + struct.pack("<I", len(data))
    )
    return header + bytes(data)


def evidence(
    source: bytes,
    *,
    containment_before: bool = True,
    containment_after: bool = True,
    reparse_component_seen: bool = False,
    initial_root_identity: str = "root_identity",
    final_root_identity: str = "root_identity",
    initial_file_identity: str = "file_identity",
    final_file_identity: str = "file_identity",
    final_byte_length: int | None = None,
    final_hash: str | None = None,
    object_replacement_observed: bool = False,
    final_read_byte_length: int | None = None,
) -> SecureOpenEvidence:
    digest = "sha256:" + hashlib.sha256(source).hexdigest()
    final_length = len(source) if final_byte_length is None else final_byte_length
    return SecureOpenEvidence(
        initial_root_identity=initial_root_identity,
        final_root_identity=final_root_identity,
        initial_file_identity=initial_file_identity,
        final_file_identity=final_file_identity,
        initial_byte_length=len(source),
        final_byte_length=final_length,
        containment_before=containment_before,
        containment_after=containment_after,
        reparse_component_seen=reparse_component_seen,
        snapshot_media_byte_hash=digest,
        final_same_object_media_byte_hash=digest if final_hash is None else final_hash,
        object_replacement_observed=object_replacement_observed,
        final_read_byte_length=final_length if final_read_byte_length is None else final_read_byte_length,
    )


class _SecurePathStub:
    _kurgu_secure_audio_reader_v1 = True

    def __init__(
        self,
        source: bytes,
        *,
        open_evidence: SecureOpenEvidence | None = None,
        reverify_evidence: SecureOpenEvidence | None = None,
        open_error: Exception | None = None,
        reverify_error: Exception | None = None,
    ):
        self.source = source
        self.open_evidence = open_evidence or evidence(source)
        self.reverify_evidence = reverify_evidence or evidence(source)
        self.open_error = open_error
        self.reverify_error = reverify_error
        self.access_count = 0
        self.snapshot_read_count = 0
        self.reverify_read_count = 0
        self.opened_segments: tuple[str, ...] | None = None

    def open_snapshot(self, trusted_root, validated_logical_segments):
        self.access_count += 1
        self.opened_segments = validated_logical_segments
        if self.open_error is not None:
            raise self.open_error
        self.snapshot_read_count += 1
        snapshot = SecureAudioSnapshot(
            self.source,
            self.open_evidence,
            self.reverify_evidence,
        )
        if self.reverify_error is None:
            return snapshot

        class FailingSnapshot(SecureAudioSnapshot):
            def reverify_same_object(inner_self):
                self.reverify_read_count += 1
                raise self.reverify_error

        return FailingSnapshot(
            self.source,
            self.open_evidence,
            self.reverify_evidence,
        )


def fx29_bytes() -> bytes:
    return wave_bytes(
        sample_rate_hz=8000,
        channel_count=1,
        sample_frame_count=8,
    )


def fx14_bytes() -> bytes:
    return wave_bytes(
        sample_rate_hz=8000,
        channel_count=1,
        sample_frame_count=12000,
    )


def binding_a() -> NarrationRevisionBinding:
    return NarrationRevisionBinding(
        project_id="prj_audiofx",
        document_id="nardoc_audiofx",
        narration_revision_id=REVISION_A,
        narration_revision_hash=REVISION_HASH_A,
    )


def runtime_for(reader: _SecurePathStub) -> AudioArtifactMaterializationRuntime:
    return AudioArtifactMaterializationRuntime(
        trusted_root=TrustedRootReference("C:/trusted/root"),
        secure_reader=reader,
    )


def fx29_value(**overrides) -> dict:
    value = {
        "schema_version": AUDIO_ARTIFACT_INPUT_V1,
        "project_id": "prj_audiofx",
        "document_id": "nardoc_audiofx",
        "narration_revision_id": REVISION_A,
        "narration_revision_hash": REVISION_HASH_A,
        "logical_input": {
            "schema_version": SECURE_AUDIO_INPUT_V1,
            "kind": "LOCAL_FILE",
            "logical_path": "audio/narration.wav",
        },
        "declared_media_byte_hash": FX29_MEDIA_HASH,
        "declared_sample_rate_hz": 8000,
        "declared_channel_count": 1,
        "declared_sample_frame_count": 8,
        "extensions": {},
    }
    value.update(overrides)
    return value


def materialize(value: dict | None = None, *, reader: _SecurePathStub | None = None):
    active_reader = reader or _SecurePathStub(fx29_bytes())
    return materialize_audio_artifact(
        fx29_value() if value is None else value,
        narration_binding=binding_a(),
        runtime=runtime_for(active_reader),
    )


def assert_rejected_without_artifact(exc_info) -> None:
    assert not hasattr(exc_info.value, "audio_artifact_id")
    assert not hasattr(exc_info.value, "audio_artifact_hash")
    assert not hasattr(exc_info.value, "canonical_bytes")


def test_fx29_audio_materializes_exact_hash_id_and_bytes() -> None:
    source = fx29_bytes()
    reader = _SecurePathStub(source)

    artifact = materialize(reader=reader)

    assert len(source) == 60
    assert "sha256:" + hashlib.sha256(source).hexdigest() == FX29_MEDIA_HASH
    assert artifact.schema_version == AUDIO_ARTIFACT_V1
    assert artifact.hash_scope_version == AUDIO_ARTIFACT_HASH_V1
    assert artifact.media_byte_hash == FX29_MEDIA_HASH
    assert artifact.audio_artifact_hash == FX29_ARTIFACT_HASH
    assert artifact.audio_artifact_id == FX29_ARTIFACT_ID
    assert artifact.decoded_metadata.duration_us_numerator == 1000
    assert artifact.decoded_metadata.duration_us_denominator == 1
    assert serialize_audio_artifact(artifact) == FX29_CANONICAL_BYTES
    assert reader.opened_segments == ("audio", "narration.wav")
    assert reader.access_count == 1
    assert reader.snapshot_read_count == 1


def test_fx14_truncation_rejects_without_artifact_identity() -> None:
    source = fx14_bytes()
    reader = _SecurePathStub(source)
    value = fx29_value(
        declared_media_byte_hash=FX14_MEDIA_HASH,
        declared_sample_frame_count=24000,
    )

    with pytest.raises(AudioArtifactContractError) as exc_info:
        materialize(value, reader=reader)

    assert len(source) == 24044
    assert "sha256:" + hashlib.sha256(source).hexdigest() == FX14_MEDIA_HASH
    assert exc_info.value.ordered_issue_codes == ("AUDIO_TRUNCATED",)
    assert_rejected_without_artifact(exc_info)


def test_fx15_binding_mismatch_happens_before_secure_access() -> None:
    reader = _SecurePathStub(fx29_bytes())
    value = fx29_value(
        narration_revision_id=REVISION_B,
        narration_revision_hash=REVISION_HASH_B,
    )

    with pytest.raises(AudioArtifactContractError) as exc_info:
        materialize(value, reader=reader)

    assert exc_info.value.issue_code == "AUDIO_REVISION_MISMATCH"
    assert reader.access_count == 0
    assert reader.snapshot_read_count == 0
    assert reader.reverify_read_count == 0


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.pop("project_id"),
        lambda value: value.update(extra="forbidden"),
        lambda value: value.update(project_id=None),
    ],
)
def test_missing_unknown_and_null_fields_fail_closed(mutate) -> None:
    value = fx29_value()
    mutate(value)

    with pytest.raises(AudioArtifactContractError) as exc_info:
        materialize(value)

    assert exc_info.value.issue_code is None
    assert exc_info.value.ordered_issue_codes == ()


@pytest.mark.parametrize(
    ("mutate", "replacement"),
    [
        (lambda value, replacement: value.update(schema_version=replacement), CustomString(AUDIO_ARTIFACT_INPUT_V1)),
        (lambda value, replacement: value.update(schema_version=replacement), StringEnum.LOCAL),
        (lambda value, replacement: value.update(schema_version=replacement), ArbitraryEnum.LOCAL),
        (lambda value, replacement: value.update(schema_version=replacement), object()),
        (lambda value, replacement: value.update(schema_version=replacement), b"AUDIO-ARTIFACT-INPUT-V1"),
        (lambda value, replacement: value.update(schema_version=replacement), 1),
        (lambda value, replacement: value.update(schema_version=replacement), True),
        (lambda value, replacement: value.update(schema_version=replacement), []),
        (lambda value, replacement: value.update(schema_version=replacement), {}),
        (lambda value, replacement: value.update(schema_version=replacement), None),
        (
            lambda value, replacement: value["logical_input"].update(schema_version=replacement),
            CustomString(SECURE_AUDIO_INPUT_V1),
        ),
        (
            lambda value, replacement: value["logical_input"].update(schema_version=replacement),
            StringEnum.LOCAL,
        ),
        (
            lambda value, replacement: value["logical_input"].update(schema_version=replacement),
            ArbitraryEnum.LOCAL,
        ),
        (
            lambda value, replacement: value["logical_input"].update(schema_version=replacement),
            object(),
        ),
        (
            lambda value, replacement: value["logical_input"].update(schema_version=replacement),
            b"SECURE-AUDIO-INPUT-V1",
        ),
        (
            lambda value, replacement: value["logical_input"].update(schema_version=replacement),
            1,
        ),
        (
            lambda value, replacement: value["logical_input"].update(schema_version=replacement),
            True,
        ),
        (
            lambda value, replacement: value["logical_input"].update(schema_version=replacement),
            [],
        ),
        (
            lambda value, replacement: value["logical_input"].update(schema_version=replacement),
            {},
        ),
        (
            lambda value, replacement: value["logical_input"].update(schema_version=replacement),
            None,
        ),
        (lambda value, replacement: value["logical_input"].update(kind=replacement), CustomString("LOCAL_FILE")),
        (lambda value, replacement: value["logical_input"].update(kind=replacement), StringEnum.LOCAL),
        (lambda value, replacement: value["logical_input"].update(kind=replacement), ArbitraryEnum.LOCAL),
    ],
)
def test_raw_string_boundary_rejects_subclasses_enums_and_coercions(mutate, replacement) -> None:
    value = fx29_value()
    mutate(value, replacement)

    with pytest.raises(AudioArtifactContractError) as exc_info:
        materialize(value)

    assert exc_info.value.issue_code is None


def test_bool_as_int_and_unsupported_enums_are_rejected() -> None:
    value = fx29_value(declared_channel_count=True)
    with pytest.raises(AudioArtifactContractError):
        materialize(value)

    value = fx29_value(schema_version="AUDIO-ARTIFACT-INPUT-V9")
    with pytest.raises(AudioArtifactContractError) as exc_info:
        materialize(value)
    assert exc_info.value.issue_code == "UNSUPPORTED_CONTRACT_ENUM"

    value = fx29_value()
    value["logical_input"]["kind"] = "REMOTE_URI"
    with pytest.raises(AudioArtifactContractError) as enum_error:
        materialize(value)
    assert enum_error.value.issue_code == "UNSUPPORTED_CONTRACT_ENUM"


@pytest.mark.parametrize(
    ("logical_path", "issue_code"),
    [
        ("//server/share.wav", "PATH_UNC_FORBIDDEN"),
        ("\\\\server\\share.wav", "PATH_UNC_FORBIDDEN"),
        ("//?/C:/audio.wav", "PATH_DEVICE_FORBIDDEN"),
        ("C:/audio.wav", "PATH_TRAVERSAL"),
        ("/audio.wav", "PATH_TRAVERSAL"),
        ("../audio.wav", "PATH_TRAVERSAL"),
        ("audio/clip:ads", "PATH_ADS_FORBIDDEN"),
        ("audio/CON.wav", "PATH_RESERVED_NAME"),
        ("audio/name. ", "PATH_RESERVED_NAME"),
        ("audio//clip.wav", "PATH_SYNTAX_INVALID"),
        ("audio\\clip.wav", "PATH_SYNTAX_INVALID"),
        ("cafe\u0301/clip.wav", "PATH_SYNTAX_INVALID"),
    ],
)
def test_logical_path_lexical_matrix(logical_path: str, issue_code: str) -> None:
    value = fx29_value()
    value["logical_input"]["logical_path"] = logical_path

    with pytest.raises(AudioArtifactContractError) as exc_info:
        materialize(value)

    assert exc_info.value.issue_code == issue_code


@pytest.mark.parametrize(
    ("logical_path", "ordered"),
    [
        ("https://example.com/audio.wav", ("AUDIO_INPUT_URI_FORBIDDEN",)),
        ("https://user@example.com/audio.wav", ("URI_USER_INFO",)),
        ("https://example.com/audio.wav?sig=x", ("URI_SENSITIVE_COMPONENT",)),
        (
            "https://user@example.com/audio.wav?sig=x#frag",
            ("URI_USER_INFO", "URI_SENSITIVE_COMPONENT"),
        ),
    ],
)
def test_uri_boundary_one_and_two_code_behavior(logical_path: str, ordered) -> None:
    value = fx29_value()
    value["logical_input"]["logical_path"] = logical_path

    with pytest.raises(AudioArtifactContractError) as exc_info:
        materialize(value)

    assert exc_info.value.ordered_issue_codes == ordered
    assert logical_path not in str(exc_info.value)


@pytest.mark.parametrize(
    "extensions",
    [
        {"kurgu.audio/uri": "opaque"},
        {"kurgu.audio/meta": {"token": "opaque"}},
        {"kurgu.audio/meta": ["https://example.com/audio.wav"]},
        {"kurgu.audio/meta": {"safe": "C:/secret.wav"}},
        {"kurgu.audio/meta": {"safe": "bad\u0000value"}},
    ],
)
def test_extension_security_recurses_names_and_string_predicates(extensions) -> None:
    value = fx29_value(extensions=extensions)

    with pytest.raises(AudioArtifactContractError) as exc_info:
        materialize(value)

    assert exc_info.value.issue_code == "AUDIO_EXTENSION_SECURITY_VIOLATION"


@pytest.mark.parametrize(
    "sentinel",
    [
        "https://example.invalid/token",
        "/host/path",
        "C:\\secret",
        "bad\u0000key",
        "bad\u001fkey",
        "bad\u007fkey",
        "api_key",
    ],
)
def test_nested_extension_keys_are_screened_without_raw_leakage(sentinel: str) -> None:
    value = fx29_value(extensions={"kurgu.audio/meta": {"safe": {sentinel: "opaque"}}})

    with pytest.raises(AudioArtifactContractError) as exc_info:
        materialize(value)

    error = exc_info.value
    assert error.issue_code == "AUDIO_EXTENSION_SECURITY_VIOLATION"
    visible = (error.pointer, str(error), repr(error), error.issue_code or "")
    assert all(sentinel not in field for field in visible)


@pytest.mark.parametrize("key", [CustomString("safe"), StringEnum.LOCAL])
def test_nested_extension_keys_must_be_exact_builtin_strings(key) -> None:
    value = fx29_value(extensions={"kurgu.audio/meta": {key: "opaque"}})

    with pytest.raises(AudioArtifactContractError) as exc_info:
        materialize(value)

    assert exc_info.value.issue_code == "AUDIO_EXTENSION_SECURITY_VIOLATION"


@pytest.mark.parametrize(
    ("source", "issue_code"),
    [
        (b"", "AUDIO_EMPTY"),
        (b"not-wave", "AUDIO_DECODE_FAILED"),
        (
            wave_bytes(sample_rate_hz=8000, channel_count=1, sample_frame_count=8)
            + b"trail",
            "AUDIO_DECODE_FAILED",
        ),
        (
            wave_bytes(
                sample_rate_hz=8000,
                channel_count=1,
                sample_frame_count=0,
                bits_per_sample=8,
            ),
            "AUDIO_FORMAT_UNSUPPORTED",
        ),
        (
            wave_bytes(
                sample_rate_hz=8000,
                channel_count=1,
                sample_frame_count=8,
                bits_per_sample=8,
            ),
            "AUDIO_FORMAT_UNSUPPORTED",
        ),
        (
            wave_bytes(sample_rate_hz=8000, channel_count=1, sample_frame_count=0),
            "AUDIO_EMPTY",
        ),
    ],
)
def test_wave_decode_empty_and_format_boundaries(source: bytes, issue_code: str) -> None:
    value = fx29_value(declared_media_byte_hash="sha256:" + hashlib.sha256(source).hexdigest())

    with pytest.raises(AudioArtifactContractError) as exc_info:
        materialize(value, reader=_SecurePathStub(source))

    assert exc_info.value.issue_code == issue_code


def test_byte_hash_metadata_and_shorter_declaration_precedence() -> None:
    with pytest.raises(AudioArtifactContractError) as hash_error:
        materialize(fx29_value(declared_media_byte_hash="sha256:" + "0" * 64))
    assert hash_error.value.issue_code == "AUDIO_BYTE_HASH_MISMATCH"

    with pytest.raises(AudioArtifactContractError) as metadata_error:
        materialize(fx29_value(declared_sample_rate_hz=16000))
    assert metadata_error.value.issue_code == "AUDIO_METADATA_MISMATCH"

    with pytest.raises(AudioArtifactContractError) as shorter_error:
        materialize(fx29_value(declared_sample_frame_count=7))
    assert shorter_error.value.issue_code == "AUDIO_METADATA_MISMATCH"


def test_riff_data_bound_failure_is_stable_size_code() -> None:
    source = (
        b"RIFF"
        + struct.pack("<I", 36)
        + b"WAVEfmt "
        + struct.pack("<IHHIIHH", 16, 1, 1, 8000, 16000, 2, 16)
        + b"data"
        + struct.pack("<I", 4_294_967_260)
    )
    value = fx29_value(declared_media_byte_hash="sha256:" + hashlib.sha256(source).hexdigest())

    with pytest.raises(AudioArtifactContractError) as exc_info:
        materialize(value, reader=_SecurePathStub(source))

    assert exc_info.value.issue_code == "AUDIO_SIZE_OUT_OF_BOUNDS"


def test_open_read_containment_identity_and_replacement_taxonomy() -> None:
    with pytest.raises(AudioArtifactContractError) as open_error:
        materialize(reader=_SecurePathStub(fx29_bytes(), open_error=OSError("secret path")))
    assert open_error.value.issue_code == "AUDIO_INPUT_OPEN_FAILED"
    assert "secret path" not in str(open_error.value)

    bad_open_evidence = evidence(fx29_bytes())
    bad_open_evidence = SecureOpenEvidence(
        **{**bad_open_evidence.__dict__, "initial_byte_length": 59}
    )
    with pytest.raises(AudioArtifactContractError) as mismatch_error:
        materialize(reader=_SecurePathStub(fx29_bytes(), open_evidence=bad_open_evidence))
    assert mismatch_error.value.issue_code == "AUDIO_INPUT_READ_FAILED"

    final = evidence(fx29_bytes(), final_read_byte_length=59)
    with pytest.raises(AudioArtifactContractError) as second_read_error:
        materialize(reader=_SecurePathStub(fx29_bytes(), reverify_evidence=final))
    assert second_read_error.value.issue_code == "AUDIO_INPUT_READ_FAILED"

    final = evidence(fx29_bytes(), containment_after=False)
    with pytest.raises(AudioArtifactContractError) as containment_error:
        materialize(reader=_SecurePathStub(fx29_bytes(), reverify_evidence=final))
    assert containment_error.value.issue_code == "SECURE_INPUT_CONTAINMENT_FAILED"

    final = evidence(fx29_bytes(), final_file_identity="changed")
    with pytest.raises(AudioArtifactContractError) as identity_error:
        materialize(reader=_SecurePathStub(fx29_bytes(), reverify_evidence=final))
    assert identity_error.value.issue_code == "SECURE_INPUT_IDENTITY_CHANGED"

    final = evidence(fx29_bytes(), object_replacement_observed=True)
    with pytest.raises(AudioArtifactContractError) as replacement_error:
        materialize(reader=_SecurePathStub(fx29_bytes(), reverify_evidence=final))
    assert replacement_error.value.issue_code == "SECURE_INPUT_IDENTITY_CHANGED"


def test_second_read_exception_is_read_failed_and_does_not_reopen_path() -> None:
    reader = _SecurePathStub(fx29_bytes(), reverify_error=OSError("lost handle"))

    with pytest.raises(AudioArtifactContractError) as exc_info:
        materialize(reader=reader)

    assert exc_info.value.issue_code == "AUDIO_INPUT_READ_FAILED"
    assert reader.access_count == 1
    assert reader.snapshot_read_count == 1
    assert reader.reverify_read_count == 1


def test_no_sensitive_root_path_uri_or_evidence_serializes() -> None:
    value = fx29_value(extensions={"kurgu.audio/safe_note": "opaque"})
    artifact = materialize(value)
    serialized = serialize_audio_artifact(artifact)

    assert b"C:/trusted/root" not in serialized
    assert b"root_identity" not in serialized
    assert b"file_identity" not in serialized
    assert b"https://" not in serialized


def test_models_are_deeply_immutable_and_extensions_excluded_from_identity() -> None:
    base = materialize()
    with pytest.raises(FrozenInstanceError):
        base.project_id = "prj_changed"
    assert isinstance(base.extensions, MappingProxyType)

    with_ext = materialize(
        fx29_value(extensions={"kurgu.audio/safe_note": {"nested": ["ok"]}})
    )
    assert with_ext.audio_artifact_hash == base.audio_artifact_hash
    assert with_ext.audio_artifact_id == base.audio_artifact_id
    assert serialize_audio_artifact(with_ext) != serialize_audio_artifact(base)
    assert isinstance(with_ext.extensions["kurgu.audio/safe_note"], MappingProxyType)
    assert isinstance(with_ext.extensions["kurgu.audio/safe_note"]["nested"], tuple)

    original_extensions = {"kurgu.audio/safe_note": {"nested": ["ok"]}}
    frozen = materialize(fx29_value(extensions=original_extensions))
    original_extensions["kurgu.audio/safe_note"]["nested"].append("changed")
    assert frozen.extensions["kurgu.audio/safe_note"]["nested"] == ("ok",)


def test_serialize_rejects_forged_and_copied_audio_artifacts() -> None:
    genuine = materialize()
    assert serialize_audio_artifact(genuine) == FX29_CANONICAL_BYTES

    forged = AudioArtifact(
        schema_version=genuine.schema_version,
        hash_scope_version=genuine.hash_scope_version,
        audio_artifact_id=genuine.audio_artifact_id,
        audio_artifact_hash=genuine.audio_artifact_hash,
        project_id=genuine.project_id,
        document_id=genuine.document_id,
        narration_revision_id=genuine.narration_revision_id,
        narration_revision_hash=genuine.narration_revision_hash,
        media_byte_hash=genuine.media_byte_hash,
        logical_input=genuine.logical_input,
        decoded_metadata=genuine.decoded_metadata,
        extensions={"kurgu.audio/safe_note": {"nested": ["ok"]}},
    )
    with pytest.raises(TypeError):
        serialize_audio_artifact(forged)
    assert isinstance(forged.extensions, MappingProxyType)
    assert isinstance(forged.extensions["kurgu.audio/safe_note"], MappingProxyType)

    copied = replace(genuine)
    with pytest.raises(TypeError):
        serialize_audio_artifact(copied)

    fake_identity = replace(
        genuine,
        audio_artifact_id="aud_fakefakefakefakefake",
        audio_artifact_hash="sha256:" + "f" * 64,
    )
    with pytest.raises(TypeError):
        serialize_audio_artifact(fake_identity)

    new_instance = object.__new__(AudioArtifact)
    object.__setattr__(new_instance, "schema_version", AUDIO_ARTIFACT_V1)
    with pytest.raises(TypeError):
        serialize_audio_artifact(new_instance)


def test_materialized_artifact_provenance_does_not_hold_strong_reference() -> None:
    def build_reference() -> weakref.ReferenceType[AudioArtifact]:
        artifact = materialize()
        assert serialize_audio_artifact(artifact) == FX29_CANONICAL_BYTES
        return weakref.ref(artifact)

    artifact_reference = build_reference()
    gc.collect()

    assert artifact_reference() is None


def test_nominal_narration_binding_and_runtime_boundaries_reject_lookalikes() -> None:
    class FakeRevision:
        project_id = "prj_audiofx"
        document_id = "nardoc_audiofx"
        revision_id = REVISION_A
        revision_hash = REVISION_HASH_A

    class FakeBinding:
        project_id = "prj_audiofx"
        document_id = "nardoc_audiofx"
        narration_revision_id = REVISION_A
        narration_revision_hash = REVISION_HASH_A

    class FakeRuntime:
        trusted_root = TrustedRootReference("C:/trusted/root")
        secure_reader = _SecurePathStub(fx29_bytes())

    class FakeRoot:
        canonical_absolute_root = "C:/trusted/root"

    class FakeReader:
        access_count = 0
        snapshot_read_count = 0
        reverify_read_count = 0

        def open_snapshot(self, trusted_root, validated_logical_segments):
            raise AssertionError("fake reader must not be trusted")

    reader = _SecurePathStub(fx29_bytes())
    assert materialize(reader=reader).audio_artifact_id == FX29_ARTIFACT_ID

    with pytest.raises(TypeError):
        NarrationRevisionBinding.from_validated_revision(FakeRevision())
    with pytest.raises(TypeError):
        NarrationRevisionBinding.from_validated_revision({"revision_id": REVISION_A})
    with pytest.raises(TypeError):
        materialize_audio_artifact(
            fx29_value(),
            narration_binding=FakeBinding(),
            runtime=runtime_for(_SecurePathStub(fx29_bytes())),
        )
    with pytest.raises(TypeError):
        materialize_audio_artifact(
            fx29_value(),
            narration_binding=binding_a(),
            runtime=FakeRuntime(),
        )
    with pytest.raises(TypeError):
        AudioArtifactMaterializationRuntime(
            trusted_root=FakeRoot(),
            secure_reader=_SecurePathStub(fx29_bytes()),
        )
    with pytest.raises(TypeError):
        AudioArtifactMaterializationRuntime(
            trusted_root=TrustedRootReference("C:/trusted/root"),
            secure_reader=FakeReader(),
        )


def test_public_model_runtime_boundaries() -> None:
    reference = SecureAudioInputReference(
        schema_version=SECURE_AUDIO_INPUT_V1,
        kind="LOCAL_FILE",
        logical_path="audio/narration.wav",
    )
    assert reference.kind == "LOCAL_FILE"
    with pytest.raises(TypeError):
        NarrationRevisionBinding.from_validated_revision({"revision_id": REVISION_A})
    with pytest.raises(TypeError):
        serialize_audio_artifact(copy.deepcopy(fx29_value()))
