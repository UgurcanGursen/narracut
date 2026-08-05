from __future__ import annotations

import dataclasses

import pytest

from engine.acquisition import (
    AccessStatus, AcquisitionAdapterId, AccessibleHtmlAdapter, DOMRegion,
    EvidenceTreatmentPlanner, FeedApiAdapter, FallbackMode, ManualCaptureAdapter,
    ManualCapturePackage, OfficialPdfAdapter,
    PlannerGateDecision, ReplaySourcePackage, SourceAcquisitionError,
    SourceAdapterRegistry, SourcePreviewRenderer, SourceType,
    gate_primary_source_requirement, rank_source_packages, source_priority_policy_from_snapshot,
)
from engine.contracts.domain import policy_snapshot_hash
from engine.contracts.models import DomainPolicySnapshot


def _region(path: str, text: str) -> DOMRegion:
    return DOMRegion(path, text, 10_000, 10_000, 400_000, 200_000)


def _package(*, adapter=AcquisitionAdapterId.ACCESSIBLE_HTML, status=AccessStatus.ACCESSIBLE, target="Revenue rose 10%.", text="Headline. Revenue rose 10%.", regions: tuple[DOMRegion, ...] | None = None) -> ReplaySourcePackage:
    return ReplaySourcePackage(
        "src_acme", SourceType.REGULATOR_FILING, adapter,
        "https://example.com/report?year=2026", status, "Acme IR", "2026-08-05",
        text, target, None, (() if target is None else (_region("/article/p[2]", target),)) if regions is None else regions,
    )


def _snapshot(*, ranked: list[str], mandatory: list[str]) -> DomainPolicySnapshot:
    resolved_policy = {"policy_bundles": [{"ref": "policy.json", "policy": {"research": {"source_priority_policy": {
        "policy_version": "SOURCE-PRIORITY-POLICY-V1", "ranked_source_types": ranked,
        "mandatory_primary_source_types": mandatory,
    }}}}], "extensions": {}, "enabled_extensions": [], "overrides": {}}
    data = {
        "schema_version": "3.0.0", "domain_id": "business-tech", "domain_pack_version": "0.1.0",
        "profile_id": "profile_business", "manifest_hash": "sha256:" + "a" * 64,
        "resolved_policy": resolved_policy, "immutable": True, "created_at": "2026-08-05T00:00:00Z", "version": 1,
    }
    digest = policy_snapshot_hash(data)
    return DomainPolicySnapshot(**(data | {"snapshot_id": "dps_" + digest[7:27], "canonical_hash": digest}))


def _registry() -> SourceAdapterRegistry:
    return SourceAdapterRegistry((OfficialPdfAdapter(), AccessibleHtmlAdapter(), FeedApiAdapter(), ManualCaptureAdapter()))


def test_three_explicit_regions_produce_three_distinct_focus_events() -> None:
    regions = (
        _region("/article/header", "Headline"),
        _region("/article/p[2]", "Revenue rose 10%."),
        _region("/article/p[3]", "The number is audited."),
    )
    capture = _registry().acquire(_package(
        text="Headline Revenue rose 10%. The number is audited.", regions=regions,
    ))
    treatment = EvidenceTreatmentPlanner().plan(capture)
    assert [item.region.dom_path for item in treatment.focus_events] == [item.dom_path for item in regions]
    assert len({item.focus_id for item in treatment.focus_events}) == 3


def test_missing_or_ambiguous_target_never_fabricates_coordinates() -> None:
    missing = _registry().acquire(_package(target="Absent", text="Headline only."))
    ambiguous = _registry().acquire(_package(text="Revenue rose 10%. Revenue rose 10%."))
    for capture in (missing, ambiguous):
        assert capture.access_status is AccessStatus.TEXT_NOT_FOUND
        assert capture.fallback_mode is FallbackMode.TEXT_ONLY_EVIDENCE
        assert capture.target_dom_path is None
        assert capture.crop_regions == ()


def test_source_package_hash_changes_when_document_or_verified_region_changes() -> None:
    original = _registry().acquire(_package())
    changed_text = _registry().acquire(_package(text="Headline. Revenue rose 10%. Corrected."))
    changed_region = _registry().acquire(_package(regions=(_region("/article/p[4]", "Revenue rose 10%."),)))
    assert original.source_package_hash != changed_text.source_package_hash
    assert original.source_capture_plan_hash != changed_text.source_capture_plan_hash
    assert original.source_package_hash != changed_region.source_package_hash


def test_unverified_focus_region_is_rejected_instead_of_becoming_a_coordinate_guess() -> None:
    capture = _registry().acquire(_package())
    with pytest.raises(SourceAcquisitionError, match="EVIDENCE_REGION_UNVERIFIED"):
        EvidenceTreatmentPlanner().plan(capture, focus_regions=(_region("/foreign/p[1]", "Invented region"),))


