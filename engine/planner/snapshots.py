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

    def catalog(self, *, project_id: str, policy: PlannerPolicyV1,
                eligible_family_pairs: Iterable[tuple[str, str]]) -> dict[str, object]:
        return PlannerSnapshotV1("asset_catalog", project_id, policy.policy_snapshot_id, policy.policy_snapshot_hash, tuple(eligible_family_pairs)).data()

    def capabilities(self, *, project_id: str, policy: PlannerPolicyV1,
                     capability_pairs: Iterable[tuple[str, str]]) -> dict[str, object]:
        return PlannerSnapshotV1("template_capability", project_id, policy.policy_snapshot_id, policy.policy_snapshot_hash, tuple(capability_pairs)).data()

    def continuity(self, *, project_id: str, policy: PlannerPolicyV1,
                   accepted_state_pairs: Iterable[tuple[str, str]]) -> dict[str, object]:
        pairs = tuple(accepted_state_pairs)
        if len(pairs) > 2:
            raise PlannerContractError("PLANNER_CONTINUITY_SNAPSHOT_INVALID")
        return PlannerSnapshotV1("continuity", project_id, policy.policy_snapshot_id, policy.policy_snapshot_hash, pairs).data()
