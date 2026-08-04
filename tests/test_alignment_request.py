from __future__ import annotations

import copy
import dataclasses
import gc
import hashlib
import json
import weakref
from collections.abc import Mapping
from dataclasses import replace
from enum import Enum

import pytest

import engine.contracts.alignment as alignment_contracts
import engine.contracts.audio as audio_contracts
import engine.contracts.narration as narration_contracts
import engine.contracts.temporal as temporal_contracts
from engine.contracts import (
    AlignmentRequest,
    AlignmentRequestContractError,
    AlignmentRequestMode,
    AlignmentRequestRejectionReason,
    AudioArtifact,
    CanonicalNarrationDocument,
    CanonicalRawPackage,
    NarrationRevision,
    STABLE_ISSUE_CODES,
    materialize_alignment_request,
    serialize_alignment_request,
)
from engine.contracts.audio import (
    NarrationRevisionBinding,
    materialize_audio_artifact,
)
from tests.test_audio_artifact import (
    _SecurePathStub,
    fx29_bytes,
    fx29_value,
    runtime_for,
)
from tests.test_canonical_narration import materialize_fx34
from tests.test_temporal_raw_package import (
    FX20_CANONICAL_BYTES,
    FX20_CANONICAL_HASH,
    canonicalize_fx20,
)


