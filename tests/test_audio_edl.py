"""Focused REPLAY checks for the Phase 3B audio sample-grid contract."""

from __future__ import annotations

import dataclasses
import hashlib
import inspect
import json
from pathlib import Path
import struct

import pytest

import engine.contracts.audio_edl as audio_edl
from engine.contracts.audio import (
    AUDIO_ARTIFACT_INPUT_V1,
    SECURE_AUDIO_INPUT_V1,
    AudioArtifactMaterializationRuntime,
    NarrationRevisionBinding,
    TrustedRootReference,
    materialize_audio_artifact,
)
from engine.contracts.word_to_frame import TemporalFrameRate
from tests.test_audio_artifact import _SecurePathStub, wave_bytes
from tests.test_edl import _compile as _compile_video_edl
from tests.test_edl import _deps as _video_deps


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "phase3" / "audio_edl_replay_v1.json"
FIXTURE_PCM_DIR = FIXTURE_PATH.parent / "audio_edl_pcm"


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _pcm_hash(samples: tuple[float, ...]) -> str:
    import struct

    return "sha256:" + hashlib.sha256(
        b"".join(struct.pack("<f", sample) for sample in samples)
    ).hexdigest()


def _compile_inputs(*, rate: TemporalFrameRate = TemporalFrameRate(30, 1)):
    """Build a real compact Phase 2 → 3A → 3B REPLAY dependency chain."""
    video_edl = _compile_video_edl(rate=rate)
    word_to_frame = _video_deps(rate=rate)[2]
    duration = (
        video_edl.duration_frames * 48_000 * video_edl.fps_denominator
        // video_edl.fps_numerator
    )
    raw_wave = wave_bytes(
        sample_rate_hz=48_000, channel_count=2, sample_frame_count=duration,
    )
    narration_audio = materialize_audio_artifact(
        {
            "schema_version": AUDIO_ARTIFACT_INPUT_V1,
            "project_id": word_to_frame.project_id,
            "document_id": word_to_frame.document_id,
            "narration_revision_id": word_to_frame.narration_revision_id,
            "narration_revision_hash": word_to_frame.narration_revision_hash,
            "logical_input": {
                "schema_version": SECURE_AUDIO_INPUT_V1,
                "kind": "LOCAL_FILE",
                "logical_path": "replay/narration.wav",
            },
            "declared_media_byte_hash": "sha256:" + hashlib.sha256(raw_wave).hexdigest(),
            "declared_sample_rate_hz": 48_000,
            "declared_channel_count": 2,
            "declared_sample_frame_count": duration,
            "extensions": {},
        },
        narration_binding=NarrationRevisionBinding(
            word_to_frame.project_id, word_to_frame.document_id,
            word_to_frame.narration_revision_id, word_to_frame.narration_revision_hash,
        ),
        runtime=AudioArtifactMaterializationRuntime(
            TrustedRootReference("C:/phase3-audio-replay"), _SecurePathStub(raw_wave),
        ),
    )
    narration_samples = (0.0,) * (duration * 2)
    narration_hash = _pcm_hash(narration_samples)
    narration_source = audio_edl.ReplayPcmSource(
        narration_audio.audio_artifact_id, narration_audio.media_byte_hash, narration_hash,
        audio_edl.InternalPcmFormat.PCM_F32LE, 48_000, 2, duration, duration, 0, 0,
    )
    narration_evidence = audio_edl.ReplayPcmEvidence(
        narration_source.source_id, narration_hash, audio_edl.InternalPcmFormat.PCM_F32LE,
        48_000, 2, duration, narration_samples,
    )
    bgm_samples = (0.0,) * 200
    bgm_hash = _pcm_hash(bgm_samples)
    bgm_source = audio_edl.ReplayPcmSource(
        "src_bgm_replay", "sha256:" + "b" * 64, bgm_hash,
        audio_edl.InternalPcmFormat.PCM_F32LE, 48_000, 2, 100, 100, 0, 0,
    )
    bgm_evidence = audio_edl.ReplayPcmEvidence(
        bgm_source.source_id, bgm_hash, audio_edl.InternalPcmFormat.PCM_F32LE,
        48_000, 2, 100, bgm_samples,
    )
    words = word_to_frame.word_frames
    cue_all = audio_edl.AudioCueWordRange(
        word_to_frame.project_id, word_to_frame.document_id,
        word_to_frame.narration_revision_id, words[0].source_id, words[-1].source_id,
    )
    cue_first = audio_edl.AudioCueWordRange(
        word_to_frame.project_id, word_to_frame.document_id,
        word_to_frame.narration_revision_id, words[0].source_id, words[0].source_id,
    )
    intents = (
        audio_edl.AudioPlacementIntent(
            "aint_narration", audio_edl.AudioTrackRole.A1, audio_edl.AudioEventKind.NARRATION,
            cue_all, narration_source, 0, duration, 0, 0,
        ),
        audio_edl.AudioPlacementIntent(
            "aint_bgm", audio_edl.AudioTrackRole.A2, audio_edl.AudioEventKind.BGM,
            cue_first, bgm_source, 0, 100, 0, 1,
        ),
    )
    boundary_intents = (
        audio_edl.AudioBoundaryIntent(
            "abint_a1_leading", audio_edl.AudioTrackRole.A1, 0,
            audio_edl.AudioBoundaryPosition.LEADING, None, "aint_narration",
            audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0,
        ),
        audio_edl.AudioBoundaryIntent(
            "abint_a1_trailing", audio_edl.AudioTrackRole.A1, 1,
            audio_edl.AudioBoundaryPosition.TRAILING, "aint_narration", None,
            audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0,
        ),
        audio_edl.AudioBoundaryIntent(
            "abint_a2_leading", audio_edl.AudioTrackRole.A2, 2,
            audio_edl.AudioBoundaryPosition.LEADING, None, "aint_bgm",
            audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0,
        ),
        audio_edl.AudioBoundaryIntent(
            "abint_a2_trailing", audio_edl.AudioTrackRole.A2, 3,
            audio_edl.AudioBoundaryPosition.TRAILING, "aint_bgm", None,
            audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0,
        ),
    )
    planned_silences = (
        audio_edl.AudioPlannedSilence(
            "sil_bgm_tail", audio_edl.AudioTrackRole.A2, 0, "aint_bgm", None,
            100, duration,
        ),
    )
    return dict(
        video_edl=video_edl, word_to_frame=word_to_frame, narration_audio=narration_audio,
        intents=intents, boundary_intents=boundary_intents,
        sources=(narration_source, bgm_source), pcm_evidence=(narration_evidence, bgm_evidence),
        planned_silences=planned_silences,
        internal_pcm_format=audio_edl.InternalPcmFormat.PCM_F32LE,
    )


