"""Typed Phase 10 planner policy resolver."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.domain import policy_snapshot_hash
from engine.contracts.models import DomainPolicySnapshot


PLANNER_POLICY_V1 = "PLANNER-POLICY-V1"
CORE_BEAT_KINDS = frozenset({"hook", "context", "promise", "rise", "reveal", "contradiction", "mechanism", "example", "consequence", "counterargument", "payoff", "chapter_reset", "final_question", "reconstruct_timeline", "compare_accounts", "introduce_entity"})


class PlannerPolicyError(ValueError):
    pass


def _fail(code: str) -> None:
    raise PlannerPolicyError(code)


def _token(value: object) -> str:
    if type(value) is not str or not value or value != value.strip() or value != value.lower():
        _fail("PLANNER_POLICY_TOKEN_INVALID")
    return value


def _tokens(value: object, *, allow_empty: bool = False) -> tuple[str, ...]:
    if type(value) is not list:
        _fail("PLANNER_POLICY_TOKEN_INVALID")
    result = tuple(_token(item) for item in value)
    if (not result and not allow_empty) or len(set(result)) != len(result):
        _fail("PLANNER_POLICY_TOKEN_INVALID")
    return result


@dataclass(frozen=True)
class PlannerPolicyV1:
    policy_snapshot_id: str
    policy_snapshot_hash: str
    allowed_core_beat_kinds: tuple[str, ...]
    allowed_domain_beat_subtypes: tuple[str, ...]
    allowed_editorial_roles: tuple[str, ...]
    allowed_visual_role_tokens: tuple[str, ...]
    allowed_safe_wording_tokens: tuple[str, ...]
    min_sequence_duration_ms: int
    max_sequence_duration_ms: int
    max_claims_per_sequence: int
    max_asset_briefs_per_sequence: int
    min_edit_events_per_sequence: int
    max_edit_events_per_sequence: int

    @property
    def policy_hash(self) -> str:
        value = {name: (list(getattr(self, name)) if name.startswith("allowed_") else getattr(self, name)) for name in self.__dataclass_fields__}
        return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def planner_policy_from_snapshot(snapshot: DomainPolicySnapshot) -> PlannerPolicyV1:
    if type(snapshot) is not DomainPolicySnapshot or not snapshot.immutable:
        _fail("PLANNER_POLICY_SNAPSHOT_INVALID")
    raw_snapshot = {field: getattr(snapshot, field) for field in snapshot.__dataclass_fields__}
    if snapshot.canonical_hash != policy_snapshot_hash(raw_snapshot):
        _fail("PLANNER_POLICY_SNAPSHOT_INVALID")
    bundles = snapshot.resolved_policy.get("policy_bundles") if type(snapshot.resolved_policy) is dict else None
    matches = [bundle["policy"]["planner"]["planner_policy"] for bundle in bundles or () if type(bundle) is dict and type(bundle.get("policy")) is dict and type(bundle["policy"].get("planner")) is dict and "planner_policy" in bundle["policy"]["planner"]]
    required = {"policy_version", "allowed_core_beat_kinds", "allowed_domain_beat_subtypes", "allowed_editorial_roles", "allowed_visual_role_tokens", "allowed_safe_wording_tokens", "min_sequence_duration_ms", "max_sequence_duration_ms", "max_claims_per_sequence", "max_asset_briefs_per_sequence", "min_edit_events_per_sequence", "max_edit_events_per_sequence"}
    if len(matches) != 1 or type(matches[0]) is not dict or set(matches[0]) != required or matches[0]["policy_version"] != PLANNER_POLICY_V1:
        _fail("PLANNER_POLICY_MISSING")
    raw = matches[0]
    values = {name: _tokens(raw[name], allow_empty=name == "allowed_domain_beat_subtypes") for name in required if name.startswith("allowed_")}
    if not set(values["allowed_core_beat_kinds"]).issubset(CORE_BEAT_KINDS):
        _fail("PLANNER_POLICY_CORE_BEAT_INVALID")
    ints = {name: raw[name] for name in required if name.endswith("_ms") or name.startswith(("max_", "min_"))}
    if any(type(value) is not int or value <= 0 for value in ints.values()) or raw["min_sequence_duration_ms"] > raw["max_sequence_duration_ms"] or raw["min_edit_events_per_sequence"] > raw["max_edit_events_per_sequence"]:
        _fail("PLANNER_POLICY_RANGE_INVALID")
    return PlannerPolicyV1(snapshot.snapshot_id, snapshot.canonical_hash, **values, **ints)
