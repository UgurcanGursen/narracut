from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.contracts import DomainPackRegistry, DomainPolicyResolver, SchemaCatalog
from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.planner import (ChapterBriefV1, GlobalOutlineV1, NarrativeBeatV1,
                            PlannerAssembler, PlannerAssetBriefV1,
                            PlannerContractError, PlannerSnapshotV1,
                            PlannerStore, PlannerTaskPackageBuilder,
                            PlannerTaskService, SequencePlanV1,
                            planner_policy_from_snapshot, validate_response)
from engine.research import BackendMode


ROOT = Path(__file__).resolve().parents[1]
STAMP = "2026-08-05T00:00:00Z"


def _snapshot(pack: str = "business-tech"):
    catalog = SchemaCatalog(ROOT / "shared-schemas" / "v3")
    roots = [ROOT / "domain-packs", ROOT / "tests" / "fixtures" / "domain-packs"]
    registry = DomainPackRegistry(roots, catalog); registry.discover()
    profile = json.loads((ROOT / "samples" / "v3" / "business-tech" / "workspace.json").read_text(encoding="utf-8"))["domain"]["profile"]
    if pack == "dummy":
        profile = {"schema_version": "3.0.0", "profile_id": "dpf_dummy", "domain_id": "dummy-domain", "domain_pack_version": "1.0.0", "enabled_extensions": [], "policy_overrides": {}, "status": "ready", "version": 1}
        return DomainPolicyResolver(catalog).resolve(registry.get("dummy-domain", "1.0.0"), profile)[0]
    return DomainPolicyResolver(catalog).resolve(registry.get(pack, "0.1.0"), profile)[0]


def _chain(policy):
    outline = GlobalOutlineV1("prj_phase10", policy.policy_snapshot_id, policy.policy_snapshot_hash, "Why did it change?", "A sharp hook.", ("chapter_01",), ("The reveal",), (), "The payoff.", "What follows?", "accepted", 1, STAMP).data()
    chapter = ChapterBriefV1("prj_phase10", policy, outline["outline_id"], outline["outline_hash"], 0, "Explain", "before", "after", (("clm_01", "sha256:" + "b" * 64),), (("fact_01", "sha256:" + "c" * 64),), "Reveal", "Counterpoint", ("show_evidence",), "handoff", 30_000, "accepted", 1, STAMP).data()
    beat = NarrativeBeatV1("prj_phase10", policy, chapter["chapter_brief_id"], chapter["chapter_brief_hash"], 0, "mechanism" if "mechanism" in policy.allowed_core_beat_kinds else "hook", None, "mechanism" if "mechanism" in policy.allowed_editorial_roles else "dummy_role", (("clm_01", "sha256:" + "b" * 64),), "Explain the mechanism.", ("reported",), 30_000, "accepted", 1, STAMP).data()
    brief = PlannerAssetBriefV1("prj_phase10", policy, beat["narrative_beat_id"], beat["narrative_beat_hash"], 0, "show_evidence", (("fact_01", "sha256:" + "c" * 64),), "Show source evidence.", ("show_evidence",), (), "require_review", "accepted", 1, STAMP).data()
    sequence = SequencePlanV1("prj_phase10", policy, beat["narrative_beat_id"], beat["narrative_beat_hash"], 0, "Explain the mechanism.", 30_000, (("clm_01", "sha256:" + "b" * 64),), (("fact_01", "sha256:" + "c" * 64),), (("cap_01", "sha256:" + "d" * 64),), ((brief["planner_asset_brief_id"], brief["planner_asset_brief_hash"]),), tuple(f"edit {index}" for index in range(10)), ("key figure",), ("neutral",), None, None, "accepted", 1, STAMP).data()
    return outline, chapter, beat, brief, sequence


def test_business_planner_policy_is_snapshot_bound() -> None:
    policy = planner_policy_from_snapshot(_snapshot())
    assert policy.min_sequence_duration_ms == 30_000
    assert "mechanism" in policy.allowed_core_beat_kinds