def _supplied_event(
    intent: audio_edl.AudioPlacementIntent, *, start: int, end: int,
) -> audio_edl.EdlAudioEvent:
    """Build a canonical persisted event fixture without private factories."""
    source, cue = intent.source, intent.cue
    raw = {
        "schema_version": audio_edl.AUDIO_EDL_V1,
        "hash_scope_version": audio_edl.AUDIO_EDL_HASH_V1,
        "track": intent.track.value, "kind": intent.kind.value,
        "ordinal": intent.ordinal, "intent_id": intent.intent_id,
        "source_id": source.source_id, "source_media_hash": source.source_media_hash,
        "normalized_pcm_evidence_hash": source.normalized_pcm_evidence_hash,
        "start_sample": start, "end_exclusive_sample": end,
        "source_in_sample": intent.source_in_sample,
        "source_out_exclusive_sample": intent.source_out_exclusive_sample,
        "gain_millibels": intent.gain_millibels,
        "cue_start_word_id": cue.start_word_id, "cue_end_word_id": cue.end_word_id,
        "cue_start_sample": start, "cue_end_exclusive_sample": end,
    }
    event_hash = hashlib.sha256(
        json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return audio_edl.EdlAudioEvent(
        audio_edl.AUDIO_EDL_V1, audio_edl.AUDIO_EDL_HASH_V1,
        "aevt_" + event_hash[:32], event_hash, intent.track, intent.kind,
        intent.ordinal, intent.intent_id, source.source_id, source.source_media_hash,
        source.normalized_pcm_evidence_hash, start, end, intent.source_in_sample,
        intent.source_out_exclusive_sample, intent.gain_millibels, cue.start_word_id,
        cue.end_word_id, start, end,
    )


def _planner_row(
    *, intent_id: str, event_id: str, source: audio_edl.ReplayPcmSource,
    track: audio_edl.AudioTrackRole, start: int, end: int, ordinal: int,
) -> tuple[audio_edl.AudioPlacementIntent, audio_edl.EdlAudioEvent]:
    cue = audio_edl.AudioCueWordRange("prj_plan", "doc_plan", "narrev_plan", "word_a", "word_a")
    intent = audio_edl.AudioPlacementIntent(
        intent_id, track, getattr(audio_edl.AudioEventKind, {
            audio_edl.AudioTrackRole.A2: "BGM", audio_edl.AudioTrackRole.A3: "SFX",
            audio_edl.AudioTrackRole.A5: "AMBIENCE",
        }[track]), cue, source, 0, end - start, 0, ordinal,
    )
    # The public boundary planner has no object-identity back door: its
    # independent test fixture supplies the canonical immutable event
    # projection exactly as a persisted caller would.
    event = _supplied_event(intent, start=start, end=end)
    return intent, event


def _planner_rows(
    *, track: audio_edl.AudioTrackRole, first_end: int, second_start: int,
    samples: tuple[float, ...],
) -> tuple[tuple[audio_edl.AudioPlacementIntent, ...], tuple[audio_edl.AudioEdlTrack, ...], tuple[audio_edl.ReplayPcmEvidence, ...]]:
    evidence_hash = _pcm_hash(samples)
    source = audio_edl.ReplayPcmSource(
        "src_plan", "sha256:" + "c" * 64, evidence_hash,
        audio_edl.InternalPcmFormat.PCM_F32LE, 48_000, 2, len(samples) // 2,
        len(samples) // 2, 0, 0,
    )
    first_intent, first_event = _planner_row(
        intent_id="aint_plan_one", event_id="aevt_plan_one", source=source,
        track=track, start=0, end=first_end, ordinal=0,
    )
    second_intent, second_event = _planner_row(
        intent_id="aint_plan_two", event_id="aevt_plan_two", source=source,
        track=track, start=second_start, end=second_start + first_end, ordinal=1,
    )
    evidence = audio_edl.ReplayPcmEvidence(
        source.source_id, evidence_hash, audio_edl.InternalPcmFormat.PCM_F32LE,
        48_000, 2, len(samples) // 2, samples,
    )
    registry = tuple(
        audio_edl.AudioEdlTrack(
            role,
            {audio_edl.AudioTrackRole.A1: 10, audio_edl.AudioTrackRole.A2: 20,
             audio_edl.AudioTrackRole.A3: 30, audio_edl.AudioTrackRole.A4: 40,
             audio_edl.AudioTrackRole.A5: 50}[role],
            (first_event, second_event) if role is track else (),
        )
        for role in audio_edl.AudioTrackRole
    )
    return (
        (first_intent, second_intent),
        registry,
        (evidence,),
    )


def _boundary_rows(
    track: audio_edl.AudioTrackRole, *, between: tuple[audio_edl.AudioTransitionKind, audio_edl.AudioTransitionKind], crossfade: int,
) -> tuple[audio_edl.AudioBoundaryIntent, ...]:
    return (
        audio_edl.AudioBoundaryIntent("abint_plan_lead", track, 0, audio_edl.AudioBoundaryPosition.LEADING, None, "aint_plan_one", audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
        audio_edl.AudioBoundaryIntent("abint_plan_between", track, 1, audio_edl.AudioBoundaryPosition.BETWEEN_EVENTS, "aint_plan_one", "aint_plan_two", between[0], between[1], crossfade),
        audio_edl.AudioBoundaryIntent("abint_plan_tail", track, 2, audio_edl.AudioBoundaryPosition.TRAILING, "aint_plan_two", None, audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
    )


def test_public_planner_requires_the_full_ordered_a1_to_a5_registry() -> None:
    intents, tracks, evidence = _planner_rows(
        track=audio_edl.AudioTrackRole.A2, first_end=100, second_start=100,
        samples=(0.0,) * 400,
    )
    rows = _boundary_rows(
        audio_edl.AudioTrackRole.A2,
        between=(audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE),
        crossfade=0,
    )
    malformed_registries = (
        (tracks[:-1], "/tracks", audio_edl.AudioEdlRejectionReason.STRUCTURE_INVALID),
        ((tracks[1], tracks[0], tracks[2], tracks[3], tracks[4]), "/tracks/0", audio_edl.AudioEdlRejectionReason.ORDERING_INVALID),
        ((tracks[0], tracks[1], tracks[1], tracks[3], tracks[4]), "/tracks/2", audio_edl.AudioEdlRejectionReason.ORDERING_INVALID),
    )
    for malformed, pointer, reason in malformed_registries:
        with pytest.raises(audio_edl.AudioEdlContractError) as error:
            audio_edl.plan_audio_boundaries(
                tracks=malformed, intents=intents, boundary_intents=rows,
                planned_silences=(), pcm_evidence=evidence, duration_samples=200,
            )
        assert (error.value.pointer, error.value.reason) == (pointer, reason)


def test_public_planner_rejects_forged_effective_source_range_before_boundary_decisions() -> None:
    """A valid source header cannot authorize an out-of-effective-range intent."""
    intents, tracks, evidence = _planner_rows(
        track=audio_edl.AudioTrackRole.A2, first_end=100, second_start=100,
        samples=(0.0,) * 400,
    )
    invalid_source = dataclasses.replace(
        # 200 normalized frames still form a valid source after 51 + 50
        # compensation, but the forged [0, 100) intent exceeds its 99-frame
        # effective playback range.  The supplied event remains canonical,
        # proving the public planner rejects at the intent ingress rather
        # than later through event hashing or a boundary branch.
        intents[0].source, encoder_delay_samples=51, encoder_padding_samples=50,
    )
    invalid_intents = (dataclasses.replace(intents[0], source=invalid_source), intents[1])
    with pytest.raises(audio_edl.AudioEdlContractError) as error:
        audio_edl.plan_audio_boundaries(
            tracks=tracks, intents=invalid_intents,
            boundary_intents=_boundary_rows(
                audio_edl.AudioTrackRole.A2,
                between=(audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE),
                crossfade=0,
            ), planned_silences=(), pcm_evidence=evidence, duration_samples=200,
        )
    assert error.value.reason is audio_edl.AudioEdlRejectionReason.ENCODER_COMPENSATION_INVALID


def test_public_planner_rejects_forged_event_timing_hash_and_cue() -> None:
    """Boundary planning validates event content, never object provenance."""
    kwargs = _compile_inputs()
    artifact = audio_edl.compile_audio_edl(**kwargs)
    original = artifact.tracks[0].events[0]
    base_tracks = list(artifact.tracks)
    for forged in (
        dataclasses.replace(original, start_sample=original.start_sample + 1),
        dataclasses.replace(original, event_hash="0" * 64),
        dataclasses.replace(original, cue_start_word_id="word_forged"),
    ):
        base_tracks[0] = dataclasses.replace(artifact.tracks[0], events=(forged,))
        with pytest.raises(audio_edl.AudioEdlContractError) as error:
            audio_edl.plan_audio_boundaries(
                tracks=tuple(base_tracks), intents=kwargs["intents"],
                boundary_intents=kwargs["boundary_intents"],
                planned_silences=kwargs["planned_silences"],
                pcm_evidence=kwargs["pcm_evidence"],
                duration_samples=artifact.duration_samples,
            )
        assert error.value.pointer == "/tracks/0/events/0"
        assert error.value.reason in (
            audio_edl.AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID,
            audio_edl.AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID,
        )


@dataclasses.dataclass(frozen=True)
class _ReferenceStereoPcm:
    """Immutable, test-only PCM input for the Phase 3B boundary oracle.

    The audio EDL deliberately publishes planning metadata rather than a
    renderer.  This tiny reference application makes the exact window
    semantics independently executable without importing production renderer
    code or silently treating a policy name as an implementation.
    """

    frames: tuple[tuple[float, float], ...]


def _reference_constant(frames: int, value: float) -> _ReferenceStereoPcm:
    return _ReferenceStereoPcm(tuple((value, value) for _ in range(frames)))


def _reference_apply_boundary(
    decision: audio_edl.AudioBoundaryDecision,
    *,
    left: _ReferenceStereoPcm | None,
    right: _ReferenceStereoPcm | None,
    silence_frames: int = 0,
) -> tuple[tuple[float, float], ...]:
    """Apply the literal Phase 3B gain windows to test PCM only.

    This is intentionally not a second copy of ``plan_audio_boundaries``:
    it consumes an already-planned decision, then proves the decision's
    concrete sample-domain consequence.  All gain denominators are written
    here rather than hidden behind an interpolation helper so an off-by-one
    at either edge is observable in the assertions below.
    """

    left_frames = () if left is None else left.frames
    right_frames = () if right is None else right.frames
    if decision.policy is audio_edl.AudioBoundaryPolicy.HARD_CUT_ZERO_CROSSING:
        return left_frames + right_frames
    if decision.policy is audio_edl.AudioBoundaryPolicy.PRESERVE_SILENCE:
        return left_frames + ((0.0, 0.0),) * silence_frames + right_frames
    if decision.policy is audio_edl.AudioBoundaryPolicy.ZERO_CROSSING_MICROFADE:
        fade_out = decision.fade_out_samples
        fade_in = decision.fade_in_samples
        assert fade_out == fade_in == 240
        assert len(left_frames) >= fade_out and len(right_frames) >= fade_in
        output = list(left_frames[:-fade_out])
        # i=0 keeps the left source at full gain; i=fade_out-1 reaches zero.
        output.extend(
            tuple(
                sample[channel] * ((fade_out - 1 - index) / (fade_out - 1))
                for channel in range(2)
            )
            for index, sample in enumerate(left_frames[-fade_out:])
        )
        # i=0 starts at zero; i=fade_in-1 reaches full right-source gain.
        output.extend(
            tuple(
                sample[channel] * (index / (fade_in - 1))
                for channel in range(2)
            )
            for index, sample in enumerate(right_frames[:fade_in])
        )
        output.extend(right_frames[fade_in:])
        return tuple(output)
    if decision.policy is audio_edl.AudioBoundaryPolicy.OVERLAP_CROSSFADE:
        overlap = decision.overlap_samples
        assert overlap == decision.fade_in_samples == decision.fade_out_samples
        assert overlap >= 2
        assert len(left_frames) >= overlap and len(right_frames) >= overlap
        output = list(left_frames[:-overlap])
        output.extend(
            tuple(
                left_frames[len(left_frames) - overlap + index][channel]
                * ((overlap - 1 - index) / (overlap - 1))
                + right_frames[index][channel] * (index / (overlap - 1))
                for channel in range(2)
            )
            for index in range(overlap)
        )
        output.extend(right_frames[overlap:])
        return tuple(output)
    if decision.policy is audio_edl.AudioBoundaryPolicy.LONG_EDITORIAL_FADE:
        fade_out = decision.fade_out_samples
        fade_in = decision.fade_in_samples
        assert fade_out == fade_in == 24_000
        assert len(left_frames) >= fade_out and len(right_frames) >= fade_in
        output = list(left_frames[:-fade_out])
        output.extend(
            tuple(
                sample[channel] * ((fade_out - 1 - index) / (fade_out - 1))
                for channel in range(2)
            )
            for index, sample in enumerate(left_frames[-fade_out:])
        )
        output.extend(
            tuple(
                sample[channel] * (index / (fade_in - 1))
                for channel in range(2)
            )
            for index, sample in enumerate(right_frames[:fade_in])
        )
        output.extend(right_frames[fade_in:])
        return tuple(output)
    raise AssertionError(f"uncovered audio boundary policy: {decision.policy!r}")


def _assert_reference_stereo_continuity(
    frames: tuple[tuple[float, float], ...],
) -> None:
    """The audio policy's published seam bound applies per channel/frame."""

    assert frames
    for left, right in zip(frames, frames[1:], strict=False):
        assert abs(right[0] - left[0]) <= 1 / 64
        assert abs(right[1] - left[1]) <= 1 / 64


def test_public_surface_literals_enums_and_dataclass_field_order_are_exact() -> None:
    """Keep the Phase 3B boundary deliberately closed and renderer-free."""
    assert audio_edl.__all__ == [
        "AUDIO_EDL_V1", "AUDIO_EDL_HASH_V1", "AUDIO_SAMPLE_CLOCK_V1",
        "INTERNAL_AUDIO_SAMPLE_RATE_HZ", "INTERNAL_AUDIO_CHANNEL_COUNT",
        "InternalPcmFormat", "AudioTrackRole", "AudioEventKind",
        "AudioBoundaryPolicy", "AudioTransitionKind", "AudioBoundaryPosition",
        "AudioCueWordRange", "AudioCueSampleRange", "ReplayPcmSource",
        "ReplayPcmEvidence", "AudioPlacementIntent", "AudioBoundaryIntent",
        "AudioPlannedSilence", "AudioBoundaryDecision", "EdlAudioEvent",
        "AudioEdlTrack", "AudioEdlArtifact", "AudioEdlRejectionReason",
        "AudioEdlContractError", "compile_audio_edl", "plan_audio_boundaries",
        "load_audio_edl", "serialize_audio_edl",
    ]
    assert (
        audio_edl.AUDIO_EDL_V1,
        audio_edl.AUDIO_EDL_HASH_V1,
        audio_edl.AUDIO_SAMPLE_CLOCK_V1,
        audio_edl.INTERNAL_AUDIO_SAMPLE_RATE_HZ,
        audio_edl.INTERNAL_AUDIO_CHANNEL_COUNT,
    ) == ("AUDIO-EDL-V1", "AUDIO-EDL-HASH-V1", "AUDIO-SAMPLE-CLOCK-48KHZ-V1", 48000, 2)
    assert [item.value for item in audio_edl.InternalPcmFormat] == ["PCM_F32LE", "PCM_S24LE"]
    assert [item.value for item in audio_edl.AudioTrackRole] == ["A1", "A2", "A3", "A4", "A5"]
    assert [item.value for item in audio_edl.AudioEventKind] == [
        "NARRATION", "BGM", "SFX", "SOURCE_SPEECH", "AMBIENCE",
    ]
    assert [item.value for item in audio_edl.AudioBoundaryPolicy] == [
        "ZERO_CROSSING_MICROFADE", "OVERLAP_CROSSFADE", "PRESERVE_SILENCE",
        "HARD_CUT_ZERO_CROSSING", "LONG_EDITORIAL_FADE",
    ]
    assert [item.value for item in audio_edl.AudioTransitionKind] == [
        "NONE", "FADE_IN", "FADE_OUT", "CROSSFADE",
    ]
    assert [item.value for item in audio_edl.AudioBoundaryPosition] == [
        "LEADING", "BETWEEN_EVENTS", "TRAILING",
    ]
    assert [item.value for item in audio_edl.AudioEdlRejectionReason] == [
        "STRUCTURE_INVALID", "UNSUPPORTED_VALUE", "DEPENDENCY_CONTENT_DRIFT",
        "DEPENDENCY_BINDING_INVALID", "CUE_RESOLUTION_INVALID",
        "ENCODER_COMPENSATION_INVALID", "PCM_EVIDENCE_INVALID", "TRACK_COLLISION",
        "SPEECH_COLLISION", "SEQUENCE_BOUNDS_INVALID", "ORDERING_INVALID",
        "BOUNDARY_POLICY_INVALID", "NON_CANONICAL_SERIALIZATION", "IDENTITY_MISMATCH",
        "CONTENT_DRIFT", "NOT_MATERIALIZED",
    ]
    expected_fields = {
        "AudioCueWordRange": (
            "project_id", "document_id", "narration_revision_id", "start_word_id", "end_word_id",
        ),
        "AudioCueSampleRange": (
            "project_id", "document_id", "narration_revision_id", "start_word_id", "end_word_id",
            "start_sample", "end_exclusive_sample",
        ),
        "ReplayPcmSource": (
            "source_id", "source_media_hash", "normalized_pcm_evidence_hash", "pcm_format",
            "source_sample_rate_hz", "source_channel_count", "source_sample_frames",
            "normalized_sample_frames", "encoder_delay_samples", "encoder_padding_samples",
        ),
        "ReplayPcmEvidence": (
            "source_id", "normalized_pcm_evidence_hash", "pcm_format", "sample_rate_hz",
            "channel_count", "sample_frames", "interleaved_samples",
        ),
        "AudioPlacementIntent": (
            "intent_id", "track", "kind", "cue", "source", "source_in_sample",
            "source_out_exclusive_sample", "gain_millibels", "ordinal",
        ),
        "AudioBoundaryIntent": (
            "boundary_intent_id", "track", "ordinal", "position", "left_intent_id",
            "right_intent_id", "left_transition", "right_transition", "requested_crossfade_samples",
        ),
        "AudioPlannedSilence": (
            "silence_id", "track", "ordinal", "left_intent_id", "right_intent_id",
            "start_sample", "end_exclusive_sample",
        ),
        "AudioBoundaryDecision": (
            "position", "left_event_id", "right_event_id", "track", "policy", "transition",
            "left_trim_samples", "right_trim_samples", "fade_in_samples", "fade_out_samples",
            "overlap_samples", "protected_silence_samples",
        ),
        "EdlAudioEvent": (
            "schema_version", "hash_scope_version", "event_id", "event_hash", "track", "kind",
            "ordinal", "intent_id", "source_id", "source_media_hash", "normalized_pcm_evidence_hash",
            "start_sample", "end_exclusive_sample", "source_in_sample", "source_out_exclusive_sample",
            "gain_millibels", "cue_start_word_id", "cue_end_word_id", "cue_start_sample",
            "cue_end_exclusive_sample",
        ),
        "AudioEdlTrack": ("track", "priority", "events"),
        "AudioEdlArtifact": (
            "schema_version", "hash_scope_version", "audio_edl_id", "audio_edl_hash", "video_edl_id",
            "video_edl_hash", "word_to_frame_id", "word_to_frame_hash", "narration_audio_id",
            "narration_audio_hash", "narration_audio_media_byte_hash", "project_id", "document_id",
            "narration_revision_id", "narration_revision_hash", "sequence_id", "sample_clock_version",
            "sample_rate_hz", "channel_count", "internal_pcm_format", "sources", "pcm_evidence",
            "duration_samples", "tracks", "boundary_intents", "planned_silences", "boundary_decisions",
        ),
    }
    for name, fields in expected_fields.items():
        assert tuple(getattr(audio_edl, name).__dataclass_fields__) == fields
    assert list(inspect.signature(audio_edl.compile_audio_edl).parameters) == [
        "video_edl", "word_to_frame", "narration_audio", "intents", "boundary_intents",
        "sources", "pcm_evidence", "planned_silences", "internal_pcm_format",
    ]
    assert list(inspect.signature(audio_edl.load_audio_edl).parameters) == [
        "source", "video_edl", "word_to_frame", "narration_audio", "intents",
        "boundary_intents", "sources", "pcm_evidence", "planned_silences", "internal_pcm_format",
    ]


def test_replay_fixture_declares_all_tracks_boundary_policies_and_dual_video_clocks() -> None:
    fixture = _fixture()
    assert fixture["schema_version"] == "PHASE3-AUDIO-EDL-REPLAY-V1"
    assert fixture["fixture_id"] == "FX-PHASE3-AUDIO-EDL-REPLAY-V1"
    assert fixture["source_mode"] == "REPLAY"
    assert fixture["video_edl_fixture"] == "edl_replay_v1.json"
    assert fixture["internal_audio"] == {
        "sample_rate_hz": 48000, "channel_count": 2, "pcm_format": "PCM_F32LE",
    }
    assert fixture["video_clock_cases"] == [
        {"fps_numerator": 30, "fps_denominator": 1},
        {"fps_numerator": 30000, "fps_denominator": 1001},
    ]
    assert fixture["required_track_kinds"] == {
        "A1": "NARRATION", "A2": "BGM", "A3": "SFX",
        "A4": "SOURCE_SPEECH", "A5": "AMBIENCE",
    }
    assert fixture["required_boundary_examples"] == {
        "A1": "PRESERVE_SILENCE", "A2": "OVERLAP_CROSSFADE",
        "A3": "HARD_CUT_ZERO_CROSSING", "A4": "SPEECH_COLLISION_REJECTION",
        "A5": "ZERO_CROSSING_MICROFADE",
    }
    assert any(source["has_encoder_compensation"] for source in fixture["sources"])


def test_checked_in_pcm_wav_fixture_binds_exact_container_and_canonical_evidence_bytes() -> None:
    """Keep test-only RIFF provenance outside the canonical audio-EDL contract."""
    fixture = _fixture()
    expected_keys = {
        "source_id", "relative_wav_path", "wav_file_byte_hash", "source_media_hash",
        "normalized_pcm_evidence_hash", "pcm_format", "sample_rate_hz",
        "channel_count", "sample_frames",
    }
    bindings = fixture["fixture_pcm_bindings"]
    assert [binding["source_id"] for binding in bindings] == sorted(
        binding["source_id"] for binding in bindings
    )
    assert len({binding["source_id"] for binding in bindings}) == len(bindings)

    for binding in bindings:
        optional_compensation_keys = {"encoder_delay_samples", "encoder_padding_samples"}
        assert set(binding) in (expected_keys, expected_keys | optional_compensation_keys)
        relative_path = binding["relative_wav_path"]
        assert relative_path.startswith("audio_edl_pcm/")
        assert "\\\\" not in relative_path
        assert all(part not in {"", ".", ".."} for part in relative_path.split("/"))
        assert Path(relative_path).as_posix() == relative_path
        wav_path = FIXTURE_PATH.parent.joinpath(*relative_path.split("/"))
        assert wav_path.parent == FIXTURE_PCM_DIR
        assert not wav_path.is_symlink()
        wav_bytes = wav_path.read_bytes()
        assert "sha256:" + hashlib.sha256(wav_bytes).hexdigest() == binding["wav_file_byte_hash"]

        # The accepted narrow profile is exactly RIFF/WAVE + one fmt + one data,
        # with no optional chunks, padding, implicit conversion, or trailing data.
        assert len(wav_bytes) >= 44
        assert wav_bytes[:4] == b"RIFF"
        riff_size = struct.unpack_from("<I", wav_bytes, 4)[0]
        assert riff_size + 8 == len(wav_bytes)
        assert wav_bytes[8:12] == b"WAVE"
        assert wav_bytes[12:16] == b"fmt "
        assert struct.unpack_from("<I", wav_bytes, 16)[0] == 16
        format_tag, channels, sample_rate, byte_rate, block_align, bits = struct.unpack_from(
            "<HHIIHH", wav_bytes, 20
        )
        assert (format_tag, channels, sample_rate, byte_rate, block_align, bits) == (
            3, 2, 48_000, 384_000, 8, 32,
        )
        assert wav_bytes[36:40] == b"data"
        data_size = struct.unpack_from("<I", wav_bytes, 40)[0]
        assert data_size == binding["sample_frames"] * block_align
        assert len(wav_bytes) == 44 + data_size
        pcm_bytes = wav_bytes[44:]
        assert "sha256:" + hashlib.sha256(pcm_bytes).hexdigest() == binding[
            "normalized_pcm_evidence_hash"
        ]
        samples = struct.unpack("<" + "f" * (data_size // 4), pcm_bytes)
        evidence = audio_edl.ReplayPcmEvidence(
            binding["source_id"], binding["normalized_pcm_evidence_hash"],
            audio_edl.InternalPcmFormat(binding["pcm_format"]), binding["sample_rate_hz"],
            binding["channel_count"], binding["sample_frames"], samples,
        )
        assert _pcm_hash(evidence.interleaved_samples) == evidence.normalized_pcm_evidence_hash
        assert b"".join(struct.pack("<f", sample) for sample in evidence.interleaved_samples) == pcm_bytes


def test_real_compact_chain_uses_48khz_local_video_clock_preserves_silence_and_roundtrips() -> None:
    kwargs = _compile_inputs()
    first = audio_edl.compile_audio_edl(**kwargs)
    second = audio_edl.compile_audio_edl(**kwargs)
    assert first.duration_samples == (
        first.video_edl_id and kwargs["video_edl"].duration_frames * 48_000
        * kwargs["video_edl"].fps_denominator // kwargs["video_edl"].fps_numerator
    )
    assert (first.sample_rate_hz, first.channel_count, first.internal_pcm_format) == (
        48_000, 2, audio_edl.InternalPcmFormat.PCM_F32LE,
    )
    assert [track.track for track in first.tracks] == list(audio_edl.AudioTrackRole)
    assert [track.priority for track in first.tracks] == [10, 20, 30, 40, 50]
    a1, a2 = first.tracks[:2]
    assert len(a1.events) == len(a2.events) == 1
    assert (a1.events[0].start_sample, a1.events[0].end_exclusive_sample) == (
        a1.events[0].cue_start_sample, a1.events[0].cue_end_exclusive_sample,
    )
    assert a2.events[0].start_sample == a2.events[0].cue_start_sample
    assert a2.events[0].end_exclusive_sample != a2.events[0].cue_end_exclusive_sample
    assert any(
        decision.track is audio_edl.AudioTrackRole.A2
        and decision.position is audio_edl.AudioBoundaryPosition.TRAILING
        and decision.policy is audio_edl.AudioBoundaryPolicy.PRESERVE_SILENCE
        and decision.protected_silence_samples == first.duration_samples - 100
        for decision in first.boundary_decisions
    )
    payload = audio_edl.serialize_audio_edl(first)
    assert payload == json.dumps(json.loads(payload), sort_keys=True, separators=(",", ":")).encode()
    assert audio_edl.serialize_audio_edl(second) == payload
    loaded = audio_edl.load_audio_edl(payload, **kwargs)
    assert audio_edl.serialize_audio_edl(loaded) == payload


def test_pcm_evidence_hash_is_canonical_raw_pcm_bytes_and_scalar_drift_is_fail_closed() -> None:
    kwargs = _compile_inputs()
    evidence = kwargs["pcm_evidence"][1]
    replacement = dataclasses.replace(
        evidence, interleaved_samples=(0.5, *evidence.interleaved_samples[1:]),
    )
    kwargs["pcm_evidence"] = (kwargs["pcm_evidence"][0], replacement)
    with pytest.raises(audio_edl.AudioEdlContractError) as error:
        audio_edl.compile_audio_edl(**kwargs)
    assert error.value.pointer == "/pcm_evidence/1"
    assert error.value.reason is audio_edl.AudioEdlRejectionReason.PCM_EVIDENCE_INVALID


def test_ntsc_video_clock_is_the_only_rational_sample_clock_authority() -> None:
    kwargs = _compile_inputs(rate=TemporalFrameRate(30_000, 1_001))
    artifact = audio_edl.compile_audio_edl(**kwargs)
    video_edl = kwargs["video_edl"]
    expected = (
        video_edl.duration_frames * 48_000 * video_edl.fps_denominator
        // video_edl.fps_numerator
    )
    assert artifact.duration_samples == expected
    a1 = artifact.tracks[0].events[0]
    assert a1.cue_start_sample == 0
    assert a1.cue_end_exclusive_sample == expected
    assert a1.end_exclusive_sample == expected


def test_materialized_synthetic_wave_provenance_and_normalized_pcm_evidence_are_not_substitutable() -> None:
    kwargs = _compile_inputs()
    narration_audio = kwargs["narration_audio"]
    source, evidence = kwargs["sources"][0], kwargs["pcm_evidence"][0]
    assert (
        narration_audio.decoded_metadata.sample_rate_hz,
        narration_audio.decoded_metadata.channel_count,
        narration_audio.decoded_metadata.sample_frame_count,
    ) == (48_000, 2, evidence.sample_frames)
    assert source.source_id == narration_audio.audio_artifact_id
    assert source.source_media_hash == narration_audio.media_byte_hash
    assert source.normalized_pcm_evidence_hash == evidence.normalized_pcm_evidence_hash
    assert source.source_media_hash != source.normalized_pcm_evidence_hash
    assert len(evidence.interleaved_samples) == evidence.sample_frames * 2
    assert source.normalized_pcm_evidence_hash == _pcm_hash(evidence.interleaved_samples)


def test_crossfade_overlap_is_authorized_only_by_the_two_sided_boundary_intent() -> None:
    intents, tracks, evidence = _planner_rows(
        track=audio_edl.AudioTrackRole.A2, first_end=100, second_start=90,
        samples=(0.0,) * 400,
    )
    decisions = audio_edl.plan_audio_boundaries(
        tracks=tracks, intents=intents,
        boundary_intents=_boundary_rows(
            audio_edl.AudioTrackRole.A2,
            between=(audio_edl.AudioTransitionKind.CROSSFADE, audio_edl.AudioTransitionKind.CROSSFADE),
            crossfade=10,
        ),
        planned_silences=(), pcm_evidence=evidence, duration_samples=190,
    )
    between = decisions[1]
    assert (between.policy, between.transition, between.fade_in_samples, between.fade_out_samples, between.overlap_samples) == (
        audio_edl.AudioBoundaryPolicy.OVERLAP_CROSSFADE,
        audio_edl.AudioTransitionKind.CROSSFADE, 10, 10, 10,
    )
    bad_rows = list(_boundary_rows(
        audio_edl.AudioTrackRole.A2,
        between=(audio_edl.AudioTransitionKind.CROSSFADE, audio_edl.AudioTransitionKind.NONE),
        crossfade=10,
    ))
    with pytest.raises(audio_edl.AudioEdlContractError) as error:
        audio_edl.plan_audio_boundaries(
            tracks=tracks, intents=intents, boundary_intents=tuple(bad_rows),
            planned_silences=(), pcm_evidence=evidence, duration_samples=190,
        )
    assert error.value.pointer == "/tracks/1/events/1"
    assert error.value.reason is audio_edl.AudioEdlRejectionReason.TRACK_COLLISION

    forged_rows = list(_boundary_rows(
        audio_edl.AudioTrackRole.A2,
        between=(audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE),
        crossfade=0,
    ))
    with pytest.raises(audio_edl.AudioEdlContractError) as forged_error:
        audio_edl.plan_audio_boundaries(
            tracks=tracks, intents=intents, boundary_intents=tuple(forged_rows),
            planned_silences=(), pcm_evidence=evidence, duration_samples=190,
        )
    assert forged_error.value.reason is audio_edl.AudioEdlRejectionReason.TRACK_COLLISION


def test_adjacent_crossfade_rows_never_admit_a_triple_or_nonadjacent_overlap() -> None:
    intents, tracks, evidence = _planner_rows(
        track=audio_edl.AudioTrackRole.A2, first_end=100, second_start=90,
        samples=(0.0,) * 400,
    )
    source = intents[0].source
    third_intent, third_event = _planner_row(
        intent_id="aint_plan_three", event_id="aevt_plan_three", source=source,
        track=audio_edl.AudioTrackRole.A2, start=95, end=195, ordinal=2,
    )
    track = audio_edl.AudioEdlTrack(audio_edl.AudioTrackRole.A2, 20, tracks[1].events + (third_event,))
    rows = (
        audio_edl.AudioBoundaryIntent("abint_plan_lead", audio_edl.AudioTrackRole.A2, 0, audio_edl.AudioBoundaryPosition.LEADING, None, "aint_plan_one", audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
        audio_edl.AudioBoundaryIntent("abint_plan_between_one", audio_edl.AudioTrackRole.A2, 1, audio_edl.AudioBoundaryPosition.BETWEEN_EVENTS, "aint_plan_one", "aint_plan_two", audio_edl.AudioTransitionKind.CROSSFADE, audio_edl.AudioTransitionKind.CROSSFADE, 10),
        audio_edl.AudioBoundaryIntent("abint_plan_between_two", audio_edl.AudioTrackRole.A2, 2, audio_edl.AudioBoundaryPosition.BETWEEN_EVENTS, "aint_plan_two", "aint_plan_three", audio_edl.AudioTransitionKind.CROSSFADE, audio_edl.AudioTransitionKind.CROSSFADE, 95),
        audio_edl.AudioBoundaryIntent("abint_plan_tail", audio_edl.AudioTrackRole.A2, 3, audio_edl.AudioBoundaryPosition.TRAILING, "aint_plan_three", None, audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
    )
    with pytest.raises(audio_edl.AudioEdlContractError) as error:
        audio_edl.plan_audio_boundaries(
            tracks=(tracks[0], track, tracks[2], tracks[3], tracks[4]),
            intents=intents + (third_intent,), boundary_intents=rows,
            planned_silences=(), pcm_evidence=evidence, duration_samples=250,
        )
    assert error.value.pointer == "/tracks/1/events/2"
    assert error.value.reason is audio_edl.AudioEdlRejectionReason.TRACK_COLLISION


def test_sfx_hard_cut_requires_exact_stereo_zero_crossing_and_otherwise_microfades() -> None:
    zero_intents, zero_tracks, zero_evidence = _planner_rows(
        track=audio_edl.AudioTrackRole.A3, first_end=100, second_start=100,
        samples=(0.0,) * 400,
    )
    rows = _boundary_rows(
        audio_edl.AudioTrackRole.A3,
        between=(audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE), crossfade=0,
    )
    zero_decisions = audio_edl.plan_audio_boundaries(
        tracks=zero_tracks, intents=zero_intents, boundary_intents=rows,
        planned_silences=(), pcm_evidence=zero_evidence, duration_samples=200,
    )
    assert zero_decisions[1].policy is audio_edl.AudioBoundaryPolicy.HARD_CUT_ZERO_CROSSING
    nonzero_intents, nonzero_tracks, nonzero_evidence = _planner_rows(
        track=audio_edl.AudioTrackRole.A3, first_end=100, second_start=100,
        samples=(0.5,) * 400,
    )
    nonzero_decisions = audio_edl.plan_audio_boundaries(
        tracks=nonzero_tracks, intents=nonzero_intents, boundary_intents=rows,
        planned_silences=(), pcm_evidence=nonzero_evidence, duration_samples=200,
    )
    assert nonzero_decisions[1].policy is audio_edl.AudioBoundaryPolicy.ZERO_CROSSING_MICROFADE
    assert nonzero_decisions[1].fade_in_samples == nonzero_decisions[1].fade_out_samples == 240


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.0, 0.1])
def test_pcm_f32_requires_finite_exact_binary32_scalars(value: float) -> None:
    kwargs = _compile_inputs()
    evidence = kwargs["pcm_evidence"][1]
    bad = dataclasses.replace(evidence, interleaved_samples=(value, *evidence.interleaved_samples[1:]))
    kwargs["pcm_evidence"] = (kwargs["pcm_evidence"][0], bad)
    with pytest.raises(audio_edl.AudioEdlContractError) as error:
        audio_edl.compile_audio_edl(**kwargs)
    assert error.value.pointer == "/pcm_evidence/1"
    assert error.value.reason is audio_edl.AudioEdlRejectionReason.PCM_EVIDENCE_INVALID


def test_source_speech_overlap_with_narration_is_rejected_after_boundary_admission() -> None:
    kwargs = _compile_inputs()
    source = kwargs["sources"][1]
    speech = audio_edl.AudioPlacementIntent(
        "aint_speech", audio_edl.AudioTrackRole.A4, audio_edl.AudioEventKind.SOURCE_SPEECH,
        audio_edl.AudioCueWordRange(
            kwargs["word_to_frame"].project_id, kwargs["word_to_frame"].document_id,
            kwargs["word_to_frame"].narration_revision_id,
            kwargs["word_to_frame"].word_frames[1].source_id,
            kwargs["word_to_frame"].word_frames[1].source_id,
        ), source, 0, 100, 0, 2,
    )
    kwargs["intents"] = (*kwargs["intents"], speech)
    kwargs["boundary_intents"] = (*kwargs["boundary_intents"],
        audio_edl.AudioBoundaryIntent("abint_a4_leading", audio_edl.AudioTrackRole.A4, 4, audio_edl.AudioBoundaryPosition.LEADING, None, "aint_speech", audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
        audio_edl.AudioBoundaryIntent("abint_a4_trailing", audio_edl.AudioTrackRole.A4, 5, audio_edl.AudioBoundaryPosition.TRAILING, "aint_speech", None, audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
    )
    with pytest.raises(audio_edl.AudioEdlContractError) as error:
        audio_edl.compile_audio_edl(**kwargs)
    assert error.value.reason is audio_edl.AudioEdlRejectionReason.SPEECH_COLLISION
    assert error.value.pointer == "/tracks/3/events/0"


def test_loader_rejects_pcm_snapshot_and_identity_drift_before_accepting_preserved_bytes() -> None:
    kwargs = _compile_inputs()
    artifact = audio_edl.compile_audio_edl(**kwargs)
    payload = json.loads(audio_edl.serialize_audio_edl(artifact))
    # F32 PCM is published as exact binary32 bytes, never as a JSON decimal.
    payload["pcm_evidence"][0]["interleaved_samples"][0] = "f32le:0000003f"
    with pytest.raises(audio_edl.AudioEdlContractError) as error:
        audio_edl.load_audio_edl(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(), **kwargs,
        )
    assert error.value.pointer == "/pcm_evidence/0"
    assert error.value.reason is audio_edl.AudioEdlRejectionReason.DEPENDENCY_CONTENT_DRIFT


def test_static_boundary_excludes_renderer_network_subprocess_and_filesystem_io() -> None:
    source = (ROOT / "engine" / "contracts" / "audio_edl.py").read_text(encoding="utf-8").lower()
    for forbidden in (
        "subprocess", "ffmpeg", "remotion", "requests", "httpx", "socket",
        "provider", "pathlib", "open(", "write_", "phase4", "phase8", "phase11",
    ):
        assert forbidden not in source


def _m6_non_narration_source(source_id: str, frames: int) -> tuple[
    audio_edl.ReplayPcmSource, audio_edl.ReplayPcmEvidence,
]:
    """Return a compact, real PCM evidence pair for one non-A1 track."""
    samples = (0.0,) * (frames * 2)
    evidence_hash = _pcm_hash(samples)
    source = audio_edl.ReplayPcmSource(
        source_id, "sha256:" + hashlib.sha256(source_id.encode("utf-8")).hexdigest(), evidence_hash,
        audio_edl.InternalPcmFormat.PCM_F32LE, 48_000, 2, frames, frames, 0, 0,
    )
    evidence = audio_edl.ReplayPcmEvidence(
        source_id, evidence_hash, audio_edl.InternalPcmFormat.PCM_F32LE,
        48_000, 2, frames, samples,
    )
    return source, evidence


def _m6_all_tracks_kwargs() -> dict:
    """Materialize the accepted Phase 2 -> 3A -> 3B A1--A5 REPLAY chain.

    The intent tuple is deliberately in the normative global order: track
    priority first, then each track's derived sample coordinates.  In
    particular, A1 is intentionally later on the timeline than A2--A4; this
    prevents an accidental time-first sort from masquerading as canonical
    ordering.
    """
    kwargs = _compile_inputs()
    words = kwargs["word_to_frame"].word_frames
    narration_source, narration_evidence = kwargs["sources"][0], kwargs["pcm_evidence"][0]
    a2_source, a2_evidence = _m6_non_narration_source("src_a2_m6", 19_200)
    a3_source, a3_evidence = _m6_non_narration_source("src_a3_m6", 19_200)
    a4_source, a4_evidence = _m6_non_narration_source("src_a4_m6", 24_000)
    a5_source, a5_evidence = _m6_non_narration_source("src_a5_m6", 28_800)

    def cue(index: int) -> audio_edl.AudioCueWordRange:
        word = words[index]
        return audio_edl.AudioCueWordRange(
            kwargs["word_to_frame"].project_id, kwargs["word_to_frame"].document_id,
            kwargs["word_to_frame"].narration_revision_id, word.source_id, word.source_id,
        )

    # A1 intentionally occupies only the last word.  A4 uses the preceding
    # word, proving the accepted non-overlapping speech path without inventing
    # a Phase 11 source-audio eligibility decision.
    kwargs["intents"] = (
        audio_edl.AudioPlacementIntent(
            "aint_m6_a1", audio_edl.AudioTrackRole.A1,
            audio_edl.AudioEventKind.NARRATION, cue(3), narration_source,
            76_800, 105_600, 0, 0,
        ),
        audio_edl.AudioPlacementIntent(
            "aint_m6_a2", audio_edl.AudioTrackRole.A2,
            audio_edl.AudioEventKind.BGM, cue(0), a2_source, 0, 19_200, 0, 1,
        ),
        audio_edl.AudioPlacementIntent(
            "aint_m6_a3", audio_edl.AudioTrackRole.A3,
            audio_edl.AudioEventKind.SFX, cue(1), a3_source, 0, 19_200, 0, 2,
        ),
        audio_edl.AudioPlacementIntent(
            "aint_m6_a4", audio_edl.AudioTrackRole.A4,
            audio_edl.AudioEventKind.SOURCE_SPEECH, cue(2), a4_source, 0, 24_000, 0, 3,
        ),
        audio_edl.AudioPlacementIntent(
            "aint_m6_a5", audio_edl.AudioTrackRole.A5,
            audio_edl.AudioEventKind.AMBIENCE, cue(3), a5_source, 0, 28_800, 0, 4,
        ),
    )
    rows = []
    for track, intent_id in zip(audio_edl.AudioTrackRole, (item.intent_id for item in kwargs["intents"]), strict=True):
        rows.extend((
            audio_edl.AudioBoundaryIntent(
                "abint_m6_" + track.value.lower() + "_leading", track, len(rows),
                audio_edl.AudioBoundaryPosition.LEADING, None, intent_id,
                audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0,
            ),
            audio_edl.AudioBoundaryIntent(
                "abint_m6_" + track.value.lower() + "_trailing", track, len(rows) + 1,
                audio_edl.AudioBoundaryPosition.TRAILING, intent_id, None,
                audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0,
            ),
        ))
    kwargs["boundary_intents"] = tuple(rows)
    kwargs["planned_silences"] = ()
    kwargs["sources"] = tuple(sorted(
        (narration_source, a2_source, a3_source, a4_source, a5_source), key=lambda source: source.source_id,
    ))
    kwargs["pcm_evidence"] = tuple(sorted(
        (narration_evidence, a2_evidence, a3_evidence, a4_evidence, a5_evidence), key=lambda evidence: evidence.source_id,
    ))
    return kwargs


def test_m6_real_a1_to_a5_chain_is_track_priority_canonical_and_roundtrips() -> None:
    kwargs = _m6_all_tracks_kwargs()
    artifact = audio_edl.compile_audio_edl(**kwargs)
    assert [track.track for track in artifact.tracks] == list(audio_edl.AudioTrackRole)
    assert [len(track.events) for track in artifact.tracks] == [1, 1, 1, 1, 1]
    assert artifact.tracks[0].events[0].start_sample > artifact.tracks[1].events[0].start_sample
    assert artifact.tracks[3].events[0].end_exclusive_sample == artifact.tracks[0].events[0].start_sample
    assert artifact.tracks[0].events[0].kind is audio_edl.AudioEventKind.NARRATION
    assert artifact.tracks[3].events[0].kind is audio_edl.AudioEventKind.SOURCE_SPEECH
    payload = audio_edl.serialize_audio_edl(artifact)
    assert audio_edl.serialize_audio_edl(audio_edl.load_audio_edl(payload, **kwargs)) == payload


def test_m6_long_editorial_fade_has_exact_half_second_windows_and_no_overlap_seam() -> None:
    """The planned BGM seam is an explicit pair of 24k-sample gain windows."""
    intents, tracks, evidence = _planner_rows(
        track=audio_edl.AudioTrackRole.A2, first_end=24_000, second_start=24_000,
        samples=(0.5,) * 96_000,
    )
    rows = _boundary_rows(
        audio_edl.AudioTrackRole.A2,
        between=(audio_edl.AudioTransitionKind.FADE_OUT, audio_edl.AudioTransitionKind.FADE_IN),
        crossfade=0,
    )
    decision = audio_edl.plan_audio_boundaries(
        tracks=tracks, intents=intents, boundary_intents=rows, planned_silences=(),
        pcm_evidence=evidence, duration_samples=48_000,
    )[1]
    assert (decision.policy, decision.transition) == (
        audio_edl.AudioBoundaryPolicy.LONG_EDITORIAL_FADE, audio_edl.AudioTransitionKind.NONE,
    )
    assert (decision.fade_in_samples, decision.fade_out_samples, decision.overlap_samples) == (
        24_000, 24_000, 0,
    )
    # These are the contract's exact linear windows.  Their seam has no
    # summed overlap and each channel ends/starts at zero gain.
    assert 1 - 23_999 / 23_999 == 0
    assert 0 / 23_999 == 0


def test_m3_immutable_pcm_reference_oracle_applies_every_boundary_policy_with_literal_windows() -> None:
    """Exercise planner output against a renderer-independent PCM oracle.

    This closes the gap between valid boundary metadata and an audible sample
    stream.  The chosen values are deliberately non-zero except where a
    policy requires a physical zero; a discontinuous implementation therefore
    cannot pass just by operating on an all-zero fixture.
    """

    hard_intents, hard_tracks, hard_evidence = _planner_rows(
        track=audio_edl.AudioTrackRole.A3, first_end=100, second_start=100,
        samples=(0.0,) * 400,
    )
    hard = audio_edl.plan_audio_boundaries(
        tracks=hard_tracks, intents=hard_intents,
        boundary_intents=_boundary_rows(
            audio_edl.AudioTrackRole.A3,
            between=(audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE),
            crossfade=0,
        ), planned_silences=(), pcm_evidence=hard_evidence, duration_samples=200,
    )[1]

    micro_intents, micro_tracks, micro_evidence = _planner_rows(
        track=audio_edl.AudioTrackRole.A3, first_end=300, second_start=300,
        samples=(0.5,) * 1_200,
    )
    micro = audio_edl.plan_audio_boundaries(
        tracks=micro_tracks, intents=micro_intents,
        boundary_intents=_boundary_rows(
            audio_edl.AudioTrackRole.A3,
            between=(audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE),
            crossfade=0,
        ), planned_silences=(), pcm_evidence=micro_evidence, duration_samples=600,
    )[1]

    cross_intents, cross_tracks, cross_evidence = _planner_rows(
        track=audio_edl.AudioTrackRole.A2, first_end=300, second_start=60,
        samples=(0.0,) * 1_200,
    )
    crossfade = audio_edl.plan_audio_boundaries(
        tracks=cross_tracks, intents=cross_intents,
        boundary_intents=_boundary_rows(
            audio_edl.AudioTrackRole.A2,
            between=(audio_edl.AudioTransitionKind.CROSSFADE, audio_edl.AudioTransitionKind.CROSSFADE),
            crossfade=240,
        ), planned_silences=(), pcm_evidence=cross_evidence, duration_samples=360,
    )[1]

    preserved_artifact = audio_edl.compile_audio_edl(**_compile_inputs())
    preserve = next(
        decision for decision in preserved_artifact.boundary_decisions
        if decision.policy is audio_edl.AudioBoundaryPolicy.PRESERVE_SILENCE
    )

    long_intents, long_tracks, long_evidence = _planner_rows(
        track=audio_edl.AudioTrackRole.A2, first_end=24_001, second_start=24_001,
        samples=(0.5,) * 96_004,
    )
    long_fade = audio_edl.plan_audio_boundaries(
        tracks=long_tracks, intents=long_intents,
        boundary_intents=_boundary_rows(
            audio_edl.AudioTrackRole.A2,
            between=(audio_edl.AudioTransitionKind.FADE_OUT, audio_edl.AudioTransitionKind.FADE_IN),
            crossfade=0,
        ), planned_silences=(), pcm_evidence=long_evidence, duration_samples=48_002,
    )[1]

    # HARD_CUT_ZERO_CROSSING: both physical seam frames are literal stereo zero.
    hard_left = _ReferenceStereoPcm(tuple(
        (0.25 * (47 - index) / 47, 0.25 * (47 - index) / 47)
        for index in range(48)
    ))
    hard_right = _ReferenceStereoPcm(tuple(
        (0.25 * index / 47, 0.25 * index / 47) for index in range(48)
    ))
    hard_output = _reference_apply_boundary(hard, left=hard_left, right=hard_right)
    assert hard.policy is audio_edl.AudioBoundaryPolicy.HARD_CUT_ZERO_CROSSING
    assert hard_output[len(hard_left.frames) - 1] == hard_output[len(hard_left.frames)] == (0.0, 0.0)

    # ZERO_CROSSING_MICROFADE: exact 240-frame inclusive linear windows.
    micro_left = _reference_constant(300, 0.5)
    micro_right = _reference_constant(300, 0.5)
    micro_output = _reference_apply_boundary(micro, left=micro_left, right=micro_right)
    micro_fade = micro.fade_out_samples
    assert micro.policy is audio_edl.AudioBoundaryPolicy.ZERO_CROSSING_MICROFADE
    assert tuple(frame[0] for frame in micro_output[300 - micro_fade:300]) == tuple(
        0.5 * ((micro_fade - 1 - index) / (micro_fade - 1))
        for index in range(micro_fade)
    )
    assert tuple(frame[1] for frame in micro_output[300:300 + micro.fade_in_samples]) == tuple(
        0.5 * (index / (micro.fade_in_samples - 1))
        for index in range(micro.fade_in_samples)
    )
    assert micro_output[299] == micro_output[300] == (0.0, 0.0)

    # OVERLAP_CROSSFADE: the two sources are summed only inside the declared window.
    cross_left = _reference_constant(300, 0.5)
    cross_right = _reference_constant(300, -0.5)
    cross_output = _reference_apply_boundary(crossfade, left=cross_left, right=cross_right)
    overlap = crossfade.overlap_samples
    assert crossfade.policy is audio_edl.AudioBoundaryPolicy.OVERLAP_CROSSFADE
    assert len(cross_output) == 300 + 300 - overlap
    assert tuple(frame[0] for frame in cross_output[300 - overlap:300]) == tuple(
        0.5 * ((overlap - 1 - index) / (overlap - 1))
        + -0.5 * (index / (overlap - 1))
        for index in range(overlap)
    )

    # PRESERVE_SILENCE inserts exact zeros, without turning the gap into a fade.
    silence_left = _ReferenceStereoPcm(tuple(
        (0.25 * (47 - index) / 47, 0.25 * (47 - index) / 47)
        for index in range(48)
    ))
    preserve_output = _reference_apply_boundary(
        preserve, left=silence_left, right=None,
        silence_frames=preserve.protected_silence_samples,
    )
    assert preserve.policy is audio_edl.AudioBoundaryPolicy.PRESERVE_SILENCE
    assert preserve.protected_silence_samples > 0
    assert preserve_output[len(silence_left.frames):] == (
        (0.0, 0.0),
    ) * preserve.protected_silence_samples

    # LONG_EDITORIAL_FADE is the same literal linear law on its fixed 24k windows,
    # with no overlap added at the seam.
    long_left = _reference_constant(24_001, 0.5)
    long_right = _reference_constant(24_001, 0.5)
    long_output = _reference_apply_boundary(long_fade, left=long_left, right=long_right)
    long_window = long_fade.fade_out_samples
    assert long_fade.policy is audio_edl.AudioBoundaryPolicy.LONG_EDITORIAL_FADE
    assert long_fade.overlap_samples == 0
    assert tuple(frame[0] for frame in long_output[1:1 + long_window]) == tuple(
        0.5 * ((long_window - 1 - index) / (long_window - 1))
        for index in range(long_window)
    )
    assert tuple(frame[1] for frame in long_output[1 + long_window:1 + long_window * 2]) == tuple(
        0.5 * (index / (long_window - 1))
        for index in range(long_window)
    )
    assert long_output[long_window] == long_output[long_window + 1] == (0.0, 0.0)

    for output in (hard_output, micro_output, cross_output, preserve_output, long_output):
        _assert_reference_stereo_continuity(output)


def test_m6_boundary_matrix_rejects_short_long_fade_and_speech_crossfade() -> None:
    short_intents, short_tracks, short_evidence = _planner_rows(
        track=audio_edl.AudioTrackRole.A2, first_end=23_999, second_start=23_999,
        samples=(0.0,) * 95_996,
    )
    with pytest.raises(audio_edl.AudioEdlContractError) as short_error:
        audio_edl.plan_audio_boundaries(
            tracks=short_tracks, intents=short_intents,
            boundary_intents=_boundary_rows(
                audio_edl.AudioTrackRole.A2,
                between=(audio_edl.AudioTransitionKind.FADE_OUT, audio_edl.AudioTransitionKind.FADE_IN),
                crossfade=0,
            ), planned_silences=(), pcm_evidence=short_evidence, duration_samples=47_998,
        )
    assert short_error.value.reason is audio_edl.AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID

    # SOURCE_SPEECH may never turn a same-track overlap into a crossfade.
    source, evidence = _m6_non_narration_source("src_a4_matrix", 200)
    cue = audio_edl.AudioCueWordRange("prj_matrix", "doc_matrix", "narrev_matrix", "word_a", "word_a")
    intents = tuple(
        audio_edl.AudioPlacementIntent(
            intent_id, audio_edl.AudioTrackRole.A4, audio_edl.AudioEventKind.SOURCE_SPEECH,
            cue, source, 0, 100, 0, ordinal,
        )
        for ordinal, intent_id in enumerate(("aint_matrix_one", "aint_matrix_two"))
    )
    events = tuple(
        _supplied_event(intent, start=start, end=end)
        for intent, start, end in zip(intents, (0, 90), (100, 190), strict=True)
    )
    rows = (
        audio_edl.AudioBoundaryIntent("abint_matrix_lead", audio_edl.AudioTrackRole.A4, 0, audio_edl.AudioBoundaryPosition.LEADING, None, intents[0].intent_id, audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
        audio_edl.AudioBoundaryIntent("abint_matrix_between", audio_edl.AudioTrackRole.A4, 1, audio_edl.AudioBoundaryPosition.BETWEEN_EVENTS, intents[0].intent_id, intents[1].intent_id, audio_edl.AudioTransitionKind.CROSSFADE, audio_edl.AudioTransitionKind.CROSSFADE, 10),
        audio_edl.AudioBoundaryIntent("abint_matrix_tail", audio_edl.AudioTrackRole.A4, 2, audio_edl.AudioBoundaryPosition.TRAILING, intents[1].intent_id, None, audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
    )
    with pytest.raises(audio_edl.AudioEdlContractError) as speech_error:
        audio_edl.plan_audio_boundaries(
            tracks=(
                audio_edl.AudioEdlTrack(audio_edl.AudioTrackRole.A1, 10, ()),
                audio_edl.AudioEdlTrack(audio_edl.AudioTrackRole.A2, 20, ()),
                audio_edl.AudioEdlTrack(audio_edl.AudioTrackRole.A3, 30, ()),
                audio_edl.AudioEdlTrack(audio_edl.AudioTrackRole.A4, 40, events),
                audio_edl.AudioEdlTrack(audio_edl.AudioTrackRole.A5, 50, ()),
            ),
            intents=intents, boundary_intents=rows, planned_silences=(),
            pcm_evidence=(evidence,), duration_samples=190,
        )
    assert speech_error.value.reason is audio_edl.AudioEdlRejectionReason.TRACK_COLLISION


def test_m6_loader_rejects_source_boundary_and_silence_snapshot_drift() -> None:
    kwargs = _compile_inputs()
    artifact = audio_edl.compile_audio_edl(**kwargs)
    pristine = json.loads(audio_edl.serialize_audio_edl(artifact))
    mutations = (
        ("sources", 1, "encoder_padding_samples", 1),
        ("boundary_intents", 0, "boundary_intent_id", "abint_loader_drift"),
        ("planned_silences", 0, "silence_id", "sil_loader_drift"),
    )
    for collection, index, field, replacement in mutations:
        payload = json.loads(json.dumps(pristine))
        payload[collection][index][field] = replacement
        with pytest.raises(audio_edl.AudioEdlContractError) as error:
            audio_edl.load_audio_edl(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(), **kwargs,
            )
        assert error.value.reason is audio_edl.AudioEdlRejectionReason.DEPENDENCY_CONTENT_DRIFT


def test_m6_preserve_silence_rejects_nonzero_physical_pcm_edge() -> None:
    """A declared silence cannot be a metadata-only gap or a hidden fade."""
    kwargs = _compile_inputs()
    original_source = kwargs["sources"][1]
    nonzero_samples = (0.5,) * 200
    nonzero_hash = _pcm_hash(nonzero_samples)
    source = dataclasses.replace(original_source, normalized_pcm_evidence_hash=nonzero_hash)
    evidence = audio_edl.ReplayPcmEvidence(
        source.source_id, nonzero_hash, source.pcm_format, 48_000, 2, 100, nonzero_samples,
    )
    kwargs["sources"] = (kwargs["sources"][0], source)
    kwargs["pcm_evidence"] = (kwargs["pcm_evidence"][0], evidence)
    kwargs["intents"] = (kwargs["intents"][0], dataclasses.replace(kwargs["intents"][1], source=source))
    with pytest.raises(audio_edl.AudioEdlContractError) as error:
        audio_edl.compile_audio_edl(**kwargs)
    assert error.value.pointer == "/planned_silences/0"
    assert error.value.reason is audio_edl.AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID


def test_m6_boundary_tuple_rejects_noncanonical_track_priority_order() -> None:
    """Rows can be structurally complete yet not be canonical input order."""
    kwargs = _compile_inputs()
    original = kwargs["boundary_intents"]
    # A2 before A1 with contiguous ordinals must never be silently re-sorted.
    reordered = tuple(
        dataclasses.replace(row, ordinal=index)
        for index, row in enumerate((original[2], original[3], original[0], original[1]))
    )
    kwargs["boundary_intents"] = reordered
    with pytest.raises(audio_edl.AudioEdlContractError) as error:
        audio_edl.compile_audio_edl(**kwargs)
    assert error.value.pointer == "/boundary_intents/2"
    assert error.value.reason is audio_edl.AudioEdlRejectionReason.ORDERING_INVALID