FX_ARQ_01_PROJECTION_BYTES = (
    b'{"adapter_capability":{"adapter_id":"adapter_fxarq","adapter_version":"1.0.0",'
    b'"confidence_output":"SUPPORTED","language_tag":"en","license_class":"LOCAL",'
    b'"media_type":"audio/wav","mode":"LOCAL","network_access":"FORBIDDEN",'
    b'"schema_version":"ADAPTER-CAPABILITY-V1"},"audio_artifact_hash":'
    b'"sha256:417ef497d9ac4baeb067908ca5235c79a272899e8bed7ffd5862e9b9c6d06f28",'
    b'"audio_artifact_id":"aud_417ef497d9ac4baeb067","document_id":"nardoc_fx34",'
    b'"hash_scope_version":"ALIGNMENT-REQUEST-HASH-V1","mode":"LOCAL",'
    b'"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0",'
    b'"narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34",'
    b'"schema_version":"ALIGNMENT-REQUEST-V1","temporal_raw_package_hash":'
    b'"sha256:4c33882460f8cd26bd773a939bfd3e789edea04b28eaad88974b0e808754983e",'
    b'"transcript_reference":{"narration_revision_hash":'
    b'"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0",'
    b'"narration_revision_id":"narrev_d60d7ae087efb0e309d4",'
    b'"text_scope":"CANONICAL_NARRATION"}}'
)
FX_ARQ_01_ENVELOPE_BYTES = (
    b'{"adapter_capability":{"adapter_id":"adapter_fxarq","adapter_version":"1.0.0",'
    b'"confidence_output":"SUPPORTED","language_tag":"en","license_class":"LOCAL",'
    b'"media_type":"audio/wav","mode":"LOCAL","network_access":"FORBIDDEN",'
    b'"schema_version":"ADAPTER-CAPABILITY-V1"},"alignment_request_hash":'
    b'"bfd2a97af22b1f105c2ebe9356ce2fe684b0add89be14fea09e6b21cfbe54e51",'
    b'"alignment_request_id":"arq_bfd2a97af22b1f105c2ebe9356ce2fe6",'
    b'"audio_artifact_hash":"sha256:417ef497d9ac4baeb067908ca5235c79a272899e8bed7ffd5862e9b9c6d06f28",'
    b'"audio_artifact_id":"aud_417ef497d9ac4baeb067","document_id":"nardoc_fx34",'
    b'"hash_scope_version":"ALIGNMENT-REQUEST-HASH-V1","mode":"LOCAL",'
    b'"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0",'
    b'"narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34",'
    b'"schema_version":"ALIGNMENT-REQUEST-V1","temporal_raw_package_hash":'
    b'"sha256:4c33882460f8cd26bd773a939bfd3e789edea04b28eaad88974b0e808754983e",'
    b'"transcript_reference":{"narration_revision_hash":'
    b'"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0",'
    b'"narration_revision_id":"narrev_d60d7ae087efb0e309d4",'
    b'"text_scope":"CANONICAL_NARRATION"}}'
)
FX_ARQ_01_HASH = (
    "bfd2a97af22b1f105c2ebe9356ce2fe684b0add89be14fea09e6b21cfbe54e51"
)
FX_ARQ_01_ID = "arq_bfd2a97af22b1f105c2ebe9356ce2fe6"
FX_ARQ_01_PROJECTION_LENGTH = 1034
FX_ARQ_01_ENVELOPE_LENGTH = 1188
FX_ARQ_01_ENVELOPE_SHA256 = (
    "b2b0d24b02932b90c315bae348071aba2d3295d1f8d12281feb9f100e8a8ea45"
)
PRE_SLICE4_PUBLIC_EXPORTS = frozenset(
    {
        "AUDIO_ARTIFACT_HASH_V1",
        "AUDIO_ARTIFACT_INPUT_V1",
        "AUDIO_ARTIFACT_V1",
        "AudioArtifact",
        "AudioArtifactContractError",
        "AudioArtifactMaterializationInput",
        "AudioArtifactMaterializationRuntime",
        "ArtifactRecord",
        "Asset",
        "Beat",
        "CANONICAL_NARRATION_DOCUMENT_V1",
        "NARRATION_LINEAGE_V1",
        "CanonicalNarrationDocument",
        "CanonicalNarrationMaterialization",
        "CanonicalTextToken",
        "CanonicalWord",
        "CanonicalRawPackage",
        "Chapter",
        "DomainPack",
        "DomainPackError",
        "DomainPackManifest",
        "DomainPackRegistry",
        "DomainPolicyResolver",
        "DomainPolicySnapshot",
        "DomainProfile",
        "DecodedAudioMetadata",
        "EditorialSequence",
        "EventEnvelope",
        "LoadedWorkspace",
        "LineageNodeType",
        "NARRATION_REVISION_HASH_V1",
        "NARRATION_REVISION_V1",
        "NORMALIZATION_PROFILE_HASH_V1",
        "NarrationContractError",
        "NarrationLineageManifest",
        "NarrationParagraph",
        "NarrationRejectionReason",
        "NarrationRevision",
        "NarrationRevisionBinding",
        "NarrationSection",
        "NarrationSentence",
        "NodeLineageRecord",
        "NodeLineageRelation",
        "NormalizationProfileRef",
        "Project",
        "RetentionPolicy",
        "RawPackageRejectionReason",
        "SECURE_AUDIO_INPUT_V1",
        "SchemaCatalog",
        "SecureAudioInputReference",
        "SecureAudioReader",
        "SecureAudioSnapshot",
        "SecureOpenEvidence",
        "STABLE_ISSUE_CODES",
        "SpokenFormOverride",
        "SpokenFormOverrideSource",
        "TRP_RAW_V1",
        "TemporalRawPackageError",
        "TokenKind",
        "TrustedRootReference",
        "TypedNodeReference",
        "ValidationIssue",
        "ValidationResult",
        "Workspace",
        "WorkspaceLoader",
        "WordRangeConsumer",
        "WordRangeReference",
        "canonical_json",
        "canonicalize_temporal_raw_package",
        "load_temporal_raw_package",
        "materialize_canonical_narration",
        "materialize_audio_artifact",
        "normalization_profile_hash",
        "policy_snapshot_hash",
        "resolve_word_range",
        "serialize_audio_artifact",
        "validate_artifact_graph",
        "validate_issue_codes",
        "validate_retention_policy",
    }
)
SLICE4_PUBLIC_EXPORTS = frozenset(
    {
        "AlignmentRequestMode",
        "AdapterCapability",
        "CanonicalTranscriptReference",
        "AlignmentRequest",
        "AlignmentRequestRejectionReason",
        "AlignmentRequestContractError",
        "materialize_alignment_request",
        "serialize_alignment_request",
    }
)
SLICE5_PUBLIC_EXPORTS = frozenset(
    {
        "ADAPTER_EXECUTION_V1",
        "ADAPTER_EXECUTION_HASH_V1",
        "PAID_FALLBACK_AUTHORIZATION_EVIDENCE_V1",
        "REPLAY_EVIDENCE_V1",
        "CONFIDENCE_AVAILABILITY_EVIDENCE_V1",
        "AdapterExecutionMode",
        "AdapterExecutionStatus",
        "PaidFallbackAuthorizationSource",
        "PaidFallbackAuthorizationDecision",
        "ConfidenceAvailability",
        "PaidFallbackAuthorizationEvidence",
        "ReplayEvidence",
        "ConfidenceAvailabilityEvidence",
        "AdapterExecution",
        "AdapterExecutionRejectionReason",
        "AdapterExecutionContractError",
        "materialize_adapter_execution",
        "load_adapter_execution",
        "serialize_adapter_execution",
    }
)
ALIGNMENT_RESULT_PUBLIC_EXPORTS = frozenset(
    {
        "ALIGNMENT_RESULT_V1",
        "ALIGNMENT_RESULT_HASH_V1",
        "ALIGNMENT_TOKEN_OBSERVATION_V1",
        "TIMING_ORIGIN_EVIDENCE_V1",
        "TIMING_ORIGIN_EVIDENCE_HASH_V1",
        "AlignmentTimingSource",
        "AlignmentResultRejectionReason",
        "TimingOriginEvidence",
        "WordTiming",
        "AlignmentResult",
        "AlignmentResultContractError",
        "load_repository_timing_origin_evidence",
        "materialize_alignment_result",
        "load_alignment_result",
        "serialize_alignment_result",
    }
)
CAPTION_GROUPS_PUBLIC_EXPORTS = frozenset(
    {
        "CAPTION_GROUP_V1",
        "CAPTION_GROUP_HASH_V1",
        "CAPTION_GROUPS_V1",
        "CAPTION_GROUPS_HASH_V1",
        "PHRASE_GROUPING_POLICY_V1",
        "CaptionGroupWordCountPolicy",
        "CaptionGroupingRejectionReason",
        "CaptionGroup",
        "CaptionGroupsArtifact",
        "CaptionGroupsContractError",
        "compile_caption_groups",
        "load_caption_groups",
        "serialize_caption_groups",
    }
)
PRE_SLICE4_STABLE_ISSUE_CODES = frozenset(
    {
        "ADAPTER_FAILURE",
        "ADAPTER_PRECISION_OVERSTATED",
        "ADAPTER_UNSUPPORTED_LANGUAGE",
        "AUDIO_BYTE_HASH_MISMATCH",
        "AUDIO_DECODE_FAILED",
        "AUDIO_EMPTY",
        "AUDIO_EXTENSION_SECURITY_VIOLATION",
        "AUDIO_FORMAT_UNSUPPORTED",
        "AUDIO_INPUT_OPEN_FAILED",
        "AUDIO_INPUT_READ_FAILED",
        "AUDIO_INPUT_URI_FORBIDDEN",
        "AUDIO_METADATA_MISMATCH",
        "AUDIO_REVISION_MISMATCH",
        "AUDIO_SIZE_OUT_OF_BOUNDS",
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
        "PATH_SYNTAX_INVALID",
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
    }
)
SLICE4_STABLE_ISSUE_CODES = frozenset(
    {
        "ALIGNMENT_REQUEST_WIRE_INVALID",
        "ALIGNMENT_REQUEST_UNSUPPORTED_VALUE",
        "ALIGNMENT_REQUEST_LINEAGE_MISMATCH",
        "ALIGNMENT_REQUEST_MODE_PRESENCE_MISMATCH",
        "ALIGNMENT_REQUEST_TRANSCRIPT_INVALID",
        "ALIGNMENT_REQUEST_AUTHORIZATION_FORBIDDEN",
        "ALIGNMENT_REQUEST_CAPABILITY_INVALID",
        "ALIGNMENT_REQUEST_MODE_CAPABILITY_MISMATCH",
        "ALIGNMENT_REQUEST_EXTENSIONS_FORBIDDEN",
        "ALIGNMENT_REQUEST_SENSITIVE_DATA",
        "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
    }
)


