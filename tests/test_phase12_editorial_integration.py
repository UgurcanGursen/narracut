from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.acquisition import (AssetIngestionInputV1, MediaType, SelectedRangeV1,
                                SemanticDeclarationV1, SourceAudioEligibilityV1,
                                SourceAudioStatus, SourceDescriptorV1,
                                asset_catalog_policy_from_snapshot,
                                compile_asset_catalog, empty_asset_catalog)
from engine.audio_director import (AudioDirectionPlanV1, ChapterAudioDirectionV1,
                                   audio_director_policy_from_snapshot)
from engine.contracts import DomainPackRegistry, DomainPolicyResolver, SchemaCatalog
from engine.contracts.edl import CueWordRange, SourceDescriptor, SourceFitMode, SourcePlaybackMode
from engine.editorial_integration import (ApprovedAssetSelectionV1, ContinuityStateV1,
                                           EditorialIntegrationCompiler,
                                           EditorialIntegrationError,
                                           canonical_executable_editorial_plan_json,
                                           compile_phase3_video_edl_from_execution,
                                           editorial_integration_policy_from_snapshot,
                                           template_capabilities_from_snapshot)
from engine.planner import PlannerAssemblyRequestV1, SequencePlanV1, planner_policy_from_snapshot


ROOT = Path(__file__).resolve().parents[1]
HASH = "sha256:" + "a" * 64


def _snapshot(pack: str = "business-tech"):
    catalog = SchemaCatalog(ROOT / "shared-schemas" / "v3")
    registry = DomainPackRegistry([ROOT / "domain-packs", ROOT / "tests" / "fixtures" / "domain-packs"], catalog)
    registry.discover()
    if pack == "dummy":
        profile = {"schema_version": "3.0.0", "profile_id": "dpf_dummy", "domain_id": "dummy-domain", "domain_pack_version": "1.0.0", "enabled_extensions": [], "policy_overrides": {}, "status": "ready", "version": 1}
        return DomainPolicyResolver(catalog).resolve(registry.get("dummy-domain", "1.0.0"), profile)[0]
    profile = json.loads((ROOT / "samples" / "v3" / "business-tech" / "workspace.json").read_text(encoding="utf-8"))["domain"]["profile"]
    return DomainPolicyResolver(catalog).resolve(registry.get(pack, "0.1.0"), profile)[0]


def _inputs():
    snapshot = _snapshot(); project = "prj_phase12"; asset_policy = asset_catalog_policy_from_snapshot(snapshot)
    source = SourceDescriptorV1("pexels", "urn:fixture:video", "editorial", ("video",), "local_replay")
    catalog = compile_asset_catalog(
        input_value=AssetIngestionInputV1(b"phase8-fixture-video", project, None, source, SemanticDeclarationV1(("company",), ("operating",), "workspace", "analytical", ("broll",), ("generic_server_room",), ("company",), ("attribution_required",)), (SelectedRangeV1(0, 500),), SourceAudioEligibilityV1(SourceAudioStatus.NOT_APPLICABLE, ("no_source_audio",), ())),
        policy=asset_policy, catalog=empty_asset_catalog(project, asset_policy),
    ).catalog
    asset = catalog.records[0]; caps = template_capabilities_from_snapshot(snapshot); cap = caps[0]
    planner_policy = planner_policy_from_snapshot(snapshot); brief = ("pbrief_phase12", HASH)
    sequence = SequencePlanV1(project, planner_policy, "beat_phase12", HASH, 0, "Explain", 30_000, (("clm_phase12", HASH),), (("fact_phase12", HASH),), ((cap.capability_id, cap.capability_hash),), (brief,), tuple(f"edit {x}" for x in range(10)), (), (), None, None, "accepted", 1, "2026-08-06T00:00:00Z").data()
    request = PlannerAssemblyRequestV1(project, snapshot.snapshot_id, snapshot.canonical_hash, ((sequence["sequence_plan_id"], sequence["sequence_plan_hash"]),), ("psnap_claim", HASH), ("psnap_asset", HASH), ("psnap_template", HASH), ("psnap_cont", HASH)).data()
    range_data = asset.selected_ranges[0]
    selection = ApprovedAssetSelectionV1(brief, asset.asset_id, asset.asset_hash, str(range_data["range_id"]), str(range_data["range_hash"]), 0, 0, 1_000_000, 1_000_000, "replay_approved")
    audio_policy = audio_director_policy_from_snapshot(snapshot)
    audio = AudioDirectionPlanV1(project, audio_policy, (ChapterAudioDirectionV1("chap_phase12", HASH, "medium", ("music_start",), ()),), ())
    return snapshot, request, sequence, catalog, selection, caps, audio


