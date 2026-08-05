"""Deterministic Phase 10 assembly request; deliberately not an EDL compiler."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

from engine.contracts._canonical_json import encode_canonical_json_bytes

from .contracts import PlannerContractError
from .store import PlannerStore


def _pair(value: object, prefix: str) -> tuple[str, str]:
    if type(value) not in {tuple, list} or len(value) != 2 or type(value[0]) is not str or not value[0].startswith(prefix) or type(value[1]) is not str or not value[1].startswith("sha256:"):
        raise PlannerContractError("PLANNER_ASSEMBLY_INVALID")
    return value[0], value[1]


@dataclass(frozen=True)
class PlannerAssemblyRequestV1:
    project_id: str; policy_snapshot_id: str; policy_snapshot_hash: str; sequence_pairs: tuple[tuple[str,str],...]; claim_evidence_snapshot_pair: tuple[str,str]; asset_catalog_snapshot_pair: tuple[str,str]; template_capability_snapshot_pair: tuple[str,str]; continuity_snapshot_pair: tuple[str,str]
    def data(self) -> dict[str,object]:
        sequences = tuple(_pair(item, "splan_") for item in self.sequence_pairs)
        if not self.project_id.startswith("prj_") or not self.policy_snapshot_id.startswith("dps_") or not self.policy_snapshot_hash.startswith("sha256:") or not sequences:
            raise PlannerContractError("PLANNER_ASSEMBLY_INVALID")
        snapshots = (_pair(self.claim_evidence_snapshot_pair, "psnap_"), _pair(self.asset_catalog_snapshot_pair, "psnap_"), _pair(self.template_capability_snapshot_pair, "psnap_"), _pair(self.continuity_snapshot_pair, "psnap_"))
        body={"schema_version":"PHASE10-PLANNER-ASSEMBLY-V1","project_id":self.project_id,"policy_snapshot_id":self.policy_snapshot_id,"policy_snapshot_hash":self.policy_snapshot_hash,"ordered_sequence_plan_id_hash_pairs":[list(item) for item in sequences],"claim_evidence_snapshot_id_hash":list(snapshots[0]),"asset_catalog_snapshot_id_hash":list(snapshots[1]),"template_capability_snapshot_id_hash":list(snapshots[2]),"continuity_snapshot_id_hash":list(snapshots[3])}
        digest="sha256:"+hashlib.sha256(encode_canonical_json_bytes(body)).hexdigest()
        return {"request_id":"pareq_"+digest[7:27],"request_hash":digest,**body}


class PlannerAssembler:
    """Reads accepted records, validates lineage, and emits only an assembly request."""

    def assemble(self, *, store: PlannerStore, project_id: str, policy_snapshot_id: str,
                 policy_snapshot_hash: str, snapshots: Mapping[str, tuple[str, str]]) -> PlannerAssemblyRequestV1:
        required = {"claim_evidence", "asset_catalog", "template_capability", "continuity"}
        if set(snapshots) != required:
            raise PlannerContractError("PLANNER_ASSEMBLY_SNAPSHOT_INVALID")
        outlines = store.accepted(kind="outline", project_id=project_id)
        if len(outlines) != 1 or outlines[0]["policy_snapshot_id"] != policy_snapshot_id or outlines[0]["policy_snapshot_hash"] != policy_snapshot_hash:
            raise PlannerContractError("PLANNER_ASSEMBLY_OUTLINE_INVALID")
        outline = outlines[0]
        chapters = sorted((item for item in store.accepted(kind="chapter_brief", project_id=project_id) if item["outline_id"] == outline["outline_id"] and item["outline_hash"] == outline["outline_hash"]), key=lambda item: item["order"])
        # Outline chapter_order is the human-facing chapter key order.  Stable
        # brief IDs are created only after the outline, so the authoritative
        # machine ordering is the contiguous explicit child order below.
        if [item["order"] for item in chapters] != list(range(len(chapters))) or len(chapters) != len(outline["chapter_order"]):
            raise PlannerContractError("PLANNER_ASSEMBLY_ORDER_INVALID")
        ordered: list[tuple[str, str]] = []
        for chapter in chapters:
            beats = sorted((item for item in store.accepted(kind="narrative_beat", project_id=project_id) if item["chapter_brief_id"] == chapter["chapter_brief_id"] and item["chapter_brief_hash"] == chapter["chapter_brief_hash"]), key=lambda item: item["order"])
            if [item["order"] for item in beats] != list(range(len(beats))) or chapter["estimated_duration_ms"] != sum(item["estimated_duration_ms"] for item in beats):
                raise PlannerContractError("PLANNER_ASSEMBLY_BEAT_INVALID")
            for beat in beats:
                plans = sorted((item for item in store.accepted(kind="sequence_plan", project_id=project_id) if item["narrative_beat_id"] == beat["narrative_beat_id"] and item["narrative_beat_hash"] == beat["narrative_beat_hash"]), key=lambda item: item["order"])
                if [item["order"] for item in plans] != list(range(len(plans))) or beat["estimated_duration_ms"] != sum(item["duration_ms"] for item in plans):
                    raise PlannerContractError("PLANNER_ASSEMBLY_SEQUENCE_INVALID")
                ordered.extend((item["sequence_plan_id"], item["sequence_plan_hash"]) for item in plans)
        return PlannerAssemblyRequestV1(project_id, policy_snapshot_id, policy_snapshot_hash, tuple(ordered), snapshots["claim_evidence"], snapshots["asset_catalog"], snapshots["template_capability"], snapshots["continuity"])