class CustomString(str):
    pass


class StringEnum(str, Enum):
    LOCAL = "LOCAL"


class ArbitraryEnum(Enum):
    LOCAL = "LOCAL"


def _dependencies():
    raw = canonicalize_fx20()
    narration = materialize_fx34()
    source = fx29_bytes()
    value = fx29_value(
        project_id=narration.revision.project_id,
        document_id=narration.revision.document_id,
        narration_revision_id=narration.revision.revision_id,
        narration_revision_hash=narration.revision.revision_hash,
        declared_media_byte_hash="sha256:" + hashlib.sha256(source).hexdigest(),
    )
    artifact = materialize_audio_artifact(
        value,
        narration_binding=NarrationRevisionBinding.from_validated_revision(
            narration.revision
        ),
        runtime=runtime_for(_SecurePathStub(source)),
    )
    return raw, narration.document, narration.revision, artifact


def _fixture_canonical_bytes(value: Mapping) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fixture_identity_digest(value: Mapping) -> str:
    projection = {
        "adapter_capability": dict(value["adapter_capability"]),
        "audio_artifact_hash": value["audio_artifact_hash"],
        "audio_artifact_id": value["audio_artifact_id"],
        "document_id": value["document_id"],
        "hash_scope_version": value["hash_scope_version"],
        "mode": value["mode"],
        "narration_revision_hash": value["narration_revision_hash"],
        "narration_revision_id": value["narration_revision_id"],
        "project_id": value["project_id"],
        "schema_version": value["schema_version"],
        "temporal_raw_package_hash": value["temporal_raw_package_hash"],
        "transcript_reference": (
            None
            if value["transcript_reference"] is None
            else dict(value["transcript_reference"])
        ),
    }
    return hashlib.sha256(_fixture_canonical_bytes(projection)).hexdigest()


def _raw_request(
    *,
    mode: str = "LOCAL",
    adapter_mode: str | None = None,
    transcript_reference=...,
    overrides: dict | None = None,
    dependencies=None,
) -> tuple[dict, tuple]:
    deps = _dependencies() if dependencies is None else dependencies
    raw, document, revision, artifact = deps
    if transcript_reference is ...:
        transcript_reference = {
            "narration_revision_id": revision.revision_id,
            "narration_revision_hash": revision.revision_hash,
            "text_scope": "CANONICAL_NARRATION",
        }
    capability = {
        "schema_version": "ADAPTER-CAPABILITY-V1",
        "adapter_id": "adapter_fxarq",
        "adapter_version": "1.0.0",
        "mode": mode if adapter_mode is None else adapter_mode,
        "language_tag": document.language,
        "media_type": "audio/wav",
        "confidence_output": "SUPPORTED",
        "network_access": "REQUIRED" if mode == "FREE_API" else "FORBIDDEN",
        "license_class": {
            "LOCAL": "LOCAL",
            "REPLAY": "REPLAY",
            "FREE_API": "FREE",
            "MANUAL_UI": "MANUAL",
        }.get(mode, "LOCAL"),
    }
    value = {
        "schema_version": "ALIGNMENT-REQUEST-V1",
        "hash_scope_version": "ALIGNMENT-REQUEST-HASH-V1",
        "alignment_request_id": FX_ARQ_01_ID,
        "alignment_request_hash": FX_ARQ_01_HASH,
        "project_id": revision.project_id,
        "document_id": revision.document_id,
        "temporal_raw_package_hash": raw.canonical_hash,
        "narration_revision_id": revision.revision_id,
        "narration_revision_hash": revision.revision_hash,
        "audio_artifact_id": artifact.audio_artifact_id,
        "audio_artifact_hash": artifact.audio_artifact_hash,
        "mode": mode,
        "adapter_capability": capability,
        "transcript_reference": transcript_reference,
    }
    if overrides:
        value.update(overrides)
    non_golden_fixture = (
        mode != "LOCAL"
        or adapter_mode is not None
        or transcript_reference is None
    )
    if non_golden_fixture and not (
        overrides
        and (
            "alignment_request_hash" in overrides
            or "alignment_request_id" in overrides
        )
    ):
        digest = _fixture_identity_digest(value)
        value["alignment_request_hash"] = digest
        value["alignment_request_id"] = "arq_" + digest[:32]
    return value, deps


def _materialize(value: dict | None = None, *, dependencies=None):
    if value is None:
        value, dependencies = _raw_request(dependencies=dependencies)
    raw, document, revision, artifact = dependencies or _dependencies()
    return materialize_alignment_request(
        value,
        temporal_raw_package=raw,
        narration_document=document,
        narration_revision=revision,
        audio_artifact=artifact,
    )


def _assert_error(exc_info, reason, issue_code, pointer) -> None:
    assert type(exc_info.value) is AlignmentRequestContractError
    assert exc_info.value.reason is reason
    assert exc_info.value.issue_code == issue_code
    assert exc_info.value.pointer == pointer
    assert not hasattr(exc_info.value, "alignment_request_id")
    assert not hasattr(exc_info.value, "alignment_request_hash")
    assert not hasattr(exc_info.value, "canonical_bytes")


