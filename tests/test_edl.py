"""Focused REPLAY checks for the Phase 3A video EDL contract."""

from __future__ import annotations

import dataclasses
import gc
import hashlib
import inspect
import json
from pathlib import Path
import weakref

import pytest

import engine.contracts.edl as edl
import engine.contracts.timeline_debug as timeline_debug
from engine.contracts.caption_preview import compile_caption_preview
from engine.contracts.emphasis_events import compile_emphasis_events
from engine.contracts.v5_v6_collision import compile_v5_v6_collision_report
from engine.contracts.word_to_frame import TemporalFrameRate, compile_word_to_frame
from engine.contracts import (
    DomainPackRegistry, DomainPolicyResolver, EmphasisIntensity, EmphasisIntent,
    EmphasisTypeRef, SchemaCatalog, WordRangeReference, compile_caption_groups,
)
from tests.test_caption_preview import _policy
from tests.test_emphasis_events import _build_fx
from tests.test_alignment_result import build_phase3_edl_high_cardinality_replay


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "phase3" / "edl_replay_v1.json"
HIGH_CARDINALITY_FIXTURE_PATH = ROOT / "tests" / "fixtures" / "phase3" / "edl_high_cardinality_replay_v1.json"


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _high_cardinality_fixture() -> dict:
    return json.loads(HIGH_CARDINALITY_FIXTURE_PATH.read_text(encoding="utf-8"))


def _deps(*, rate: TemporalFrameRate = TemporalFrameRate(30, 1)):
    document, revision, result, groups, snapshot, registry, intents = _build_fx()
    events = compile_emphasis_events(
        narration_document=document, narration_revision=revision,
        alignment_result=result, caption_groups=groups,
        domain_policy_snapshot=snapshot, domain_pack_registry=registry, intents=intents,
    )
    frames = compile_word_to_frame(
        alignment_result=result, caption_groups=groups, emphasis_events=events,
        frame_rate=rate,
    )
    preview = compile_caption_preview(
        caption_groups=groups, emphasis_events=events, word_to_frame=frames,
        layout_policy=_policy(),
    )
    report = compile_v5_v6_collision_report(caption_preview=preview)
    return groups, events, frames, preview, report


def _intent(*, ordinal: int = 0, track=None, start=0, end=1, mode=None, fit=None):
    groups, _, frames, _, _ = _deps()
    del groups
    track = edl.TimelineTrack.V1 if track is None else track
    mode = edl.SourcePlaybackMode.HOLD if mode is None else mode
    fit = edl.SourceFitMode.COVER if fit is None else fit
    words = frames.word_frames
    cue = edl.CueWordRange(
        frames.project_id, frames.document_id, frames.narration_revision_id,
        words[start].start_word_id, words[end].end_word_id,
    )
    source = edl.SourceDescriptor(
        "asset_replay_" + str(ordinal), 30, 1, 0, 120, mode, fit,
        0, 0, 1_000_000, 1_000_000, 1_000_000,
        cue.start_word_id, cue.end_word_id,
    )
    return edl.VideoEditIntent(
        "intent_replay_" + str(ordinal), track, cue, source,
        "replay_editorial_role", ordinal,
    )


def _fixture_intents():
    """Turn the compact checked-in REPLAY declarative request into typed intents."""
    frames = _deps()[2]
    words = frames.word_frames
    result = []
    # The fixture describes independent editorial requests.  The public
    # contract receives its typed tuple in the required resolved frame order;
    # this test materializer intentionally uses the same sparse key rather
    # than teaching the production scheduler to sort untrusted caller input.
    items = sorted(
        _fixture()["caller_intents"],
        key=lambda item: (
            words[item["start_word_ordinal"]].start_frame,
            words[item["end_word_ordinal"]].end_exclusive_frame,
            item["intent_id"],
        ),
    )
    for ordinal, item in enumerate(items):
        cue = edl.CueWordRange(
            frames.project_id, frames.document_id, frames.narration_revision_id,
            words[item["start_word_ordinal"]].start_word_id,
            words[item["end_word_ordinal"]].end_word_id,
        )
        source = edl.SourceDescriptor(
            "asset_fixture_" + str(ordinal), 30, 1, 0, 60,
            edl.SourcePlaybackMode(item["playback_mode"]), edl.SourceFitMode(item["fit_mode"]),
            0, 0, 1_000_000, 1_000_000, 1_000_000,
            cue.start_word_id, cue.end_word_id,
        )
        result.append(edl.VideoEditIntent(
            item["intent_id"], edl.TimelineTrack(item["track"]), cue, source,
            item["editorial_role"], ordinal,
        ))
    return tuple(result)


def _compile(*, rate: TemporalFrameRate = TemporalFrameRate(30, 1), intents=None):
    groups, events, frames, preview, report = _deps(rate=rate)
    if intents is None:
        intents = (_intent(),)
    words = frames.word_frames
    return edl.compile_video_edl(
        intents=tuple(intents), sequence_id="sequence_replay",
        sequence_start_word_id=words[0].start_word_id,
        sequence_end_word_id=words[-1].end_word_id,
        caption_groups=groups, emphasis_events=events, word_to_frame=frames,
        caption_preview=preview, v5_v6_collision_report=report,
        fps_numerator=rate.numerator, fps_denominator=rate.denominator,
    )


