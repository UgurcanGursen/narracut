from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.contracts import DomainPackRegistry, DomainPolicyResolver, SchemaCatalog
from engine.planner import GlobalOutlineV1, NarrativeBeatV1, PlannerAssemblyRequestV1, PlannerContractError, PlannerRepairBuilder, PlannerStore, PlannerTaskPackageBuilder, PlannerTaskService, SequencePlanV1, planner_policy_from_snapshot, validate_response
from engine.research import BackendMode
from engine.contracts._canonical_json import encode_canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]


def _snapshot():
    catalog = SchemaCatalog(ROOT / "shared-schemas" / "v3")
    registry = DomainPackRegistry([ROOT / "domain-packs"], catalog); registry.discover()
    profile = json.loads((ROOT / "samples" / "v3" / "business-tech" / "workspace.json").read_text(encoding="utf-8"))["domain"]["profile"]
    return DomainPolicyResolver(catalog).resolve(registry.get("business-tech", "0.1.0"), profile)[0]


def test_business_planner_policy_is_snapshot_bound() -> None:
    policy = planner_policy_from_snapshot(_snapshot())
    assert policy.min_sequence_duration_ms == 30_000
    assert policy.max_sequence_duration_ms == 90_000
    assert "mechanism" in policy.allowed_core_beat_kinds


def test_sequence_plan_enforces_policy_duration_and_density() -> None:
    policy = planner_policy_from_snapshot(_snapshot())
    beat = NarrativeBeatV1("prj_phase10", policy, "chap_01", "sha256:" + "a" * 64, 0, "mechanism", None, "mechanism", (("clm_01", "sha256:" + "b" * 64),), "Explain the mechanism.", ("reported",), 30_000).data()
    plan = SequencePlanV1("prj_phase10", policy, beat["narrative_beat_id"], beat["narrative_beat_hash"], 0, "Explain the mechanism.", 30_000, (("clm_01", "sha256:" + "b" * 64),), (("fact_01", "sha256:" + "c" * 64),), (), tuple(f"edit_{index}" for index in range(10))).data()
    assert plan["sequence_plan_id"].startswith("splan_")
    with pytest.raises(PlannerContractError, match="SEQUENCE_PLAN_INVALID"):
        SequencePlanV1("prj_phase10", policy, beat["narrative_beat_id"], beat["narrative_beat_hash"], 0, "Explain", 29_999, (("clm_01", "sha256:" + "b" * 64),), (), (), tuple(f"edit_{index}" for index in range(10))).data()


def test_store_preserves_exact_outline_bytes(tmp_path: Path) -> None:
    outline = GlobalOutlineV1("prj_phase10", "dps_policy", "sha256:" + "a" * 64, "Why did it change?", "A sharp hook.", ("chapter_01",), ("The reveal",), (), "The payoff.", "What follows?").data()
    store = PlannerStore(tmp_path / "planner.sqlite")
    store.put(kind="outline", record=outline)
    assert store.get(kind="outline", record_id=outline["outline_id"], expected_hash=outline["outline_hash"], project_id="prj_phase10") == outline
    assert store.export_jsonl(tmp_path / "planner.jsonl").read_bytes()
    store.close()


def test_manual_planner_package_and_response_binding(tmp_path: Path) -> None:
    policy = planner_policy_from_snapshot(_snapshot())
    task = PlannerTaskService().create(task_type="outline", project_id="prj_phase10", policy=policy, backend_mode=BackendMode.MANUAL_UI, parent_id=None, parent_hash=None, context_snapshot_hashes=("sha256:" + "a" * 64,), expected_result_fields=("outline",))
    package = PlannerTaskPackageBuilder().build(task=task, workspace_root=tmp_path, prompt_text="Return JSON.", context={"claims": []})
    assert (package / "response").is_dir()
    payload = encode_canonical_json_bytes({"schema_version":"PHASE10-PLANNER-RESPONSE-V1","task_id":task.task_id,"task_hash":task.task_hash,"task_type":"outline","policy_snapshot_id":policy.policy_snapshot_id,"policy_snapshot_hash":policy.policy_snapshot_hash,"result":{"outline":{}}})
    assert validate_response(task=task, payload=payload)["result"] == {"outline": {}}


def test_assembly_request_is_not_an_edl() -> None:
    request = PlannerAssemblyRequestV1("prj_phase10", "dps_policy", "sha256:" + "a" * 64, (("splan_01", "sha256:" + "b" * 64),), "sha256:" + "c" * 64, "sha256:" + "d" * 64, "sha256:" + "e" * 64, "sha256:" + "f" * 64).data()
    assert request["request_id"].startswith("pareq_") and "edl" not in request


def test_repair_package_is_scoped(tmp_path: Path) -> None:
    policy = planner_policy_from_snapshot(_snapshot()); service = PlannerTaskService()
    failed = service.create(task_type="outline", project_id="prj_phase10", policy=policy, backend_mode=BackendMode.MANUAL_UI, parent_id=None, parent_hash=None, context_snapshot_hashes=("sha256:" + "a" * 64,), expected_result_fields=("outline",))
    repair, path = PlannerRepairBuilder().build(failed_task=failed, policy=policy, service=service, workspace_root=tmp_path, prompt_text="Repair only invalid fields.", context={"outline": {}}, original_response=b"{}", validation_errors=("outline_invalid",))
    assert repair.parent_id == failed.task_id and (path / "response" / "validation_errors.json").is_file()
