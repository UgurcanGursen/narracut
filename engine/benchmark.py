"""Phase 16 deterministic editorial-composition benchmark reducer.

The reducer deliberately measures only canonical planning/EDL facts.  It does
not download, inspect or imitate third-party videos.  Reference profiles hold
domain-local editorial ranges only; they cannot contain source media, brands or
transcripts.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.audio_edl import AudioEdlArtifact, serialize_audio_edl
from engine.contracts.domain import policy_snapshot_hash
from engine.contracts.edl import EdlPayloadKind, TimelineTrack, VideoEdlArtifact, serialize_video_edl
from engine.contracts.models import DomainPolicySnapshot
from engine.editorial_integration import ExecutableEditorialPlanV1, canonical_executable_editorial_plan_json

BENCHMARK_V1 = "PHASE16-BENCHMARK-V1"
BENCHMARK_DELTA_V1 = "PHASE16-BENCHMARK-DELTA-V1"
BENCHMARK_REFERENCE_V1 = "PHASE16-BENCHMARK-REFERENCE-V1"
BENCHMARK_REFERENCE_COMPARISON_V1 = "PHASE16-BENCHMARK-REFERENCE-COMPARISON-V1"
_REFERENCE_FIELDS = ("schema_version", "domain_id", "domain_pack_version", "profile_key", "metric_ranges")


def _hash(value: object) -> str:
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _fail(code: str) -> None:
    raise ValueError(code)


@dataclass(frozen=True)
class BenchmarkReportV1:
    report_id: str
    report_hash: str
    project_id: str
    domain_id: str
    domain_pack_version: str
    policy_snapshot_id: str
    policy_snapshot_hash: str
    executable_plan_id: str
    executable_plan_hash: str
    metrics: dict[str, Any]

    def data(self) -> dict[str, Any]:
        return {"schema_version": BENCHMARK_V1, **self.__dict__}


@dataclass(frozen=True)
class BenchmarkDeltaV1:
    candidate_report_id: str
    prior_report_id: str
    domain_id: str
    domain_pack_version: str
    numeric_deltas: dict[str, int]

    def data(self) -> dict[str, Any]:
        return {"schema_version": BENCHMARK_DELTA_V1, **self.__dict__}


@dataclass(frozen=True)
class BenchmarkReferenceProfileV1:
    profile_id: str
    profile_hash: str
    domain_id: str
    domain_pack_version: str
    profile_key: str
    metric_ranges: dict[str, dict[str, int]]

    def data(self) -> dict[str, Any]:
        return {"schema_version": BENCHMARK_REFERENCE_V1, **self.__dict__}


@dataclass(frozen=True)
class BenchmarkReferenceComparisonV1:
    report_id: str
    reference_profile_id: str
    reference_profile_hash: str
    domain_id: str
    domain_pack_version: str
    metric_assessments: dict[str, str]

    def data(self) -> dict[str, Any]:
        return {"schema_version": BENCHMARK_REFERENCE_COMPARISON_V1, **self.__dict__}


def canonical_benchmark_json(value: BenchmarkReportV1) -> bytes:
    if not _valid_report(value):
        _fail("BENCHMARK_REPORT_INVALID")
    return encode_canonical_json_bytes(value.data())


def _valid_report(value: object) -> bool:
    if type(value) is not BenchmarkReportV1 or type(value.metrics) is not dict:
        return False
    text_fields = (
        "project_id", "domain_id", "domain_pack_version", "policy_snapshot_id",
        "policy_snapshot_hash", "executable_plan_id", "executable_plan_hash",
    )
    if not all(type(getattr(value, field)) is str and getattr(value, field) for field in text_fields):
        return False
    body = {field: getattr(value, field) for field in (*text_fields, "metrics")}
    expected_hash = _hash(body)
    return (value.report_hash, value.report_id) == (expected_hash, "bmr_" + expected_hash[7:27])


def load_benchmark_reference_profile(source: bytes) -> BenchmarkReferenceProfileV1:
    """Load a strict, brand-free domain benchmark profile from checked-in JSON."""
    if type(source) is not bytes:
        _fail("BENCHMARK_REFERENCE_INVALID")
    try:
        raw = json.loads(source.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("BENCHMARK_REFERENCE_INVALID") from exc
    if type(raw) is not dict or tuple(raw) != _REFERENCE_FIELDS or raw.get("schema_version") != BENCHMARK_REFERENCE_V1:
        _fail("BENCHMARK_REFERENCE_INVALID")
    domain_id, version, profile_key, ranges = (raw[key] for key in _REFERENCE_FIELDS[1:])
    if not all(type(value) is str and value for value in (domain_id, version, profile_key)) or type(ranges) is not dict or not ranges:
        _fail("BENCHMARK_REFERENCE_INVALID")
    normalized: dict[str, dict[str, int]] = {}
    for metric, bounds in ranges.items():
        if type(metric) is not str or not metric or type(bounds) is not dict or tuple(bounds) != ("min", "max"):
            _fail("BENCHMARK_REFERENCE_INVALID")
        low, high = bounds["min"], bounds["max"]
        if type(low) is not int or type(high) is not int or low < 0 or high < low:
            _fail("BENCHMARK_REFERENCE_INVALID")
        normalized[metric] = {"min": low, "max": high}
    body = {key: raw[key] for key in _REFERENCE_FIELDS[1:]}
    profile_hash = _hash(body)
    return BenchmarkReferenceProfileV1(
        "bref_" + profile_hash[7:27], profile_hash, domain_id, version, profile_key, dict(sorted(normalized.items()))
    )


def canonical_benchmark_reference_profile_json(value: BenchmarkReferenceProfileV1) -> bytes:
    if not _valid_reference(value):
        _fail("BENCHMARK_REFERENCE_INVALID")
    return encode_canonical_json_bytes(value.data())


def _valid_reference(value: object) -> bool:
    if type(value) is not BenchmarkReferenceProfileV1:
        return False
    if not all(type(getattr(value, field)) is str and getattr(value, field) for field in ("domain_id", "domain_pack_version", "profile_key")):
        return False
    body = {
        "domain_id": value.domain_id, "domain_pack_version": value.domain_pack_version,
        "profile_key": value.profile_key, "metric_ranges": value.metric_ranges,
    }
    expected_hash = _hash(body)
    return (value.profile_hash, value.profile_id) == (expected_hash, "bref_" + expected_hash[7:27])


def compare_benchmarks(*, candidate: BenchmarkReportV1, prior: BenchmarkReportV1) -> BenchmarkDeltaV1:
    if not _valid_report(candidate) or not _valid_report(prior):
        _fail("BENCHMARK_DOMAIN_MISMATCH")
    if (candidate.domain_id, candidate.domain_pack_version, candidate.policy_snapshot_id) != (
        prior.domain_id, prior.domain_pack_version, prior.policy_snapshot_id
    ):
        _fail("BENCHMARK_DOMAIN_MISMATCH")
    keys = ("sequence_count", "duration_ms", "video_edit_event_count", "video_edit_events_per_minute", "audio_event_count")
    if any(type(candidate.metrics.get(key)) is not int or type(prior.metrics.get(key)) is not int for key in keys):
        _fail("BENCHMARK_INPUT_UNAVAILABLE")
    return BenchmarkDeltaV1(
        candidate.report_id,
        prior.report_id,
        candidate.domain_id,
        candidate.domain_pack_version,
        {key: int(candidate.metrics[key]) - int(prior.metrics[key]) for key in keys},
    )


def compare_benchmark_to_reference(*, report: BenchmarkReportV1, reference: BenchmarkReferenceProfileV1) -> BenchmarkReferenceComparisonV1:
    """Classify measured values; this intentionally never declares a quality winner."""
    if not _valid_report(report) or not _valid_reference(reference):
        _fail("BENCHMARK_REFERENCE_INVALID")
    if (report.domain_id, report.domain_pack_version) != (reference.domain_id, reference.domain_pack_version):
        _fail("BENCHMARK_DOMAIN_MISMATCH")
    assessments: dict[str, str] = {}
    for metric, bounds in reference.metric_ranges.items():
        value = report.metrics.get(metric)
        if type(value) is not int:
            assessments[metric] = "UNAVAILABLE"
        elif value < bounds["min"]:
            assessments[metric] = "BELOW_RANGE"
        elif value > bounds["max"]:
            assessments[metric] = "ABOVE_RANGE"
        else:
            assessments[metric] = "IN_RANGE"
    return BenchmarkReferenceComparisonV1(
        report.report_id, reference.profile_id, reference.profile_hash, report.domain_id,
        report.domain_pack_version, dict(sorted(assessments.items()))
    )


def compile_benchmark(
    *, snapshot: DomainPolicySnapshot, plan: ExecutableEditorialPlanV1,
    videos: tuple[VideoEdlArtifact, ...], audios: tuple[AudioEdlArtifact, ...]
) -> BenchmarkReportV1:
    if type(snapshot) is not DomainPolicySnapshot or not snapshot.immutable or snapshot.canonical_hash != policy_snapshot_hash({name: getattr(snapshot, name) for name in snapshot.__dataclass_fields__}):
        _fail("BENCHMARK_DOMAIN_MISMATCH")
    if type(plan) is not ExecutableEditorialPlanV1 or type(videos) is not tuple or type(audios) is not tuple:
        _fail("BENCHMARK_INPUT_UNAVAILABLE")
    try:
        canonical_executable_editorial_plan_json(plan)
        for video in videos:
            serialize_video_edl(video)
        for audio in audios:
            serialize_audio_edl(audio)
    except Exception as exc:
        raise ValueError("BENCHMARK_INPUT_UNAVAILABLE") from exc
    plan_data = plan.data()
    rows = plan_data["sequences"]
    if len(rows) != len(videos) or len(rows) != len(audios) or any(
        video.sequence_id != row["executable_sequence_id"] or audio.sequence_id != row["executable_sequence_id"]
        for row, video, audio in zip(rows, videos, audios, strict=True)
    ):
        _fail("BENCHMARK_INPUT_UNAVAILABLE")

    video_events = [event for video in videos for track in video.tracks for event in track.events]
    audio_events = [event for audio in audios for track in audio.tracks for event in track.events]
    duration_ms = sum(video.duration_frames * 1000 * video.fps_denominator // video.fps_numerator for video in videos)
    base_shots = [
        event for event in video_events
        if event.track is TimelineTrack.V1 and event.payload.kind is EdlPayloadKind.CALLER_SOURCE
    ]
    templates: dict[str, int] = {}
    asset_briefs: dict[str, int] = {}
    modes: dict[str, int] = {}
    track_counts: dict[str, int] = {}
    boundary_counts: dict[str, int] = {}
    for row in rows:
        template_key = str(row["template_capability_id_hash"][0])
        templates[template_key] = templates.get(template_key, 0) + 1
        mode = str(row["execution_mode"])
        modes[mode] = modes.get(mode, 0) + 1
        for selection in row["approved_asset_selections"]:
            brief = str(selection["planner_asset_brief_id_hash"][0])
            asset_briefs[brief] = asset_briefs.get(brief, 0) + 1
    for audio in audios:
        for track in audio.tracks:
            track_counts[track.track.value] = track_counts.get(track.track.value, 0) + len(track.events)
        for decision in audio.boundary_decisions:
            boundary_counts[decision.policy.value] = boundary_counts.get(decision.policy.value, 0) + 1
    base_shot_duration_ms = sum(
        (event.end_exclusive_frame - event.start_frame) * 1000 * video.fps_denominator // video.fps_numerator
        for video in videos for track in video.tracks for event in track.events
        if event.track is TimelineTrack.V1 and event.payload.kind is EdlPayloadKind.CALLER_SOURCE
    )
    metrics = {
        "chapter_structure": "UNAVAILABLE",
        "sequence_count": len(rows),
        "duration_ms": duration_ms,
        "base_shot_count": len(base_shots),
        "base_shot_density_per_minute": 0 if not duration_ms else len(base_shots) * 60000 // duration_ms,
        "average_static_duration_ms": 0 if not base_shots else base_shot_duration_ms // len(base_shots),
        "video_edit_event_count": len(video_events),
        "video_edit_events_per_minute": 0 if not duration_ms else len(video_events) * 60000 // duration_ms,
        "source_treatment_distribution": "UNAVAILABLE",
        "template_distribution": dict(sorted(templates.items())),
        "asset_brief_distribution": dict(sorted(asset_briefs.items())),
        "execution_mode_distribution": dict(sorted(modes.items())),
        "audio_event_count": len(audio_events),
        "audio_transition_count": sum(boundary_counts.values()),
        "audio_track_distribution": dict(sorted(track_counts.items())),
        "audio_boundary_distribution": dict(sorted(boundary_counts.items())),
        "source_audio_usage": "UNAVAILABLE",
        "source_density": "UNAVAILABLE",
        "stock_ratio": "UNAVAILABLE",
        "chart_ratio": "UNAVAILABLE",
        "quote_card_ratio": "UNAVAILABLE",
        "kinetic_text_density": "UNAVAILABLE",
    }
    body = {
        "project_id": plan_data["project_id"], "domain_id": snapshot.domain_id,
        "domain_pack_version": snapshot.domain_pack_version, "policy_snapshot_id": snapshot.snapshot_id,
        "policy_snapshot_hash": snapshot.canonical_hash,
        "executable_plan_id": plan_data["executable_editorial_plan_id"],
        "executable_plan_hash": plan_data["executable_editorial_plan_hash"], "metrics": metrics,
    }
    report_hash = _hash(body)
    return BenchmarkReportV1("bmr_" + report_hash[7:27], report_hash, **body)