def _collect_until_dead(reference: weakref.ReferenceType[object]) -> None:
    for _ in range(5):
        if reference() is None:
            return
        gc.collect()
    assert reference() is None


def _clone_dataclass_identity(value):
    clone = object.__new__(type(value))
    for field in dataclasses.fields(value):
        object.__setattr__(
            clone,
            field.name,
            object.__getattribute__(value, field.name),
        )
    return clone


def _is_genuine_dependency(value) -> bool:
    return (
        temporal_contracts._is_materialized_raw_package(value)
        or narration_contracts._is_materialized_narration_document(value)
        or narration_contracts._is_materialized_narration_revision(value)
        or audio_contracts._is_materialized_artifact(value)
    )


def test_fx_arq_01_materializes_exact_golden_request() -> None:
    deps = _dependencies()
    request_value, _ = _raw_request(dependencies=deps)
    request = _materialize(request_value, dependencies=deps)

    assert temporal_contracts._is_materialized_raw_package(deps[0])
    assert narration_contracts._is_materialized_narration_document(deps[1])
    assert narration_contracts._is_materialized_narration_revision(deps[2])
    assert audio_contracts._is_materialized_artifact(deps[3])
    parsed = alignment_contracts._parse_alignment_request(request_value)
    projection = alignment_contracts._identity_projection(
        parsed,
        mode=request.mode,
        capability=request.adapter_capability,
        transcript=request.transcript_reference,
    )
    projection_bytes = alignment_contracts.encode_canonical_json_bytes(projection)
    assert len(FX_ARQ_01_PROJECTION_BYTES) == FX_ARQ_01_PROJECTION_LENGTH
    assert hashlib.sha256(FX_ARQ_01_PROJECTION_BYTES).hexdigest() == FX_ARQ_01_HASH
    assert len(FX_ARQ_01_ENVELOPE_BYTES) == FX_ARQ_01_ENVELOPE_LENGTH
    assert (
        hashlib.sha256(FX_ARQ_01_ENVELOPE_BYTES).hexdigest()
        == FX_ARQ_01_ENVELOPE_SHA256
    )
    assert FX_ARQ_01_ID == "arq_" + FX_ARQ_01_HASH[:32]
    assert projection_bytes == FX_ARQ_01_PROJECTION_BYTES
    assert len(projection_bytes) == FX_ARQ_01_PROJECTION_LENGTH
    assert request.alignment_request_hash == FX_ARQ_01_HASH
    assert request.alignment_request_id == FX_ARQ_01_ID
    envelope_bytes = serialize_alignment_request(request)
    assert envelope_bytes == FX_ARQ_01_ENVELOPE_BYTES
    assert len(envelope_bytes) == FX_ARQ_01_ENVELOPE_LENGTH
    assert hashlib.sha256(envelope_bytes).hexdigest() == FX_ARQ_01_ENVELOPE_SHA256
    assert alignment_contracts._is_materialized_alignment_request(request)


def test_dependency_preflight_rejects_wrong_types_and_forgeries() -> None:
    raw, document, revision, artifact = _dependencies()
    adversaries = [
        ("temporal_raw_package", object(), document, revision, artifact),
        ("narration_document", raw, object(), revision, artifact),
        ("narration_revision", raw, document, object(), artifact),
        ("audio_artifact", raw, document, revision, object()),
        (
            "temporal_raw_package",
            CanonicalRawPackage(FX20_CANONICAL_BYTES, FX20_CANONICAL_HASH),
            document,
            revision,
            artifact,
        ),
        (
            "narration_document",
            raw,
            _clone_dataclass_identity(document),
            revision,
            artifact,
        ),
        (
            "narration_revision",
            raw,
            document,
            _clone_dataclass_identity(revision),
            artifact,
        ),
        (
            "audio_artifact",
            raw,
            document,
            revision,
            _clone_dataclass_identity(artifact),
        ),
    ]
    value, _ = _raw_request(dependencies=(raw, document, revision, artifact))

    for expected_name, dep_raw, dep_doc, dep_rev, dep_art in adversaries:
        with pytest.raises(TypeError, match=expected_name):
            materialize_alignment_request(
                value,
                temporal_raw_package=dep_raw,
                narration_document=dep_doc,
                narration_revision=dep_rev,
                audio_artifact=dep_art,
            )


def test_dependency_preflight_copy_identity_semantics() -> None:
    deps = _dependencies()
    request_value, _ = _raw_request(dependencies=deps)

    for index, original in enumerate(deps):
        copied_values = [copy.copy(original)]
        try:
            copied_values.append(copy.deepcopy(original))
        except TypeError:
            assert _is_genuine_dependency(original)
        for copied in copied_values:
            active = list(deps)
            active[index] = copied
            if copied is original:
                _materialize(request_value, dependencies=tuple(active))
            else:
                with pytest.raises(TypeError):
                    _materialize(request_value, dependencies=tuple(active))
    _materialize(request_value, dependencies=deps)


def test_dependency_preflight_stops_before_raw_and_lineage_access() -> None:
    class BombMapping(Mapping):
        touched = False

        def __iter__(self):
            self.touched = True
            raise AssertionError("raw request was accessed")

        def __len__(self):
            self.touched = True
            raise AssertionError("raw request was accessed")

        def __getitem__(self, key):
            self.touched = True
            raise AssertionError("raw request was accessed")

    bomb = BombMapping()
    _, document, revision, artifact = _dependencies()

    with pytest.raises(TypeError, match="temporal_raw_package"):
        materialize_alignment_request(
            bomb,
            temporal_raw_package=object(),
            narration_document=document,
            narration_revision=revision,
            audio_artifact=artifact,
        )
    assert not bomb.touched


