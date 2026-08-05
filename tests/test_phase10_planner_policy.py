from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.contracts import DomainPackRegistry, DomainPolicyResolver, SchemaCatalog
from engine.planner import GlobalOutlineV1, NarrativeBeatV1, PlannerContractError, PlannerStore, SequencePlanV1, planner_policy_from_snapshot


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
