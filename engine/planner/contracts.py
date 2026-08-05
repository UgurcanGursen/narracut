"""Phase 10 immutable planner artifacts; no Workspace or EDL mutation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable

from engine.contracts._canonical_json import encode_canonical_json_bytes

from .policy import PlannerPolicyV1


PLANNER_ARTIFACT_V1 = "PHASE10-PLANNER-ARTIFACT-V1"


class PlannerContractError(ValueError):
    pass


def _fail(code: str) -> None: raise PlannerContractError(code)
def _hash(value: object) -> str: return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()
def _id(value: object, prefix: str) -> bool: return type(value) is str and value.startswith(prefix) and len(value) > len(prefix)
def _token(value: object) -> str:
    if type(value) is not str or not value or value != value.strip() or value != value.lower(): _fail("PLANNER_TOKEN_INVALID")
    return value
def _pairs(value: object, prefix: str) -> tuple[tuple[str, str], ...]:
    if type(value) not in {tuple, list}: _fail("PLANNER_REFERENCE_INVALID")
    result = tuple(value)
    if any(type(item) is not tuple or len(item) != 2 or not _id(item[0], prefix) or type(item[1]) is not str or not item[1].startswith("sha256:") for item in result) or len({item[0] for item in result}) != len(result): _fail("PLANNER_REFERENCE_INVALID")
    return result


@dataclass(frozen=True)
class GlobalOutlineV1:
    project_id: str; policy_snapshot_id: str; policy_snapshot_hash: str; central_question: str; hook: str; chapter_order: tuple[str, ...]; major_reveals: tuple[str, ...]; counterarguments: tuple[str, ...]; payoff: str; final_question: str
    def data(self) -> dict[str, object]:
        if not _id(self.project_id, "prj_") or not _id(self.policy_snapshot_id, "dps_") or any(type(item) is not str or not item for item in (self.central_question,self.hook,self.payoff,self.final_question)) or not self.chapter_order: _fail("OUTLINE_INVALID")
        body={"schema_version":PLANNER_ARTIFACT_V1,"project_id":self.project_id,"policy_snapshot_id":self.policy_snapshot_id,"policy_snapshot_hash":self.policy_snapshot_hash,"central_question":self.central_question,"hook":self.hook,"chapter_order":list(self.chapter_order),"major_reveals":list(self.major_reveals),"counterarguments":list(self.counterarguments),"payoff":self.payoff,"final_question":self.final_question}
        digest=_hash(body); return {"outline_id":"out_"+digest[7:27],"outline_hash":digest,**body}


@dataclass(frozen=True)
class NarrativeBeatV1:
    project_id: str; policy: PlannerPolicyV1; chapter_brief_id: str; chapter_brief_hash: str; order: int; core_kind: str; domain_subtype: str | None; editorial_role: str; claim_pairs: tuple[tuple[str,str],...]; narration_intent: str; safe_wording_tokens: tuple[str,...]; estimated_duration_ms: int
    def data(self) -> dict[str, object]:
        claims=_pairs(self.claim_pairs,"clm_")
        if not _id(self.project_id,"prj_") or not _id(self.chapter_brief_id,"chap_") or type(self.order) is not int or self.order<0 or _token(self.core_kind) not in self.policy.allowed_core_beat_kinds or (self.domain_subtype is not None and _token(self.domain_subtype) not in self.policy.allowed_domain_beat_subtypes) or _token(self.editorial_role) not in self.policy.allowed_editorial_roles or not claims or type(self.narration_intent) is not str or not self.narration_intent or any(_token(item) not in self.policy.allowed_safe_wording_tokens for item in self.safe_wording_tokens) or type(self.estimated_duration_ms) is not int or self.estimated_duration_ms<=0: _fail("NARRATIVE_BEAT_INVALID")
        body={"schema_version":PLANNER_ARTIFACT_V1,"project_id":self.project_id,"policy_snapshot_id":self.policy.policy_snapshot_id,"policy_snapshot_hash":self.policy.policy_snapshot_hash,"chapter_brief_id":self.chapter_brief_id,"chapter_brief_hash":self.chapter_brief_hash,"order":self.order,"core_kind":self.core_kind,"domain_subtype":self.domain_subtype,"editorial_role":self.editorial_role,"claim_id_hash_pairs":[list(item) for item in claims],"narration_intent":self.narration_intent,"safe_wording_tokens":list(self.safe_wording_tokens),"estimated_duration_ms":self.estimated_duration_ms}
        digest=_hash(body); return {"narrative_beat_id":"beat_"+digest[7:27],"narrative_beat_hash":digest,**body}


@dataclass(frozen=True)
class SequencePlanV1:
    project_id: str; policy: PlannerPolicyV1; narrative_beat_id: str; narrative_beat_hash: str; order: int; narration_intent: str; duration_ms: int; claim_pairs: tuple[tuple[str,str],...]; evidence_pairs: tuple[tuple[str,str],...]; brief_pairs: tuple[tuple[str,str],...]; edit_event_intents: tuple[str,...]
    def data(self) -> dict[str, object]:
        claims=_pairs(self.claim_pairs,"clm_"); evidence=_pairs(self.evidence_pairs,"fact_"); briefs=_pairs(self.brief_pairs,"pbrief_")
        if not _id(self.project_id,"prj_") or not _id(self.narrative_beat_id,"beat_") or type(self.order) is not int or self.order<0 or type(self.narration_intent) is not str or not self.narration_intent or not self.policy.min_sequence_duration_ms<=self.duration_ms<=self.policy.max_sequence_duration_ms or not claims or len(claims)>self.policy.max_claims_per_sequence or len(briefs)>self.policy.max_asset_briefs_per_sequence or not self.policy.min_edit_events_per_sequence<=len(self.edit_event_intents)<=self.policy.max_edit_events_per_sequence: _fail("SEQUENCE_PLAN_INVALID")
        body={"schema_version":PLANNER_ARTIFACT_V1,"project_id":self.project_id,"policy_snapshot_id":self.policy.policy_snapshot_id,"policy_snapshot_hash":self.policy.policy_snapshot_hash,"narrative_beat_id":self.narrative_beat_id,"narrative_beat_hash":self.narrative_beat_hash,"order":self.order,"narration_intent":self.narration_intent,"duration_ms":self.duration_ms,"claim_id_hash_pairs":[list(item) for item in claims],"evidence_id_hash_pairs":[list(item) for item in evidence],"planner_asset_brief_id_hash_pairs":[list(item) for item in briefs],"edit_event_intents":list(self.edit_event_intents)}
        digest=_hash(body); return {"sequence_plan_id":"splan_"+digest[7:27],"sequence_plan_hash":digest,**body}
