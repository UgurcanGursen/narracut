from __future__ import annotations

import copy
import dataclasses
import hashlib
import inspect
import json
import struct
import gc
import weakref
from collections.abc import Mapping
from typing import Any

import pytest

import engine.contracts as contracts
import engine.contracts.alignment_result as result_contracts
import engine.contracts.narration as narration_contracts
from engine.contracts import (
    ALIGNMENT_RESULT_HASH_V1,
    ALIGNMENT_RESULT_V1,
    ALIGNMENT_TOKEN_OBSERVATION_V1,
    TIMING_ORIGIN_EVIDENCE_HASH_V1,
    TIMING_ORIGIN_EVIDENCE_V1,
    AdapterExecutionStatus,
    AlignmentResult,
    AlignmentResultContractError,
    AlignmentResultRejectionReason,
    AlignmentTimingSource,
    AudioArtifactMaterializationRuntime,
    ConfidenceAvailability,
    NarrationRevisionBinding,
    SecureAudioSnapshot,
    SecureOpenEvidence,
    SecureAudioReader,
    TrustedRootReference,
    WordTiming,
    canonicalize_temporal_raw_package,
    load_alignment_result,
    load_repository_timing_origin_evidence,
    materialize_adapter_execution,
    materialize_alignment_request,
    materialize_alignment_result,
    materialize_audio_artifact,
    serialize_alignment_result,
)
from tests.test_canonical_narration import fx34_value, materialize_fx34


EVIDENCE_BYTES = result_contracts._GOLDEN_EVIDENCE
PAYLOAD_BYTES = result_contracts._GOLDEN_TIMING_PAYLOAD
RESULT_HASH = "1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb"
RESULT_ID = "alr_" + RESULT_HASH[:32]


def build_phase2_high_cardinality_replay(
    fixture: Mapping[str, Any],
):
    """Materialize the immutable, public Phase 2 96-word REPLAY chain seed."""
    if type(fixture) is not dict:
        raise TypeError("fixture must be an exact dict")
    words = fixture.get("words")
    policy = fixture.get("timing_policy")
    if (
        fixture.get("fixture_id") != "FX-PHASE2-TPUB-96-REPLAY"
        or type(words) is not list
        or tuple(words) != result_contracts._PHASE2_HIGH_CARDINALITY_WORDS
        or type(policy) is not dict
        or policy != {
            "first_start_ms": 0,
            "word_duration_ms": 180,
            "inter_word_gap_ms": 20,
            "low_confidence_word_ordinal": 17,
            "low_confidence_millionths": 940000,
            "default_confidence_millionths": 980000,
        }
    ):
        raise ValueError("fixture does not match the immutable Phase 2 REPLAY allowlist")

    source_text = " ".join(words) + "."
    candidate = fx34_value()
    candidate["title"] = "FX-96"
    candidate["sections"] = [{
        "order": 0, "source_start": 0, "source_end": len(source_text),
        "paragraphs": [{
            "order": 0, "source_start": 0, "source_end": len(source_text),
            "sentences": [{
                "order": 0, "source_start": 0, "source_end": len(source_text),
                "segmentation_rule_version": "fx34-sentence-v1", "extensions": {},
            }],
            "extensions": {},
        }], "extensions": {},
    }]
    tokens: list[dict[str, Any]] = []
    canonical_words: list[dict[str, int]] = []
    offset = 0
    for ordinal, word in enumerate(words):
        end = offset + len(word)
        tokens.append({
            "kind": "SPOKEN", "display_text": word,
            "normalized_alignment_text": word, "text_order": ordinal,
            "canonical_word_ordinal": ordinal, "source_start": offset,
            "source_end": end, "section_order": 0, "paragraph_order": 0,
            "sentence_order": 0, "extensions": {},
        })
        canonical_words.append({"text_order": ordinal, "canonical_word_ordinal": ordinal})
        offset = end + 1
    tokens.append({
        "kind": "PUNCTUATION", "display_text": ".", "normalized_alignment_text": None,
        "text_order": 96, "canonical_word_ordinal": None,
        "source_start": len(source_text) - 1, "source_end": len(source_text),
        "section_order": 0, "paragraph_order": 0, "sentence_order": 0,
        "extensions": {},
    })
    candidate["text_tokens"] = tokens
    candidate["canonical_words"] = canonical_words
    narration = materialize_fx34(candidate, source_bytes=source_text.encode("utf-8"))

    payload_bytes = result_contracts._PHASE2_HIGH_CARDINALITY_TIMING_PAYLOAD
    payload = json.loads(payload_bytes)
    raw = canonicalize_temporal_raw_package({
        "schema_version": "TRP-RAW-V1", "run_id": "run_phase2_tpub_96",
        "raw_id": "raw_phase2_tpub_96", "payload": payload,
        "payload_byte_hash": "sha256:" + hashlib.sha256(payload_bytes).hexdigest(),
        "media_type": "application/vnd.kurgu.alignment-token-observation+json",
        "issue_codes": [],
    }, payload_bytes=payload_bytes)
    wave = _phase2_high_cardinality_wave()
    audio = materialize_audio_artifact({
        "schema_version": "AUDIO-ARTIFACT-INPUT-V1",
        "project_id": narration.document.project_id, "document_id": narration.document.document_id,
        "narration_revision_id": narration.revision.revision_id,
        "narration_revision_hash": narration.revision.revision_hash,
        "logical_input": {"schema_version": "SECURE-AUDIO-INPUT-V1", "kind": "LOCAL_FILE", "logical_path": "audio/narration.wav"},
        "declared_media_byte_hash": "sha256:" + hashlib.sha256(wave).hexdigest(),
        "declared_sample_rate_hz": 8000, "declared_channel_count": 1,
        "declared_sample_frame_count": 160000, "extensions": {},
    }, narration_binding=NarrationRevisionBinding.from_validated_revision(narration.revision),
       runtime=AudioArtifactMaterializationRuntime(TrustedRootReference("C:/trusted/root"), _Reader(wave)))
    base = raw, narration.document, narration.revision, audio
    source_request = materialize_alignment_request(_request_value(base, "LOCAL"), temporal_raw_package=raw, narration_document=narration.document, narration_revision=narration.revision, audio_artifact=audio)
    source_execution = materialize_adapter_execution(_execution_value(source_request, "LOCAL"), alignment_request=source_request)
    request = materialize_alignment_request(_request_value(base, "REPLAY"), temporal_raw_package=raw, narration_document=narration.document, narration_revision=narration.revision, audio_artifact=audio)
    replay = {"schema_version": "REPLAY-EVIDENCE-V1", "source_adapter_execution_id": source_execution.adapter_execution_id, "source_adapter_execution_hash": source_execution.adapter_execution_hash, "source_alignment_request_id": source_request.alignment_request_id, "source_alignment_request_hash": source_request.alignment_request_hash}
    execution = materialize_adapter_execution(_execution_value(request, "REPLAY", replay=replay), alignment_request=request, source_alignment_request=source_request, source_execution=source_execution)
    evidence = load_repository_timing_origin_evidence(result_contracts._PHASE2_HIGH_CARDINALITY_EVIDENCE)
    value = {
        "schema_version": ALIGNMENT_RESULT_V1, "hash_scope_version": ALIGNMENT_RESULT_HASH_V1,
        "alignment_result_id": "alr_" + "0" * 32, "alignment_result_hash": "0" * 64,
        "project_id": narration.document.project_id, "document_id": narration.document.document_id,
        "temporal_raw_package_hash": raw.canonical_hash, "narration_revision_id": narration.revision.revision_id,
        "narration_revision_hash": narration.revision.revision_hash, "audio_artifact_id": audio.audio_artifact_id,
        "audio_artifact_hash": audio.audio_artifact_hash, "alignment_request_id": request.alignment_request_id,
        "alignment_request_hash": request.alignment_request_hash, "adapter_execution_id": execution.adapter_execution_id,
        "adapter_execution_hash": execution.adapter_execution_hash, "timing_origin_evidence_id": evidence.timing_origin_evidence_id,
        "timing_origin_evidence_hash": evidence.timing_origin_evidence_hash,
        "timing_source": "REPLAY_VERIFIED", "confidence_availability": "AVAILABLE",
        "word_timings": [
            {"word_id": word.word_id, "start_ms": ordinal * 200, "end_ms": ordinal * 200 + 180,
             "confidence_millionths": 940000 if ordinal == 17 else 980000,
             "source_token_indices": [ordinal]}
            for ordinal, word in enumerate(narration.revision.canonical_words)
        ],
    }
    result = materialize_alignment_result(_rehash(value, "alignment_result_id", "alignment_result_hash", "alr_"), temporal_raw_package=raw, narration_document=narration.document, narration_revision=narration.revision, audio_artifact=audio, alignment_request=request, adapter_execution=execution, timing_origin_evidence=evidence)
    return narration.document, narration.revision, result


