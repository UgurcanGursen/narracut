"""Focused REPLAY coverage for the V5/V6 collision contract."""

import hashlib
import json
import gc
import weakref
import engine.contracts.v5_v6_collision as collision

import pytest

from engine.contracts.caption_preview import (
    CAPTION_PREVIEW_POLICY_V1,
    CaptionPreviewLayoutPolicy,
    PreviewRect,
    compile_caption_preview,
)
from engine.contracts.emphasis_events import EmphasisIntent, EmphasisIntensity, EmphasisTypeRef, compile_emphasis_events
from engine.contracts.narration import WordRangeReference
from engine.contracts.word_to_frame import TemporalFrameRate, compile_word_to_frame
from engine.contracts.v5_v6_collision import (
    V5_V6_COLLISION_FINDING_HASH_V1,
    V5_V6_COLLISION_FINDING_V1,
    V5_V6_COLLISION_REPORT_HASH_V1,
    V5_V6_COLLISION_REPORT_V1,
    V5V6CollisionFindingKind,
    V5V6CollisionRejectionReason,
    V5V6CollisionSeverity,
    compile_v5_v6_collision_report,
    load_v5_v6_collision_report,
    render_v5_v6_collision_diagnostic_svg,
    serialize_v5_v6_collision_report,
)
from tests.test_caption_preview import _deps, _policy
from tests.test_emphasis_events import _build_fx


def _preview(*, overlap=False, unsafe=False):
    groups, events, frames = _deps()
    policy = _policy(overlap=overlap)
    if unsafe:
        policy = CaptionPreviewLayoutPolicy(
            CAPTION_PREVIEW_POLICY_V1, PreviewRect(50_000, 50_000, 950_000, 950_000),
            PreviewRect(0, 80_000, 920_000, 260_000), policy.v6_rect,
        )
    return compile_caption_preview(caption_groups=groups, emphasis_events=events,
        word_to_frame=frames, layout_policy=policy)


def _multi_preview():
    document, revision, result, groups, snapshot, registry, _ = _build_fx()
    type_ref = EmphasisTypeRef("business-tech", "earnings_sting", "0.1.0")
    events = compile_emphasis_events(narration_document=document, narration_revision=revision,
        alignment_result=result, caption_groups=groups, domain_policy_snapshot=snapshot,
        domain_pack_registry=registry, intents=(
            EmphasisIntent(WordRangeReference(revision.revision_id, 0, 1), type_ref, EmphasisIntensity.SUBTLE),
            EmphasisIntent(WordRangeReference(revision.revision_id, 1, 2), type_ref, EmphasisIntensity.MEDIUM),
        ))
    frames = compile_word_to_frame(alignment_result=result, caption_groups=groups,
        emphasis_events=events, frame_rate=TemporalFrameRate(30, 1))
    return compile_caption_preview(caption_groups=groups, emphasis_events=events, word_to_frame=frames,
        layout_policy=_policy(overlap=True))


def test_public_literals_and_clean_preview_pass_with_svg_oracle() -> None:
    assert collision.__all__ == [
        "V5_V6_COLLISION_REPORT_V1", "V5_V6_COLLISION_REPORT_HASH_V1", "V5_V6_COLLISION_FINDING_V1", "V5_V6_COLLISION_FINDING_HASH_V1", "V5V6CollisionFindingKind", "V5V6CollisionSeverity", "V5V6CollisionRejectionReason", "V5V6CollisionFinding", "V5V6CollisionReport", "V5V6CollisionContractError", "compile_v5_v6_collision_report", "load_v5_v6_collision_report", "serialize_v5_v6_collision_report", "render_v5_v6_collision_diagnostic_svg",
    ]
    assert (V5_V6_COLLISION_REPORT_V1, V5_V6_COLLISION_REPORT_HASH_V1) == (
        "V5-V6-COLLISION-REPORT-V1", "V5-V6-COLLISION-REPORT-HASH-V1")
    assert (V5_V6_COLLISION_FINDING_V1, V5_V6_COLLISION_FINDING_HASH_V1) == (
        "V5-V6-COLLISION-FINDING-V1", "V5-V6-COLLISION-FINDING-HASH-V1")
    report = compile_v5_v6_collision_report(caption_preview=_preview())
    assert report.findings == () and report.finding_count == report.blocker_count == 0
    payload = serialize_v5_v6_collision_report(report)
    assert payload == json.dumps(json.loads(payload), sort_keys=True, separators=(",", ":")).encode()
    assert load_v5_v6_collision_report(payload, caption_preview=_preview()).v5_v6_collision_report_hash == report.v5_v6_collision_report_hash
    svg = render_v5_v6_collision_diagnostic_svg(report, caption_preview=_preview())
    assert svg.startswith("<svg ") and 'data-kind="safe-area"' in svg and "#D7263D" not in svg
    assert hashlib.sha256(payload).hexdigest() == hashlib.sha256(serialize_v5_v6_collision_report(report)).hexdigest()