def _load_kwargs(*, intents=None):
    """Build one coherent dependency set for strict-loader precedence checks."""
    groups, events, frames, preview, report = _deps()
    words = frames.word_frames
    return dict(
        intents=(_intent(),) if intents is None else tuple(intents),
        sequence_id="sequence_replay",
        sequence_start_word_id=words[0].start_word_id,
        sequence_end_word_id=words[-1].end_word_id,
        caption_groups=groups, emphasis_events=events, word_to_frame=frames,
        caption_preview=preview, v5_v6_collision_report=report,
        fps_numerator=30, fps_denominator=1,
    )


def _high_cardinality_deps():
    """Build the 10k trusted REPLAY chain without private registry shortcuts."""
    document, revision, result = build_phase3_edl_high_cardinality_replay(_high_cardinality_fixture())
    groups = compile_caption_groups(
        narration_document=document, narration_revision=revision, alignment_result=result,
    )
    catalog = SchemaCatalog(ROOT / "schema" / "v3")
    registry = DomainPackRegistry([ROOT / "domain-packs"], catalog)
    registry.discover()
    profile = json.loads((ROOT / "samples/v3/business-tech/domain/profile.json").read_text(encoding="utf-8"))
    snapshot, _ = DomainPolicyResolver(catalog).resolve(
        registry.get("business-tech", "0.1.0"), profile,
    )
    intents = tuple(
        EmphasisIntent(
            WordRangeReference(revision.revision_id, ordinal * 10, ordinal * 10 + 2),
            EmphasisTypeRef("business-tech", "earnings_sting", "0.1.0"),
            EmphasisIntensity.STRONG,
        )
        for ordinal in range(1_000)
    )
    events = compile_emphasis_events(
        narration_document=document, narration_revision=revision, alignment_result=result,
        caption_groups=groups, domain_policy_snapshot=snapshot,
        domain_pack_registry=registry, intents=intents,
    )
    frames = compile_word_to_frame(
        alignment_result=result, caption_groups=groups, emphasis_events=events,
        frame_rate=TemporalFrameRate(30, 1),
    )
    preview = compile_caption_preview(
        caption_groups=groups, emphasis_events=events, word_to_frame=frames,
        layout_policy=_policy(),
    )
    report = compile_v5_v6_collision_report(caption_preview=preview)
    return document, revision, result, groups, events, frames, preview, report


def _high_cardinality_intents(frames):
    words = frames.word_frames
    return tuple(
        edl.VideoEditIntent(
            "intent_high_" + str(ordinal), edl.TimelineTrack.V1,
            edl.CueWordRange(
                frames.project_id, frames.document_id, frames.narration_revision_id,
                words[ordinal * 2].start_word_id, words[ordinal * 2].end_word_id,
            ),
            edl.SourceDescriptor(
                "asset_high_" + str(ordinal), 30, 1, 0, 1,
                edl.SourcePlaybackMode.HOLD, edl.SourceFitMode.COVER,
                0, 0, 1_000_000, 1_000_000, 1_000_000,
                words[ordinal * 2].start_word_id, words[ordinal * 2].end_word_id,
            ),
            "replay_editorial_role", ordinal,
        )
        for ordinal in range(5_000)
    )


def test_public_surface_and_compact_fixture_are_stable() -> None:
    assert edl.__all__ == [
        "VIDEO_EDL_V1", "VIDEO_EDL_HASH_V1", "VIDEO_CLOCK_V1", "TimelineTrack",
        "EdlTrackKind", "EdlPayloadKind", "SourcePlaybackMode", "SourceFitMode",
        "CueWordRange", "SourceDescriptor", "VideoEditIntent", "EdlRenderPayload",
        "EdlVideoEvent", "EdlTrack", "VideoEdlArtifact", "VideoEdlRejectionReason",
        "VideoEdlContractError", "compile_video_edl", "load_video_edl",
        "serialize_video_edl",
    ]
    assert (edl.VIDEO_EDL_V1, edl.VIDEO_EDL_HASH_V1, edl.VIDEO_CLOCK_V1) == (
        "VIDEO-EDL-V1", "VIDEO-EDL-HASH-V1", "VIDEO-FRAME-CLOCK-V1",
    )
    assert [item.value for item in edl.TimelineTrack] == [
        "V1", "V2", "V3", "V4", "V5", "V6", "V7", "A1", "A2", "A3", "A4", "A5",
    ]
    assert list(inspect.signature(edl.compile_video_edl).parameters) == [
        "intents", "sequence_id", "sequence_start_word_id", "sequence_end_word_id",
        "caption_groups", "emphasis_events", "word_to_frame", "caption_preview",
        "v5_v6_collision_report", "fps_numerator", "fps_denominator",
    ]
    fixture = _fixture()
    assert fixture["fixture_id"] == "FX-PHASE3-EDL-REPLAY-V1"
    assert fixture["words"] == ["Alpha", "beta", "Gamma", "delta"]
    assert fixture["repeated_word_probe"] == ["repeat", "repeat"]
    assert fixture["expected"]["caller_event_count"] == len(fixture["caller_intents"])
    assert set(fixture["expected"]["video_track_event_counts"]) == {"V1", "V2", "V3", "V4", "V5", "V6", "V7"}