def test_challenge_is_a_fallback_and_cannot_be_previewed() -> None:
    capture = _registry().acquire(_package(status=AccessStatus.CHALLENGE_DETECTED, target=None, text=None))
    assert capture.fallback_mode is FallbackMode.MANUAL_CAPTURE_PACKAGE
    with pytest.raises(SourceAcquisitionError, match="CHALLENGE_CANNOT_RENDER"):
        EvidenceTreatmentPlanner().plan(capture)


def test_challenge_snapshot_is_rejected_before_any_renderable_plan_exists() -> None:
    package = _package(status=AccessStatus.CHALLENGE_DETECTED, target=None, text=None)
    package = ReplaySourcePackage(**(package.__dict__ | {"snapshot_hash": "sha256:" + "b" * 64}))
    with pytest.raises(SourceAcquisitionError, match="CHALLENGE_SNAPSHOT_FORBIDDEN"):
        _registry().acquire(package)


def test_feed_evidence_is_browser_independent_and_preview_is_diagnostic_only() -> None:
    capture = _registry().acquire(_package(adapter=AcquisitionAdapterId.FEED_API))
    treatment = EvidenceTreatmentPlanner().plan(capture)
    svg = SourcePreviewRenderer().render_svg(treatment, capture=capture)
    assert b"Acme IR" in svg
    assert b"https://" not in svg


def test_preview_requires_the_exact_verified_capture_plan() -> None:
    capture = _registry().acquire(_package())
    treatment = EvidenceTreatmentPlanner().plan(capture)
    other = _registry().acquire(ReplaySourcePackage(**(_package().__dict__ | {"source_id": "src_other"})))
    with pytest.raises(SourceAcquisitionError, match="SOURCE_PREVIEW_INVALID"):
        SourcePreviewRenderer().render_svg(treatment, capture=other)


def test_manual_capture_is_content_addressed_and_uses_the_same_adapter_boundary() -> None:
    package = ManualCapturePackage(
        "src_manual", SourceType.OFFICIAL_REPORT, "https://example.com/report",
        "Acme annual report", "2026-08-05", "sha256:" + "c" * 64,
        (_region("/main/p[1]", "Audited annual result."),),
    )
    capture = _registry().acquire(package.as_replay_source_package())
    assert capture.acquisition_adapter is AcquisitionAdapterId.MANUAL_CAPTURE
    assert capture.fallback_mode is FallbackMode.SNAPSHOT_EVIDENCE
    assert EvidenceTreatmentPlanner().plan(capture).focus_events[0].region == package.regions[0]


def test_policy_ranking_changes_without_adapter_domain_fork() -> None:
    one = source_priority_policy_from_snapshot(_snapshot(
        ranked=["regulator_filing", "company_filing"], mandatory=["regulator_filing"]
    ))
    two = source_priority_policy_from_snapshot(_snapshot(
        ranked=["company_filing", "regulator_filing"], mandatory=["company_filing"]
    ))
    packages = (
        ReplaySourcePackage(**(_package().__dict__ | {"source_id": "src_company", "source_type": SourceType.COMPANY_FILING})),
        _package(),
    )
    assert [item.source_id for item in rank_source_packages(one, packages)] == ["src_acme", "src_company"]
    assert [item.source_id for item in rank_source_packages(two, packages)] == ["src_company", "src_acme"]
    assert isinstance(_registry()._adapters[AcquisitionAdapterId.ACCESSIBLE_HTML], AccessibleHtmlAdapter)


def test_mandatory_primary_source_blocks_planner_until_present() -> None:
    policy = source_priority_policy_from_snapshot(_snapshot(
        ranked=["regulator_filing", "company_filing"], mandatory=["regulator_filing"]
    ))
    no_primary = _registry().acquire(ReplaySourcePackage(**(_package().__dict__ | {"source_type": SourceType.COMPANY_FILING})))
    primary = _registry().acquire(_package())
    assert gate_primary_source_requirement(policy, (no_primary,)) is PlannerGateDecision.BLOCKED
    assert gate_primary_source_requirement(policy, (no_primary, primary)) is PlannerGateDecision.ALLOWED


def test_challenged_or_text_only_primary_never_satisfies_the_planner_gate() -> None:
    policy = source_priority_policy_from_snapshot(_snapshot(
        ranked=["regulator_filing", "company_filing"], mandatory=["regulator_filing"]
    ))
    challenged = _registry().acquire(_package(status=AccessStatus.CHALLENGE_DETECTED, target=None, text=None))
    text_only = _registry().acquire(_package(target="Absent", text="No target here."))
    assert gate_primary_source_requirement(policy, (challenged,)) is PlannerGateDecision.BLOCKED
    assert gate_primary_source_requirement(policy, (text_only,)) is PlannerGateDecision.BLOCKED
    forged = dataclasses.replace(challenged, source_type=SourceType.COMPANY_FILING)
    with pytest.raises(SourceAcquisitionError, match="CAPTURE_PLAN_INVALID"):
        gate_primary_source_requirement(policy, (forged,))