@pytest.mark.parametrize(
    ("name", "mutate", "reason", "issue_code", "pointer"),
    [
        (
            "FX-ARQ-02",
            lambda value: value.update(extra="forbidden"),
            AlignmentRequestRejectionReason.STRUCTURE_INVALID,
            "ALIGNMENT_REQUEST_WIRE_INVALID",
            "/extra",
        ),
        (
            "FX-ARQ-03",
            lambda value: value.update(schema_version="ALIGNMENT-REQUEST-V9"),
            AlignmentRequestRejectionReason.UNSUPPORTED_VALUE,
            "ALIGNMENT_REQUEST_UNSUPPORTED_VALUE",
            "/schema_version",
        ),
        (
            "FX-ARQ-04",
            lambda value: value.update(temporal_raw_package_hash="sha256:" + "0" * 64),
            AlignmentRequestRejectionReason.LINEAGE_MISMATCH,
            "ALIGNMENT_REQUEST_LINEAGE_MISMATCH",
            "/temporal_raw_package_hash",
        ),
        (
            "FX-ARQ-05",
            lambda value: value.update(transcript_reference=None),
            AlignmentRequestRejectionReason.MODE_PRESENCE_MISMATCH,
            "ALIGNMENT_REQUEST_MODE_PRESENCE_MISMATCH",
            "/transcript_reference",
        ),
        (
            "FX-ARQ-06A",
            lambda value: value["transcript_reference"].update(text_scope="WORD_RANGE"),
            AlignmentRequestRejectionReason.TRANSCRIPT_INVALID,
            "ALIGNMENT_REQUEST_TRANSCRIPT_INVALID",
            "/transcript_reference/text_scope",
        ),
        (
            "FX-ARQ-06B",
            lambda value: value.update(authorization_reference=None),
            AlignmentRequestRejectionReason.AUTHORIZATION_FORBIDDEN,
            "ALIGNMENT_REQUEST_AUTHORIZATION_FORBIDDEN",
            "/authorization_reference",
        ),
        (
            "FX-ARQ-09",
            lambda value: value["adapter_capability"].update(confidence_output="MAYBE"),
            AlignmentRequestRejectionReason.CAPABILITY_INVALID,
            "ALIGNMENT_REQUEST_CAPABILITY_INVALID",
            "/adapter_capability/confidence_output",
        ),
        (
            "FX-ARQ-10",
            lambda value: value["adapter_capability"].update(mode="REPLAY"),
            AlignmentRequestRejectionReason.MODE_CAPABILITY_MISMATCH,
            "ALIGNMENT_REQUEST_MODE_CAPABILITY_MISMATCH",
            "/adapter_capability/mode",
        ),
        (
            "FX-ARQ-11",
            lambda value: value.update(extensions=None),
            AlignmentRequestRejectionReason.EXTENSIONS_FORBIDDEN,
            "ALIGNMENT_REQUEST_EXTENSIONS_FORBIDDEN",
            "/extensions",
        ),
        (
            "FX-ARQ-12",
            lambda value: value.update(alignment_request_hash="0" * 64),
            AlignmentRequestRejectionReason.IDENTITY_MISMATCH,
            "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
            "/alignment_request_hash",
        ),
        (
            "FX-ARQ-SEC-01",
            lambda value: value.update(alignment_request_id="/secret"),
            AlignmentRequestRejectionReason.SENSITIVE_DATA,
            "ALIGNMENT_REQUEST_SENSITIVE_DATA",
            "/",
        ),
        (
            "FX-ARQ-13",
            lambda value: value.update(mode="PAID_API"),
            AlignmentRequestRejectionReason.UNSUPPORTED_VALUE,
            "ALIGNMENT_REQUEST_UNSUPPORTED_VALUE",
            "/mode",
        ),
    ],
)
def test_alignment_request_stable_issue_fixtures(
    name,
    mutate,
    reason,
    issue_code,
    pointer,
) -> None:
    value, deps = _raw_request()
    mutate(value)

    with pytest.raises(AlignmentRequestContractError) as exc_info:
        _materialize(value, dependencies=deps)

    assert name.startswith("FX-ARQ")
    _assert_error(exc_info, reason, issue_code, pointer)


def test_alignment_request_rejection_precedence() -> None:
    value, deps = _raw_request()
    value["extra"] = "forbidden"
    value["schema_version"] = "bad"
    with pytest.raises(AlignmentRequestContractError) as exc_info:
        _materialize(value, dependencies=deps)
    assert exc_info.value.issue_code == "ALIGNMENT_REQUEST_WIRE_INVALID"

    value, deps = _raw_request()
    value["alignment_request_hash"] = "0" * 64
    value["alignment_request_id"] = "arq_wrongwrongwrongwrongwrongwrong"
    with pytest.raises(AlignmentRequestContractError) as hash_error:
        _materialize(value, dependencies=deps)
    assert hash_error.value.pointer == "/alignment_request_hash"

    value, deps = _raw_request()
    value["authorization_reference"] = None
    value["extensions"] = None
    with pytest.raises(AlignmentRequestContractError) as auth_error:
        _materialize(value, dependencies=deps)
    assert auth_error.value.pointer == "/authorization_reference"

    value, deps = _raw_request()
    value["extensions"] = None
    value["alignment_request_id"] = "/secret"
    with pytest.raises(AlignmentRequestContractError) as ext_error:
        _materialize(value, dependencies=deps)
    assert ext_error.value.pointer == "/extensions"


def test_alignment_request_mode_matrix() -> None:
    for mode in ("LOCAL", "REPLAY", "MANUAL_UI"):
        value, deps = _raw_request(mode=mode)
        assert _materialize(value, dependencies=deps).mode.value == mode
    value, deps = _raw_request(mode="FREE_API", transcript_reference=None)
    assert _materialize(value, dependencies=deps).transcript_reference is None
    for mode in ("PAID_API", "DISABLED", "OTHER"):
        value, deps = _raw_request()
        value["mode"] = mode
        with pytest.raises(AlignmentRequestContractError) as exc_info:
            _materialize(value, dependencies=deps)
        assert exc_info.value.issue_code == "ALIGNMENT_REQUEST_UNSUPPORTED_VALUE"


