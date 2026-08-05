"""Phase 3B checked-in-REPLAY end-to-end acceptance evidence.

This is deliberately separate from the unit-contract suite: it reads the
checked-in fixture and RIFF payload, builds the immutable sources/evidence,
then runs the real compile -> serialize -> load chain for both accepted video
clocks.  No renderer, decoder, provider, or generated fixture is involved.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
import struct

import pytest

import engine.contracts.audio_edl as audio_edl
from engine.contracts.word_to_frame import TemporalFrameRate
from tests.test_audio_edl import _compile_inputs, _pcm_hash


_ROOT = Path(__file__).resolve().parents[1]
_FIXTURE_PATH = _ROOT / "tests" / "fixtures" / "phase3" / "audio_edl_replay_v1.json"


def _fixture() -> dict[str, object]:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _checked_in_pcm(binding_index: int = 0) -> tuple[dict[str, object], tuple[float, ...]]:
    fixture = _fixture()
    binding = fixture["fixture_pcm_bindings"][binding_index]
    path = _FIXTURE_PATH.parent.joinpath(*binding["relative_wav_path"].split("/"))
    wav = path.read_bytes()
    assert "sha256:" + hashlib.sha256(wav).hexdigest() == binding["wav_file_byte_hash"]
    assert wav[:4] == b"RIFF" and wav[8:12] == b"WAVE" and wav[12:16] == b"fmt "
    assert struct.unpack_from("<HHIIHH", wav, 20) == (3, 2, 48_000, 384_000, 8, 32)
    assert wav[36:40] == b"data"
    data_size = struct.unpack_from("<I", wav, 40)[0]
    assert data_size == binding["sample_frames"] * 8 == len(wav) - 44
    samples = struct.unpack("<" + "f" * (data_size // 4), wav[44:])
    assert _pcm_hash(samples) == binding["normalized_pcm_evidence_hash"]
    return binding, samples


def _source(
    source_id: str, samples: tuple[float, ...], *, media_byte: str,
    encoder_delay_samples: int = 0, encoder_padding_samples: int = 0,
) -> tuple[audio_edl.ReplayPcmSource, audio_edl.ReplayPcmEvidence]:
    frames = len(samples) // 2
    evidence_hash = _pcm_hash(samples)
    source = audio_edl.ReplayPcmSource(
        source_id, media_byte, evidence_hash, audio_edl.InternalPcmFormat.PCM_F32LE,
        48_000, 2, frames, frames, encoder_delay_samples, encoder_padding_samples,
    )
    evidence = audio_edl.ReplayPcmEvidence(
        source_id, evidence_hash, audio_edl.InternalPcmFormat.PCM_F32LE,
        48_000, 2, frames, samples,
    )
    return source, evidence


def _all_track_kwargs(*, rate: TemporalFrameRate) -> dict[str, object]:
    """Build valid all-track evidence from public upstream REPLAY materializers."""
    base = _compile_inputs(rate=rate)
    binding, wav_samples = _checked_in_pcm()
    compensated_binding, compensated_samples = _checked_in_pcm(1)
    words = base["word_to_frame"].word_frames
    video = base["video_edl"]
    sample_at = lambda frame: frame * 48_000 * video.fps_denominator // video.fps_numerator
    starts = [sample_at(word.start_frame - video.sequence_start_frame) for word in words]
    ends = [sample_at(word.end_exclusive_frame - video.sequence_start_frame) for word in words]
    duration = sample_at(video.duration_frames)
    assert starts[0] == 0 and 0 < ends[0] <= starts[1] < starts[2] < duration

    # The fixture's four IEEE-754 samples are not synthetically re-authored:
    # they are read from the checked-in RIFF data payload and reused verbatim.
    fixture_source, fixture_evidence = _source(
        binding["source_id"], wav_samples, media_byte=binding["source_media_hash"],
    )
    compensated_source, compensated_evidence = _source(
        compensated_binding["source_id"], compensated_samples,
        media_byte=compensated_binding["source_media_hash"],
        encoder_delay_samples=compensated_binding["encoder_delay_samples"],
        encoder_padding_samples=compensated_binding["encoder_padding_samples"],
    )
    a3_samples = (0.0,) * ((starts[2] - starts[1] + 4) * 2)
    a3_source, a3_evidence = _source("src_a3_replay", a3_samples, media_byte="sha256:" + "3" * 64)
    a4_source, a4_evidence = _source("src_a4_replay", wav_samples, media_byte="sha256:" + "4" * 64)
    narration_source, narration_evidence = base["sources"][0], base["pcm_evidence"][0]

    lineage = base["word_to_frame"]
    def cue(index: int) -> audio_edl.AudioCueWordRange:
        word = words[index]
        return audio_edl.AudioCueWordRange(
            lineage.project_id, lineage.document_id, lineage.narration_revision_id,
            word.source_id, word.source_id,
        )

    # Ordinal/order follows the public compiler ingress rule: fixed track
    # priority first, then time.  A2's two same-cue rows make a 3-sample
    # authorized overlap using the checked-in WAV source.
    intents = (
        audio_edl.AudioPlacementIntent("aint_a1", audio_edl.AudioTrackRole.A1, audio_edl.AudioEventKind.NARRATION, cue(0), narration_source, 0, ends[0], 0, 0),
        audio_edl.AudioPlacementIntent("aint_a2_left", audio_edl.AudioTrackRole.A2, audio_edl.AudioEventKind.BGM, cue(0), fixture_source, 0, 3, 0, 1),
        audio_edl.AudioPlacementIntent("aint_a2_right", audio_edl.AudioTrackRole.A2, audio_edl.AudioEventKind.BGM, cue(0), fixture_source, 0, 4, 0, 2),
        audio_edl.AudioPlacementIntent("aint_a3_left", audio_edl.AudioTrackRole.A3, audio_edl.AudioEventKind.SFX, cue(1), a3_source, 0, starts[2] - starts[1], 0, 3),
        audio_edl.AudioPlacementIntent("aint_a3_right", audio_edl.AudioTrackRole.A3, audio_edl.AudioEventKind.SFX, cue(2), a3_source, 0, 4, 0, 4),
        audio_edl.AudioPlacementIntent("aint_a4", audio_edl.AudioTrackRole.A4, audio_edl.AudioEventKind.SOURCE_SPEECH, cue(2), a4_source, 0, 4, 0, 5),
        audio_edl.AudioPlacementIntent("aint_a5_left", audio_edl.AudioTrackRole.A5, audio_edl.AudioEventKind.AMBIENCE, cue(0), compensated_source, 0, 2, 0, 6),
        audio_edl.AudioPlacementIntent("aint_a5_right", audio_edl.AudioTrackRole.A5, audio_edl.AudioEventKind.AMBIENCE, cue(1), compensated_source, 0, 2, 0, 7),
    )
    boundary_intents = (
        audio_edl.AudioBoundaryIntent("abint_a1_lead", audio_edl.AudioTrackRole.A1, 0, audio_edl.AudioBoundaryPosition.LEADING, None, "aint_a1", audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
        audio_edl.AudioBoundaryIntent("abint_a1_tail", audio_edl.AudioTrackRole.A1, 1, audio_edl.AudioBoundaryPosition.TRAILING, "aint_a1", None, audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
        audio_edl.AudioBoundaryIntent("abint_a2_lead", audio_edl.AudioTrackRole.A2, 2, audio_edl.AudioBoundaryPosition.LEADING, None, "aint_a2_left", audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
        audio_edl.AudioBoundaryIntent("abint_a2_between", audio_edl.AudioTrackRole.A2, 3, audio_edl.AudioBoundaryPosition.BETWEEN_EVENTS, "aint_a2_left", "aint_a2_right", audio_edl.AudioTransitionKind.CROSSFADE, audio_edl.AudioTransitionKind.CROSSFADE, 3),
        audio_edl.AudioBoundaryIntent("abint_a2_tail", audio_edl.AudioTrackRole.A2, 4, audio_edl.AudioBoundaryPosition.TRAILING, "aint_a2_right", None, audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
        audio_edl.AudioBoundaryIntent("abint_a3_lead", audio_edl.AudioTrackRole.A3, 5, audio_edl.AudioBoundaryPosition.LEADING, None, "aint_a3_left", audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
        audio_edl.AudioBoundaryIntent("abint_a3_between", audio_edl.AudioTrackRole.A3, 6, audio_edl.AudioBoundaryPosition.BETWEEN_EVENTS, "aint_a3_left", "aint_a3_right", audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
        audio_edl.AudioBoundaryIntent("abint_a3_tail", audio_edl.AudioTrackRole.A3, 7, audio_edl.AudioBoundaryPosition.TRAILING, "aint_a3_right", None, audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
        audio_edl.AudioBoundaryIntent("abint_a4_lead", audio_edl.AudioTrackRole.A4, 8, audio_edl.AudioBoundaryPosition.LEADING, None, "aint_a4", audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
        audio_edl.AudioBoundaryIntent("abint_a4_tail", audio_edl.AudioTrackRole.A4, 9, audio_edl.AudioBoundaryPosition.TRAILING, "aint_a4", None, audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
        audio_edl.AudioBoundaryIntent("abint_a5_lead", audio_edl.AudioTrackRole.A5, 10, audio_edl.AudioBoundaryPosition.LEADING, None, "aint_a5_left", audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
        audio_edl.AudioBoundaryIntent("abint_a5_between", audio_edl.AudioTrackRole.A5, 11, audio_edl.AudioBoundaryPosition.BETWEEN_EVENTS, "aint_a5_left", "aint_a5_right", audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
        audio_edl.AudioBoundaryIntent("abint_a5_tail", audio_edl.AudioTrackRole.A5, 12, audio_edl.AudioBoundaryPosition.TRAILING, "aint_a5_right", None, audio_edl.AudioTransitionKind.NONE, audio_edl.AudioTransitionKind.NONE, 0),
    )
    silence = audio_edl.AudioPlannedSilence("sil_a1_tail", audio_edl.AudioTrackRole.A1, 0, "aint_a1", None, ends[0], duration)
    # Sources/evidence are exact source-id order, a canonical compile input.
    source_pairs = sorted(
        ((narration_source, narration_evidence), (fixture_source, fixture_evidence), (compensated_source, compensated_evidence), (a3_source, a3_evidence), (a4_source, a4_evidence)),
        key=lambda item: item[0].source_id,
    )
    return {
        "video_edl": video, "word_to_frame": lineage, "narration_audio": base["narration_audio"],
        "intents": intents, "boundary_intents": boundary_intents,
        "sources": tuple(item[0] for item in source_pairs), "pcm_evidence": tuple(item[1] for item in source_pairs),
        "planned_silences": (silence,), "internal_pcm_format": audio_edl.InternalPcmFormat.PCM_F32LE,
    }


@pytest.mark.parametrize("rate", (TemporalFrameRate(30, 1), TemporalFrameRate(30_000, 1_001)))
def test_checked_in_replay_fixture_drives_all_track_compile_load_and_boundary_examples(rate: TemporalFrameRate) -> None:
    kwargs = _all_track_kwargs(rate=rate)
    artifact = audio_edl.compile_audio_edl(**kwargs)
    payload = audio_edl.serialize_audio_edl(artifact)
    loaded = audio_edl.load_audio_edl(payload, **kwargs)
    assert audio_edl.serialize_audio_edl(loaded) == payload
    assert artifact.duration_samples == (
        kwargs["video_edl"].duration_frames * 48_000 * rate.denominator // rate.numerator
    )
    fixture = _fixture()
    required = fixture["required_track_kinds"]
    assert {track.track.value: track.events[0].kind.value for track in artifact.tracks} == required
    assert all(track.events for track in artifact.tracks)
    policies = {(row.track.value, row.position.value): row.policy.value for row in artifact.boundary_decisions}
    assert policies[("A1", "TRAILING")] == fixture["required_boundary_examples"]["A1"]
    assert policies[("A2", "BETWEEN_EVENTS")] == fixture["required_boundary_examples"]["A2"]
    assert policies[("A3", "BETWEEN_EVENTS")] == fixture["required_boundary_examples"]["A3"]
    assert policies[("A5", "BETWEEN_EVENTS")] == fixture["required_boundary_examples"]["A5"]
    a5_between = next(
        row for row in artifact.boundary_decisions
        if row.track is audio_edl.AudioTrackRole.A5
        and row.position is audio_edl.AudioBoundaryPosition.BETWEEN_EVENTS
    )
    # The checked-in payload uses physical PCM coordinates.  For an effective
    # source position e, the sample consulted by the seam search is
    # delay + source_in + (e - source_in): here 1 + 0 + (1 - 0) == 2.
    # Frame 2 is non-zero on both channels, so the physical crossing search
    # must select the microfade branch rather than treating effective index 1
    # as an unshifted zero boundary.
    compensated = next(s for s in artifact.sources if s.source_id == "src_fixture_pcm_delay_padding")
    assert (compensated.encoder_delay_samples, compensated.encoder_padding_samples) == (1, 1)
    assert compensated.encoder_delay_samples + 0 + (1 - 0) == 2
    assert (a5_between.left_trim_samples, a5_between.right_trim_samples) == (0, 0)
    assert (a5_between.fade_in_samples, a5_between.fade_out_samples) == (240, 240)


def test_checked_in_replay_chain_rejects_a4_speech_collision() -> None:
    kwargs = _all_track_kwargs(rate=TemporalFrameRate(30, 1))
    a4 = kwargs["intents"][5]
    a1 = kwargs["intents"][0]
    kwargs["intents"] = (*kwargs["intents"][:5], dataclasses.replace(a4, cue=a1.cue), *kwargs["intents"][6:])
    with pytest.raises(audio_edl.AudioEdlContractError) as error:
        audio_edl.compile_audio_edl(**kwargs)
    assert error.value.pointer == "/tracks/3/events/0"
    assert error.value.reason is audio_edl.AudioEdlRejectionReason.SPEECH_COLLISION


def test_wav_container_header_hash_is_test_only_and_never_audio_edl_identity() -> None:
    """A RIFF header change invalidates fixture binding, not source-media identity."""
    binding, samples = _checked_in_pcm()
    path = _FIXTURE_PATH.parent.joinpath(*binding["relative_wav_path"].split("/"))
    wav = bytearray(path.read_bytes())
    wav[4] ^= 0x01  # RIFF length header only; data payload remains byte-identical.
    mutated_media_hash = "sha256:" + hashlib.sha256(wav).hexdigest()
    assert _pcm_hash(samples) == binding["normalized_pcm_evidence_hash"]
    assert mutated_media_hash != binding["wav_file_byte_hash"]
    assert mutated_media_hash != binding["normalized_pcm_evidence_hash"]

    assert binding["source_media_hash"] != binding["wav_file_byte_hash"]
    assert binding["source_media_hash"] != mutated_media_hash
    # The accepted plan consumes its canonical source-media hash, not the
    # container checksum used solely by the fixture loader.
    baseline = audio_edl.compile_audio_edl(**_all_track_kwargs(rate=TemporalFrameRate(30, 1)))
    repeat = audio_edl.compile_audio_edl(**_all_track_kwargs(rate=TemporalFrameRate(30, 1)))
    assert repeat.audio_edl_id == baseline.audio_edl_id
    assert repeat.audio_edl_hash == baseline.audio_edl_hash