def test_positive_overlap_and_safe_area_are_blockers_with_half_open_behavior() -> None:
    overlap = compile_v5_v6_collision_report(caption_preview=_preview(overlap=True))
    assert overlap.finding_count > 0
    assert all(item.kind is V5V6CollisionFindingKind.CROSS_TRACK_OCCLUSION for item in overlap.findings)
    assert all(item.severity is V5V6CollisionSeverity.BLOCKER for item in overlap.findings)
    assert [item.ordinal for item in overlap.findings] == list(range(len(overlap.findings)))
    assert all(item.overlap_start_frame < item.overlap_end_exclusive_frame for item in overlap.findings)
    assert 'fill="#D7263D"' in render_v5_v6_collision_diagnostic_svg(overlap, caption_preview=_preview(overlap=True))
    unsafe = compile_v5_v6_collision_report(caption_preview=_preview(unsafe=True))
    assert any(item.kind is V5V6CollisionFindingKind.SAFE_AREA_VIOLATION and item.secondary_preview_scene_id is None for item in unsafe.findings)


def test_literal_blocked_report_and_svg_replay_oracles_are_stable() -> None:
    preview = _preview(overlap=True)
    report = compile_v5_v6_collision_report(caption_preview=preview)
    payload = serialize_v5_v6_collision_report(report)
    svg = render_v5_v6_collision_diagnostic_svg(report, caption_preview=preview)
    assert (len(payload), hashlib.sha256(payload).hexdigest()) == (
        1069, "a739d38a986de6ec1ff87aaf019054c690c0ee4ff394c5d4bb616535c2b4257e")
    assert (len(svg.encode()), hashlib.sha256(svg.encode()).hexdigest()) == (
        969, "95ec94a3a422896ff3abc7d2c97c6bbae01477242bb3bbdc5283766f9f0c0ec5")
    assert report.finding_count == 1
    assert (report.v5_v6_collision_report_id, report.v5_v6_collision_report_hash) == (
        "v5v6r_55eb4d1a676845f394b2150309a38130",
        "55eb4d1a676845f394b2150309a38130c8a2aee1f645d67bce2f81819c2fee14",
    )
    finding = report.findings[0]
    assert (finding.v5_v6_collision_finding_id, finding.v5_v6_collision_finding_hash) == (
        "v5v6f_2f797d63c2b450856b50454caf3d5c2c",
        "2f797d63c2b450856b50454caf3d5c2cfb118aa60b0a03bdeccf9fe04bd8b169",
    )
    assert (finding.ordinal, finding.kind, finding.severity, finding.overlap_start_frame,
            finding.overlap_end_exclusive_frame, finding.overlap_rect) == (
        0, V5V6CollisionFindingKind.CROSS_TRACK_OCCLUSION,
        V5V6CollisionSeverity.BLOCKER, 3, 27,
        PreviewRect(80_000, 200_000, 920_000, 260_000))
    assert json.dumps(json.loads(payload), ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode() == payload


@pytest.mark.parametrize("v6_rect", [
    PreviewRect(80_000, 260_000, 920_000, 420_000),  # shared horizontal edge
    PreviewRect(920_000, 260_000, 980_000, 420_000),  # corner-only contact
    PreviewRect(920_000, 80_000, 980_000, 260_000),  # shared vertical edge
])
def test_half_open_spatial_edge_and_corner_contact_are_not_collisions(v6_rect: PreviewRect) -> None:
    groups, events, frames = _deps()
    policy = CaptionPreviewLayoutPolicy(CAPTION_PREVIEW_POLICY_V1,
        PreviewRect(0, 0, 1_000_000, 1_000_000), PreviewRect(80_000, 80_000, 920_000, 260_000), v6_rect)
    preview = compile_caption_preview(caption_groups=groups, emphasis_events=events, word_to_frame=frames, layout_policy=policy)
    assert not [item for item in compile_v5_v6_collision_report(caption_preview=preview).findings if item.kind is V5V6CollisionFindingKind.CROSS_TRACK_OCCLUSION]


def test_two_genuine_v5_events_are_cross_track_only_and_ordinal_ordered() -> None:
    preview = _multi_preview()
    report = compile_v5_v6_collision_report(caption_preview=preview)
    cross = [item for item in report.findings if item.kind is V5V6CollisionFindingKind.CROSS_TRACK_OCCLUSION]
    assert len(cross) == 2
    assert [item.primary_preview_scene_id for item in cross] == [scene.preview_scene_id for scene in preview.scenes if scene.track.value == "V5"]
    assert all(item.secondary_preview_scene_id == [scene.preview_scene_id for scene in preview.scenes if scene.track.value == "V6"][0] for item in cross)
    # The second canonical caption span is [36,69), disjoint from both V5
    # spans ([3,15), [15,27)); adjacency at frame 15 is half-open and no V5/V6
    # finding can be produced from the later caption.
    assert [(scene.start_frame, scene.end_exclusive_frame) for scene in preview.scenes if scene.track.value == "V6"] == [(3, 27), (36, 69)]
    assert [(scene.start_frame, scene.end_exclusive_frame) for scene in preview.scenes if scene.track.value == "V5"] == [(3, 15), (15, 27)]


@pytest.mark.parametrize("source", [b"{", b'{"x":NaN}', b'{"x":1.0}', b'{"x":1,"x":2}', b"\xef\xbb\xbf{}"])
def test_loader_rejects_hostile_or_noncanonical_bytes(source: bytes) -> None:
    with pytest.raises(Exception) as error:
        load_v5_v6_collision_report(source, caption_preview=_preview())
    assert error.value.reason is V5V6CollisionRejectionReason.NON_CANONICAL_SERIALIZATION


def test_preview_binding_and_registered_mutation_are_fail_closed() -> None:
    preview = _preview(); report = compile_v5_v6_collision_report(caption_preview=preview)
    with pytest.raises(Exception) as error:
        render_v5_v6_collision_diagnostic_svg(report, caption_preview=_preview(overlap=True))
    assert error.value.reason is V5V6CollisionRejectionReason.DEPENDENCY_BINDING_INVALID
    object.__setattr__(report, "v5_v6_collision_report_id", "v5v6r_mutated")
    with pytest.raises(Exception) as error:
        serialize_v5_v6_collision_report(report)
    assert error.value.reason is V5V6CollisionRejectionReason.CONTENT_DRIFT


def test_loader_type_shape_precedes_binding_and_non_blocker_is_finding_invalid() -> None:
    preview = _preview(overlap=True)
    payload = serialize_v5_v6_collision_report(compile_v5_v6_collision_report(caption_preview=preview))
    value = json.loads(payload)
    value["caption_preview_id"] = 1
    with pytest.raises(Exception) as error:
        load_v5_v6_collision_report(json.dumps(value, sort_keys=True, separators=(",", ":")).encode(), caption_preview=preview)
    assert error.value.reason is V5V6CollisionRejectionReason.STRUCTURE_INVALID
    value = json.loads(payload); value["findings"][0]["severity"] = "WARNING"
    with pytest.raises(Exception) as error:
        load_v5_v6_collision_report(json.dumps(value, sort_keys=True, separators=(",", ":")).encode(), caption_preview=preview)
    assert error.value.reason is V5V6CollisionRejectionReason.FINDING_INVALID

    value = json.loads(payload); value["findings"][0]["kind"] = "UNKNOWN"
    with pytest.raises(Exception) as error:
        load_v5_v6_collision_report(json.dumps(value, sort_keys=True, separators=(",", ":")).encode(), caption_preview=preview)
    assert error.value.reason is V5V6CollisionRejectionReason.UNSUPPORTED_VALUE

    value = json.loads(payload); value["findings"][0]["v5_v6_collision_finding_hash"] = "x" * 64
    with pytest.raises(Exception) as error:
        load_v5_v6_collision_report(json.dumps(value, sort_keys=True, separators=(",", ":")).encode(), caption_preview=preview)
    assert error.value.reason is V5V6CollisionRejectionReason.IDENTITY_MISMATCH


def test_weak_registry_does_not_retain_report_after_collection() -> None:
    report = compile_v5_v6_collision_report(caption_preview=_preview())
    reference = weakref.ref(report)
    del report
    gc.collect()
    assert reference() is None