def test_executable_plan_is_deterministic_and_policy_bound() -> None:
    snapshot, request, sequence, catalog, selection, caps, audio = _inputs()
    policy = editorial_integration_policy_from_snapshot(snapshot)
    compiler = EditorialIntegrationCompiler()
    first = compiler.compile(project_id="prj_phase12", assembly_request=request, policy=policy, sequence_plans=(sequence,), catalog=catalog, selections=(selection,), capabilities=caps, audio_plan=audio, visualizations=(None,))
    second = compiler.compile(project_id="prj_phase12", assembly_request=request, policy=policy, sequence_plans=(sequence,), catalog=catalog, selections=(selection,), capabilities=caps, audio_plan=audio, visualizations=(None,))
    assert first.data() == second.data()
    assert canonical_executable_editorial_plan_json(first) == canonical_executable_editorial_plan_json(second)
    assert first.data()["sequences"][0]["execution_mode"] == "asset_only"
    assert "edl" not in first.data() and "renderer" not in first.data()


def test_missing_approved_range_and_reuse_violation_fail_closed() -> None:
    snapshot, request, sequence, catalog, selection, caps, audio = _inputs()
    policy = editorial_integration_policy_from_snapshot(snapshot)
    invalid = ApprovedAssetSelectionV1(selection.planner_asset_brief_pair, selection.asset_id, selection.asset_hash, "rng_missing", selection.range_hash, 0, 0, 1_000_000, 1_000_000, "replay_approved")
    with pytest.raises(EditorialIntegrationError, match="APPROVED_ASSET_SELECTION_INVALID"):
        EditorialIntegrationCompiler().compile(project_id="prj_phase12", assembly_request=request, policy=policy, sequence_plans=(sequence,), catalog=catalog, selections=(invalid,), capabilities=caps, audio_plan=audio, visualizations=(None,))
    first = ContinuityStateV1("splan_one", 0, "fam_one", "cap_one", None, "low").data(previous=None, policy=policy)
    second = ContinuityStateV1("splan_two", 1, "fam_one", "cap_one", None, "low").data(previous=first, policy=policy)
    with pytest.raises(EditorialIntegrationError, match="CONTINUITY_REUSE_DENIED"):
        ContinuityStateV1("splan_three", 2, "fam_one", "cap_one", None, "low").data(previous=second, policy=policy)


def test_dummy_pack_resolves_the_same_core_capability_contract() -> None:
    business = editorial_integration_policy_from_snapshot(_snapshot())
    dummy = editorial_integration_policy_from_snapshot(_snapshot("dummy"))
    assert tuple(type(item) for item in template_capabilities_from_snapshot(_snapshot())) == tuple(type(item) for item in template_capabilities_from_snapshot(_snapshot("dummy")))
    assert business.allowed_execution_modes == dummy.allowed_execution_modes


def test_phase3_video_compiler_receives_only_explicit_execution_handoff() -> None:
    from tests.test_edl import _deps
    snapshot, request, sequence, catalog, selection, caps, audio = _inputs()
    plan = EditorialIntegrationCompiler().compile(project_id="prj_phase12", assembly_request=request, policy=editorial_integration_policy_from_snapshot(snapshot), sequence_plans=(sequence,), catalog=catalog, selections=(selection,), capabilities=caps, audio_plan=audio, visualizations=(None,)).data()
    groups, events, frames, preview, report = _deps()
    first, last = frames.word_frames[0], frames.word_frames[-1]
    cue = CueWordRange(frames.project_id, frames.document_id, frames.narration_revision_id, first.source_id, last.source_id)
    source = SourceDescriptor(selection.asset_id, 30, 1, 0, 30, SourcePlaybackMode.FIT, SourceFitMode.COVER, 0, 0, 1_000_000, 1_000_000, 1_000_000, first.source_id, last.source_id)
    edl = compile_phase3_video_edl_from_execution(execution=plan["sequences"][0], cue=cue, source=source, caption_groups=groups, emphasis_events=events, word_to_frame=frames, caption_preview=preview, v5_v6_collision_report=report, fps_numerator=30, fps_denominator=1)
    assert edl.sequence_id == plan["sequences"][0]["executable_sequence_id"]
