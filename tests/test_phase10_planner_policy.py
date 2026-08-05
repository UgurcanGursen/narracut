from __future__ import annotations

import json
from pathlib import Path

from engine.contracts import DomainPackRegistry, DomainPolicyResolver, SchemaCatalog
from engine.planner import PlannerPolicyError, planner_policy_from_snapshot


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