def test_full_hierarchy_is_immutable_and_duration_bound(tmp_path: Path) -> None:
    policy = planner_policy_from_snapshot(_snapshot()); records = _chain(policy)
    store = PlannerStore(tmp_path / "planner.sqlite")
    for kind, record in zip(("outline", "chapter_brief", "narrative_beat", "planner_asset_brief", "sequence_plan"), records): store.put(kind=kind, record=record)
    assert store.get(kind="outline", record_id=records[0]["outline_id"], expected_hash=records[0]["outline_hash"], project_id="prj_phase10") == records[0]
    with pytest.raises(PlannerContractError, match="SEQUENCE_PLAN_INVALID"):
        SequencePlanV1("prj_phase10", policy, records[2]["narrative_beat_id"], records[2]["narrative_beat_hash"], 0, "Explain", 29_999, (("clm_01", "sha256:" + "b" * 64),), (), (), (), tuple(f"edit {index}" for index in range(10)), (), (), None, None, "accepted", 1, STAMP).data()
    store.close()


def test_assembly_is_deterministic_and_not_an_edl(tmp_path: Path) -> None:
    policy = planner_policy_from_snapshot(_snapshot()); records = _chain(policy); store = PlannerStore(tmp_path / "planner.sqlite")
    for kind, record in zip(("outline", "chapter_brief", "narrative_beat", "planner_asset_brief", "sequence_plan"), records): store.put(kind=kind, record=record)
    snapshots = {key: (data[next(name for name in data if name.endswith("_id"))], data[next(name for name in data if name.endswith("_hash"))]) for key, data in {"claim_evidence": PlannerSnapshotV1("claim_evidence", "prj_phase10", policy.policy_snapshot_id, policy.policy_snapshot_hash, (("clm_01", "sha256:" + "b" * 64),)).data(), "asset_catalog": PlannerSnapshotV1("asset_catalog", "prj_phase10", policy.policy_snapshot_id, policy.policy_snapshot_hash, (("fam_01", "sha256:" + "c" * 64),)).data(), "template_capability": PlannerSnapshotV1("template_capability", "prj_phase10", policy.policy_snapshot_id, policy.policy_snapshot_hash, (("cap_01", "sha256:" + "d" * 64),)).data(), "continuity": PlannerSnapshotV1("continuity", "prj_phase10", policy.policy_snapshot_id, policy.policy_snapshot_hash, (("cont_01", "sha256:" + "e" * 64),)).data()}.items()}
    request = PlannerAssembler().assemble(store=store, project_id="prj_phase10", policy_snapshot_id=policy.policy_snapshot_id, policy_snapshot_hash=policy.policy_snapshot_hash, snapshots=snapshots).data()
    assert request["request_id"].startswith("pareq_") and "edl" not in request
    store.close()


def test_task_package_and_response_binding_are_domain_pack_bound(tmp_path: Path) -> None:
    policy = planner_policy_from_snapshot(_snapshot())
    root = ROOT / "domain-packs" / "business-tech"
    task = PlannerTaskService().create(task_type="outline", project_id="prj_phase10", policy=policy, backend_mode=BackendMode.MANUAL_UI, prompt_template_ref="prompts/planner_outline.md", domain_pack_root=root, parent_id=None, parent_hash=None, context_snapshot_hashes=("sha256:" + "a" * 64,), expected_result_fields=("outline",))
    package = PlannerTaskPackageBuilder().build(task=task, workspace_root=tmp_path, domain_pack_root=root, context={"claims": []})
    payload = encode_canonical_json_bytes({"schema_version":"PHASE10-PLANNER-RESPONSE-V1","task_id":task.task_id,"task_hash":task.task_hash,"task_type":"outline","policy_snapshot_id":policy.policy_snapshot_id,"policy_snapshot_hash":policy.policy_snapshot_hash,"result":{"outline":{}}})
    assert (package / "response").is_dir() and validate_response(task=task, payload=payload)["result"] == {"outline": {}}


def test_dummy_pack_resolves_without_core_domain_branch() -> None:
    policy = planner_policy_from_snapshot(_snapshot("dummy"))
    assert policy.allowed_editorial_roles == ("dummy_role",)
