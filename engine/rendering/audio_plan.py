"""Closed Phase 4B projection of accepted Audio EDL data into FFmpeg audio.

The module deliberately has no filesystem or process access.  PCM resolution owns
paths and materialization; this compiler only proves their bindings and emits the
single deterministic filter-script artifact consumed by the full-render runner.
"""
from __future__ import annotations

import hashlib
from typing import Any

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.audio_edl import (
    AudioBoundaryPolicy, AudioBoundaryPosition, AudioEdlArtifact,
    AudioTransitionKind,
)


AUDIO_RENDER_PLAN_V1 = "AUDIO-RENDER-PLAN-V1"
AUDIO_FILTER_SCRIPT_V1 = "AUDIO-FILTER-SCRIPT-V1"


class AudioRenderPlanError(ValueError):
    """All closed plan/filter ingress failures use the Phase 4B PCM oracle."""

    code = "PCM_INPUT_INVALID"


def _reject() -> None:
    raise AudioRenderPlanError(AudioRenderPlanError.code)


def _canonical(value: Any) -> bytes:
    return encode_canonical_json_bytes(value)


def _sha(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _identity(prefix: str, value: dict[str, Any], *excluded: str) -> tuple[str, str]:
    digest = _sha(_canonical({key: item for key, item in value.items() if key not in excluded}))
    return prefix + digest[7:39], digest


def _millibels(value: int) -> str:
    if type(value) is not int:
        _reject()
    sign = "-" if value < 0 else ""
    whole, fraction = divmod(abs(value), 1000)
    return f"{sign}{whole}" + (f".{fraction:03d}".rstrip("0") if fraction else "") + "dB"


def _rows(audio_edl: AudioEdlArtifact) -> list[Any]:
    if type(audio_edl) is not AudioEdlArtifact or audio_edl.sample_rate_hz != 48000 or audio_edl.channel_count != 2:
        _reject()
    result: list[Any] = []
    for expected_track, track in zip(("A1", "A2", "A3", "A4", "A5"), audio_edl.tracks, strict=True):
        if track.track.value != expected_track:
            _reject()
        result.extend(track.events)
    if not result or [event.ordinal for event in result] != list(range(len(result))):
        _reject()
    return result


def _boundaries(audio_edl: AudioEdlArtifact, clips: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    edge_seen: set[tuple[str, str | None, str | None]] = set()
    for decision in audio_edl.boundary_decisions:
        key = (decision.track.value, decision.left_event_id, decision.right_event_id)
        if key in edge_seen or decision.position.value not in {"LEADING", "BETWEEN_EVENTS", "TRAILING"}:
            _reject()
        edge_seen.add(key)
        left = clips.get(decision.left_event_id or "")
        right = clips.get(decision.right_event_id or "")
        if (decision.position is AudioBoundaryPosition.LEADING) != (left is None and right is not None): _reject()
        if (decision.position is AudioBoundaryPosition.TRAILING) != (left is not None and right is None): _reject()
        if (decision.position is AudioBoundaryPosition.BETWEEN_EVENTS) != (left is not None and right is not None): _reject()
        values = (decision.left_trim_samples, decision.right_trim_samples, decision.fade_in_samples,
                  decision.fade_out_samples, decision.overlap_samples, decision.protected_silence_samples)
        if any(type(item) is not int or item < 0 for item in values): _reject()
        if left: left["trailing_trim_samples"] += decision.left_trim_samples
        if right: right["leading_trim_samples"] += decision.right_trim_samples
        policy = decision.policy
        if policy in {AudioBoundaryPolicy.PRESERVE_SILENCE, AudioBoundaryPolicy.HARD_CUT_ZERO_CROSSING}:
            if decision.transition is not AudioTransitionKind.NONE or any(values[:5]) or (policy is AudioBoundaryPolicy.PRESERVE_SILENCE and decision.protected_silence_samples <= 0) or (policy is AudioBoundaryPolicy.HARD_CUT_ZERO_CROSSING and decision.protected_silence_samples != 0): _reject()
        elif policy is AudioBoundaryPolicy.OVERLAP_CROSSFADE:
            if decision.transition is not AudioTransitionKind.CROSSFADE or decision.overlap_samples < 2 or decision.fade_in_samples != decision.overlap_samples or decision.fade_out_samples != decision.overlap_samples or decision.left_trim_samples or decision.right_trim_samples or decision.protected_silence_samples or not left or not right or left["scheduled_end_exclusive_sample"] - right["scheduled_start_sample"] != decision.overlap_samples: _reject()
        elif policy in {AudioBoundaryPolicy.ZERO_CROSSING_MICROFADE, AudioBoundaryPolicy.LONG_EDITORIAL_FADE}:
            if decision.transition is not AudioTransitionKind.NONE or decision.overlap_samples or decision.protected_silence_samples: _reject()
        else: _reject()
        result.append({"track": decision.track.value, "position": decision.position.value,
                       "left_event_id": decision.left_event_id, "right_event_id": decision.right_event_id,
                       "policy": policy.value, "transition": decision.transition.value,
                       "left_trim_samples": decision.left_trim_samples, "right_trim_samples": decision.right_trim_samples,
                       "fade_in_samples": decision.fade_in_samples, "fade_out_samples": decision.fade_out_samples,
                       "overlap_samples": decision.overlap_samples, "protected_silence_samples": decision.protected_silence_samples})
    return result


def _fade_expression(*, clip: dict[str, Any], decision: dict[str, Any] | None, side: str) -> str:
    if decision is None or decision["policy"] in {"PRESERVE_SILENCE", "HARD_CUT_ZERO_CROSSING"}:
        return "anull"
    amount = decision["fade_in_samples"] if side == "in" else decision["fade_out_samples"]
    if decision["policy"] == "OVERLAP_CROSSFADE": amount = decision["overlap_samples"]
    if amount == 0: return "anull"
    start = clip["effective_start_sample"] if side == "in" else clip["effective_end_exclusive_sample"] - amount
    if amount <= 0 or amount > clip["effective_end_exclusive_sample"] - clip["effective_start_sample"]: _reject()
    return f"afade=t={'in' if side == 'in' else 'out'}:ss={start}:ns={amount}:curve=tri"


def compile_audio_render_plan(*, audio_edl: AudioEdlArtifact, pcm_manifest: dict[str, Any], pcm_materialization_report: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    """Compile immutable plan and its sole executable FFmpeg filter-script.

    ``pcm_manifest`` and ``pcm_materialization_report`` are resolver outputs;
    their closed fields are rechecked here instead of trusting caller ordering.
    """
    events = _rows(audio_edl)
    if type(pcm_manifest) is not dict or type(pcm_materialization_report) is not dict or pcm_manifest.get("schema_version") != "FULL-RENDER-PCM-MANIFEST-V1" or pcm_materialization_report.get("schema_version") != "PCM-MATERIALIZATION-REPORT-V1": _reject()
    if (pcm_manifest.get("audio_edl_id"), pcm_manifest.get("audio_edl_hash")) != (audio_edl.audio_edl_id, audio_edl.audio_edl_hash): _reject()
    if pcm_manifest.get("sample_rate_hz") != 48000 or pcm_manifest.get("channel_layout") != "stereo" or pcm_manifest.get("duration_samples") != audio_edl.duration_samples: _reject()
    if (pcm_materialization_report.get("pcm_manifest_id"), pcm_materialization_report.get("pcm_manifest_hash")) != (pcm_manifest.get("manifest_id"), pcm_manifest.get("manifest_hash")): _reject()
    manifest_entries = pcm_manifest.get("entries"); report_entries = pcm_materialization_report.get("entries")
    if type(manifest_entries) is not list or type(report_entries) is not list or not (len(events) == len(manifest_entries) == len(report_entries)): _reject()
    clips: list[dict[str, Any]] = []
    by_event: dict[str, dict[str, Any]] = {}
    for slot, (event, manifest, report) in enumerate(zip(events, manifest_entries, report_entries, strict=True)):
        if type(manifest) is not dict or type(report) is not dict: _reject()
        binding = (event.event_id, event.event_hash, event.track.value, event.ordinal, event.normalized_pcm_evidence_hash, event.source_in_sample, event.source_out_exclusive_sample)
        if (manifest.get("event_id"), manifest.get("event_hash"), manifest.get("track"), manifest.get("ordinal"), manifest.get("normalized_pcm_evidence_hash"), manifest.get("source_in_sample"), manifest.get("source_out_exclusive_sample")) != binding: _reject()
        if (report.get("pcm_input_slot"), report.get("ffmpeg_audio_input_index"), report.get("manifest_event_id"), report.get("manifest_event_hash")) != (slot, slot + 1, event.event_id, event.event_hash): _reject()
        path = report.get("materialized_pcm_relative_path")
        if type(path) is not str or not path.startswith(f"pcm/{event.track.value}/{event.ordinal}-") or not path.endswith(".wav"): _reject()
        pcm_hash = manifest.get("pcm_content_sha256")
        if type(pcm_hash) is not str or report.get("materialized_pcm_content_sha256") != pcm_hash or report.get("sample_rate_hz") != 48000 or report.get("channel_layout") != "stereo": _reject()
        clip = {"event_id": event.event_id, "event_hash": event.event_hash, "track": event.track.value, "ordinal": event.ordinal,
                "pcm_input_slot": slot, "ffmpeg_audio_input_index": slot + 1, "materialized_pcm_relative_path": path,
                "materialized_pcm_content_sha256": pcm_hash, "source_in_sample": event.source_in_sample,
                "source_out_exclusive_sample": event.source_out_exclusive_sample, "scheduled_start_sample": event.start_sample,
                "scheduled_end_exclusive_sample": event.end_exclusive_sample, "gain_millibels": event.gain_millibels,
                "leading_trim_samples": 0, "trailing_trim_samples": 0, "fade_in_samples": 0, "fade_out_samples": 0, "overlap_samples": 0}
        clips.append(clip); by_event[event.event_id] = clip
    boundaries = _boundaries(audio_edl, by_event)
    incoming: dict[str, dict[str, Any]] = {}; outgoing: dict[str, dict[str, Any]] = {}
    for boundary in boundaries:
        if boundary["right_event_id"]: incoming[boundary["right_event_id"]] = boundary
        if boundary["left_event_id"]: outgoing[boundary["left_event_id"]] = boundary
    lines: list[str] = []
    for clip in clips:
        clip["effective_start_sample"] = clip["scheduled_start_sample"] + clip["leading_trim_samples"]
        clip["effective_end_exclusive_sample"] = clip["scheduled_end_exclusive_sample"] - clip["trailing_trim_samples"]
        source_start = clip["source_in_sample"] + clip["leading_trim_samples"]
        source_end = clip["source_out_exclusive_sample"] - clip["trailing_trim_samples"]
        if source_start >= source_end or clip["effective_start_sample"] >= clip["effective_end_exclusive_sample"]: _reject()
        slot = clip["pcm_input_slot"]
        lines.append(f"[{clip['ffmpeg_audio_input_index']}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=start_sample={source_start}:end_sample={source_end},asetpts=PTS-STARTPTS,adelay={clip['effective_start_sample']}S:all=1,volume={_millibels(clip['gain_millibels'])}[p{slot}_pre]")
        left = _fade_expression(clip=clip, decision=incoming.get(clip["event_id"]), side="in")
        right = _fade_expression(clip=clip, decision=outgoing.get(clip["event_id"]), side="out")
        lines += [f"[p{slot}_pre]{left}[p{slot}_left]", f"[p{slot}_left]{right}[p{slot}_right]", f"[p{slot}_right]anull[p{slot}_post]", f"[p{slot}_post]anull[p{slot}_mix]"]
    lines += ["".join(f"[p{clip['pcm_input_slot']}_mix]" for clip in clips) + f"amix=inputs={len(clips)}:duration=longest:dropout_transition=0[mixed]", f"[mixed]aformat=sample_rates=48000:channel_layouts=stereo,atrim=end_sample={audio_edl.duration_samples}[aout]"]
    script = ("\n".join(lines) + "\n").encode("utf-8")
    if b"\x00" in script: _reject()
    mix = {"duration_samples": audio_edl.duration_samples, "sample_rate_hz": 48000, "channel_layout": "stereo", "track_order": ["A1", "A2", "A3", "A4", "A5"], "clip_event_ids": [clip["event_id"] for clip in clips]}
    for clip in clips:
        clip.pop("effective_start_sample"); clip.pop("effective_end_exclusive_sample")
    plan = {"schema_version": AUDIO_RENDER_PLAN_V1, "audio_render_plan_id": "", "audio_render_plan_hash": "", "audio_edl_id": audio_edl.audio_edl_id, "audio_edl_hash": audio_edl.audio_edl_hash, "pcm_manifest_id": pcm_manifest["manifest_id"], "pcm_manifest_hash": pcm_manifest["manifest_hash"], "pcm_materialization_report_id": pcm_materialization_report["report_id"], "pcm_materialization_report_hash": pcm_materialization_report["report_hash"], "sample_rate_hz": 48000, "channel_layout": "stereo", "duration_samples": audio_edl.duration_samples, "clips": clips, "boundaries": boundaries, "mix": mix}
    plan_id, plan_hash = _identity("arp_", plan, "audio_render_plan_id", "audio_render_plan_hash")
    plan["audio_render_plan_id"], plan["audio_render_plan_hash"] = plan_id, plan_hash
    artifact = {"schema_version": AUDIO_FILTER_SCRIPT_V1, "audio_filter_script_id": "", "audio_filter_script_hash": "", "audio_render_plan_id": plan_id, "audio_render_plan_hash": plan_hash, "filter_script_utf8_sha256": _sha(script), "byte_length": len(script)}
    artifact_id, artifact_hash = _identity("afs_", artifact, "audio_filter_script_id", "audio_filter_script_hash")
    artifact["audio_filter_script_id"], artifact["audio_filter_script_hash"] = artifact_id, artifact_hash
    return plan, artifact, script