def build_phase3_edl_high_cardinality_replay(
    fixture: Mapping[str, Any],
):
    """Materialize the immutable 10k REPLAY seed through public contracts only."""
    expected_policy = {
        "first_start_ms": 0, "word_duration_ms": 40,
        "inter_word_gap_ms": 0, "default_confidence_millionths": 980000,
    }
    if (
        type(fixture) is not dict
        or fixture.get("fixture_id") != "FX-PHASE3-EDL-10000-REPLAY"
        or fixture.get("word_template") != "token-{ordinal:05d}"
        or fixture.get("word_count") != 10_000
        or fixture.get("timing_policy") != expected_policy
    ):
        raise ValueError("fixture does not match the immutable Phase 3 EDL REPLAY allowlist")
    words = result_contracts._PHASE3_EDL_HIGH_CARDINALITY_WORDS
    source_text = " ".join(words) + "."
    candidate = fx34_value()
    candidate["title"] = "FX-PHASE3-10000"
    sentence_ranges: list[dict[str, Any]] = []
    sentence_start = 0
    for ordinal in range(2_000):
        sentence_end = sentence_start + sum(
            len(word) for word in words[ordinal * 5:ordinal * 5 + 5]
        ) + 4
        sentence_ranges.append({
            "order": ordinal, "source_start": sentence_start,
            "source_end": len(source_text) if ordinal == 1_999 else sentence_end,
            "segmentation_rule_version": "fx34-sentence-v1", "extensions": {},
        })
        sentence_start = sentence_end + 1
    candidate["sections"] = [{
        "order": 0, "source_start": 0, "source_end": len(source_text),
        "paragraphs": [{
            "order": 0, "source_start": 0, "source_end": len(source_text),
            "sentences": sentence_ranges, "extensions": {},
        }], "extensions": {},
    }]
    tokens: list[dict[str, Any]] = []
    canonical_words: list[dict[str, int]] = []
    offset = 0
    for ordinal, word in enumerate(words):
        end = offset + len(word)
        tokens.append({
            "kind": "SPOKEN", "display_text": word,
            "normalized_alignment_text": word, "text_order": ordinal,
            "canonical_word_ordinal": ordinal, "source_start": offset,
            "source_end": end, "section_order": 0, "paragraph_order": 0,
            "sentence_order": ordinal // 5, "extensions": {},
        })
        canonical_words.append({"text_order": ordinal, "canonical_word_ordinal": ordinal})
        offset = end + 1
    tokens.append({
        "kind": "PUNCTUATION", "display_text": ".", "normalized_alignment_text": None,
        "text_order": 10_000, "canonical_word_ordinal": None,
        "source_start": len(source_text) - 1, "source_end": len(source_text),
        "section_order": 0, "paragraph_order": 0, "sentence_order": 1_999,
        "extensions": {},
    })
    candidate["text_tokens"] = tokens
    candidate["canonical_words"] = canonical_words
    narration = materialize_fx34(candidate, source_bytes=source_text.encode("utf-8"))
    payload_bytes = result_contracts._PHASE3_EDL_HIGH_CARDINALITY_TIMING_PAYLOAD
    payload = json.loads(payload_bytes)
    raw = canonicalize_temporal_raw_package({
        "schema_version": "TRP-RAW-V1", "run_id": "run_phase3_edl_10000",
        "raw_id": "raw_phase3_edl_10000", "payload": payload,
        "payload_byte_hash": "sha256:" + hashlib.sha256(payload_bytes).hexdigest(),
        "media_type": "application/vnd.kurgu.alignment-token-observation+json",
        "issue_codes": [],
    }, payload_bytes=payload_bytes)
    wave = _phase3_edl_high_cardinality_wave()
    audio = materialize_audio_artifact({
        "schema_version": "AUDIO-ARTIFACT-INPUT-V1",
        "project_id": narration.document.project_id, "document_id": narration.document.document_id,
        "narration_revision_id": narration.revision.revision_id,
        "narration_revision_hash": narration.revision.revision_hash,
        "logical_input": {"schema_version": "SECURE-AUDIO-INPUT-V1", "kind": "LOCAL_FILE", "logical_path": "audio/narration.wav"},
        "declared_media_byte_hash": "sha256:" + hashlib.sha256(wave).hexdigest(),
        "declared_sample_rate_hz": 8000, "declared_channel_count": 1,
        "declared_sample_frame_count": 3_200_000, "extensions": {},
    }, narration_binding=NarrationRevisionBinding.from_validated_revision(narration.revision),
       runtime=AudioArtifactMaterializationRuntime(TrustedRootReference("C:/trusted/root"), _Reader(wave)))
    base = raw, narration.document, narration.revision, audio
    source_request = materialize_alignment_request(_request_value(base, "LOCAL"), temporal_raw_package=raw, narration_document=narration.document, narration_revision=narration.revision, audio_artifact=audio)
    source_execution = materialize_adapter_execution(_execution_value(source_request, "LOCAL"), alignment_request=source_request)
    request = materialize_alignment_request(_request_value(base, "REPLAY"), temporal_raw_package=raw, narration_document=narration.document, narration_revision=narration.revision, audio_artifact=audio)
    replay = {"schema_version": "REPLAY-EVIDENCE-V1", "source_adapter_execution_id": source_execution.adapter_execution_id, "source_adapter_execution_hash": source_execution.adapter_execution_hash, "source_alignment_request_id": source_request.alignment_request_id, "source_alignment_request_hash": source_request.alignment_request_hash}
    execution = materialize_adapter_execution(_execution_value(request, "REPLAY", replay=replay), alignment_request=request, source_alignment_request=source_request, source_execution=source_execution)
    evidence = load_repository_timing_origin_evidence(result_contracts._PHASE3_EDL_HIGH_CARDINALITY_EVIDENCE)
    value = {
        "schema_version": ALIGNMENT_RESULT_V1, "hash_scope_version": ALIGNMENT_RESULT_HASH_V1,
        "alignment_result_id": "alr_" + "0" * 32, "alignment_result_hash": "0" * 64,
        "project_id": narration.document.project_id, "document_id": narration.document.document_id,
        "temporal_raw_package_hash": raw.canonical_hash, "narration_revision_id": narration.revision.revision_id,
        "narration_revision_hash": narration.revision.revision_hash, "audio_artifact_id": audio.audio_artifact_id,
        "audio_artifact_hash": audio.audio_artifact_hash, "alignment_request_id": request.alignment_request_id,
        "alignment_request_hash": request.alignment_request_hash, "adapter_execution_id": execution.adapter_execution_id,
        "adapter_execution_hash": execution.adapter_execution_hash, "timing_origin_evidence_id": evidence.timing_origin_evidence_id,
        "timing_origin_evidence_hash": evidence.timing_origin_evidence_hash,
        "timing_source": "REPLAY_VERIFIED", "confidence_availability": "AVAILABLE",
        "word_timings": [
            {"word_id": word.word_id, "start_ms": ordinal * 40, "end_ms": ordinal * 40 + 40,
             "confidence_millionths": 980000, "source_token_indices": [ordinal]}
            for ordinal, word in enumerate(narration.revision.canonical_words)
        ],
    }
    result = materialize_alignment_result(_rehash(value, "alignment_result_id", "alignment_result_hash", "alr_"), temporal_raw_package=raw, narration_document=narration.document, narration_revision=narration.revision, audio_artifact=audio, alignment_request=request, adapter_execution=execution, timing_origin_evidence=evidence)
    return narration.document, narration.revision, result


