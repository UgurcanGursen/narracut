"""Authoritative high-cardinality REPLAY evidence for the final Phase 2 gate."""

from __future__ import annotations

import json
from pathlib import Path

from engine.contracts.alignment_report import (
    ALIGNMENT_REPORT_POLICY_V1,
    AlignmentReportPolicy,
    AlignmentReportStatus,
    compile_alignment_report,
)
from engine.contracts.caption_groups import compile_caption_groups, serialize_caption_groups
from engine.contracts.caption_preview import (
    CAPTION_PREVIEW_POLICY_V1,
    CaptionPreviewLayoutPolicy,
    PreviewRect,
    compile_caption_preview,
)
from engine.contracts.domain import DomainPackRegistry, DomainPolicyResolver, SchemaCatalog
from engine.contracts.emphasis_events import (
    EmphasisIntensity,
    EmphasisIntent,
    EmphasisTypeRef,
    compile_emphasis_events,
    serialize_emphasis_events,
)
from engine.contracts.narration import WordRangeReference
from engine.contracts.timing_publication import publish_timing_artifacts
from engine.contracts.v5_v6_collision import (
    V5V6CollisionSeverity,
    compile_v5_v6_collision_report,
)
from engine.contracts.word_to_frame import TemporalFrameRate, compile_word_to_frame
from engine.contracts.alignment_result import serialize_alignment_result
from tests.test_alignment_result import build_phase2_high_cardinality_replay


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "phase2" / "timing_publication_replay_v1.json"
REPORT_POLICY = AlignmentReportPolicy(
    ALIGNMENT_REPORT_POLICY_V1,
    950_000,
    900_000,
    950_000,
    900_000,
    250_000,
    750_000,
)


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _domain_policy():
    catalog = SchemaCatalog(ROOT / "schema" / "v3")
    registry = DomainPackRegistry([ROOT / "domain-packs"], catalog)
    registry.discover()
    profile = json.loads(
        (ROOT / "samples" / "v3" / "business-tech" / "domain" / "profile.json").read_text(encoding="utf-8")
    )
    snapshot, _ = DomainPolicyResolver(catalog).resolve(
        registry.get("business-tech", "0.1.0"), profile
    )
    return snapshot, registry


def _clean_policy() -> CaptionPreviewLayoutPolicy:
    return CaptionPreviewLayoutPolicy(
        CAPTION_PREVIEW_POLICY_V1,
        PreviewRect(50_000, 50_000, 950_000, 950_000),
        PreviewRect(80_000, 80_000, 920_000, 260_000),
        PreviewRect(80_000, 760_000, 920_000, 920_000),
    )


def _overlap_policy() -> CaptionPreviewLayoutPolicy:
    return CaptionPreviewLayoutPolicy(
        CAPTION_PREVIEW_POLICY_V1,
        PreviewRect(50_000, 50_000, 950_000, 950_000),
        PreviewRect(80_000, 80_000, 920_000, 260_000),
        PreviewRect(80_000, 200_000, 920_000, 360_000),
    )


def test_phase2_high_cardinality_replay_chain_publishes_only_verified_timing_files(tmp_path: Path) -> None:
    fixture = _fixture()
    assert fixture["schema_version"] == "PHASE2-TIMING-PUBLICATION-REPLAY-V1"
    assert len(fixture["words"]) == fixture["expected"]["word_count"] == 96
    ranges = fixture["emphasis_ranges"]
    assert all(
        0 <= item["start_word_ordinal"] < item["end_exclusive_word_ordinal"] <= 96
        for item in ranges
    )
    assert all(
        left["end_exclusive_word_ordinal"] <= right["start_word_ordinal"]
        for left, right in zip(ranges, ranges[1:])
    )

    document, revision, alignment_result = build_phase2_high_cardinality_replay(fixture)
    assert len(revision.canonical_words) == len(alignment_result.word_timings) == 96

    caption_groups = compile_caption_groups(
        narration_document=document,
        narration_revision=revision,
        alignment_result=alignment_result,
    )
    assert len(caption_groups.caption_groups) >= fixture["expected"]["caption_group_minimum"]
    snapshot, registry = _domain_policy()
    type_ref = EmphasisTypeRef("business-tech", "earnings_sting", "0.1.0")
    intents = tuple(
        EmphasisIntent(
            WordRangeReference(
                revision.revision_id,
                item["start_word_ordinal"],
                item["end_exclusive_word_ordinal"],
            ),
            type_ref,
            EmphasisIntensity(item["intensity"]),
        )
        for item in ranges
    )
    emphasis_events = compile_emphasis_events(
        narration_document=document,
        narration_revision=revision,
        alignment_result=alignment_result,
        caption_groups=caption_groups,
        domain_policy_snapshot=snapshot,
        domain_pack_registry=registry,
        intents=intents,
    )
    word_to_frame = compile_word_to_frame(
        alignment_result=alignment_result,
        caption_groups=caption_groups,
        emphasis_events=emphasis_events,
        frame_rate=TemporalFrameRate(30, 1),
    )

    # The compiler preserves sparse word/group/event records; it never expands a frame range.
    assert len(word_to_frame.word_frames) == 96
    assert len(word_to_frame.caption_frames) == len(caption_groups.caption_groups)
    assert len(word_to_frame.emphasis_frames) == len(emphasis_events.emphasis_events)
    assert word_to_frame.word_frames[-1].end_exclusive_frame > len(word_to_frame.word_frames)

    report = compile_alignment_report(
        narration_document=document,
        narration_revision=revision,
        alignment_result=alignment_result,
        caption_groups=caption_groups,
        policy=REPORT_POLICY,
    )
    assert report.status is AlignmentReportStatus.REVIEW_REQUIRED
    assert any(
        finding.word_ordinal == fixture["expected"]["review_required_word_ordinal"]
        for finding in report.findings
    )

    preview = compile_caption_preview(
        caption_groups=caption_groups,
        emphasis_events=emphasis_events,
        word_to_frame=word_to_frame,
        layout_policy=_clean_policy(),
    )
    clean_collision = compile_v5_v6_collision_report(caption_preview=preview)
    assert clean_collision.blocker_count == 0

    blocked_preview = compile_caption_preview(
        caption_groups=caption_groups,
        emphasis_events=emphasis_events,
        word_to_frame=word_to_frame,
        layout_policy=_overlap_policy(),
    )
    visible_blocker = compile_v5_v6_collision_report(caption_preview=blocked_preview)
    assert visible_blocker.blocker_count > 0
    assert all(item.severity is V5V6CollisionSeverity.BLOCKER for item in visible_blocker.findings)
    assert visible_blocker is not clean_collision

    receipt = publish_timing_artifacts(
        alignment_result=alignment_result,
        caption_groups=caption_groups,
        emphasis_events=emphasis_events,
        word_to_frame=word_to_frame,
        project_root=tmp_path,
    )
    expected_payloads = {
        "timing/word_timeline.json": serialize_alignment_result(alignment_result),
        "timing/caption_groups.json": serialize_caption_groups(caption_groups),
        "timing/emphasis_events.json": serialize_emphasis_events(emphasis_events),
    }
    assert tuple(item.relative_path for item in receipt.files) == tuple(expected_payloads)
    for relative_path, expected in expected_payloads.items():
        assert (tmp_path / relative_path).read_bytes() == expected