def test_alignment_request_capability_boundaries() -> None:
    value, deps = _raw_request()
    value["adapter_capability"]["media_type"] = "audio/x_wav"
    with pytest.raises(AlignmentRequestContractError) as exc_info:
        _materialize(value, dependencies=deps)
    _assert_error(
        exc_info,
        AlignmentRequestRejectionReason.MODE_CAPABILITY_MISMATCH,
        "ALIGNMENT_REQUEST_MODE_CAPABILITY_MISMATCH",
        "/adapter_capability/media_type",
    )

    for replacement in (
        CustomString("ADAPTER-CAPABILITY-V1"),
        StringEnum.LOCAL,
        ArbitraryEnum.LOCAL,
        1,
        b"ADAPTER-CAPABILITY-V1",
    ):
        value, deps = _raw_request()
        value["adapter_capability"]["schema_version"] = replacement
        with pytest.raises(AlignmentRequestContractError) as exc_info:
            _materialize(value, dependencies=deps)
        assert exc_info.value.issue_code == "ALIGNMENT_REQUEST_CAPABILITY_INVALID"

    for field, replacement in (
        ("schema_version", "ADAPTER-CAPABILITY-V2"),
        ("adapter_id", "-bad"),
        ("adapter_version", "bad space"),
        ("language_tag", "EN-us"),
        ("media_type", "Audio/WAV"),
        ("network_access", "OPTIONAL"),
        ("license_class", "PAID"),
    ):
        value, deps = _raw_request()
        value["adapter_capability"][field] = replacement
        with pytest.raises(AlignmentRequestContractError):
            _materialize(value, dependencies=deps)

    value, deps = _raw_request()
    value["adapter_capability"]["extra"] = "forbidden"
    with pytest.raises(AlignmentRequestContractError):
        _materialize(value, dependencies=deps)


def test_alignment_request_lineage_bindings() -> None:
    mutations = [
        lambda value: value.update(temporal_raw_package_hash="sha256:" + "0" * 64),
        lambda value: value.update(project_id="prj_other"),
        lambda value: value.update(document_id="nardoc_other"),
        lambda value: value.update(narration_revision_id="narrev_other"),
        lambda value: value.update(narration_revision_hash="sha256:" + "0" * 64),
        lambda value: value.update(audio_artifact_id="aud_other"),
        lambda value: value.update(audio_artifact_hash="sha256:" + "0" * 64),
        lambda value: value["transcript_reference"].update(
            narration_revision_hash="sha256:" + "0" * 64
        ),
    ]
    for mutate in mutations:
        value, deps = _raw_request()
        mutate(value)
        with pytest.raises(AlignmentRequestContractError) as exc_info:
            _materialize(value, dependencies=deps)
        assert exc_info.value.issue_code in {
            "ALIGNMENT_REQUEST_LINEAGE_MISMATCH",
            "ALIGNMENT_REQUEST_TRANSCRIPT_INVALID",
        }


def test_alignment_request_sensitive_data_scan() -> None:
    for sentinel in (
        "https://example.invalid/token",
        "/host/path",
        "C:\\secret",
        "\\server",
        "bad\x00value",
        "bad\x1fvalue",
        "bad\x7fvalue",
    ):
        value, deps = _raw_request()
        value["alignment_request_id"] = sentinel
        with pytest.raises(AlignmentRequestContractError) as exc_info:
            _materialize(value, dependencies=deps)
        visible = (
            exc_info.value.pointer,
            str(exc_info.value),
            repr(exc_info.value),
            repr(exc_info.value.args),
        )
        assert exc_info.value.issue_code == "ALIGNMENT_REQUEST_SENSITIVE_DATA"
        assert all(sentinel not in item for item in visible)

    for local_name in ("credential", "ACCESS_TOKEN", "nested/path/password"):
        value, deps = _raw_request()
        value["adapter_capability"] = dict(value["adapter_capability"])
        value["adapter_capability"]["adapter_id"] = "adapter_fxarq"
        value["transcript_reference"][local_name] = "opaque"
        with pytest.raises(AlignmentRequestContractError):
            _materialize(value, dependencies=deps)


def test_alignment_request_failure_publishes_nothing() -> None:
    value, deps = _raw_request()
    value["alignment_request_hash"] = "0" * 64
    with pytest.raises(AlignmentRequestContractError) as exc_info:
        _materialize(value, dependencies=deps)
    _assert_error(
        exc_info,
        AlignmentRequestRejectionReason.IDENTITY_MISMATCH,
        "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
        "/alignment_request_hash",
    )


def test_serialize_alignment_request_rejects_non_materialized_instances() -> None:
    genuine = _materialize()
    assert serialize_alignment_request(genuine) == FX_ARQ_01_ENVELOPE_BYTES

    class Subclass(AlignmentRequest):
        pass

    class Proxy:
        def __init__(self, target):
            self.target = target

        def __getattr__(self, name):
            return getattr(self.target, name)

    for forged in (
        object(),
        AlignmentRequest(**dataclasses.asdict(genuine)),
        object.__new__(AlignmentRequest),
        replace(genuine),
        Subclass(**dataclasses.asdict(genuine)),
        Proxy(genuine),
    ):
        with pytest.raises(AlignmentRequestContractError) as exc_info:
            serialize_alignment_request(forged)
        _assert_error(
            exc_info,
            AlignmentRequestRejectionReason.NOT_MATERIALIZED,
            None,
            "/",
        )