def test_phase3_edl_high_cardinality_builder_is_allowlisted_and_materialized() -> None:
    fixture = {
        "fixture_id": "FX-PHASE3-EDL-10000-REPLAY",
        "word_template": "token-{ordinal:05d}", "word_count": 10_000,
        "timing_policy": {
            "first_start_ms": 0, "word_duration_ms": 40,
            "inter_word_gap_ms": 0, "default_confidence_millionths": 980000,
        },
    }
    document, revision, result = build_phase3_edl_high_cardinality_replay(fixture)
    assert (document.document_id, revision.revision_id, len(result.word_timings)) == (
        "nardoc_fx34", "narrev_dd7762a76fa6a6a25018", 10_000,
    )
    assert result.timing_origin_evidence_id == "toe_e76005d1fa87e6ba9fd706b823cc8f9c"
    with pytest.raises(ValueError):
        build_phase3_edl_high_cardinality_replay({**fixture, "word_count": 9_999})


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()


class _Reader(SecureAudioReader):
    def __init__(self, source: bytes):
        self.source = source
        self.access_count = 0
        self.snapshot_read_count = 0
        self.reverify_read_count = 0
        result_contracts_audio = __import__("engine.contracts.audio", fromlist=["x"])
        result_contracts_audio._authorize_secure_audio_reader_for_testing(self)

    def _evidence(self) -> SecureOpenEvidence:
        digest = "sha256:" + hashlib.sha256(self.source).hexdigest()
        return SecureOpenEvidence(
            initial_root_identity="root_identity", final_root_identity="root_identity",
            initial_file_identity="file_identity", final_file_identity="file_identity",
            initial_byte_length=len(self.source), final_byte_length=len(self.source),
            containment_before=True, containment_after=True, reparse_component_seen=False,
            snapshot_media_byte_hash=digest, final_same_object_media_byte_hash=digest,
            object_replacement_observed=False, final_read_byte_length=len(self.source),
        )

    def open_snapshot(self, trusted_root, validated_logical_segments):
        self.access_count += 1
        self.snapshot_read_count += 1
        evidence = self._evidence()
        return SecureAudioSnapshot(self.source, evidence, evidence)


def _wave() -> bytes:
    samples = bytearray()
    for frame in range(32000):
        samples += struct.pack("<h", ((frame * 257 + 12345) % 65536) - 32768)
    return (
        b"RIFF" + struct.pack("<I", 64036) + b"WAVEfmt "
        + struct.pack("<IHHIIHH", 16, 1, 1, 8000, 16000, 2, 16)
        + b"data" + struct.pack("<I", 64000) + bytes(samples)
    )


def _phase2_high_cardinality_wave() -> bytes:
    samples = bytearray()
    for frame in range(160_000):
        samples += struct.pack("<h", ((frame * 257 + 12345) % 65536) - 32768)
    return (
        b"RIFF" + struct.pack("<I", 320036) + b"WAVEfmt "
        + struct.pack("<IHHIIHH", 16, 1, 1, 8000, 16000, 2, 16)
        + b"data" + struct.pack("<I", 320000) + bytes(samples)
    )


def _phase3_edl_high_cardinality_wave() -> bytes:
    samples = bytearray()
    for frame in range(3_200_000):
        samples += struct.pack("<h", ((frame * 257 + 12345) % 65536) - 32768)
    return (
        b"RIFF" + struct.pack("<I", 6400036) + b"WAVEfmt "
        + struct.pack("<IHHIIHH", 16, 1, 1, 8000, 16000, 2, 16)
        + b"data" + struct.pack("<I", 6400000) + bytes(samples)
    )


def _rehash(value: dict, id_field: str, hash_field: str, prefix: str) -> dict:
    projection = {key: item for key, item in value.items() if key not in {id_field, hash_field}}
    digest = hashlib.sha256(_canonical(projection)).hexdigest()
    value[hash_field] = digest
    value[id_field] = prefix + digest[:32]
    return value


def _request_value(deps, mode: str) -> dict:
    raw, document, revision, audio = deps
    capability = {
        "schema_version": "ADAPTER-CAPABILITY-V1",
        "adapter_id": "adapter_alignment_fx01", "adapter_version": "1.0.0",
        "mode": mode, "language_tag": "en", "media_type": "audio/wav",
        "confidence_output": "SUPPORTED", "network_access": "FORBIDDEN",
        "license_class": mode,
    }
    value = {
        "schema_version": "ALIGNMENT-REQUEST-V1",
        "hash_scope_version": "ALIGNMENT-REQUEST-HASH-V1",
        "alignment_request_id": "arq_" + "0" * 32,
        "alignment_request_hash": "0" * 64,
        "project_id": document.project_id, "document_id": document.document_id,
        "temporal_raw_package_hash": raw.canonical_hash,
        "narration_revision_id": revision.revision_id,
        "narration_revision_hash": revision.revision_hash,
        "audio_artifact_id": audio.audio_artifact_id,
        "audio_artifact_hash": audio.audio_artifact_hash,
        "mode": mode, "adapter_capability": capability,
        "transcript_reference": {
            "narration_revision_id": revision.revision_id,
            "narration_revision_hash": revision.revision_hash,
            "text_scope": "CANONICAL_NARRATION",
        },
    }
    return _rehash(value, "alignment_request_id", "alignment_request_hash", "arq_")