def test_normative_dataclass_field_orders_and_identity_projection_are_exact() -> None:
    assert tuple(edl.CueWordRange.__dataclass_fields__) == (
        "project_id", "document_id", "narration_revision_id", "start_word_id", "end_word_id",
    )
    assert tuple(edl.SourceDescriptor.__dataclass_fields__) == (
        "source_ref", "source_fps_numerator", "source_fps_denominator", "source_in_frame",
        "source_out_exclusive_frame", "playback_mode", "fit_mode", "crop_left_millionths",
        "crop_top_millionths", "crop_right_millionths", "crop_bottom_millionths",
        "opacity_millionths", "bound_start_word_id", "bound_end_word_id",
    )
    assert tuple(edl.EdlVideoEvent.__dataclass_fields__) == (
        "schema_version", "hash_scope_version", "event_id", "event_hash", "track", "ordinal",
        "intent_id", "editorial_role", "start_frame", "end_exclusive_frame", "start_word_id",
        "end_word_id", "payload",
    )
    assert tuple(edl.VideoEditIntent.__dataclass_fields__) == (
        "intent_id", "track", "cue", "source", "editorial_role", "ordinal",
    )
    assert tuple(edl.EdlRenderPayload.__dataclass_fields__) == (
        "kind", "source", "source_artifact_id", "source_artifact_hash",
        "source_record_id", "source_record_hash", "source_record_ordinal",
        "preview_scene_id", "preview_scene_hash", "preview_left_millionths",
        "preview_top_millionths", "preview_right_millionths",
        "preview_bottom_millionths", "text", "emphasis_type_ref", "emphasis_intensity",
    )
    assert tuple(edl.EdlTrack.__dataclass_fields__) == (
        "track", "kind", "priority", "events",
    )
    assert tuple(edl.VideoEdlArtifact.__dataclass_fields__) == (
        "schema_version", "hash_scope_version", "video_edl_id", "video_edl_hash",
        "project_id", "document_id", "narration_revision_id", "narration_revision_hash",
        "sequence_id", "sequence_start_word_id", "sequence_end_word_id",
        "sequence_start_frame", "sequence_content_end_exclusive_frame",
        "trailing_silence_frames", "sequence_end_exclusive_frame", "word_to_frame_id",
        "word_to_frame_hash", "caption_preview_id", "caption_preview_hash",
        "v5_v6_collision_report_id", "v5_v6_collision_report_hash", "clock_version",
        "fps_numerator", "fps_denominator", "duration_frames", "tracks",
    )
    artifact = _compile()
    root = json.loads(edl.serialize_video_edl(artifact))
    projection = dict(root)
    projection.pop("video_edl_id")
    projection.pop("video_edl_hash")
    expected_hash = hashlib.sha256(
        json.dumps(projection, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert artifact.video_edl_hash == expected_hash
    assert artifact.video_edl_id == "vedl_" + expected_hash[:32]
    for track in root["tracks"]:
        for event in track["events"]:
            event_projection = dict(event)
            event_projection.pop("event_id")
            event_projection.pop("event_hash")
            event_hash = hashlib.sha256(
                json.dumps(event_projection, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            assert event["event_hash"] == event_hash
            assert event["event_id"] == "vevt_" + event_hash[:32]


def test_closed_enum_values_and_compact_literal_golden_are_exact() -> None:
    assert [member.value for member in edl.EdlTrackKind] == ["VIDEO", "AUDIO"]
    assert [member.value for member in edl.EdlPayloadKind] == [
        "CALLER_SOURCE", "KINETIC_EMPHASIS", "CAPTION",
    ]
    assert [member.value for member in edl.SourcePlaybackMode] == ["HOLD", "LOOP", "FIT"]
    assert [member.value for member in edl.SourceFitMode] == ["CONTAIN", "COVER", "STRETCH"]
    assert [member.value for member in edl.VideoEdlRejectionReason] == [
        "STRUCTURE_INVALID", "UNSUPPORTED_VALUE", "DEPENDENCY_CONTENT_DRIFT",
        "DEPENDENCY_BINDING_INVALID", "CUE_RESOLUTION_INVALID", "TRACK_COLLISION",
        "V5_V6_COLLISION_BLOCKED", "NON_CANONICAL_SERIALIZATION",
        "IDENTITY_MISMATCH", "CONTENT_DRIFT", "NOT_MATERIALIZED",
    ]
    assert hashlib.sha256(edl.serialize_video_edl(_compile())).hexdigest() == "d3f405ae83c911dc9c6d933ac96868932bd1509d9ad5652d5096f12e304f3fe5"


def test_high_cardinality_replay_fixture_has_required_sparse_cardinality_and_linear_bound() -> None:
    fixture = _high_cardinality_fixture()
    assert fixture["fixture_id"] == "FX-PHASE3-EDL-10000-REPLAY"
    assert (fixture["word_count"], fixture["caption_group_count"], fixture["emphasis_event_count"], fixture["caller_intent_count"]) == (10_000, 2_000, 1_000, 5_000)
    assert fixture["caption_group_count"] * fixture["caption_group_span_words"] == fixture["word_count"]
    assert fixture["expected"]["video_event_count"] == 8_000
    assert fixture["expected"]["linear_work_bound"] == "O(W+C+E+I+O)"
    words = tuple(fixture["word_template"].format(ordinal=ordinal) for ordinal in range(fixture["word_count"]))
    assert len(words) == len(set(words)) == 10_000
    assert (words[0], words[-1]) == ("token-00000", "token-09999")


def test_high_cardinality_replay_chain_is_genuine_deterministic_and_linear() -> None:
    first = _high_cardinality_deps()
    second = _high_cardinality_deps()
    for current in (first, second):
        _, _, result, groups, events, frames, preview, report = current
        assert len(result.word_timings) == 10_000
        assert len(groups.caption_groups) == 2_000
        assert len(events.emphasis_events) == 1_000
        assert len(frames.word_frames) == 10_000
        assert len(preview.scenes) == 3_000
        assert report.blocker_count == 0
    assert first[2].alignment_result_hash == second[2].alignment_result_hash
    assert first[3].caption_groups_hash == second[3].caption_groups_hash
    assert first[4].emphasis_events_hash == second[4].emphasis_events_hash
    assert first[5].word_to_frame_hash == second[5].word_to_frame_hash
    caller = _high_cardinality_intents(first[5])
    artifacts = []
    for current in (first, second):
        _, _, _, groups, events, frames, preview, report = current
        words = frames.word_frames
        artifacts.append(edl.compile_video_edl(
            intents=_high_cardinality_intents(frames), sequence_id="sequence_high_10000",
            sequence_start_word_id=words[0].start_word_id,
            sequence_end_word_id=words[-1].end_word_id,
            caption_groups=groups, emphasis_events=events, word_to_frame=frames,
            caption_preview=preview, v5_v6_collision_report=report,
            fps_numerator=30, fps_denominator=1,
        ))
    assert len(caller) == 5_000
    assert all(sum(len(track.events) for track in artifact.tracks) == 8_000 for artifact in artifacts)
    assert edl.serialize_video_edl(artifacts[0]) == edl.serialize_video_edl(artifacts[1])
    debug_artifacts = tuple(
        timeline_debug.compile_timeline_debug(video_edl=artifact) for artifact in artifacts
    )
    assert all(len(artifact.entries) == 8_000 for artifact in debug_artifacts)
    assert timeline_debug.serialize_timeline_debug(debug_artifacts[0]) == timeline_debug.serialize_timeline_debug(debug_artifacts[1])
    # The compiler may index/merge sparse records, but must never turn the
    # accepted duration into a per-frame work list.
    implementation = inspect.getsource(edl)
    assert "range(duration" not in implementation
    assert "[None] * duration" not in implementation


def test_compile_emits_fixed_registry_word_cued_generated_tracks_and_roundtrips() -> None:
    artifact = _compile(intents=_fixture_intents())
    assert [track.track.value for track in artifact.tracks] == [
        "V1", "V2", "V3", "V4", "V5", "V6", "V7", "A1", "A2", "A3", "A4", "A5",
    ]
    assert [track.priority for track in artifact.tracks] == [10, 20, 30, 40, 50, 60, 70, 10, 20, 30, 40, 50]
    assert all(not track.events for track in artifact.tracks[7:])
    assert [len(track.events) for track in artifact.tracks[:7]] == [1, 1, 1, 1, 1, 2, 1]
    v5 = artifact.tracks[4].events
    v6 = artifact.tracks[5].events
    assert v5 and v6
    assert all(event.payload.kind is edl.EdlPayloadKind.KINETIC_EMPHASIS for event in v5)
    assert all(event.payload.kind is edl.EdlPayloadKind.CAPTION for event in v6)
    assert all(event.intent_id.startswith("emphasis:") for event in v5)
    assert all(event.intent_id.startswith("caption:") for event in v6)
    assert all(event.editorial_role == "kinetic_emphasis" for event in v5)
    assert all(event.editorial_role == "readable_subtitle" for event in v6)
    payload = edl.serialize_video_edl(artifact)
    assert payload == json.dumps(json.loads(payload), sort_keys=True, separators=(",", ":")).encode()
    loaded = edl.load_video_edl(
        payload, intents=_fixture_intents(), sequence_id="sequence_replay",
        sequence_start_word_id=_deps()[2].word_frames[0].start_word_id,
        sequence_end_word_id=_deps()[2].word_frames[-1].end_word_id,
        caption_groups=_deps()[0], emphasis_events=_deps()[1], word_to_frame=_deps()[2],
        caption_preview=_deps()[3], v5_v6_collision_report=_deps()[4],
        fps_numerator=30, fps_denominator=1,
    )
    assert edl.serialize_video_edl(loaded) == payload


def test_payload_null_matrix_and_preview_binding_are_exact() -> None:
    artifact = _compile()
    caller = artifact.tracks[0].events[0].payload
    assert caller.kind is edl.EdlPayloadKind.CALLER_SOURCE
    assert caller.source is not None and caller.source_record_id == "intent_replay_0"
    assert caller.source_record_hash is None and caller.preview_scene_id is None
    assert caller.text is None and caller.emphasis_type_ref is None and caller.emphasis_intensity is None
    v5 = artifact.tracks[4].events[0].payload
    assert v5.source is None and v5.source_artifact_id and v5.source_artifact_hash
    assert v5.source_record_id and v5.source_record_hash and v5.source_record_ordinal == 0
    assert v5.preview_scene_id and v5.preview_scene_hash and v5.text.startswith("[EMPHASIS:")
    assert v5.emphasis_type_ref is not None and v5.emphasis_intensity is not None
    v6 = artifact.tracks[5].events[0].payload
    assert v6.source is None and v6.source_artifact_id and v6.source_artifact_hash
    assert v6.source_record_id and v6.source_record_hash and v6.source_record_ordinal == 0
    assert v6.preview_scene_id and v6.preview_scene_hash and v6.text
    assert v6.emphasis_type_ref is None and v6.emphasis_intensity is None


def test_ntsc_rate_is_exact_and_rate_conversion_is_rejected() -> None:
    rate = TemporalFrameRate(30000, 1001)
    artifact = _compile(rate=rate)
    assert (artifact.fps_numerator, artifact.fps_denominator) == (30000, 1001)
    groups, events, frames, preview, report = _deps(rate=rate)
    words = frames.word_frames
    with pytest.raises(edl.VideoEdlContractError) as error:
        edl.compile_video_edl(
            intents=(), sequence_id="sequence_replay", sequence_start_word_id=words[0].start_word_id,
            sequence_end_word_id=words[-1].end_word_id, caption_groups=groups,
            emphasis_events=events, word_to_frame=frames, caption_preview=preview,
            v5_v6_collision_report=report, fps_numerator=30, fps_denominator=1,
        )
    assert error.value.reason is edl.VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID


def test_half_open_touching_events_pass_and_same_track_overlap_fails_closed() -> None:
    touch = (_intent(ordinal=0, start=0, end=0), _intent(ordinal=1, start=1, end=1))
    artifact = _compile(intents=touch)
    assert len(artifact.tracks[0].events) == 2
    overlap = (_intent(ordinal=0, start=0, end=1), _intent(ordinal=1, start=1, end=2))
    with pytest.raises(edl.VideoEdlContractError) as error:
        _compile(intents=overlap)
    assert error.value.reason is edl.VideoEdlRejectionReason.TRACK_COLLISION


def test_cross_track_layering_is_admitted_while_each_track_has_its_own_ordinal_namespace() -> None:
    first = _intent(ordinal=0, track=edl.TimelineTrack.V1, start=0, end=1)
    second = _intent(ordinal=1, track=edl.TimelineTrack.V2, start=0, end=1)
    artifact = _compile(intents=(first, second))
    assert [track.events[0].ordinal for track in artifact.tracks[:2]] == [0, 0]
    assert [track.events[0].start_frame for track in artifact.tracks[:2]] == [0, 0]
    bad_ordinal = dataclasses.replace(second, ordinal=2)
    with pytest.raises(edl.VideoEdlContractError) as error:
        _compile(intents=(first, bad_ordinal))
    assert error.value.reason is edl.VideoEdlRejectionReason.CUE_RESOLUTION_INVALID


@pytest.mark.parametrize("track", [edl.TimelineTrack.V5, edl.TimelineTrack.V6, edl.TimelineTrack.A1])
def test_caller_cannot_own_generated_or_audio_tracks(track: edl.TimelineTrack) -> None:
    with pytest.raises(edl.VideoEdlContractError) as error:
        _compile(intents=(_intent(track=track),))
    assert error.value.reason is edl.VideoEdlRejectionReason.CUE_RESOLUTION_INVALID


def test_cue_resolution_is_stable_id_only_and_source_binding_cannot_be_reused() -> None:
    intent = _intent(start=0, end=1)
    # Word text is deliberately not part of an EDL cue.  Altering only the
    # source binding must fail even if a renderer could display the same text.
    wrong_bound_source = dataclasses.replace(
        intent.source, bound_start_word_id=_deps()[2].word_frames[1].start_word_id,
    )
    with pytest.raises(edl.VideoEdlContractError) as error:
        _compile(intents=(dataclasses.replace(intent, source=wrong_bound_source),))
    assert error.value.reason is edl.VideoEdlRejectionReason.CUE_RESOLUTION_INVALID
    source = (ROOT / "engine" / "contracts" / "edl.py").read_text(encoding="utf-8")
    cue_resolution = source[source.index("def _word_index"):source.index("def _event")]
    assert ".text" not in cue_resolution


def test_caller_input_order_is_validated_before_same_track_collision_scheduler() -> None:
    out_of_order = (
        _intent(ordinal=0, start=2, end=2),
        _intent(ordinal=1, start=0, end=0),
    )
    with pytest.raises(edl.VideoEdlContractError) as error:
        _compile(intents=out_of_order)
    assert error.value.reason is edl.VideoEdlRejectionReason.CUE_RESOLUTION_INVALID
    assert error.value.pointer == "/intents/1"


def test_canonical_global_caller_order_allows_cross_track_layering_and_per_track_ordinals() -> None:
    intents = (
        _intent(ordinal=0, track=edl.TimelineTrack.V1, start=0, end=0),
        _intent(ordinal=1, track=edl.TimelineTrack.V2, start=0, end=1),
        _intent(ordinal=2, track=edl.TimelineTrack.V1, start=1, end=1),
    )
    artifact = _compile(intents=intents)
    v1, v2 = artifact.tracks[0].events, artifact.tracks[1].events
    assert [(event.start_frame, event.end_exclusive_frame, event.intent_id) for event in v1] == sorted(
        (event.start_frame, event.end_exclusive_frame, event.intent_id) for event in v1
    )
    assert [event.ordinal for event in v1] == [0, 1]
    assert [event.ordinal for event in v2] == [0]


@pytest.mark.parametrize("mode, expected", [
    (edl.SourcePlaybackMode.HOLD, [0, 1, 2, 2]),
    (edl.SourcePlaybackMode.LOOP, [0, 1, 2, 0]),
    (edl.SourcePlaybackMode.FIT, [0, 0, 1, 2]),
])
def test_source_playback_modes_apply_descriptor_formula_without_media_decode(
    mode: edl.SourcePlaybackMode, expected: list[int],
) -> None:
    """The mapping is computed from the accepted descriptor, never decoded media."""
    source = dataclasses.replace(_intent(mode=mode).source, source_out_exclusive_frame=3)
    assert [
        edl._source_playback_frame(
            source, timeline_offset_frames=offset, event_duration_frames=4,
            edl_fps_numerator=30, edl_fps_denominator=1,
        )
        for offset in range(4)
    ] == expected


@pytest.mark.parametrize("field, value", [
    ("crop_left_millionths", -1), ("crop_top_millionths", 1_000_001),
    ("crop_right_millionths", 1_000_001), ("crop_bottom_millionths", -1),
    ("opacity_millionths", 1_000_001),
])
def test_source_normalized_geometry_and_opacity_are_bounded_to_millionths(field: str, value: int) -> None:
    intent = _intent()
    invalid = dataclasses.replace(intent.source, **{field: value})
    with pytest.raises(edl.VideoEdlContractError) as error:
        _compile(intents=(dataclasses.replace(intent, source=invalid),))
    assert error.value.reason is edl.VideoEdlRejectionReason.CUE_RESOLUTION_INVALID


def test_generated_v5_v6_events_must_fit_the_requested_sequence_bounds() -> None:
    groups, events, frames, preview, report = _deps()
    words = frames.word_frames
    with pytest.raises(edl.VideoEdlContractError) as error:
        edl.compile_video_edl(
            intents=(), sequence_id="sequence_replay",
            sequence_start_word_id=words[1].start_word_id,
            sequence_end_word_id=words[-2].end_word_id,
            caption_groups=groups, emphasis_events=events, word_to_frame=frames,
            caption_preview=preview, v5_v6_collision_report=report,
            fps_numerator=30, fps_denominator=1,
        )
    assert error.value.reason is edl.VideoEdlRejectionReason.CUE_RESOLUTION_INVALID


def test_collision_report_is_a_required_fail_closed_admission_gate() -> None:
    groups, events, frames, _, _ = _deps()
    blocked_preview = compile_caption_preview(
        caption_groups=groups, emphasis_events=events, word_to_frame=frames,
        layout_policy=_policy(overlap=True),
    )
    blocked_report = compile_v5_v6_collision_report(caption_preview=blocked_preview)
    assert blocked_report.finding_count == blocked_report.blocker_count > 0
    words = frames.word_frames
    with pytest.raises(edl.VideoEdlContractError) as error:
        edl.compile_video_edl(
            intents=(_intent(),), sequence_id="sequence_replay",
            sequence_start_word_id=words[0].start_word_id,
            sequence_end_word_id=words[-1].end_word_id,
            caption_groups=groups, emphasis_events=events, word_to_frame=frames,
            caption_preview=blocked_preview, v5_v6_collision_report=blocked_report,
            fps_numerator=30, fps_denominator=1,
        )
    assert error.value.reason is edl.VideoEdlRejectionReason.V5_V6_COLLISION_BLOCKED
    assert error.value.pointer == "/v5_v6_collision_report"


def test_loader_canonical_precedence_rejects_bom_and_semantic_tamper() -> None:
    artifact = _compile()
    payload = edl.serialize_video_edl(artifact)
    common = dict(
        intents=(_intent(),), sequence_id="sequence_replay",
        sequence_start_word_id=_deps()[2].word_frames[0].start_word_id,
        sequence_end_word_id=_deps()[2].word_frames[-1].end_word_id,
        caption_groups=_deps()[0], emphasis_events=_deps()[1], word_to_frame=_deps()[2],
        caption_preview=_deps()[3], v5_v6_collision_report=_deps()[4],
        fps_numerator=30, fps_denominator=1,
    )
    with pytest.raises(edl.VideoEdlContractError) as error:
        edl.load_video_edl(b"\xef\xbb\xbf" + payload, **common)
    assert error.value.reason is edl.VideoEdlRejectionReason.NON_CANONICAL_SERIALIZATION
    value = json.loads(payload)
    value["tracks"][0]["events"][0]["start_frame"] += 1
    source = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(edl.VideoEdlContractError) as error:
        edl.load_video_edl(source, **common)
    assert error.value.reason in {
        edl.VideoEdlRejectionReason.CUE_RESOLUTION_INVALID,
        edl.VideoEdlRejectionReason.IDENTITY_MISMATCH,
    }


def test_loader_exact_bytes_and_identity_precedence_rows_are_explicit() -> None:
    artifact = _compile()
    kwargs = _load_kwargs()
    with pytest.raises(TypeError):
        edl.load_video_edl("not-bytes", **kwargs)  # type: ignore[arg-type]
    value = json.loads(edl.serialize_video_edl(artifact))
    value["video_edl_hash"] = "0" * 64
    with pytest.raises(edl.VideoEdlContractError) as error:
        edl.load_video_edl(json.dumps(value, sort_keys=True, separators=(",", ":")).encode(), **kwargs)
    assert error.value.reason is edl.VideoEdlRejectionReason.IDENTITY_MISMATCH
    assert error.value.pointer == "/"
    value = json.loads(edl.serialize_video_edl(artifact))
    value["tracks"][0]["events"][0]["event_id"] = "vevt_" + "0" * 32
    with pytest.raises(edl.VideoEdlContractError) as error:
        edl.load_video_edl(json.dumps(value, sort_keys=True, separators=(",", ":")).encode(), **kwargs)
    assert error.value.reason is edl.VideoEdlRejectionReason.IDENTITY_MISMATCH
    assert error.value.pointer == "/tracks/0/events/0"


def test_two_independent_compact_compilations_are_byte_identical() -> None:
    first, second = _compile(intents=_fixture_intents()), _compile(intents=_fixture_intents())
    assert first is not second
    assert edl.serialize_video_edl(first) == edl.serialize_video_edl(second)
    assert first.video_edl_hash == second.video_edl_hash


def test_loader_validates_nested_payload_shape_and_enums_before_identity() -> None:
    artifact = _compile()
    value = json.loads(edl.serialize_video_edl(artifact))
    common = dict(
        intents=(_intent(),), sequence_id="sequence_replay",
        sequence_start_word_id=_deps()[2].word_frames[0].start_word_id,
        sequence_end_word_id=_deps()[2].word_frames[-1].end_word_id,
        caption_groups=_deps()[0], emphasis_events=_deps()[1], word_to_frame=_deps()[2],
        caption_preview=_deps()[3], v5_v6_collision_report=_deps()[4],
        fps_numerator=30, fps_denominator=1,
    )
    value["tracks"][0]["events"][0]["payload"]["source"] = {"source_ref": "source_replay"}
    with pytest.raises(edl.VideoEdlContractError) as error:
        edl.load_video_edl(json.dumps(value, sort_keys=True, separators=(",", ":")).encode(), **common)
    assert error.value.reason is edl.VideoEdlRejectionReason.STRUCTURE_INVALID
    value = json.loads(edl.serialize_video_edl(artifact))
    value["tracks"][0]["events"][0]["payload"]["source"]["playback_mode"] = "UNKNOWN"
    with pytest.raises(edl.VideoEdlContractError) as error:
        edl.load_video_edl(json.dumps(value, sort_keys=True, separators=(",", ":")).encode(), **common)
    assert error.value.reason is edl.VideoEdlRejectionReason.UNSUPPORTED_VALUE


@pytest.mark.parametrize(("mutate", "reason"), [
    (lambda value: value.__setitem__("schema_version", "NOPE"), edl.VideoEdlRejectionReason.UNSUPPORTED_VALUE),
    (lambda value: value.__setitem__("unknown", 1), edl.VideoEdlRejectionReason.STRUCTURE_INVALID),
    (lambda value: value["tracks"].__setitem__(0, "bad"), edl.VideoEdlRejectionReason.STRUCTURE_INVALID),
    (lambda value: value["tracks"][0]["events"][0].__setitem__("event_hash", "0" * 64), edl.VideoEdlRejectionReason.IDENTITY_MISMATCH),
])
def test_loader_precedence_rows_are_explicit(mutate, reason) -> None:
    artifact = _compile()
    value = json.loads(edl.serialize_video_edl(artifact))
    mutate(value)
    common = dict(
        intents=(_intent(),), sequence_id="sequence_replay",
        sequence_start_word_id=_deps()[2].word_frames[0].start_word_id,
        sequence_end_word_id=_deps()[2].word_frames[-1].end_word_id,
        caption_groups=_deps()[0], emphasis_events=_deps()[1], word_to_frame=_deps()[2],
        caption_preview=_deps()[3], v5_v6_collision_report=_deps()[4], fps_numerator=30, fps_denominator=1,
    )
    with pytest.raises(edl.VideoEdlContractError) as error:
        edl.load_video_edl(json.dumps(value, sort_keys=True, separators=(",", ":")).encode(), **common)
    assert error.value.reason is reason


@pytest.mark.parametrize(("field", "replacement"), [
    ("project_id", "project_tampered"),
    ("fps_numerator", 24),
])
def test_loader_root_lineage_and_rate_binding_precede_cue_and_identity(
    field: str, replacement: object,
) -> None:
    """Row 5 rejects root metadata as a dependency binding, not a cue error."""
    artifact = _compile()
    value = json.loads(edl.serialize_video_edl(artifact))
    value[field] = replacement
    groups, events, frames, preview, report = _deps()
    words = frames.word_frames
    with pytest.raises(edl.VideoEdlContractError) as error:
        edl.load_video_edl(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode(),
            intents=(_intent(),), sequence_id="sequence_replay",
            sequence_start_word_id=words[0].start_word_id,
            sequence_end_word_id=words[-1].end_word_id,
            caption_groups=groups, emphasis_events=events, word_to_frame=frames,
            caption_preview=preview, v5_v6_collision_report=report,
            fps_numerator=30, fps_denominator=1,
        )
    assert error.value.reason is edl.VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID
    assert error.value.pointer == "/word_to_frame"


def test_loader_supplied_dependency_binding_precedes_sequence_and_collision_gates() -> None:
    """Row 5 binds supplied dependencies before later sequence/collision checks."""
    artifact = _compile()
    groups, events, frames, _, _ = _deps()
    blocked_preview = compile_caption_preview(
        caption_groups=groups, emphasis_events=events, word_to_frame=frames,
        layout_policy=_policy(overlap=True),
    )
    blocked_report = compile_v5_v6_collision_report(caption_preview=blocked_preview)
    assert blocked_report.finding_count > 0
    words = frames.word_frames
    with pytest.raises(edl.VideoEdlContractError) as error:
        edl.load_video_edl(
            edl.serialize_video_edl(artifact), intents=(_intent(),),
            sequence_id="sequence_replay",
            sequence_start_word_id="unknown_word_id",
            sequence_end_word_id=words[-1].end_word_id,
            caption_groups=groups, emphasis_events=events, word_to_frame=frames,
            caption_preview=blocked_preview,
            v5_v6_collision_report=blocked_report,
            fps_numerator=30, fps_denominator=1,
        )
    assert error.value.reason is edl.VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID
    assert error.value.pointer == "/caption_preview"


def test_loader_supplied_preview_and_report_binding_precede_collision_gate() -> None:
    """A genuine blocked pair cannot replace the serialized clean dependencies."""
    artifact = _compile()
    groups, events, frames, _, _ = _deps()
    blocked_preview = compile_caption_preview(
        caption_groups=groups, emphasis_events=events, word_to_frame=frames,
        layout_policy=_policy(overlap=True),
    )
    blocked_report = compile_v5_v6_collision_report(caption_preview=blocked_preview)
    assert blocked_report.finding_count > 0
    words = frames.word_frames
    with pytest.raises(edl.VideoEdlContractError) as error:
        edl.load_video_edl(
            edl.serialize_video_edl(artifact), intents=(_intent(),),
            sequence_id="sequence_replay", sequence_start_word_id=words[0].start_word_id,
            sequence_end_word_id=words[-1].end_word_id, caption_groups=groups,
            emphasis_events=events, word_to_frame=frames,
            caption_preview=blocked_preview, v5_v6_collision_report=blocked_report,
            fps_numerator=30, fps_denominator=1,
        )
    assert error.value.reason is edl.VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID
    assert error.value.pointer == "/caption_preview"


@pytest.mark.parametrize(("field", "replacement"), [
    ("schema_version", "VIDEO_EDL_V0"),
    ("hash_scope_version", "VIDEO_EDL_HASH_V0"),
])
def test_loader_rejects_wrong_nested_event_contract_literals(
    field: str, replacement: str,
) -> None:
    value = json.loads(edl.serialize_video_edl(_compile()))
    event_pointer = "/tracks/0/events/0"
    value["tracks"][0]["events"][0][field] = replacement
    groups, events, frames, preview, report = _deps()
    words = frames.word_frames
    with pytest.raises(edl.VideoEdlContractError) as error:
        edl.load_video_edl(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode(),
            intents=(_intent(),), sequence_id="sequence_replay",
            sequence_start_word_id=words[0].start_word_id,
            sequence_end_word_id=words[-1].end_word_id, caption_groups=groups,
            emphasis_events=events, word_to_frame=frames, caption_preview=preview,
            v5_v6_collision_report=report, fps_numerator=30, fps_denominator=1,
        )
    assert error.value.reason is edl.VideoEdlRejectionReason.UNSUPPORTED_VALUE
    assert error.value.pointer == event_pointer


def test_mutation_and_weak_registry_lifetime_are_fail_closed() -> None:
    artifact = _compile()
    object.__setattr__(artifact, "video_edl_hash", "0" * 64)
    with pytest.raises(edl.VideoEdlContractError) as error:
        edl.serialize_video_edl(artifact)
    assert error.value.reason is edl.VideoEdlRejectionReason.CONTENT_DRIFT
    clean = _compile()
    reference = weakref.ref(clean)
    key = id(clean)
    assert key in edl._REGISTRY
    del clean
    gc.collect()
    assert reference() is None
    assert key not in edl._REGISTRY


def test_static_boundary_excludes_renderer_media_audio_and_filesystem() -> None:
    source = (ROOT / "engine" / "contracts" / "edl.py").read_text(encoding="utf-8")
    for forbidden in ("remotion", "ffmpeg", "subprocess", "requests", "pathlib", "open(", "from .v2"):
        assert forbidden not in source.lower()
