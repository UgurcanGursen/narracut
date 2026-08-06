from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from engine.benchmark import (
    canonical_benchmark_json, canonical_benchmark_reference_profile_json,
    compare_benchmark_to_reference, compare_benchmarks, compile_benchmark,
    load_benchmark_reference_profile,
)
from engine.contracts.audio_edl import compile_audio_edl
from engine.contracts.edl import CueWordRange, SourceDescriptor, SourceFitMode, SourcePlaybackMode
from engine.editorial_integration import (
    EditorialIntegrationCompiler, compile_phase3_video_edl_from_execution,
    editorial_integration_policy_from_snapshot,
)
from tests.test_audio_edl import _compile_inputs
from tests.test_edl import _deps
from tests.test_phase12_editorial_integration import _inputs


def _report():
    snapshot, request, sequence, catalog, selection, capabilities, audio, direction = _inputs()
    plan = EditorialIntegrationCompiler().compile(
        project_id="prj_phase12", assembly_request=request,
        policy=editorial_integration_policy_from_snapshot(snapshot), sequence_plans=(sequence,), catalog=catalog,
        selections=(selection,), capabilities=capabilities, audio_plan=audio,
        chapter_audio_direction_pairs=(direction,), pacing_roles=("mechanism",), visualizations=(None,),
    )
    groups, events, frames, preview, report = _deps()
    first, last = frames.word_frames[0], frames.word_frames[-1]
    cue = CueWordRange(frames.project_id, frames.document_id, frames.narration_revision_id, first.source_id, last.source_id)
    selected = plan.data()["sequences"][0]["approved_asset_selections"][0]
    source = SourceDescriptor(str(selected["asset_id"]), 30, 1, 0, 30, SourcePlaybackMode.FIT, SourceFitMode.COVER, 0, 0, 1_000_000, 1_000_000, 1_000_000, first.source_id, last.source_id)
    video = compile_phase3_video_edl_from_execution(
        execution=plan.data()["sequences"][0], cue=cue, source=source, caption_groups=groups,
        emphasis_events=events, word_to_frame=frames, caption_preview=preview, v5_v6_collision_report=report,
        fps_numerator=30, fps_denominator=1,
    )
    kwargs = _compile_inputs()
    kwargs["video_edl"] = video
    return compile_benchmark(snapshot=snapshot, plan=plan, videos=(video,), audios=(compile_audio_edl(**kwargs),))


def _reference():
    root = Path(__file__).resolve().parents[1]
    return load_benchmark_reference_profile((root / "domain-packs/business-tech/benchmarks/composition_profile_v1.json").read_bytes())


def test_phase16_report_is_canonical_and_compares_to_same_domain_reference():
    report, reference = _report(), _reference()
    assert report.metrics["sequence_count"] == 1
    assert report.metrics["stock_ratio"] == "UNAVAILABLE"
    assert canonical_benchmark_json(report) == canonical_benchmark_json(report)
    assert canonical_benchmark_reference_profile_json(reference) == canonical_benchmark_reference_profile_json(reference)
    delta = compare_benchmarks(candidate=report, prior=report)
    assert not any(delta.numeric_deltas.values())
    comparison = compare_benchmark_to_reference(report=report, reference=reference)
    assert comparison.metric_assessments["stock_ratio"] == "UNAVAILABLE"
    assert comparison.metric_assessments["sequence_count"] == "IN_RANGE"


def test_phase16_reference_rejects_cross_domain_and_non_contract_fields():
    report, reference = _report(), _reference()
    foreign = load_benchmark_reference_profile(
        (Path(__file__).resolve().parents[1] / "domain-packs/business-tech/benchmarks/composition_profile_v1.json")
        .read_bytes().replace(b'"business-tech"', b'"science-explainer"')
    )
    with pytest.raises(ValueError, match="BENCHMARK_DOMAIN_MISMATCH"):
        compare_benchmark_to_reference(report=report, reference=foreign)
    with pytest.raises(ValueError, match="BENCHMARK_REFERENCE_INVALID"):
        compare_benchmark_to_reference(report=report, reference=replace(reference, domain_id="science-explainer"))
    with pytest.raises(ValueError, match="BENCHMARK_REFERENCE_INVALID"):
        load_benchmark_reference_profile(b'{"schema_version":"PHASE16-BENCHMARK-REFERENCE-V1","domain_id":"business-tech","domain_pack_version":"0.1.0","profile_key":"x","metric_ranges":{},"brand":"forbidden"}')
