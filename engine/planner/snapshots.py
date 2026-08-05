"""Read-only, hash-verifiable planner context snapshots."""

from __future__ import annotations

from typing import Iterable, Mapping

from engine.research.store import ClaimStore
from engine.acquisition.asset_catalog import AssetCatalogV1, canonical_asset_catalog_json
from engine.rendering.template_registry import TemplateRegistry
from engine.contracts._canonical_json import encode_canonical_json_bytes
import hashlib

from .contracts import PlannerContractError, PlannerSnapshotV1
from .policy import PlannerPolicyV1
from .store import PlannerStore
from .snapshot_types import ProducedPlannerSnapshot


_PRODUCER_CAPABILITY = object()


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
        payload = PlannerSnapshotV1("claim_evidence", project_id, policy.policy_snapshot_id, policy.policy_snapshot_hash, tuple(sorted(set(pairs)))).data()
        return ProducedPlannerSnapshot("claim_evidence", payload, _PRODUCER_CAPABILITY)


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
                catalog: AssetCatalogV1) -> dict[str, object]:
        if type(catalog) is not AssetCatalogV1 or (catalog.project_id,catalog.policy_snapshot_id,catalog.policy_snapshot_hash) != (project_id,policy.policy_snapshot_id,policy.policy_snapshot_hash):
            raise PlannerContractError("PLANNER_CATALOG_SNAPSHOT_INVALID")
        families=sorted({record.visual_family_id for record in catalog.records})
        pairs=tuple(("fam_" + hashlib.sha256(encode_canonical_json_bytes({"visual_family_id": family, "catalog_hash": catalog.catalog_hash})).hexdigest()[:20], "sha256:" + hashlib.sha256(encode_canonical_json_bytes({"visual_family_id": family, "catalog_hash": catalog.catalog_hash})).hexdigest()) for family in families)
        if not pairs: raise PlannerContractError("PLANNER_CATALOG_SNAPSHOT_INVALID")
        payload = PlannerSnapshotV1("asset_catalog", project_id, policy.policy_snapshot_id, policy.policy_snapshot_hash, pairs).data()
        return ProducedPlannerSnapshot("asset_catalog", payload, _PRODUCER_CAPABILITY)

    def capabilities(self, *, project_id: str, policy: PlannerPolicyV1,
                     registry: TemplateRegistry) -> dict[str, object]:
        if type(registry) is not TemplateRegistry: raise PlannerContractError("PLANNER_CAPABILITY_SNAPSHOT_INVALID")
        pairs=tuple(("cap_" + hashlib.sha256(encode_canonical_json_bytes(definition.__dict__)).hexdigest()[:20], "sha256:" + hashlib.sha256(encode_canonical_json_bytes(definition.__dict__)).hexdigest()) for definition in registry.definitions())
        payload = PlannerSnapshotV1("template_capability", project_id, policy.policy_snapshot_id, policy.policy_snapshot_hash, pairs).data()
        return ProducedPlannerSnapshot("template_capability", payload, _PRODUCER_CAPABILITY)

    def continuity(self, *, project_id: str, policy: PlannerPolicyV1,
                   store: PlannerStore) -> dict[str, object]:
        if type(store) is not PlannerStore: raise PlannerContractError("PLANNER_CONTINUITY_SNAPSHOT_INVALID")
        pairs = store.continuity_pairs(project_id=project_id)
        if len(pairs) > 2:
            raise PlannerContractError("PLANNER_CONTINUITY_SNAPSHOT_INVALID")
        payload = PlannerSnapshotV1("continuity", project_id, policy.policy_snapshot_id, policy.policy_snapshot_hash, pairs).data()
        return ProducedPlannerSnapshot("continuity", payload, _PRODUCER_CAPABILITY)
    def persist(self, *, store: PlannerStore, snapshot: ProducedPlannerSnapshot) -> tuple[str, str]:
        """Persist only a projection returned by this typed producer boundary."""
        if type(store) is not PlannerStore or type(snapshot) is not ProducedPlannerSnapshot:
            raise PlannerContractError("PLANNER_SNAPSHOT_PERSIST_INVALID")
        return store._put_produced_snapshot(snapshot=snapshot)
