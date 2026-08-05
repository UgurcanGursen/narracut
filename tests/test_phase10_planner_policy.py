from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.contracts import DomainPackRegistry, DomainPolicyResolver, SchemaCatalog
from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.planner import (ChapterBriefV1, GlobalOutlineV1, NarrativeBeatV1,
                            PlannerAssembler, PlannerAssetBriefV1,
                            PlannerContractError, PlannerSnapshotV1,
                            PlannerResultImporter, PlannerSnapshotService, PlannerStore, PlannerTaskPackageBuilder, PlannerTaskStore,
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
    store = PlannerStore(tmp_path / "planner.sqlite", policy=policy)
    for kind, record in zip(("outline", "chapter_brief", "narrative_beat", "planner_asset_brief", "sequence_plan"), records): store.put(kind=kind, record=record)
    assert store.get(kind="outline", record_id=records[0]["outline_id"], expected_hash=records[0]["outline_hash"], project_id="prj_phase10") == records[0]
    with pytest.raises(PlannerContractError, match="SEQUENCE_PLAN_INVALID"):
        SequencePlanV1("prj_phase10", policy, records[2]["narrative_beat_id"], records[2]["narrative_beat_hash"], 0, "Explain", 29_999, (("clm_01", "sha256:" + "b" * 64),), (), (), (), tuple(f"edit {index}" for index in range(10)), (), (), None, None, "accepted", 1, STAMP).data()
    store.close()


def test_replay_assembly_is_deterministic_and_never_an_edl(tmp_path: Path) -> None:
    policy = planner_policy_from_snapshot(_snapshot()); records = _chain(policy)
    store = PlannerStore(tmp_path / "planner.sqlite", policy=policy)
    for kind, record in zip(("outline", "chapter_brief", "narrative_beat", "planner_asset_brief", "sequence_plan"), records): store.put(kind=kind, record=record)
    seeded = {"claim_evidence": (("clm_01", "sha256:" + "b" * 64), ("fact_01", "sha256:" + "c" * 64)), "asset_catalog": (("fam_01", "sha256:" + "e" * 64),), "template_capability": (("cap_01", "sha256:" + "d" * 64),), "continuity": ()}
    snapshots = {kind: PlannerSnapshotV1(kind, "prj_phase10", policy.policy_snapshot_id, policy.policy_snapshot_hash, pairs).data() for kind, pairs in seeded.items()}
    refs = {}
    for kind, snapshot in snapshots.items():
        id_key = next(key for key in snapshot if key.endswith("_id")); hash_key = next(key for key in snapshot if key.endswith("_hash"))
        store.connection.execute("INSERT INTO phase10_snapshots(kind,snapshot_id,snapshot_hash,project_id,payload) VALUES(?,?,?,?,?)", (kind, snapshot[id_key], snapshot[hash_key], "prj_phase10", encode_canonical_json_bytes(snapshot)))
        refs[kind] = (snapshot[id_key], snapshot[hash_key])
    store.connection.commit()
    first = PlannerAssembler().assemble(store=store, project_id="prj_phase10", policy_snapshot_id=policy.policy_snapshot_id, policy_snapshot_hash=policy.policy_snapshot_hash, snapshots=refs).data()
    second = PlannerAssembler().assemble(store=store, project_id="prj_phase10", policy_snapshot_id=policy.policy_snapshot_id, policy_snapshot_hash=policy.policy_snapshot_hash, snapshots=refs).data()
    assert first == second and first["request_id"].startswith("pareq_") and "edl" not in first and "renderer" not in first
    store.close()


def test_produced_snapshot_cannot_be_mutated_after_source_projection(tmp_path: Path) -> None:
    """A source-produced snapshot cannot be retargeted before store ingress."""
    policy = planner_policy_from_snapshot(_snapshot())
    store = PlannerStore(tmp_path / "planner.sqlite", policy=policy)
    snapshot = PlannerSnapshotService().continuity(
        project_id="prj_phase10", policy=policy, store=store,
    )
    payload_copy = snapshot.payload
    payload_copy["snapshot_kind"] = "claim_evidence"
    with pytest.raises(AttributeError, match="PLANNER_SNAPSHOT_IMMUTABLE"):
        snapshot.kind = "claim_evidence"
    assert snapshot.kind == "continuity"
    assert snapshot.payload["snapshot_kind"] == "continuity"
    PlannerSnapshotService().persist(store=store, snapshot=snapshot)
    store.close()


def test_task_package_and_response_binding_are_domain_pack_bound(tmp_path: Path) -> None:
    policy = planner_policy_from_snapshot(_snapshot())
    root = ROOT / "domain-packs" / "business-tech"
    task = PlannerTaskService().create(task_type="outline", project_id="prj_phase10", policy=policy, backend_mode=BackendMode.MANUAL_UI, prompt_template_ref="prompts/planner_outline.md", domain_pack_root=root, parent_id=None, parent_hash=None, context_snapshot_hashes=(), expected_result_fields=("outline",))
    package_store = PlannerStore(tmp_path / "package.sqlite", policy=policy)
    package = PlannerTaskPackageBuilder().build(task=task, workspace_root=tmp_path, domain_pack_root=root, store=package_store)
    outline = GlobalOutlineV1("prj_phase10", policy.policy_snapshot_id, policy.policy_snapshot_hash, "Why?", "Hook.", ("chapter_01",), ("Reveal",), (), "Payoff.", "Question?", "accepted", 1, STAMP).data()
    payload = encode_canonical_json_bytes({"schema_version":"PHASE10-PLANNER-RESPONSE-V1","task_id":task.task_id,"task_hash":task.task_hash,"task_type":"outline","policy_snapshot_id":policy.policy_snapshot_id,"policy_snapshot_hash":policy.policy_snapshot_hash,"result":{"outline":outline}})
    assert (package / "response").is_dir() and validate_response(task=task, payload=payload)["result"] == {"outline": outline}
    tasks = PlannerTaskStore(tmp_path / "tasks.sqlite"); tasks.put(task)
    service = PlannerTaskService()
    revision = service.revise(previous=task, policy=policy, domain_pack_root=root, status="package_ready", created_at=STAMP); tasks.put(revision)
    submitted = service.revise(previous=revision, policy=policy, domain_pack_root=root, status="response_submitted", created_at=STAMP); tasks.put(submitted)
    submitted_payload = encode_canonical_json_bytes({"schema_version":"PHASE10-PLANNER-RESPONSE-V1","task_id":submitted.task_id,"task_hash":submitted.task_hash,"task_type":"outline","policy_snapshot_id":policy.policy_snapshot_id,"policy_snapshot_hash":policy.policy_snapshot_hash,"result":{"outline":outline}})
    records = PlannerStore(tmp_path / "response.sqlite", policy=policy)
    accepted = tasks.submit_response(task=submitted, payload=submitted_payload, accepted=True, service=service, policy=policy, domain_pack_root=root, created_at=STAMP, importer=PlannerResultImporter(records))
    assert accepted.status == "accepted" and tasks.get(accepted.task_id) == accepted
    records.close()
    tasks.close()


def test_dummy_pack_resolves_without_core_domain_branch() -> None:
    policy = planner_policy_from_snapshot(_snapshot("dummy"))
    assert policy.allowed_editorial_roles == ("dummy_role",)


def test_dummy_and_business_packs_produce_the_same_task_package_structure(tmp_path: Path) -> None:
    business_policy, dummy_policy = planner_policy_from_snapshot(_snapshot()), planner_policy_from_snapshot(_snapshot("dummy"))
    inputs = ((business_policy, ROOT / "domain-packs" / "business-tech"), (dummy_policy, ROOT / "tests" / "fixtures" / "domain-packs" / "dummy"))
    layouts = []
    for index, (policy, root) in enumerate(inputs):
        task = PlannerTaskService().create(task_type="outline", project_id=f"prj_phase10_{index}", policy=policy, backend_mode=BackendMode.MANUAL_UI, prompt_template_ref="prompts/planner_outline.md", domain_pack_root=root, parent_id=None, parent_hash=None, context_snapshot_hashes=(), expected_result_fields=("outline",))
        package = PlannerTaskPackageBuilder().build(task=task, workspace_root=tmp_path / str(index), domain_pack_root=root, store=PlannerStore(tmp_path / f"{index}.sqlite", policy=policy))
        layouts.append(sorted(item.name for item in package.iterdir()))
    assert layouts[0] == layouts[1] == ["README.md", "expected_output.schema.json", "input_manifest.json", "planner_context.json", "prompt.md", "response"]


def test_rejected_task_repair_is_persistable(tmp_path: Path) -> None:
    policy = planner_policy_from_snapshot(_snapshot()); root = ROOT / "domain-packs" / "business-tech"; service = PlannerTaskService()
    initial = service.create(task_type="outline", project_id="prj_phase10", policy=policy, backend_mode=BackendMode.MANUAL_UI, prompt_template_ref="prompts/planner_outline.md", domain_pack_root=root, parent_id=None, parent_hash=None, context_snapshot_hashes=(), expected_result_fields=("outline",))
    tasks=PlannerTaskStore(tmp_path / "tasks.sqlite"); tasks.put(initial)
    ready=service.revise(previous=initial,policy=policy,domain_pack_root=root,status="package_ready",created_at=STAMP); tasks.put(ready)
    submitted=service.revise(previous=ready,policy=policy,domain_pack_root=root,status="response_submitted",created_at=STAMP); tasks.put(submitted)
    rejected=tasks.submit_response(task=submitted,payload=b"{}",accepted=False,service=service,policy=policy,domain_pack_root=root,created_at=STAMP)
    from engine.planner import PlannerRepairBuilder
    repair,_=PlannerRepairBuilder().build(failed_task=rejected,policy=policy,service=service,workspace_root=tmp_path,domain_pack_root=root,store=PlannerStore(tmp_path / "planner.sqlite", policy=policy),original_response=b"{}",validation_errors=("outline_invalid",))
    tasks.put(repair); assert tasks.get(repair.task_id) == repair