def _execution_value(request, mode: str, *, replay=None, status="SUCCEEDED") -> dict:
    value = {
        "schema_version": "ADAPTER-EXECUTION-V1",
        "hash_scope_version": "ADAPTER-EXECUTION-HASH-V1",
        "adapter_execution_id": "aex_" + "0" * 32,
        "adapter_execution_hash": "0" * 64,
        "alignment_request_id": request.alignment_request_id,
        "alignment_request_hash": request.alignment_request_hash,
        "adapter_id": request.adapter_capability.adapter_id,
        "adapter_version": request.adapter_capability.adapter_version,
        "mode": mode, "status": status,
        "paid_fallback_authorization_evidence": None,
        "replay_evidence": replay,
        "confidence_availability_evidence": {
            "schema_version": "CONFIDENCE-AVAILABILITY-EVIDENCE-V1",
            "availability": "NOT_APPLICABLE" if status == "FAILED" else "AVAILABLE",
        },
    }
    return _rehash(value, "adapter_execution_id", "adapter_execution_hash", "aex_")


def _dependencies():
    narration = materialize_fx34()
    payload = json.loads(PAYLOAD_BYTES)
    package = {
        "schema_version": "TRP-RAW-V1", "run_id": "run_alignment_result_fx01",
        "raw_id": "raw_alignment_result_fx01", "payload": payload,
        "payload_byte_hash": "sha256:" + hashlib.sha256(PAYLOAD_BYTES).hexdigest(),
        "media_type": "application/vnd.kurgu.alignment-token-observation+json",
        "issue_codes": [],
    }
    raw = canonicalize_temporal_raw_package(package, payload_bytes=PAYLOAD_BYTES)
    wave = _wave()
    media_hash = "sha256:" + hashlib.sha256(wave).hexdigest()
    audio_value = {
        "schema_version": "AUDIO-ARTIFACT-INPUT-V1",
        "project_id": narration.document.project_id,
        "document_id": narration.document.document_id,
        "narration_revision_id": narration.revision.revision_id,
        "narration_revision_hash": narration.revision.revision_hash,
        "logical_input": {"schema_version": "SECURE-AUDIO-INPUT-V1", "kind": "LOCAL_FILE", "logical_path": "audio/narration.wav"},
        "declared_media_byte_hash": media_hash, "declared_sample_rate_hz": 8000,
        "declared_channel_count": 1, "declared_sample_frame_count": 32000,
        "extensions": {},
    }
    audio = materialize_audio_artifact(
        audio_value,
        narration_binding=NarrationRevisionBinding.from_validated_revision(narration.revision),
        runtime=AudioArtifactMaterializationRuntime(TrustedRootReference("C:/trusted/root"), _Reader(wave)),
    )
    deps = raw, narration.document, narration.revision, audio
    source_request = materialize_alignment_request(
        _request_value(deps, "LOCAL"), temporal_raw_package=raw,
        narration_document=narration.document, narration_revision=narration.revision,
        audio_artifact=audio,
    )
    source_execution = materialize_adapter_execution(
        _execution_value(source_request, "LOCAL"), alignment_request=source_request,
    )
    request = materialize_alignment_request(
        _request_value(deps, "REPLAY"), temporal_raw_package=raw,
        narration_document=narration.document, narration_revision=narration.revision,
        audio_artifact=audio,
    )
    replay = {
        "schema_version": "REPLAY-EVIDENCE-V1",
        "source_adapter_execution_id": source_execution.adapter_execution_id,
        "source_adapter_execution_hash": source_execution.adapter_execution_hash,
        "source_alignment_request_id": source_request.alignment_request_id,
        "source_alignment_request_hash": source_request.alignment_request_hash,
    }
    execution = materialize_adapter_execution(
        _execution_value(request, "REPLAY", replay=replay), alignment_request=request,
        source_alignment_request=source_request, source_execution=source_execution,
    )
    evidence = load_repository_timing_origin_evidence(EVIDENCE_BYTES)
    return raw, narration.document, narration.revision, audio, request, execution, evidence


def _dynamic_dependencies(payload: dict, monkeypatch):
    narration = materialize_fx34()
    payload_bytes = _canonical(payload)
    package = {
        "schema_version": "TRP-RAW-V1", "run_id": "run_dynamic_alignment_result",
        "raw_id": "raw_dynamic_alignment_result", "payload": payload,
        "payload_byte_hash": "sha256:" + hashlib.sha256(payload_bytes).hexdigest(),
        "media_type": "application/vnd.kurgu.alignment-token-observation+json",
        "issue_codes": [],
    }
    raw = canonicalize_temporal_raw_package(package, payload_bytes=payload_bytes)
    wave = _wave()
    audio = materialize_audio_artifact(
        {
            "schema_version": "AUDIO-ARTIFACT-INPUT-V1",
            "project_id": narration.document.project_id,
            "document_id": narration.document.document_id,
            "narration_revision_id": narration.revision.revision_id,
            "narration_revision_hash": narration.revision.revision_hash,
            "logical_input": {"schema_version": "SECURE-AUDIO-INPUT-V1", "kind": "LOCAL_FILE", "logical_path": "audio/narration.wav"},
            "declared_media_byte_hash": "sha256:" + hashlib.sha256(wave).hexdigest(),
            "declared_sample_rate_hz": 8000, "declared_channel_count": 1,
            "declared_sample_frame_count": 32000, "extensions": {},
        },
        narration_binding=NarrationRevisionBinding.from_validated_revision(narration.revision),
        runtime=AudioArtifactMaterializationRuntime(TrustedRootReference("C:/trusted/root"), _Reader(wave)),
    )
    base = raw, narration.document, narration.revision, audio
    source_request = materialize_alignment_request(
        _request_value(base, "LOCAL"), temporal_raw_package=raw,
        narration_document=narration.document, narration_revision=narration.revision,
        audio_artifact=audio,
    )
    source_execution = materialize_adapter_execution(
        _execution_value(source_request, "LOCAL"), alignment_request=source_request,
    )
    request = materialize_alignment_request(
        _request_value(base, "REPLAY"), temporal_raw_package=raw,
        narration_document=narration.document, narration_revision=narration.revision,
        audio_artifact=audio,
    )
    replay = {
        "schema_version": "REPLAY-EVIDENCE-V1",
        "source_adapter_execution_id": source_execution.adapter_execution_id,
        "source_adapter_execution_hash": source_execution.adapter_execution_hash,
        "source_alignment_request_id": source_request.alignment_request_id,
        "source_alignment_request_hash": source_request.alignment_request_hash,
    }
    execution = materialize_adapter_execution(
        _execution_value(request, "REPLAY", replay=replay), alignment_request=request,
        source_alignment_request=source_request, source_execution=source_execution,
    )
    document_bytes = _canonical(narration_contracts._document_to_dict(narration.document))
    evidence_data = {
        "schema_version": TIMING_ORIGIN_EVIDENCE_V1,
        "hash_scope_version": TIMING_ORIGIN_EVIDENCE_HASH_V1,
        "timing_origin_evidence_id": "toe_" + "0" * 32,
        "timing_origin_evidence_hash": "0" * 64,
        "fixture_id": "FX-TEST-ONLY-DYNAMIC",
        "temporal_raw_package_hash": raw.canonical_hash,
        "timing_payload_byte_hash": "sha256:" + hashlib.sha256(payload_bytes).hexdigest(),
        "narration_document_snapshot_hash": "sha256:" + hashlib.sha256(document_bytes).hexdigest(),
        "narration_revision_id": narration.revision.revision_id,
        "narration_revision_hash": narration.revision.revision_hash,
        "audio_artifact_id": audio.audio_artifact_id,
        "audio_artifact_hash": audio.audio_artifact_hash,
        "alignment_request_id": request.alignment_request_id,
        "alignment_request_hash": request.alignment_request_hash,
        "adapter_execution_id": execution.adapter_execution_id,
        "adapter_execution_hash": execution.adapter_execution_hash,
    }
    projection = {key: item for key, item in evidence_data.items() if key not in {
        "timing_origin_evidence_id", "timing_origin_evidence_hash"
    }}
    digest = hashlib.sha256(_canonical(projection)).hexdigest()
    evidence_data["timing_origin_evidence_hash"] = digest
    evidence_data["timing_origin_evidence_id"] = "toe_" + digest[:32]
    evidence_bytes = _canonical(evidence_data)
    key = (
        evidence_data["fixture_id"], digest, hashlib.sha256(evidence_bytes).hexdigest(),
        len(evidence_bytes), hashlib.sha256(payload_bytes).hexdigest(), len(payload_bytes),
    )
    monkeypatch.setattr(
        result_contracts, "_allowlist_lookup",
        lambda candidate: (evidence_bytes, payload_bytes) if candidate == key else None,
    )
    monkeypatch.setattr(result_contracts, "_GOLDEN_EVIDENCE", evidence_bytes)
    monkeypatch.setattr(result_contracts, "_GOLDEN_TIMING_PAYLOAD", payload_bytes)
    evidence = load_repository_timing_origin_evidence(evidence_bytes)
    return raw, narration.document, narration.revision, audio, request, execution, evidence


