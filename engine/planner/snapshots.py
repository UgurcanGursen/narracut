"""Read-only, hash-verifiable planner context snapshots."""

from __future__ import annotations

from typing import Iterable, Mapping

from engine.research.store import ClaimStore

from .contracts import PlannerContractError, PlannerSnapshotV1
from .policy import PlannerPolicyV1


class PlannerSnapshotService:
    """The only producer of task/assembly context snapshot projections."""

    def claim_evidence(self, *, store: ClaimStore, project_id: str,
                       policy: PlannerPolicyV1, claim_ids: Iterable[str]) -> dict[str, object]:
        pairs: list[tuple[str, str]] = []
        for claim_id in claim_ids:
            claim = store.claim(claim_id, project_id=project_id)
            if (claim.project_id != project_id or claim.policy_snapshot_id != policy.policy_snapshot_id
                    or claim.policy_snapshot_hash != policy.policy_snapshot_hash):
                raise PlannerContractError("PLANNER_CLAIM_SNAPSHOT_INVALID")
            pairs.append((claim.claim_id, claim.claim_hash))
            for fact_id in claim.fact_ids:
                fact = store.fact(fact_id, project_id=project_id)
                if fact.policy_snapshot_id != policy.policy_snapshot_id or fact.policy_snapshot_hash != policy.policy_snapshot_hash:
                    raise PlannerContractError("PLANNER_CLAIM_SNAPSHOT_INVALID")
                pairs.append((fact.fact_id, fact.fact_hash))
        if not pairs:
            raise PlannerContractError("PLANNER_CLAIM_SNAPSHOT_INVALID")
        return PlannerSnapshotV1("claim_evidence", project_id, policy.policy_snapshot_id, policy.policy_snapshot_hash, tuple(sorted(set(pairs)))).data()

    def _records(self, *, kind: str, project_id: str, policy: PlannerPolicyV1,
                 records: Iterable[Mapping[str, object]], id_key: str, hash_key: str) -> tuple[tuple[str, str], ...]:
        pairs=[]
        for record in records:
            if type(record) is not dict or record.get("project_id") != project_id or record.get("policy_snapshot_id") != policy.policy_snapshot_id or record.get("policy_snapshot_hash") != policy.policy_snapshot_hash or type(record.get(id_key)) is not str or type(record.get(hash_key)) is not str:
                raise PlannerContractError("PLANNER_%s_SNAPSHOT_INVALID" % kind.upper())
            pairs.append((record[id_key],record[hash_key]))
        if not pairs or len(set(pairs)) != len(pairs): raise PlannerContractError("PLANNER_%s_SNAPSHOT_INVALID" % kind.upper())
        return tuple(sorted(pairs))

    def catalog(self, *, project_id: str, policy: PlannerPolicyV1,
                eligible_family_records: Iterable[Mapping[str, object]]) -> dict[str, object]:
        pairs=self._records(kind="catalog",project_id=project_id,policy=policy,records=eligible_family_records,id_key="family_id",hash_key="family_hash")
        return PlannerSnapshotV1("asset_catalog", project_id, policy.policy_snapshot_id, policy.policy_snapshot_hash, pairs).data()

    def capabilities(self, *, project_id: str, policy: PlannerPolicyV1,
                     capability_records: Iterable[Mapping[str, object]]) -> dict[str, object]:
        pairs=self._records(kind="capability",project_id=project_id,policy=policy,records=capability_records,id_key="capability_id",hash_key="capability_hash")
        return PlannerSnapshotV1("template_capability", project_id, policy.policy_snapshot_id, policy.policy_snapshot_hash, pairs).data()

    def continuity(self, *, project_id: str, policy: PlannerPolicyV1,
                   accepted_state_records: Iterable[Mapping[str, object]]) -> dict[str, object]:
        pairs = self._records(kind="continuity",project_id=project_id,policy=policy,records=accepted_state_records,id_key="continuity_state_id",hash_key="continuity_state_hash")
        if len(pairs) > 2:
            raise PlannerContractError("PLANNER_CONTINUITY_SNAPSHOT_INVALID")
        return PlannerSnapshotV1("continuity", project_id, policy.policy_snapshot_id, policy.policy_snapshot_hash, pairs).data()