def test_alignment_request_public_exports_are_exact() -> None:
    import engine.contracts as contracts

    current_exports = set(contracts.__all__)
    assert current_exports & SLICE4_PUBLIC_EXPORTS == SLICE4_PUBLIC_EXPORTS
    assert current_exports - PRE_SLICE4_PUBLIC_EXPORTS == (
        SLICE4_PUBLIC_EXPORTS | SLICE5_PUBLIC_EXPORTS
        | ALIGNMENT_RESULT_PUBLIC_EXPORTS | CAPTION_GROUPS_PUBLIC_EXPORTS
    )
    assert current_exports - (
        PRE_SLICE4_PUBLIC_EXPORTS | SLICE4_PUBLIC_EXPORTS
    ) == (
        SLICE5_PUBLIC_EXPORTS
        | ALIGNMENT_RESULT_PUBLIC_EXPORTS
        | CAPTION_GROUPS_PUBLIC_EXPORTS
    )
    assert PRE_SLICE4_PUBLIC_EXPORTS - current_exports == set()
    assert not hasattr(contracts, "_MATERIALIZED_ALIGNMENT_REQUESTS")
    assert not hasattr(contracts, "_is_materialized_alignment_request")


def test_alignment_request_stable_issue_inventory_delta_is_exact() -> None:
    current_codes = set(STABLE_ISSUE_CODES)

    assert current_codes - PRE_SLICE4_STABLE_ISSUE_CODES == SLICE4_STABLE_ISSUE_CODES
    assert PRE_SLICE4_STABLE_ISSUE_CODES - current_codes == set()
    assert "NOT_MATERIALIZED" not in current_codes


def test_alignment_request_registry_releases_collected_instance() -> None:
    request = _materialize()
    registry = alignment_contracts._MATERIALIZED_ALIGNMENT_REQUESTS
    identity_key = id(request)
    registered_reference = registry[identity_key]
    external_reference = weakref.ref(request)

    assert registry[identity_key] is registered_reference
    assert registered_reference() is request

    del request
    _collect_until_dead(external_reference)

    assert external_reference() is None
    assert identity_key not in registry


def test_alignment_request_stale_cleanup_preserves_replacement_entry() -> None:
    registry = alignment_contracts._MATERIALIZED_ALIGNMENT_REQUESTS
    original = _materialize()
    replacement = _materialize()
    original_key = id(original)
    replacement_key = id(replacement)
    original_reference = registry[original_key]
    replacement_reference = registry[replacement_key]
    external_original_reference = weakref.ref(original)

    registry[original_key] = replacement_reference
    try:
        del original
        _collect_until_dead(external_original_reference)

        assert registry.get(original_key) is replacement_reference
        assert registry[replacement_key] is replacement_reference
        assert alignment_contracts._is_materialized_alignment_request(replacement)
    finally:
        if registry.get(original_key) is replacement_reference:
            del registry[original_key]


def test_alignment_request_registration_failure_publishes_nothing(monkeypatch) -> None:
    class SentinelError(RuntimeError):
        pass

    class FailingRegistry(dict):
        def __setitem__(self, key, value):
            captured["candidate"] = value()
            raise SentinelError("sentinel")

    captured = {}
    monkeypatch.setattr(
        alignment_contracts,
        "_MATERIALIZED_ALIGNMENT_REQUESTS",
        FailingRegistry(),
    )

    with pytest.raises(SentinelError):
        _materialize()
    assert not alignment_contracts._is_materialized_alignment_request(
        captured["candidate"]
    )


def test_alignment_request_insertion_failure_preserves_replacement(monkeypatch) -> None:
    class SentinelError(RuntimeError):
        pass

    unrelated = _materialize()
    unrelated_key = id(unrelated)
    unrelated_reference = weakref.ref(unrelated)
    captured = {}

    class ReplacingFailingRegistry(dict):
        def __setitem__(self, key, value):
            candidate = value()
            replacement = replace(candidate)
            replacement_reference = weakref.ref(replacement)
            captured.update(
                {
                    "key": key,
                    "candidate": candidate,
                    "candidate_reference": value,
                    "replacement": replacement,
                    "replacement_reference": replacement_reference,
                }
            )
            super().__setitem__(unrelated_key, unrelated_reference)
            super().__setitem__(key, replacement_reference)
            raise SentinelError("sentinel")

    registry = ReplacingFailingRegistry()
    monkeypatch.setattr(
        alignment_contracts,
        "_MATERIALIZED_ALIGNMENT_REQUESTS",
        registry,
    )

    with pytest.raises(SentinelError, match="sentinel"):
        _materialize()

    assert registry[captured["key"]] is captured["replacement_reference"]
    assert registry[unrelated_key] is unrelated_reference
    assert captured["replacement_reference"]() is captured["replacement"]
    assert captured["candidate_reference"]() is captured["candidate"]
    assert captured["candidate"] is not captured["replacement"]
    assert captured["candidate"] == captured["replacement"]
    assert not alignment_contracts._is_materialized_alignment_request(
        captured["candidate"]
    )
    with pytest.raises(AlignmentRequestContractError) as exc_info:
        serialize_alignment_request(captured["candidate"])
    _assert_error(
        exc_info,
        AlignmentRequestRejectionReason.NOT_MATERIALIZED,
        None,
        "/",
    )


def test_alignment_request_verification_failure_rolls_back_exact_entry(monkeypatch) -> None:
    original_registry = {}
    captured = {}

    class TrackingRegistry(dict):
        def __setitem__(self, key, value):
            captured["key"] = key
            captured["reference"] = value
            captured["candidate"] = value()
            super().__setitem__(key, value)

    registry = TrackingRegistry(original_registry)
    monkeypatch.setattr(
        alignment_contracts,
        "_MATERIALIZED_ALIGNMENT_REQUESTS",
        registry,
    )
    monkeypatch.setattr(
        alignment_contracts,
        "_is_materialized_alignment_request",
        lambda value: False,
    )

    with pytest.raises(RuntimeError, match="^alignment request provenance registration failed$"):
        _materialize()
    assert registry.get(captured["key"]) is not captured["reference"]

    def raises(value):
        raise ValueError("verification sentinel")

    registry = TrackingRegistry()
    monkeypatch.setattr(
        alignment_contracts,
        "_MATERIALIZED_ALIGNMENT_REQUESTS",
        registry,
    )
    monkeypatch.setattr(
        alignment_contracts,
        "_is_materialized_alignment_request",
        raises,
    )
    with pytest.raises(ValueError, match="verification sentinel"):
        _materialize()
    assert registry.get(captured["key"]) is not captured["reference"]