def _result_value(deps) -> dict:
    raw, document, revision, audio, request, execution, evidence = deps
    value = {
        "schema_version": ALIGNMENT_RESULT_V1,
        "hash_scope_version": ALIGNMENT_RESULT_HASH_V1,
        "alignment_result_id": "alr_" + "0" * 32,
        "alignment_result_hash": "0" * 64,
        "project_id": document.project_id, "document_id": document.document_id,
        "temporal_raw_package_hash": raw.canonical_hash,
        "narration_revision_id": revision.revision_id,
        "narration_revision_hash": revision.revision_hash,
        "audio_artifact_id": audio.audio_artifact_id,
        "audio_artifact_hash": audio.audio_artifact_hash,
        "alignment_request_id": request.alignment_request_id,
        "alignment_request_hash": request.alignment_request_hash,
        "adapter_execution_id": execution.adapter_execution_id,
        "adapter_execution_hash": execution.adapter_execution_hash,
        "timing_origin_evidence_id": evidence.timing_origin_evidence_id,
        "timing_origin_evidence_hash": evidence.timing_origin_evidence_hash,
        "timing_source": "REPLAY_VERIFIED", "confidence_availability": "AVAILABLE",
        "word_timings": [
            {"word_id": "nword_5321ba14c2c4b28c31ab", "start_ms": 100, "end_ms": 500, "confidence_millionths": 980000, "source_token_indices": [0]},
            {"word_id": "nword_0cc9d55672a3cb4e9199", "start_ms": 520, "end_ms": 900, "confidence_millionths": 960000, "source_token_indices": [1]},
            {"word_id": "nword_49e85bb034c88ef36f26", "start_ms": 1200, "end_ms": 1700, "confidence_millionths": 940000, "source_token_indices": [3]},
            {"word_id": "nword_d81fe913754f8b49c296", "start_ms": 1720, "end_ms": 2300, "confidence_millionths": 920000, "source_token_indices": [4]},
        ],
    }
    return _rehash(value, "alignment_result_id", "alignment_result_hash", "alr_")


def _materialize(value, deps):
    raw, document, revision, audio, request, execution, evidence = deps
    return materialize_alignment_result(
        value, temporal_raw_package=raw, narration_document=document,
        narration_revision=revision, audio_artifact=audio,
        alignment_request=request, adapter_execution=execution,
        timing_origin_evidence=evidence,
    )


def test_public_surface_is_exact_and_additive() -> None:
    assert ALIGNMENT_RESULT_V1 == "ALIGNMENT-RESULT-V1"
    assert ALIGNMENT_RESULT_HASH_V1 == "ALIGNMENT-RESULT-HASH-V1"
    assert ALIGNMENT_TOKEN_OBSERVATION_V1 == "ALIGNMENT-TOKEN-OBSERVATION-V1"
    assert TIMING_ORIGIN_EVIDENCE_V1 == "TIMING-ORIGIN-EVIDENCE-V1"
    assert TIMING_ORIGIN_EVIDENCE_HASH_V1 == "TIMING-ORIGIN-EVIDENCE-HASH-V1"
    assert [item.value for item in AlignmentTimingSource] == ["REPLAY_VERIFIED"]
    assert [item.value for item in AlignmentResultRejectionReason] == [
        "STRUCTURE_INVALID", "UNSUPPORTED_VALUE", "DEPENDENCY_BINDING_INVALID",
        "DEPENDENCY_CONTENT_DRIFT", "EXECUTION_NOT_SUCCESSFUL",
        "TIMING_ORIGIN_EVIDENCE_INVALID", "RAW_OBSERVATION_INVALID",
        "TIMESTAMP_SOURCE_FORBIDDEN", "TRANSCRIPT_DIVERGENCE", "TIMING_INVALID",
        "CONFIDENCE_INVALID", "SENSITIVE_DATA", "NON_CANONICAL_SERIALIZATION",
        "IDENTITY_MISMATCH", "CONTENT_DRIFT", "NOT_MATERIALIZED",
    ]
    expected = {
        "ALIGNMENT_RESULT_V1", "ALIGNMENT_RESULT_HASH_V1", "ALIGNMENT_TOKEN_OBSERVATION_V1",
        "TIMING_ORIGIN_EVIDENCE_V1", "TIMING_ORIGIN_EVIDENCE_HASH_V1",
        "AlignmentTimingSource", "AlignmentResultRejectionReason", "TimingOriginEvidence",
        "WordTiming", "AlignmentResult", "AlignmentResultContractError",
        "load_repository_timing_origin_evidence", "materialize_alignment_result",
        "load_alignment_result", "serialize_alignment_result",
    }
    assert expected <= set(contracts.__all__)
    assert [field.name for field in dataclasses.fields(WordTiming)] == [
        "word_id", "start_ms", "end_ms", "confidence_millionths", "source_token_indices"
    ]
    assert [field.name for field in dataclasses.fields(AlignmentResult)] == [
        "schema_version", "hash_scope_version", "alignment_result_id",
        "alignment_result_hash", "project_id", "document_id",
        "temporal_raw_package_hash", "narration_revision_id",
        "narration_revision_hash", "audio_artifact_id", "audio_artifact_hash",
        "alignment_request_id", "alignment_request_hash", "adapter_execution_id",
        "adapter_execution_hash", "timing_origin_evidence_id",
        "timing_origin_evidence_hash", "timing_source", "confidence_availability",
        "word_timings",
    ]
    assert list(inspect.signature(materialize_alignment_result).parameters) == [
        "value", "temporal_raw_package", "narration_document", "narration_revision",
        "audio_artifact", "alignment_request", "adapter_execution", "timing_origin_evidence"
    ]
    with pytest.raises(TypeError):
        AlignmentResultContractError("/attacker/value", AlignmentResultRejectionReason.STRUCTURE_INVALID)
    with pytest.raises(TypeError):
        AlignmentResultContractError("/", AlignmentResultRejectionReason.STRUCTURE_INVALID, "NOT_CANONICAL")


