"""Deterministic Phase 10 assembly request, deliberately not an EDL compiler."""

import hashlib
from dataclasses import dataclass

from engine.contracts._canonical_json import encode_canonical_json_bytes

from .contracts import PlannerContractError


@dataclass(frozen=True)
class PlannerAssemblyRequestV1:
    project_id: str; policy_snapshot_id: str; policy_snapshot_hash: str; sequence_pairs: tuple[tuple[str,str],...]; claim_evidence_snapshot_hash: str; asset_catalog_snapshot_hash: str; template_capability_snapshot_hash: str; continuity_snapshot_hash: str
    def data(self) -> dict[str,object]:
        if not self.project_id.startswith("prj_") or not self.policy_snapshot_id.startswith("dps_") or not self.sequence_pairs or any(not item[0].startswith("splan_") or not item[1].startswith("sha256:") for item in self.sequence_pairs) or any(not value.startswith("sha256:") for value in (self.policy_snapshot_hash,self.claim_evidence_snapshot_hash,self.asset_catalog_snapshot_hash,self.template_capability_snapshot_hash,self.continuity_snapshot_hash)):
            raise PlannerContractError("PLANNER_ASSEMBLY_INVALID")
        body={"schema_version":"PHASE10-PLANNER-ASSEMBLY-V1","project_id":self.project_id,"policy_snapshot_id":self.policy_snapshot_id,"policy_snapshot_hash":self.policy_snapshot_hash,"ordered_sequence_plan_id_hash_pairs":[list(item) for item in self.sequence_pairs],"claim_evidence_snapshot_hash":self.claim_evidence_snapshot_hash,"asset_catalog_snapshot_hash":self.asset_catalog_snapshot_hash,"template_capability_snapshot_hash":self.template_capability_snapshot_hash,"continuity_snapshot_hash":self.continuity_snapshot_hash}
        digest="sha256:"+hashlib.sha256(encode_canonical_json_bytes(body)).hexdigest(); return {"request_id":"pareq_"+digest[7:27],"request_hash":digest,**body}
