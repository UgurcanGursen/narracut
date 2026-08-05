"""Phase 10 canonical, immutable planner artifacts.

This module is intentionally a planning boundary: it has no Workspace, EDL,
asset-selection or renderer dependency.  Artifact identity is computed by core
code from a canonical projection; an LLM can only supply fields to validate.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from engine.contracts._canonical_json import encode_canonical_json_bytes

from .policy import PlannerPolicyV1


PLANNER_ARTIFACT_V1 = "PHASE10-PLANNER-ARTIFACT-V1"
PLANNER_SNAPSHOT_V1 = "PHASE10-PLANNER-SNAPSHOT-V1"


class PlannerContractError(ValueError):
    pass


def _fail(code: str) -> None:
    raise PlannerContractError(code)


def _hash(value: object) -> str:
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _id(value: object, prefix: str) -> bool:
    return type(value) is str and value.startswith(prefix) and len(value) > len(prefix)


def _hash_ok(value: object) -> bool:
    return type(value) is str and len(value) == 71 and value.startswith("sha256:") and all(item in "0123456789abcdef" for item in value[7:])


def _text(value: object) -> str:
    if type(value) is not str or not value.strip():
        _fail("PLANNER_TEXT_INVALID")
    return value


def _token(value: object) -> str:
    if type(value) is not str or not value or value != value.strip() or value != value.lower():
        _fail("PLANNER_TOKEN_INVALID")
    return value


def _tokens(value: object) -> tuple[str, ...]:
    if type(value) not in {tuple, list}:
        _fail("PLANNER_TOKEN_INVALID")
    result = tuple(_token(item) for item in value)
    if len(set(result)) != len(result):
        _fail("PLANNER_TOKEN_INVALID")
    return result


def _pairs(value: object, prefix: str) -> tuple[tuple[str, str], ...]:
    if type(value) not in {tuple, list}:
        _fail("PLANNER_REFERENCE_INVALID")
    result = tuple(value)
    if any(type(item) is not tuple or len(item) != 2 or not _id(item[0], prefix) or not _hash_ok(item[1]) for item in result) or len({item[0] for item in result}) != len(result):
        _fail("PLANNER_REFERENCE_INVALID")
    return result


def _common(*, project_id: str, policy_snapshot_id: str, policy_snapshot_hash: str,
            status: str, version: int, created_at: str, parent_id: str | None,
            parent_hash: str | None, supersedes_id: str | None,
            supersedes_hash: str | None) -> dict[str, object]:
    if (not _id(project_id, "prj_") or not _id(policy_snapshot_id, "dps_")
            or not _hash_ok(policy_snapshot_hash) or _token(status) not in {"accepted", "proposed"}
            or type(version) is not int or version < 1 or type(created_at) is not str
            or not created_at.endswith("Z") or (parent_id is None) != (parent_hash is None)
            or (parent_id is not None and (type(parent_id) is not str or not _hash_ok(parent_hash)))
            or (supersedes_id is None) != (supersedes_hash is None)
            or (supersedes_id is not None and (type(supersedes_id) is not str or not _hash_ok(supersedes_hash)))):
        _fail("PLANNER_COMMON_INVALID")
    return {"schema_version": PLANNER_ARTIFACT_V1, "project_id": project_id,
            "policy_snapshot_id": policy_snapshot_id, "policy_snapshot_hash": policy_snapshot_hash,
            "status": status, "version": version, "created_at": created_at,
            "parent_id": parent_id, "parent_hash": parent_hash,
            "supersedes_id": supersedes_id, "supersedes_hash": supersedes_hash}


def _record(kind: str, prefix: str, body: dict[str, object]) -> dict[str, object]:
    digest = _hash(body)
    return {f"{kind}_id": prefix + digest[7:27], f"{kind}_hash": digest, **body}


@dataclass(frozen=True)
class GlobalOutlineV1:
    project_id: str; policy_snapshot_id: str; policy_snapshot_hash: str; central_question: str; hook: str; chapter_order: tuple[str, ...]; major_reveals: tuple[str, ...]; counterarguments: tuple[str, ...]; payoff: str; final_question: str; status: str; version: int; created_at: str; supersedes_id: str | None = None; supersedes_hash: str | None = None
    def data(self) -> dict[str, object]:
        chapters = tuple(_text(item) for item in self.chapter_order)
        if not chapters or len(set(chapters)) != len(chapters): _fail("OUTLINE_INVALID")
        body = _common(project_id=self.project_id, policy_snapshot_id=self.policy_snapshot_id, policy_snapshot_hash=self.policy_snapshot_hash, status=self.status, version=self.version, created_at=self.created_at, parent_id=None, parent_hash=None, supersedes_id=self.supersedes_id, supersedes_hash=self.supersedes_hash)
        body.update({"central_question": _text(self.central_question), "hook": _text(self.hook), "chapter_order": list(chapters), "major_reveals": list(map(_text, self.major_reveals)), "counterarguments": list(map(_text, self.counterarguments)), "payoff": _text(self.payoff), "final_question": _text(self.final_question)})
        return _record("outline", "out_", body)


@dataclass(frozen=True)
class ChapterBriefV1:
    project_id: str; policy: PlannerPolicyV1; outline_id: str; outline_hash: str; order: int; goal: str; entry_state: str; exit_state: str; claim_pairs: tuple[tuple[str, str], ...]; evidence_pairs: tuple[tuple[str, str], ...]; main_reveal: str; counterpoint: str; visual_opportunity_tokens: tuple[str, ...]; continuity_handoff: str; estimated_duration_ms: int; status: str; version: int; created_at: str; supersedes_id: str | None = None; supersedes_hash: str | None = None
    def data(self) -> dict[str, object]:
        claims, evidence = _pairs(self.claim_pairs, "clm_"), _pairs(self.evidence_pairs, "fact_")
        if not _id(self.outline_id, "out_") or not _hash_ok(self.outline_hash) or type(self.order) is not int or self.order < 0 or not claims or type(self.estimated_duration_ms) is not int or self.estimated_duration_ms <= 0 or any(item not in self.policy.allowed_visual_role_tokens for item in _tokens(self.visual_opportunity_tokens)):
            _fail("CHAPTER_BRIEF_INVALID")
        body = _common(project_id=self.project_id, policy_snapshot_id=self.policy.policy_snapshot_id, policy_snapshot_hash=self.policy.policy_snapshot_hash, status=self.status, version=self.version, created_at=self.created_at, parent_id=self.outline_id, parent_hash=self.outline_hash, supersedes_id=self.supersedes_id, supersedes_hash=self.supersedes_hash)
        body.update({"outline_id": self.outline_id, "outline_hash": self.outline_hash, "order": self.order, "goal": _text(self.goal), "entry_state": _text(self.entry_state), "exit_state": _text(self.exit_state), "claim_id_hash_pairs": [list(item) for item in claims], "required_evidence_id_hash_pairs": [list(item) for item in evidence], "main_reveal": _text(self.main_reveal), "counterpoint": _text(self.counterpoint), "visual_opportunity_tokens": list(_tokens(self.visual_opportunity_tokens)), "continuity_handoff": _text(self.continuity_handoff), "estimated_duration_ms": self.estimated_duration_ms})
        return _record("chapter_brief", "chap_", body)


@dataclass(frozen=True)
class NarrativeBeatV1:
    project_id: str; policy: PlannerPolicyV1; chapter_brief_id: str; chapter_brief_hash: str; order: int; core_kind: str; domain_subtype: str | None; editorial_role: str; claim_pairs: tuple[tuple[str, str], ...]; narration_intent: str; safe_wording_tokens: tuple[str, ...]; estimated_duration_ms: int; status: str; version: int; created_at: str; supersedes_id: str | None = None; supersedes_hash: str | None = None
    def data(self) -> dict[str, object]:
        claims = _pairs(self.claim_pairs, "clm_")
        if not _id(self.chapter_brief_id, "chap_") or not _hash_ok(self.chapter_brief_hash) or type(self.order) is not int or self.order < 0 or _token(self.core_kind) not in self.policy.allowed_core_beat_kinds or (self.domain_subtype is not None and _token(self.domain_subtype) not in self.policy.allowed_domain_beat_subtypes) or _token(self.editorial_role) not in self.policy.allowed_editorial_roles or not claims or any(item not in self.policy.allowed_safe_wording_tokens for item in _tokens(self.safe_wording_tokens)) or type(self.estimated_duration_ms) is not int or self.estimated_duration_ms <= 0:
            _fail("NARRATIVE_BEAT_INVALID")
        body = _common(project_id=self.project_id, policy_snapshot_id=self.policy.policy_snapshot_id, policy_snapshot_hash=self.policy.policy_snapshot_hash, status=self.status, version=self.version, created_at=self.created_at, parent_id=self.chapter_brief_id, parent_hash=self.chapter_brief_hash, supersedes_id=self.supersedes_id, supersedes_hash=self.supersedes_hash)
        body.update({"chapter_brief_id": self.chapter_brief_id, "chapter_brief_hash": self.chapter_brief_hash, "order": self.order, "core_kind": self.core_kind, "domain_subtype": self.domain_subtype, "editorial_role": self.editorial_role, "claim_id_hash_pairs": [list(item) for item in claims], "narration_intent": _text(self.narration_intent), "safe_wording_tokens": list(_tokens(self.safe_wording_tokens)), "estimated_duration_ms": self.estimated_duration_ms})
        return _record("narrative_beat", "beat_", body)


@dataclass(frozen=True)
class PlannerAssetBriefV1:
    project_id: str; policy: PlannerPolicyV1; narrative_beat_id: str; narrative_beat_hash: str; order: int; visual_role: str; evidence_pairs: tuple[tuple[str, str], ...]; purpose: str; preferred_type_tokens: tuple[str, ...]; avoid_family_pairs: tuple[tuple[str, str], ...]; fallback_mode: str; status: str; version: int; created_at: str; supersedes_id: str | None = None; supersedes_hash: str | None = None
    def data(self) -> dict[str, object]:
        evidence, avoid = _pairs(self.evidence_pairs, "fact_"), _pairs(self.avoid_family_pairs, "fam_")
        if not _id(self.narrative_beat_id, "beat_") or not _hash_ok(self.narrative_beat_hash) or type(self.order) is not int or self.order < 0 or _token(self.visual_role) not in self.policy.allowed_visual_role_tokens or any(item not in self.policy.allowed_visual_role_tokens for item in _tokens(self.preferred_type_tokens)) or _token(self.fallback_mode) not in {"fail_closed", "require_review"}:
            _fail("PLANNER_ASSET_BRIEF_INVALID")
        body = _common(project_id=self.project_id, policy_snapshot_id=self.policy.policy_snapshot_id, policy_snapshot_hash=self.policy.policy_snapshot_hash, status=self.status, version=self.version, created_at=self.created_at, parent_id=self.narrative_beat_id, parent_hash=self.narrative_beat_hash, supersedes_id=self.supersedes_id, supersedes_hash=self.supersedes_hash)
        body.update({"narrative_beat_id": self.narrative_beat_id, "narrative_beat_hash": self.narrative_beat_hash, "order": self.order, "visual_role": self.visual_role, "evidence_id_hash_pairs": [list(item) for item in evidence], "purpose": _text(self.purpose), "preferred_type_tokens": list(_tokens(self.preferred_type_tokens)), "avoid_family_id_hash_pairs": [list(item) for item in avoid], "fallback_mode": self.fallback_mode})
        return _record("planner_asset_brief", "pbrief_", body)


@dataclass(frozen=True)
class SequencePlanV1:
    project_id: str; policy: PlannerPolicyV1; narrative_beat_id: str; narrative_beat_hash: str; order: int; narration_intent: str; duration_ms: int; claim_pairs: tuple[tuple[str, str], ...]; evidence_pairs: tuple[tuple[str, str], ...]; template_capability_pairs: tuple[tuple[str, str], ...]; brief_pairs: tuple[tuple[str, str], ...]; edit_event_intents: tuple[str, ...]; text_emphasis_intents: tuple[str, ...]; audio_direction_tokens: tuple[str, ...]; incoming_continuity_pair: tuple[str, str] | None; outgoing_continuity_pair: tuple[str, str] | None; status: str; version: int; created_at: str; supersedes_id: str | None = None; supersedes_hash: str | None = None
    def data(self) -> dict[str, object]:
        claims, evidence, capabilities, briefs = _pairs(self.claim_pairs, "clm_"), _pairs(self.evidence_pairs, "fact_"), _pairs(self.template_capability_pairs, "cap_"), _pairs(self.brief_pairs, "pbrief_")
        incoming = None if self.incoming_continuity_pair is None else _pairs((self.incoming_continuity_pair,), "cont_")[0]
        outgoing = None if self.outgoing_continuity_pair is None else _pairs((self.outgoing_continuity_pair,), "cont_")[0]
        if not _id(self.narrative_beat_id, "beat_") or not _hash_ok(self.narrative_beat_hash) or type(self.order) is not int or self.order < 0 or type(self.duration_ms) is not int or not self.policy.min_sequence_duration_ms <= self.duration_ms <= self.policy.max_sequence_duration_ms or not claims or len(claims) > self.policy.max_claims_per_sequence or len(briefs) > self.policy.max_asset_briefs_per_sequence or not self.policy.min_edit_events_per_sequence <= len(self.edit_event_intents) <= self.policy.max_edit_events_per_sequence or incoming is None != outgoing is None:
            _fail("SEQUENCE_PLAN_INVALID")
        body = _common(project_id=self.project_id, policy_snapshot_id=self.policy.policy_snapshot_id, policy_snapshot_hash=self.policy.policy_snapshot_hash, status=self.status, version=self.version, created_at=self.created_at, parent_id=self.narrative_beat_id, parent_hash=self.narrative_beat_hash, supersedes_id=self.supersedes_id, supersedes_hash=self.supersedes_hash)
        body.update({"narrative_beat_id": self.narrative_beat_id, "narrative_beat_hash": self.narrative_beat_hash, "order": self.order, "narration_intent": _text(self.narration_intent), "duration_ms": self.duration_ms, "claim_id_hash_pairs": [list(item) for item in claims], "evidence_id_hash_pairs": [list(item) for item in evidence], "template_capability_id_hash_pairs": [list(item) for item in capabilities], "planner_asset_brief_id_hash_pairs": [list(item) for item in briefs], "edit_event_intents": list(map(_text, self.edit_event_intents)), "text_emphasis_intents": list(map(_text, self.text_emphasis_intents)), "audio_direction_tokens": list(_tokens(self.audio_direction_tokens)), "incoming_continuity_state_id_hash": None if incoming is None else list(incoming), "outgoing_continuity_state_id_hash": None if outgoing is None else list(outgoing)})
        return _record("sequence_plan", "splan_", body)


@dataclass(frozen=True)
class PlannerSnapshotV1:
    snapshot_kind: str; project_id: str; policy_snapshot_id: str; policy_snapshot_hash: str; pairs: tuple[tuple[str, str], ...]
    def data(self) -> dict[str, object]:
        prefixes = {"claim_evidence": ("claims_evidence_snapshot", ("clm_", "fact_", "src_")), "asset_catalog": ("asset_catalog_snapshot", ("fam_",)), "template_capability": ("template_capability_snapshot", ("cap_",)), "continuity": ("continuity_snapshot", ("cont_",))}
        if self.snapshot_kind not in prefixes or not _id(self.project_id, "prj_") or not _id(self.policy_snapshot_id, "dps_") or not _hash_ok(self.policy_snapshot_hash): _fail("PLANNER_SNAPSHOT_INVALID")
        raw_pairs = tuple(self.pairs)
        if ((not raw_pairs and self.snapshot_kind != "continuity") or any(type(item) is not tuple or len(item) != 2 or not any(_id(item[0], prefix) for prefix in prefixes[self.snapshot_kind][1]) or not _hash_ok(item[1]) for item in raw_pairs)):
            _fail("PLANNER_SNAPSHOT_INVALID")
        body = {"schema_version": PLANNER_SNAPSHOT_V1, "snapshot_kind": self.snapshot_kind, "project_id": self.project_id, "policy_snapshot_id": self.policy_snapshot_id, "policy_snapshot_hash": self.policy_snapshot_hash, "id_hash_pairs": [list(item) for item in raw_pairs]}
        digest = _hash(body); name = prefixes[self.snapshot_kind][0]
        return {f"{name}_id": "psnap_" + digest[7:27], f"{name}_hash": digest, **body}


def validate_record(kind: str, record: object) -> tuple[str, str, dict[str, object]]:
    """Fail closed on noncanonical bytes or a forged ID/hash pair."""
    names = {"outline": ("outline_id", "outline_hash"), "chapter_brief": ("chapter_brief_id", "chapter_brief_hash"), "narrative_beat": ("narrative_beat_id", "narrative_beat_hash"), "planner_asset_brief": ("planner_asset_brief_id", "planner_asset_brief_hash"), "sequence_plan": ("sequence_plan_id", "sequence_plan_hash")}
    if kind not in names or type(record) is not dict:
        _fail("PLANNER_STORE_INVALID")
    id_key, hash_key = names[kind]
    if id_key not in record or hash_key not in record or not _id(record[id_key], {"outline":"out_", "chapter_brief":"chap_", "narrative_beat":"beat_", "planner_asset_brief":"pbrief_", "sequence_plan":"splan_"}[kind]) or not _hash_ok(record[hash_key]): _fail("PLANNER_STORE_INVALID")
    body = {key: value for key, value in record.items() if key not in {id_key, hash_key}}
    digest = _hash(body)
    if record[hash_key] != digest or record[id_key] != {"outline":"out_", "chapter_brief":"chap_", "narrative_beat":"beat_", "planner_asset_brief":"pbrief_", "sequence_plan":"splan_"}[kind] + digest[7:27] or body.get("schema_version") != PLANNER_ARTIFACT_V1 or not _id(body.get("project_id"), "prj_"):
        _fail("PLANNER_STORE_INVALID")
    return record[id_key], record[hash_key], dict(record)