def test_golden_evidence_and_result_bytes_identity_and_loader() -> None:
    assert len(PAYLOAD_BYTES) == 1062
    assert hashlib.sha256(PAYLOAD_BYTES).hexdigest() == "86497808c046ec4334395f23eaef5a8e9976780af61a2ec7278ade6137d0b0ad"
    assert len(EVIDENCE_BYTES) == 1206
    assert hashlib.sha256(EVIDENCE_BYTES).hexdigest() == "11ba9218006576fc87f0bcac1bf7cbe808dcdfc78a3fa3f957e97918960628a9"
    deps = _dependencies()
    value = _result_value(deps)
    assert value["alignment_result_hash"] == RESULT_HASH
    assert value["alignment_result_id"] == RESULT_ID
    result = _materialize(value, deps)
    envelope = serialize_alignment_result(result)
    assert len(envelope) == 1764
    assert hashlib.sha256(envelope).hexdigest() == "c2bab562863094ae6c1d29964a86316641dfc22cc5aa2d68dcc7542d9e4aef99"
    loaded = load_alignment_result(
        envelope, temporal_raw_package=deps[0], narration_document=deps[1],
        narration_revision=deps[2], audio_artifact=deps[3], alignment_request=deps[4],
        adapter_execution=deps[5], timing_origin_evidence=deps[6],
    )
    assert loaded == result and loaded is not result
    assert serialize_alignment_result(loaded) == envelope


def test_fail_closed_evidence_and_result_provenance() -> None:
    with pytest.raises(AlignmentResultContractError) as exc:
        load_repository_timing_origin_evidence(EVIDENCE_BYTES + b"\n")
    assert exc.value.reason is AlignmentResultRejectionReason.NON_CANONICAL_SERIALIZATION
    direct = result_contracts.TimingOriginEvidence(**json.loads(EVIDENCE_BYTES))
    deps = list(_dependencies())
    deps[-1] = direct
    with pytest.raises(AlignmentResultContractError) as exc:
        _materialize(_result_value(_dependencies()), tuple(deps))
    assert exc.value.reason is AlignmentResultRejectionReason.TIMING_ORIGIN_EVIDENCE_INVALID
    genuine_deps = _dependencies()
    result = _materialize(_result_value(genuine_deps), genuine_deps)
    with pytest.raises(AlignmentResultContractError) as exc:
        serialize_alignment_result(copy.copy(result))
    assert exc.value.reason is AlignmentResultRejectionReason.NOT_MATERIALIZED
    object.__setattr__(result, "project_id", "prj_mutated")
    with pytest.raises(AlignmentResultContractError) as exc:
        serialize_alignment_result(result)
    assert exc.value.reason is AlignmentResultRejectionReason.CONTENT_DRIFT


@pytest.mark.parametrize(
    "source,reason,pointer,issue",
    [
        ("not-bytes", AlignmentResultRejectionReason.STRUCTURE_INVALID, "/timing_origin_evidence", None),
        (b"\xff", AlignmentResultRejectionReason.STRUCTURE_INVALID, "/timing_origin_evidence", None),
        (b"{", AlignmentResultRejectionReason.STRUCTURE_INVALID, "/timing_origin_evidence", None),
        (b'{"schema_version":1,"schema_version":2}', AlignmentResultRejectionReason.STRUCTURE_INVALID, "/timing_origin_evidence", None),
    ],
)
def test_evidence_wire_failures_are_sanitized(source, reason, pointer, issue) -> None:
    with pytest.raises(AlignmentResultContractError) as exc:
        load_repository_timing_origin_evidence(source)
    assert (exc.value.reason, exc.value.pointer, exc.value.issue_code) == (reason, pointer, issue)
    assert str(exc.value) == f"Alignment result rejected: {reason.value}"


def test_evidence_version_hash_id_allowlist_and_runtime_growth_are_closed(monkeypatch) -> None:
    data = json.loads(EVIDENCE_BYTES)
    data["schema_version"] = "FUTURE"
    with pytest.raises(AlignmentResultContractError) as exc:
        load_repository_timing_origin_evidence(_canonical(data))
    assert (exc.value.reason, exc.value.issue_code) == (
        AlignmentResultRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM"
    )
    data = json.loads(EVIDENCE_BYTES)
    data["timing_origin_evidence_hash"] = "0" * 64
    with pytest.raises(AlignmentResultContractError) as exc:
        load_repository_timing_origin_evidence(_canonical(data))
    assert exc.value.pointer == "/timing_origin_evidence/timing_origin_evidence_hash"
    data = json.loads(EVIDENCE_BYTES)
    data["timing_origin_evidence_id"] = "toe_" + "0" * 32
    with pytest.raises(AlignmentResultContractError) as exc:
        load_repository_timing_origin_evidence(_canonical(data))
    assert exc.value.pointer == "/timing_origin_evidence/timing_origin_evidence_id"
    data = json.loads(EVIDENCE_BYTES)
    data["fixture_id"] = "FX-UNTRUSTED"
    projection = {key: item for key, item in data.items() if key not in {
        "timing_origin_evidence_id", "timing_origin_evidence_hash"
    }}
    digest = hashlib.sha256(_canonical(projection)).hexdigest()
    data["timing_origin_evidence_hash"] = digest
    data["timing_origin_evidence_id"] = "toe_" + digest[:32]
    forged = _canonical(data)
    forged_key = ("FX-UNTRUSTED", digest, hashlib.sha256(forged).hexdigest(), len(forged), hashlib.sha256(PAYLOAD_BYTES).hexdigest(), len(PAYLOAD_BYTES))
    monkeypatch.setattr(result_contracts, "_EVIDENCE_ALLOWLIST", {forged_key: (forged, PAYLOAD_BYTES)})
    with pytest.raises(AlignmentResultContractError) as exc:
        load_repository_timing_origin_evidence(forged)
    assert (exc.value.reason, exc.value.issue_code) == (
        AlignmentResultRejectionReason.TIMING_ORIGIN_EVIDENCE_INVALID, "REPLAY_INPUT_MISMATCH"
    )


def test_evidence_registry_owns_each_load_and_cleans_up() -> None:
    first = load_repository_timing_origin_evidence(EVIDENCE_BYTES)
    second = load_repository_timing_origin_evidence(EVIDENCE_BYTES)
    assert first == second and first is not second
    first_key = id(first)
    reference = weakref.ref(first)
    assert result_contracts._MATERIALIZED_TIMING_ORIGIN_EVIDENCE[first_key][0]() is first
    del first
    for _ in range(10):
        gc.collect()
        if reference() is None:
            break
    assert reference() is None
    assert first_key not in result_contracts._MATERIALIZED_TIMING_ORIGIN_EVIDENCE


def test_replaced_registry_tuples_do_not_transfer_provenance() -> None:
    deps = _dependencies()
    evidence = deps[-1]
    evidence_key = id(evidence)
    evidence_entry = result_contracts._MATERIALIZED_TIMING_ORIGIN_EVIDENCE[evidence_key]
    result_contracts._MATERIALIZED_TIMING_ORIGIN_EVIDENCE[evidence_key] = (
        weakref.ref(evidence), evidence_entry[1], evidence_entry[2]
    )
    with pytest.raises(AlignmentResultContractError) as exc:
        _materialize(_result_value(deps), deps)
    assert exc.value.reason is AlignmentResultRejectionReason.TIMING_ORIGIN_EVIDENCE_INVALID

    deps = _dependencies()
    result = _materialize(_result_value(deps), deps)
    result_key = id(result)
    result_entry = result_contracts._MATERIALIZED_ALIGNMENT_RESULTS[result_key]
    result_contracts._MATERIALIZED_ALIGNMENT_RESULTS[result_key] = (
        weakref.ref(result), result_entry[1]
    )
    with pytest.raises(AlignmentResultContractError) as exc:
        serialize_alignment_result(result)
    assert exc.value.reason is AlignmentResultRejectionReason.CONTENT_DRIFT


