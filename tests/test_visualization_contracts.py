from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from engine.acquisition import (
    AccessStatus, AcquisitionAdapterId, AccessibleHtmlAdapter, DOMRegion,
    ReplaySourcePackage, SourceAdapterRegistry, SourceType,
)
from engine.contracts import DomainPackRegistry, DomainPolicyResolver, SchemaCatalog
from engine.contracts.word_to_frame import TemporalFrameRate, compile_word_to_frame
from engine.rendering.bridge import build_render_props, renderer_version
from engine.rendering.fixture_assets import FixtureAssetResolver
from engine.visualization import (
    ExactDecimalV1, PeriodV1, SourceCaptureEvidenceBindingV1,
    VisualizationContractError, VisualizationEdlBindingV1, VisualizationFrameBindingV1,
    VisualizationItemV1, VisualizationKind, VisualizationStageKind,
    VisualizationStageV1, VisualizationUnitKind, VisualizationPolicyV1,
    compile_visualization_artifact, compile_visualization_render_plan,
    render_replay_visualization, serialize_rendered_visualization_metadata,
    validate_visualization_render_receipt, visualization_policy_from_snapshot,
    build_visualization_replay_props,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE4_FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "phase4a"


def _capture(*, value="10", period="Q1", path="/report/p[1]"):
    region = DOMRegion(path, f"{period} revenue was {value} USD.", 10_000, 10_000, 500_000, 300_000)
    package = ReplaySourcePackage(f"src_report_{period.lower()}", SourceType.OFFICIAL_REPORT, AcquisitionAdapterId.ACCESSIBLE_HTML, f"https://example.com/report/{period}", AccessStatus.ACCESSIBLE, "Example report", "2026-01-01", region.text, region.text, None, (region,))
    return SourceAdapterRegistry((AccessibleHtmlAdapter(),)).acquire(package)


def _policy():
    return VisualizationPolicyV1(
        tuple(VisualizationKind), ("line", "bar", "area", "stacked", "comparison", "waterfall", "timeline"), (),
        ("line",), ("units",), ("index",), ("depends_on", "compares_with"), "editorial-v1", "dps_test", "sha256:" + "a" * 64,
    )


def _upstream():
    from tests.test_render_bridge import build_phase4a_rich_replay_inputs
    from tests.test_word_to_frame import _fixture_values
    replay = build_phase4a_rich_replay_inputs()
    props = build_render_props(video_edl=replay["video_edl"], audio_edl=replay["audio_edl"], fixture_assets=FixtureAssetResolver.load(PHASE4_FIXTURE_ROOT), renderer_version_value=renderer_version((REPO_ROOT / "renderer-remotion" / "package-lock.json").read_bytes()))
    result, groups, emphasis = _fixture_values()
    word = compile_word_to_frame(alignment_result=result, caption_groups=groups, emphasis_events=emphasis, frame_rate=TemporalFrameRate(30, 1))
    event = next(event for track in replay["video_edl"].tracks if track.track.value == "V4" for event in track.events)
    return props, replay["video_edl"], word, event.event_id


def _frame(word, video_edl, *, start_word_index: int, end_word_index: int) -> VisualizationFrameBindingV1:
    start, end = word.word_frames[start_word_index], word.word_frames[end_word_index]
    return VisualizationFrameBindingV1(word.word_to_frame_id, word.word_to_frame_hash, video_edl.sequence_start_frame, start.start_word_id, end.end_word_id, start.start_frame, end.end_exclusive_frame, start.start_frame - video_edl.sequence_start_frame, end.end_exclusive_frame - video_edl.sequence_start_frame)


def _binding(capture, *, numeric="10", unit="USD", period="Q1"):
    text = f"{period} revenue was {numeric} {unit}."
    return SourceCaptureEvidenceBindingV1(capture.source_capture_plan_id, capture.source_capture_plan_hash, capture.source_package_hash, f"/report/p[{period.removeprefix('Q')} ]".replace(" ", ""), text, numeric, unit, period)


def _point(capture, *, ordinal=1, value="10", period="Q1"):
    return {"point_id": f"point_{ordinal}", "value": ExactDecimalV1.from_lexeme(value), "period": PeriodV1(f"q{ordinal}", ordinal, period), "evidence": (_binding(capture, numeric=value, period=period),)}


def _chart(capture, kind="line"):
    return VisualizationItemV1("chart_main", VisualizationKind.CHART, "Revenue", {"chart_kind": kind, "series": ({"series_id": "series_revenue", "label": "Revenue", "unit": VisualizationUnitKind.CURRENCY, "currency": "USD", "datapoints": (_point(capture),)},)})


def test_exact_decimal_normalizes_without_float() -> None:
    assert ExactDecimalV1.from_lexeme("1.20") == ExactDecimalV1(12, 1)
    assert ExactDecimalV1.from_lexeme("-0.50").text() == "-0.5"
    with pytest.raises(VisualizationContractError, match="NUMERIC_LEXEME_INVALID"):
        ExactDecimalV1.from_lexeme("1e3")
    with pytest.raises(VisualizationContractError, match="EXACT_DECIMAL_INVALID"):
        ExactDecimalV1(True, 0).validate()


def test_chart_metric_evidence_and_replay_receipt() -> None:
    capture = _capture(); chart = _chart(capture)
    metric = VisualizationItemV1("metric_main", VisualizationKind.METRIC, "Revenue metric", {"metric_id": "metric_revenue", "chart_context_id": "chart_main", "value": ExactDecimalV1(10, 0), "unit": VisualizationUnitKind.CURRENCY, "currency": "USD", "period": PeriodV1("q1_metric", 1, "Q1"), "evidence": (_binding(capture),)})
    artifact = compile_visualization_artifact(title="Q1", editorial_role="quantify", policy=_policy(), items=(chart, metric), capture_plans={capture.source_capture_plan_id: capture})
    props, video_edl, word, v4_event_id = _upstream(); frame = _frame(word, video_edl, start_word_index=2, end_word_index=3)
    stages = (VisualizationStageV1("stage_axis", VisualizationStageKind.AXIS_REVEAL, ("chart_main",), frame, 1), VisualizationStageV1("stage_metric", VisualizationStageKind.METRIC_COUNT, ("metric_main",), frame, 2))
    plan = compile_visualization_render_plan(artifact=artifact, render_props=props, video_edl=video_edl, word_to_frame=word, v4_event_id=v4_event_id, stages=stages)
    svg, metadata, receipt = render_replay_visualization(artifact=artifact, plan=plan, capture_plans={capture.source_capture_plan_id: capture})
    assert svg.startswith(b"\x89PNG\r\n\x1a\n") and metadata.rendered_stage_ids == ("stage_axis", "stage_metric")
    assert receipt.svg_hash == "sha256:" + hashlib.sha256(svg).hexdigest()
    assert receipt.status == "SUCCESS" and receipt.svg_hash == metadata.rendered_svg_hash
    assert artifact.items[0].source_caption_id is not None
    assert metadata.source_caption_collection_id == artifact.source_captions.source_caption_collection_id
    assert len(receipt.dependencies) == 8
    assert build_visualization_replay_props(artifact=artifact, plan=plan, metadata=metadata)["forms"] == [{"item_id": "chart_main", "kind": "chart", "form": "line"}, {"item_id": "metric_main", "kind": "metric", "form": "metric"}]
    with pytest.raises(VisualizationContractError, match="RENDERED_METADATA_INVALID"):
        serialize_rendered_visualization_metadata(dataclasses.replace(metadata, rendered_svg_hash="sha256:" + "0" * 64))
    with pytest.raises(VisualizationContractError, match="VISUALIZATION_RECEIPT_INVALID"):
        validate_visualization_render_receipt(dataclasses.replace(receipt, status="FAILURE"))
    with pytest.raises(VisualizationContractError, match="VISUALIZATION_RECEIPT_INVALID"):
        validate_visualization_render_receipt(dataclasses.replace(receipt, dependencies=tuple(reversed(receipt.dependencies))))
    with pytest.raises(VisualizationContractError, match="FRAME_BINDING_INVALID"):
        compile_visualization_render_plan(artifact=artifact, render_props=props, video_edl=video_edl, word_to_frame=word, v4_event_id=v4_event_id, stages=(dataclasses.replace(stages[0], frame_binding=dataclasses.replace(frame, global_start_frame=frame.global_start_frame + 1)),))


def test_resolved_business_policy_drives_core_without_domain_branch() -> None:
    catalog = SchemaCatalog(REPO_ROOT / "schema" / "v3")
    registry = DomainPackRegistry([REPO_ROOT / "domain-packs"], catalog); registry.discover()
    profile = json.loads((REPO_ROOT / "samples" / "v3" / "business-tech" / "workspace.json").read_text(encoding="utf-8"))["domain"]["profile"]
    snapshot, _ = DomainPolicyResolver(catalog).resolve(registry.get("business-tech", "0.1.0"), profile)
    policy = visualization_policy_from_snapshot(snapshot)
    assert policy.allowed_chart_kinds == ("line", "bar", "area", "stacked", "comparison", "waterfall", "timeline")
    assert policy.preferred_chart_kinds == ("line", "bar", "comparison")


@pytest.mark.parametrize("chart_kind", ("line", "bar", "area", "stacked", "comparison", "waterfall", "timeline"))
def test_all_roadmap_chart_kinds_are_declarative(chart_kind: str) -> None:
    capture = _capture()
    artifact = compile_visualization_artifact(title="Q1", editorial_role="quantify", policy=_policy(), items=(_chart(capture, chart_kind),), capture_plans={capture.source_capture_plan_id: capture})
    assert artifact.items[0].payload["chart_kind"] == chart_kind


def test_three_chart_focus_stages_produce_distinct_replay_evidence() -> None:
    captures = tuple(_capture(value=value, period=period, path=f"/report/p[{ordinal}]") for ordinal, (value, period) in enumerate((("10", "Q1"), ("20", "Q2"), ("30", "Q3")), 1))
    points = tuple(_point(capture, ordinal=ordinal, value=value, period=period) for ordinal, (capture, value, period) in enumerate(zip(captures, ("10", "20", "30"), ("Q1", "Q2", "Q3"), strict=True), 1))
    chart = VisualizationItemV1("chart_main", VisualizationKind.CHART, "Revenue", {"chart_kind": "line", "series": ({"series_id": "series_revenue", "label": "Revenue", "unit": VisualizationUnitKind.CURRENCY, "currency": "USD", "datapoints": points},)})
    capture_plans = {capture.source_capture_plan_id: capture for capture in captures}
    artifact = compile_visualization_artifact(title="Q1", editorial_role="quantify", policy=_policy(), items=(chart,), capture_plans=capture_plans)
    props, video_edl, word, v4_event_id = _upstream(); frame = _frame(word, video_edl, start_word_index=2, end_word_index=3)
    stages = tuple(VisualizationStageV1(f"stage_focus_{ordinal}", VisualizationStageKind.SERIES_FOCUS, (f"point_{ordinal}",), frame, ordinal) for ordinal in range(1, 4))
    plan = compile_visualization_render_plan(artifact=artifact, render_props=props, video_edl=video_edl, word_to_frame=word, v4_event_id=v4_event_id, stages=stages)
    svgs = [render_replay_visualization(artifact=artifact, plan=plan, capture_plans=capture_plans, local_frame=local_frame)[0] for local_frame in (33, 40, 48)]
    assert len(plan.stages) == 3 and len({stage.target_ids for stage in plan.stages}) == 3 and len(set(svgs)) == 3


@pytest.mark.parametrize("kind,edge_kind", ((VisualizationKind.TIMELINE, "chronological"), (VisualizationKind.RELATIONSHIP_GRAPH, "depends_on"), (VisualizationKind.EVIDENCE_CHAIN, "supports"), (VisualizationKind.MAP, "adjacent")))
def test_topology_arms_use_the_same_evidence_core(kind, edge_kind) -> None:
    capture = _capture(); node = {"node_id": "node_one", "label": "Revenue", "value": ExactDecimalV1(10, 0), "unit": VisualizationUnitKind.CURRENCY, "currency": "USD", "period": PeriodV1("q1", 1, "Q1"), "evidence": (_binding(capture),)}
    item = VisualizationItemV1("topology", kind, "Topology", {"nodes": (node,), "edges": ()})
    artifact = compile_visualization_artifact(title="Topology", editorial_role="context", policy=_policy(), items=(item,), capture_plans={capture.source_capture_plan_id: capture})
    assert artifact.items[0].kind is kind


def test_bad_evidence_or_global_local_frame_drift_rejects() -> None:
    capture = _capture(); bad = _binding(capture, numeric="11")
    point = _point(capture); point["evidence"] = (bad,)
    item = dataclasses.replace(_chart(capture), payload={"chart_kind": "line", "series": ({"series_id": "series_revenue", "label": "Revenue", "unit": VisualizationUnitKind.CURRENCY, "currency": "USD", "datapoints": (point,)},)})
    with pytest.raises(VisualizationContractError, match="EVIDENCE_NUMERIC_MISMATCH"):
        compile_visualization_artifact(title="Q1", editorial_role="quantify", policy=_policy(), items=(item,), capture_plans={capture.source_capture_plan_id: capture})


def test_topology_duplicate_edges_and_cycles_reject() -> None:
    captures = (_capture(value="10", period="Q1", path="/report/p[1]"), _capture(value="20", period="Q2", path="/report/p[2]"))
    nodes = tuple({"node_id": f"node_{ordinal}", "label": f"Q{ordinal}", "value": ExactDecimalV1.from_lexeme(value), "unit": VisualizationUnitKind.CURRENCY, "currency": "USD", "period": PeriodV1(f"q{ordinal}", ordinal, period), "evidence": (_binding(capture, numeric=value, period=period),)} for ordinal, (capture, value, period) in enumerate(zip(captures, ("10", "20"), ("Q1", "Q2"), strict=True), 1))
    plans = {capture.source_capture_plan_id: capture for capture in captures}
    cycle = ({"edge_id": "edge_one", "edge_kind": "adjacent", "from_node_id": "node_1", "to_node_id": "node_2", "ordinal": 1, "label": None}, {"edge_id": "edge_two", "edge_kind": "adjacent", "from_node_id": "node_2", "to_node_id": "node_1", "ordinal": 2, "label": None})
    item = VisualizationItemV1("map_main", VisualizationKind.MAP, "Map", {"nodes": nodes, "edges": cycle})
    with pytest.raises(VisualizationContractError, match="TOPOLOGY_CYCLE_INVALID"):
        compile_visualization_artifact(title="Map", editorial_role="context", policy=_policy(), items=(item,), capture_plans=plans)
    duplicate = tuple(dict(edge, edge_id="edge_one") for edge in cycle)
    with pytest.raises(VisualizationContractError, match="TOPOLOGY_EDGE_INVALID"):
        compile_visualization_artifact(title="Map", editorial_role="context", policy=_policy(), items=(dataclasses.replace(item, payload={"nodes": nodes, "edges": duplicate}),), capture_plans=plans)
