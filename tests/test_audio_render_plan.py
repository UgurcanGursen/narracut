"""Focused deterministic Phase 4B AudioRenderPlan/filter-script gates."""
from __future__ import annotations

from dataclasses import replace

import pytest

from engine.contracts.audio_edl import AudioBoundaryPolicy, AudioTransitionKind
from engine.rendering.audio_plan import AudioRenderPlanError, compile_audio_render_plan
from tests.test_render_bridge import build_phase4a_rich_replay_inputs


def _inputs():
    """Use the accepted replay EDL, with neutral legal boundary projections."""
    audio = build_phase4a_rich_replay_inputs()["audio_edl"]
    # This focused compiler fixture intentionally uses hard-cut, zero-trim edges;
    # the EDL event schedule/source identity remains the accepted replay one.
    decisions = tuple(replace(item, policy=AudioBoundaryPolicy.HARD_CUT_ZERO_CROSSING,
                              transition=AudioTransitionKind.NONE, left_trim_samples=0,
                              right_trim_samples=0, fade_in_samples=0, fade_out_samples=0,
                              overlap_samples=0, protected_silence_samples=0)
                      for item in audio.boundary_decisions)
    audio = replace(audio, boundary_decisions=decisions)
    events = [event for track in audio.tracks for event in track.events]
    entries = []
    report_entries = []
    for slot, event in enumerate(events):
        pcm_hash = "sha256:" + f"{slot:x}" * 64
        entries.append({"event_id": event.event_id, "event_hash": event.event_hash,
                        "track": event.track.value, "ordinal": event.ordinal,
                        "normalized_pcm_evidence_hash": event.normalized_pcm_evidence_hash,
                        "pcm_artifact_id": "art_" + f"{slot:x}" * 32,
                        "pcm_content_sha256": pcm_hash, "byte_length": 100 + slot,
                        "sample_rate_hz": 48000, "channel_layout": "stereo",
                        "source_in_sample": event.source_in_sample,
                        "source_out_exclusive_sample": event.source_out_exclusive_sample})
        report_entries.append({"pcm_input_slot": slot, "ffmpeg_audio_input_index": slot + 1,
                               "materialized_pcm_relative_path": f"pcm/{event.track.value}/{event.ordinal}-{event.event_id}.wav",
                               "manifest_event_id": event.event_id, "manifest_event_hash": event.event_hash,
                               "materialized_pcm_content_sha256": pcm_hash, "byte_length": 100 + slot,
                               "sample_rate_hz": 48000, "channel_layout": "stereo"})
    manifest = {"schema_version": "FULL-RENDER-PCM-MANIFEST-V1", "manifest_id": "pcmm_" + "a" * 32,
                "manifest_hash": "sha256:" + "a" * 64, "sample_rate_hz": 48000,
                "channel_layout": "stereo", "duration_samples": audio.duration_samples,
                "audio_edl_id": audio.audio_edl_id, "audio_edl_hash": audio.audio_edl_hash, "entries": entries}
    report = {"schema_version": "PCM-MATERIALIZATION-REPORT-V1", "report_id": "pcmr_" + "b" * 32,
              "report_hash": "sha256:" + "b" * 64, "pcm_manifest_id": manifest["manifest_id"],
              "pcm_manifest_hash": manifest["manifest_hash"], "entries": report_entries}
    return audio, manifest, report


def test_audio_render_plan_and_filter_script_are_byte_deterministic() -> None:
    audio, manifest, report = _inputs()
    first = compile_audio_render_plan(audio_edl=audio, pcm_manifest=manifest, pcm_materialization_report=report)
    assert first == compile_audio_render_plan(audio_edl=audio, pcm_manifest=manifest, pcm_materialization_report=report)
    plan, artifact, script = first
    assert plan["schema_version"] == "AUDIO-RENDER-PLAN-V1"
    assert plan["mix"]["clip_event_ids"] == [clip["event_id"] for clip in plan["clips"]]
    assert artifact["audio_render_plan_hash"] == plan["audio_render_plan_hash"]
    assert b"acrossfade" not in script and b"asplit" not in script
    assert b"[p0_pre]anull[p0_left]" in script
    assert script.endswith(b"[aout]\n")


def test_audio_render_plan_rejects_report_slot_or_edl_binding_drift() -> None:
    audio, manifest, report = _inputs()
    report["entries"][0]["ffmpeg_audio_input_index"] = 99
    with pytest.raises(AudioRenderPlanError) as rejected:
        compile_audio_render_plan(audio_edl=audio, pcm_manifest=manifest, pcm_materialization_report=report)
    assert rejected.value.code == "PCM_INPUT_INVALID"