def test_non_replay_and_non_successful_executions_publish_nothing() -> None:
    deps = list(_dependencies())
    local_request_value = _request_value(tuple(deps[:4]), "LOCAL")
    local_request = materialize_alignment_request(
        local_request_value, temporal_raw_package=deps[0], narration_document=deps[1],
        narration_revision=deps[2], audio_artifact=deps[3],
    )
    local_execution = materialize_adapter_execution(
        _execution_value(local_request, "LOCAL"), alignment_request=local_request,
    )
    deps[4], deps[5] = local_request, local_execution
    with pytest.raises(AlignmentResultContractError) as exc:
        _materialize({}, tuple(deps))
    assert (exc.value.pointer, exc.value.reason, exc.value.issue_code) == (
        "/adapter_execution/mode", AlignmentResultRejectionReason.TIMESTAMP_SOURCE_FORBIDDEN,
        "LLM_TIMESTAMP_SOURCE_FORBIDDEN",
    )
    replay_deps = list(_dependencies())
    successful = replay_deps[5]
    failed_value = _execution_value(
        replay_deps[4], "REPLAY", replay={
            "schema_version": successful.replay_evidence.schema_version,
            "source_adapter_execution_id": successful.replay_evidence.source_adapter_execution_id,
            "source_adapter_execution_hash": successful.replay_evidence.source_adapter_execution_hash,
            "source_alignment_request_id": successful.replay_evidence.source_alignment_request_id,
            "source_alignment_request_hash": successful.replay_evidence.source_alignment_request_hash,
        }, status="FAILED",
    )
    # The source lineage objects are already proven by the successful execution;
    # retrieve matching live sources by rebuilding the bounded fixture.
    fixture = _dependencies()
    source_request_value = _request_value(tuple(fixture[:4]), "LOCAL")
    source_request = materialize_alignment_request(
        source_request_value, temporal_raw_package=fixture[0], narration_document=fixture[1],
        narration_revision=fixture[2], audio_artifact=fixture[3],
    )
    source_execution = materialize_adapter_execution(
        _execution_value(source_request, "LOCAL"), alignment_request=source_request,
    )
    failed_value["replay_evidence"] = {
        "schema_version": "REPLAY-EVIDENCE-V1",
        "source_adapter_execution_id": source_execution.adapter_execution_id,
        "source_adapter_execution_hash": source_execution.adapter_execution_hash,
        "source_alignment_request_id": source_request.alignment_request_id,
        "source_alignment_request_hash": source_request.alignment_request_hash,
    }
    failed_value = _rehash(failed_value, "adapter_execution_id", "adapter_execution_hash", "aex_")
    # Bind the failed execution to the same request lineage used for its source.
    failed_request = materialize_alignment_request(
        _request_value(tuple(fixture[:4]), "REPLAY"), temporal_raw_package=fixture[0],
        narration_document=fixture[1], narration_revision=fixture[2], audio_artifact=fixture[3],
    )
    failed_value["alignment_request_id"] = failed_request.alignment_request_id
    failed_value["alignment_request_hash"] = failed_request.alignment_request_hash
    failed_value = _rehash(failed_value, "adapter_execution_id", "adapter_execution_hash", "aex_")
    failed = materialize_adapter_execution(
        failed_value, alignment_request=failed_request,
        source_alignment_request=source_request, source_execution=source_execution,
    )
    failed_deps = list(fixture)
    failed_deps[4], failed_deps[5] = failed_request, failed
    with pytest.raises(AlignmentResultContractError) as exc:
        _materialize({}, tuple(failed_deps))
    assert (exc.value.pointer, exc.value.reason, exc.value.issue_code) == (
        "/adapter_execution/status", AlignmentResultRejectionReason.EXECUTION_NOT_SUCCESSFUL,
        "ADAPTER_FAILURE",
    )


def test_declared_timing_and_identity_mismatches_are_rejected() -> None:
    deps = _dependencies()
    value = _result_value(deps)
    value["word_timings"][0]["end_ms"] = 501
    value = _rehash(value, "alignment_result_id", "alignment_result_hash", "alr_")
    with pytest.raises(AlignmentResultContractError) as exc:
        _materialize(value, deps)
    assert exc.value.reason is AlignmentResultRejectionReason.TIMING_INVALID
    value = _result_value(deps)
    value["alignment_result_hash"] = "0" * 64
    with pytest.raises(AlignmentResultContractError) as exc:
        _materialize(value, deps)
    assert exc.value.pointer == "/alignment_result_hash"
    assert exc.value.reason is AlignmentResultRejectionReason.IDENTITY_MISMATCH


def test_result_loader_wire_precedence_and_dependency_type_preflight() -> None:
    deps = _dependencies()
    value = _result_value(deps)
    source = b" " + _canonical(value)
    with pytest.raises(AlignmentResultContractError) as exc:
        load_alignment_result(
            source, temporal_raw_package=deps[0], narration_document=deps[1],
            narration_revision=deps[2], audio_artifact=deps[3], alignment_request=deps[4],
            adapter_execution=deps[5], timing_origin_evidence=deps[6],
        )
    assert exc.value.reason is AlignmentResultRejectionReason.NON_CANONICAL_SERIALIZATION
    with pytest.raises(TypeError):
        materialize_alignment_result(
            {}, temporal_raw_package=object(), narration_document=deps[1],
            narration_revision=deps[2], audio_artifact=deps[3], alignment_request=deps[4],
            adapter_execution=deps[5], timing_origin_evidence=deps[6],
        )


def test_result_registry_cleanup_and_nested_container_mutation() -> None:
    deps = _dependencies()
    result = _materialize(_result_value(deps), deps)
    key = id(result)
    reference = weakref.ref(result)
    assert result_contracts._MATERIALIZED_ALIGNMENT_RESULTS[key][0]() is result
    object.__setattr__(result, "word_timings", list(result.word_timings))
    with pytest.raises(AlignmentResultContractError) as exc:
        serialize_alignment_result(result)
    assert exc.value.reason is AlignmentResultRejectionReason.CONTENT_DRIFT
    del exc
    del result
    for _ in range(10):
        gc.collect()
        if reference() is None:
            break
    assert reference() is None
    assert key not in result_contracts._MATERIALIZED_ALIGNMENT_RESULTS


def test_supported_split_token_mapping_is_deterministic(monkeypatch) -> None:
    payload = json.loads(PAYLOAD_BYTES)
    original = payload["tokens"]
    split = [
        {"index": 0, "kind": "SPOKEN", "normalized_alignment_text": "al", "start_ms": 100, "end_ms": 280, "confidence_millionths": 980000},
        {"index": 1, "kind": "SPOKEN", "normalized_alignment_text": "pha", "start_ms": 300, "end_ms": 500, "confidence_millionths": 970000},
    ]
    for token in original[1:]:
        token = copy.deepcopy(token)
        token["index"] += 1
        split.append(token)
    payload["tokens"] = split
    deps = _dynamic_dependencies(payload, monkeypatch)
    value = _result_value(deps)
    value["word_timings"][0].update(
        confidence_millionths=970000, source_token_indices=[0, 1]
    )
    value["word_timings"][1]["source_token_indices"] = [2]
    value["word_timings"][2]["source_token_indices"] = [4]
    value["word_timings"][3]["source_token_indices"] = [5]
    value = _rehash(value, "alignment_result_id", "alignment_result_hash", "alr_")
    result = _materialize(value, deps)
    assert result.word_timings[0] == WordTiming(
        "nword_5321ba14c2c4b28c31ab", 100, 500, 970000, (0, 1)
    )
    assert serialize_alignment_result(result) == _canonical(value)


