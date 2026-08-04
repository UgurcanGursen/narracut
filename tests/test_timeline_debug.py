"""Focused REPLAY checks for the Phase 3A timeline-debug contract."""

from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path
import weakref

import pytest

import engine.contracts.timeline_debug as debug
from tests.test_edl import ROOT, _compile


def test_public_surface_field_order_and_identity_projection_are_stable() -> None:
    assert debug.__all__ == [
        "TIMELINE_DEBUG_V1", "TIMELINE_DEBUG_HASH_V1", "TimelineDebugEntry",
        "TimelineDebugArtifact", "TimelineDebugRejectionReason", "TimelineDebugContractError",
        "compile_timeline_debug", "load_timeline_debug", "serialize_timeline_debug",
    ]
    assert (debug.TIMELINE_DEBUG_V1, debug.TIMELINE_DEBUG_HASH_V1) == (
        "TIMELINE-DEBUG-V1", "TIMELINE-DEBUG-HASH-V1",
    )
    assert tuple(debug.TimelineDebugEntry.__dataclass_fields__) == (
        "ordinal", "event_id", "track", "priority", "start_frame", "end_exclusive_frame",
        "start_word_id", "end_word_id", "intent_id",
    )
    assert tuple(debug.TimelineDebugArtifact.__dataclass_fields__) == (
        "schema_version", "hash_scope_version", "timeline_debug_id", "timeline_debug_hash",
        "video_edl_id", "video_edl_hash", "clock_version", "fps_numerator",
        "fps_denominator", "duration_frames", "entries",
    )
    artifact = debug.compile_timeline_debug(video_edl=_compile())
    value = json.loads(debug.serialize_timeline_debug(artifact))
    projection = dict(value)
    projection.pop("timeline_debug_id")
    projection.pop("timeline_debug_hash")
    expected_hash = hashlib.sha256(
        json.dumps(projection, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert artifact.timeline_debug_hash == expected_hash
    assert artifact.timeline_debug_id == "tdbg_" + expected_hash[:32]


def test_closed_reasons_and_compact_debug_literal_golden_are_exact() -> None:
    assert [item.value for item in debug.TimelineDebugRejectionReason] == [
        "STRUCTURE_INVALID", "UNSUPPORTED_VALUE", "DEPENDENCY_CONTENT_DRIFT",
        "DEPENDENCY_BINDING_INVALID", "ENTRY_INVALID", "NON_CANONICAL_SERIALIZATION",
        "IDENTITY_MISMATCH", "CONTENT_DRIFT", "NOT_MATERIALIZED",
    ]
    artifact = debug.compile_timeline_debug(video_edl=_compile())
    assert hashlib.sha256(debug.serialize_timeline_debug(artifact)).hexdigest() == "49807fb4ed45fe33d58636dcffc50c2c2cdcb111b63c8ed001423e0a251d2be0"


def test_debug_is_exact_readable_event_index_in_global_order_and_roundtrips() -> None:
    video_edl = _compile()
    artifact = debug.compile_timeline_debug(video_edl=video_edl)
    expected = [
        (event.start_frame, event.end_exclusive_frame, track.priority, event.event_id)
        for track in video_edl.tracks
        for event in track.events
    ]
    assert [
        (entry.start_frame, entry.end_exclusive_frame, entry.priority, entry.event_id)
        for entry in artifact.entries
    ] == sorted(expected)
    assert [entry.ordinal for entry in artifact.entries] == list(range(len(expected)))
    assert artifact.video_edl_id == video_edl.video_edl_id
    assert artifact.video_edl_hash == video_edl.video_edl_hash
    assert artifact.clock_version == video_edl.clock_version
    assert artifact.duration_frames == video_edl.duration_frames
    payload = debug.serialize_timeline_debug(artifact)
    assert payload == json.dumps(json.loads(payload), sort_keys=True, separators=(",", ":")).encode()
    assert debug.serialize_timeline_debug(debug.load_timeline_debug(payload, video_edl=video_edl)) == payload


@pytest.mark.parametrize(("mutate", "reason"), [
    (lambda value: value.__setitem__("schema_version", "BAD"), debug.TimelineDebugRejectionReason.UNSUPPORTED_VALUE),
    (lambda value: value.__setitem__("entries", {}), debug.TimelineDebugRejectionReason.STRUCTURE_INVALID),
    (lambda value: value["entries"][0].__setitem__("start_frame", 999), debug.TimelineDebugRejectionReason.ENTRY_INVALID),
])
def test_loader_precedence_and_entry_projection_are_fail_closed(mutate, reason) -> None:
    video_edl = _compile()
    artifact = debug.compile_timeline_debug(video_edl=video_edl)
    value = json.loads(debug.serialize_timeline_debug(artifact))
    mutate(value)
    with pytest.raises(debug.TimelineDebugContractError) as error:
        debug.load_timeline_debug(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode(),
            video_edl=video_edl,
        )
    assert error.value.reason is reason
    with pytest.raises(debug.TimelineDebugContractError) as error:
        debug.load_timeline_debug(b"\xef\xbb\xbf" + debug.serialize_timeline_debug(artifact), video_edl=video_edl)
    assert error.value.reason is debug.TimelineDebugRejectionReason.NON_CANONICAL_SERIALIZATION


def test_loader_rejects_duplicate_keys_and_entry_type_before_projection() -> None:
    video_edl = _compile()
    artifact = debug.compile_timeline_debug(video_edl=video_edl)
    duplicate = debug.serialize_timeline_debug(artifact).replace(
        b'"schema_version":"TIMELINE-DEBUG-V1",',
        b'"schema_version":"TIMELINE-DEBUG-V1","schema_version":"TIMELINE-DEBUG-V1",',
        1,
    )
    with pytest.raises(debug.TimelineDebugContractError) as error:
        debug.load_timeline_debug(duplicate, video_edl=video_edl)
    assert error.value.reason is debug.TimelineDebugRejectionReason.NON_CANONICAL_SERIALIZATION
    value = json.loads(debug.serialize_timeline_debug(artifact))
    value["entries"][0]["ordinal"] = "0"
    with pytest.raises(debug.TimelineDebugContractError) as error:
        debug.load_timeline_debug(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode(), video_edl=video_edl,
        )
    assert error.value.reason is debug.TimelineDebugRejectionReason.STRUCTURE_INVALID


def test_loader_enforces_exact_bytes_dependency_then_root_identity_precedence() -> None:
    video_edl = _compile()
    artifact = debug.compile_timeline_debug(video_edl=video_edl)
    with pytest.raises(TypeError):
        debug.load_timeline_debug("not-bytes", video_edl=video_edl)  # type: ignore[arg-type]
    value = json.loads(debug.serialize_timeline_debug(artifact))
    value["video_edl_hash"] = "0" * 64
    with pytest.raises(debug.TimelineDebugContractError) as error:
        debug.load_timeline_debug(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode(), video_edl=video_edl,
        )
    assert error.value.reason is debug.TimelineDebugRejectionReason.DEPENDENCY_BINDING_INVALID
    assert error.value.pointer == "/video_edl"
    value = json.loads(debug.serialize_timeline_debug(artifact))
    value["timeline_debug_hash"] = "0" * 64
    with pytest.raises(debug.TimelineDebugContractError) as error:
        debug.load_timeline_debug(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode(), video_edl=video_edl,
        )
    assert error.value.reason is debug.TimelineDebugRejectionReason.IDENTITY_MISMATCH
    assert error.value.pointer == "/"


def test_mutation_weak_registry_and_linear_boundary_are_enforced() -> None:
    artifact = debug.compile_timeline_debug(video_edl=_compile())
    object.__setattr__(artifact, "timeline_debug_hash", "0" * 64)
    with pytest.raises(debug.TimelineDebugContractError) as error:
        debug.serialize_timeline_debug(artifact)
    assert error.value.reason is debug.TimelineDebugRejectionReason.CONTENT_DRIFT
    clean = debug.compile_timeline_debug(video_edl=_compile())
    reference = weakref.ref(clean)
    key = id(clean)
    assert key in debug._REGISTRY
    del clean
    gc.collect()
    assert reference() is None
    assert key not in debug._REGISTRY
    source = (ROOT / "engine" / "contracts" / "timeline_debug.py").read_text(encoding="utf-8")
    assert ".sort(" not in source
    for forbidden in ("remotion", "ffmpeg", "subprocess", "requests", "pathlib", "open(", "from .v2"):
        assert forbidden not in source.lower()