def test_alignment_request_verification_false_preserves_replacement(monkeypatch) -> None:
    unrelated = _materialize()
    unrelated_key = id(unrelated)
    unrelated_reference = weakref.ref(unrelated)
    genuine_predicate = alignment_contracts._is_materialized_alignment_request
    captured = {}

    class TrackingRegistry(dict):
        def __setitem__(self, key, value):
            captured["key"] = key
            captured["candidate_reference"] = value
            captured["candidate"] = value()
            super().__setitem__(key, value)

    registry = TrackingRegistry({unrelated_key: unrelated_reference})
    monkeypatch.setattr(
        alignment_contracts,
        "_MATERIALIZED_ALIGNMENT_REQUESTS",
        registry,
    )

    def replace_and_fail(value):
        replacement = replace(value)
        replacement_reference = weakref.ref(replacement)
        captured["replacement"] = replacement
        captured["replacement_reference"] = replacement_reference
        dict.__setitem__(registry, captured["key"], replacement_reference)
        return False

    monkeypatch.setattr(
        alignment_contracts,
        "_is_materialized_alignment_request",
        replace_and_fail,
    )

    with pytest.raises(RuntimeError, match="^alignment request provenance registration failed$"):
        _materialize()

    assert registry[captured["key"]] is captured["replacement_reference"]
    assert registry[unrelated_key] is unrelated_reference
    assert captured["replacement_reference"]() is captured["replacement"]
    assert captured["candidate_reference"]() is captured["candidate"]
    assert captured["candidate"] is not captured["replacement"]
    assert captured["candidate"] == captured["replacement"]

    monkeypatch.setattr(
        alignment_contracts,
        "_is_materialized_alignment_request",
        genuine_predicate,
    )
    assert not alignment_contracts._is_materialized_alignment_request(
        captured["candidate"]
    )
    with pytest.raises(AlignmentRequestContractError) as exc_info:
        serialize_alignment_request(captured["candidate"])
    _assert_error(
        exc_info,
        AlignmentRequestRejectionReason.NOT_MATERIALIZED,
        None,
        "/",
    )


def test_alignment_request_verification_exception_preserves_replacement(monkeypatch) -> None:
    class SentinelError(RuntimeError):
        pass

    unrelated = _materialize()
    unrelated_key = id(unrelated)
    unrelated_reference = weakref.ref(unrelated)
    genuine_predicate = alignment_contracts._is_materialized_alignment_request
    captured = {}

    class TrackingRegistry(dict):
        def __setitem__(self, key, value):
            captured["key"] = key
            captured["candidate_reference"] = value
            captured["candidate"] = value()
            super().__setitem__(key, value)

    registry = TrackingRegistry({unrelated_key: unrelated_reference})
    monkeypatch.setattr(
        alignment_contracts,
        "_MATERIALIZED_ALIGNMENT_REQUESTS",
        registry,
    )

    def replace_and_raise(value):
        replacement = replace(value)
        replacement_reference = weakref.ref(replacement)
        captured["replacement"] = replacement
        captured["replacement_reference"] = replacement_reference
        dict.__setitem__(registry, captured["key"], replacement_reference)
        raise SentinelError("verification sentinel")

    monkeypatch.setattr(
        alignment_contracts,
        "_is_materialized_alignment_request",
        replace_and_raise,
    )

    with pytest.raises(SentinelError, match="verification sentinel"):
        _materialize()

    assert registry[captured["key"]] is captured["replacement_reference"]
    assert registry[unrelated_key] is unrelated_reference
    assert captured["replacement_reference"]() is captured["replacement"]
    assert captured["candidate_reference"]() is captured["candidate"]
    assert captured["candidate"] is not captured["replacement"]
    assert captured["candidate"] == captured["replacement"]

    monkeypatch.setattr(
        alignment_contracts,
        "_is_materialized_alignment_request",
        genuine_predicate,
    )
    assert not alignment_contracts._is_materialized_alignment_request(
        captured["candidate"]
    )
    with pytest.raises(AlignmentRequestContractError) as exc_info:
        serialize_alignment_request(captured["candidate"])
    _assert_error(
        exc_info,
        AlignmentRequestRejectionReason.NOT_MATERIALIZED,
        None,
        "/",
    )


def test_alignment_request_malformed_custom_mapping_and_cycles_fail_closed() -> None:
    class TrapMapping(Mapping):
        def keys(self):
            raise RuntimeError("unsafe https://example.invalid/token")

        def __iter__(self):
            raise RuntimeError("unsafe https://example.invalid/token")

        def __len__(self):
            return 1

        def __getitem__(self, key):
            raise RuntimeError("unsafe https://example.invalid/token")

    with pytest.raises(AlignmentRequestContractError) as exc_info:
        _materialize(TrapMapping(), dependencies=_dependencies())
    visible = (
        exc_info.value.pointer,
        str(exc_info.value),
        repr(exc_info.value),
        repr(exc_info.value.args),
    )
    assert all("https://example.invalid/token" not in item for item in visible)

    value, deps = _raw_request()
    value["adapter_capability"] = value
    with pytest.raises(AlignmentRequestContractError):
        _materialize(value, dependencies=deps)