@pytest.mark.parametrize(
    "mutate,issue",
    [
        (lambda payload: payload["tokens"][0].update(normalized_alignment_text="Alpha"), "TRANSCRIPT_DIVERGENCE"),
        (
            lambda payload: (
                payload["tokens"][0].update(normalized_alignment_text="alphabeta", end_ms=900),
                payload["tokens"].pop(1),
            ),
            "ADAPTER_PRECISION_OVERSTATED",
        ),
    ],
)
def test_zero_cover_diagnostics_are_closed(monkeypatch, mutate, issue) -> None:
    payload = json.loads(PAYLOAD_BYTES)
    mutate(payload)
    deps = _dynamic_dependencies(payload, monkeypatch)
    with pytest.raises(AlignmentResultContractError) as exc:
        _materialize(_result_value(deps), deps)
    assert (exc.value.pointer, exc.value.reason, exc.value.issue_code) == (
        "/raw_package/payload/tokens", AlignmentResultRejectionReason.TRANSCRIPT_DIVERGENCE,
        issue,
    )


def test_precision_diagnostic_preserves_other_supported_split_edges(monkeypatch) -> None:
    payload = json.loads(PAYLOAD_BYTES)
    payload["tokens"] = [
        {"index": 0, "kind": "SPOKEN", "normalized_alignment_text": "al", "start_ms": 100, "end_ms": 250, "confidence_millionths": 980000},
        {"index": 1, "kind": "SPOKEN", "normalized_alignment_text": "pha", "start_ms": 260, "end_ms": 500, "confidence_millionths": 970000},
        {"index": 2, "kind": "SPOKEN", "normalized_alignment_text": "betagamma", "start_ms": 520, "end_ms": 1700, "confidence_millionths": 940000},
        {"index": 3, "kind": "SPOKEN", "normalized_alignment_text": "delta", "start_ms": 1720, "end_ms": 2300, "confidence_millionths": 920000},
    ]
    deps = _dynamic_dependencies(payload, monkeypatch)
    with pytest.raises(AlignmentResultContractError) as exc:
        _materialize(_result_value(deps), deps)
    assert (exc.value.reason, exc.value.issue_code) == (
        AlignmentResultRejectionReason.TRANSCRIPT_DIVERGENCE,
        "ADAPTER_PRECISION_OVERSTATED",
    )


@pytest.mark.parametrize(
    "mutate,issue",
    [
        (lambda token: token.update(start_ms=-1), "TIMESTAMP_OUT_OF_BOUNDS"),
        (lambda token: token.update(start_ms=500), "ZERO_DURATION_WORD"),
        (lambda token: token.update(start_ms=600), "TIMESTAMP_NON_MONOTONIC"),
        (lambda token: token.update(end_ms=4_001), "TIMESTAMP_OUT_OF_BOUNDS"),
    ],
)
def test_timing_boundaries_fail_closed(monkeypatch, mutate, issue) -> None:
    payload = json.loads(PAYLOAD_BYTES)
    mutate(payload["tokens"][0])
    deps = _dynamic_dependencies(payload, monkeypatch)
    with pytest.raises(AlignmentResultContractError) as exc:
        _materialize(_result_value(deps), deps)
    assert (exc.value.reason, exc.value.issue_code) == (
        AlignmentResultRejectionReason.TIMING_INVALID, issue
    )


def test_overlap_and_confidence_failures_use_exact_issue_codes(monkeypatch) -> None:
    payload = json.loads(PAYLOAD_BYTES)
    payload["tokens"][1]["start_ms"] = 499
    deps = _dynamic_dependencies(payload, monkeypatch)
    with pytest.raises(AlignmentResultContractError) as exc:
        _materialize(_result_value(deps), deps)
    assert (exc.value.reason, exc.value.issue_code) == (
        AlignmentResultRejectionReason.TIMING_INVALID, "TIMESTAMP_OVERLAP"
    )
    payload = json.loads(PAYLOAD_BYTES)
    payload["tokens"][0]["confidence_millionths"] = None
    deps = _dynamic_dependencies(payload, monkeypatch)
    with pytest.raises(AlignmentResultContractError) as exc:
        _materialize(_result_value(deps), deps)
    assert (exc.value.reason, exc.value.issue_code) == (
        AlignmentResultRejectionReason.CONFIDENCE_INVALID,
        "CONFIDENCE_REQUIRED_UNAVAILABLE",
    )
    payload = json.loads(PAYLOAD_BYTES)
    payload["tokens"][0]["confidence_millionths"] = 1_000_001
    deps = _dynamic_dependencies(payload, monkeypatch)
    with pytest.raises(AlignmentResultContractError) as exc:
        _materialize(_result_value(deps), deps)
    assert (exc.value.reason, exc.value.issue_code) == (
        AlignmentResultRejectionReason.CONFIDENCE_INVALID,
        "ADAPTER_PRECISION_OVERSTATED",
    )


@pytest.mark.parametrize(
    "mutate,pointer",
    [
        (lambda payload: payload.update(extra=True), "/raw_package/payload"),
        (lambda payload: payload["tokens"][0].update(extra=True), "/raw_package/payload/tokens/0"),
        (lambda payload: payload["tokens"][0].update(kind="UNKNOWN"), "/raw_package/payload/tokens/0"),
        (lambda payload: payload["tokens"][2].update(start_ms=1), "/raw_package/payload/tokens/2"),
    ],
)
def test_raw_observation_shape_is_closed(monkeypatch, mutate, pointer) -> None:
    payload = json.loads(PAYLOAD_BYTES)
    mutate(payload)
    deps = _dynamic_dependencies(payload, monkeypatch)
    with pytest.raises(AlignmentResultContractError) as exc:
        _materialize(_result_value(deps), deps)
    assert (exc.value.reason, exc.value.pointer) == (
        AlignmentResultRejectionReason.RAW_OBSERVATION_INVALID, pointer
    )


def test_logical_containers_sensitive_values_and_cycles_are_rejected() -> None:
    deps = _dependencies()
    value = _result_value(deps)
    value["word_timings"] = tuple(value["word_timings"])
    with pytest.raises(AlignmentResultContractError) as exc:
        _materialize(value, deps)
    assert exc.value.reason is AlignmentResultRejectionReason.TRANSCRIPT_DIVERGENCE
    value = _result_value(deps)
    value["word_timings"][0]["source_token_indices"] = (0,)
    with pytest.raises(AlignmentResultContractError) as exc:
        _materialize(value, deps)
    assert exc.value.reason is AlignmentResultRejectionReason.STRUCTURE_INVALID
    value = _result_value(deps)
    value["alignment_result_hash"] = "https://credential.invalid"
    with pytest.raises(AlignmentResultContractError) as exc:
        _materialize(value, deps)
    assert exc.value.reason is AlignmentResultRejectionReason.SENSITIVE_DATA
