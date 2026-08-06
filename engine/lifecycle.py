"""Phase 14 durable, non-destructive artifact lifecycle planning."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.artifacts import PROTECTED_RETENTION_CLASSES


def _sha(value: object) -> str:
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _identity(prefix: str, body: dict[str, Any], *excluded: str) -> tuple[str, str]:
    digest = _sha({key: value for key, value in body.items() if key not in excluded})
    return prefix + digest[7:39], digest


@dataclass(frozen=True)
class ArtifactRegistryRecord:
    artifact_id: str; artifact_hash: str; project_id: str; content_hash: str
    size_bytes: int; retention_class: str; dependency_ids: tuple[str, ...]
    locked: bool; pinned: bool; approved: bool; producer: str; producer_version: str

    @classmethod
    def materialize(cls, value: Mapping[str, Any]) -> "ArtifactRegistryRecord":
        forbidden = ("path", "uri", "provider_uri", "secret", "stderr")
        if any(key in value for key in forbidden): raise ValueError("ARTIFACT_REGISTRY_UNSAFE_FIELD")
        required = {"artifact_id", "project_id", "content_hash", "size_bytes", "retention_class", "dependency_ids", "locked", "pinned", "approved", "producer", "producer_version"}
        if set(value) - {"artifact_hash", *required}: raise ValueError("ARTIFACT_REGISTRY_FIELDS_INVALID")
        if not required <= set(value) or type(value["size_bytes"]) is not int or value["size_bytes"] < 0: raise ValueError("ARTIFACT_REGISTRY_FIELDS_INVALID")
        if not isinstance(value["dependency_ids"], (tuple, list)) or len(set(value["dependency_ids"])) != len(value["dependency_ids"]): raise ValueError("ARTIFACT_REGISTRY_DEPENDENCIES_INVALID")
        body = {key: value[key] for key in required}
        artifact_hash = _sha(body)
        if value.get("artifact_hash") not in (None, artifact_hash): raise ValueError("ARTIFACT_REGISTRY_IDENTITY_INVALID")
        return cls(artifact_hash=artifact_hash, dependency_ids=tuple(value["dependency_ids"]), **{key: body[key] for key in required if key != "dependency_ids"})


def registry_snapshot(records: tuple[ArtifactRegistryRecord, ...]) -> str:
    by_id = {item.artifact_id: item for item in records}
    if len(by_id) != len(records): raise ValueError("ARTIFACT_REGISTRY_DUPLICATE")
    for item in records:
        if any(dep not in by_id or by_id[dep].project_id != item.project_id for dep in item.dependency_ids): raise ValueError("ARTIFACT_REGISTRY_DEPENDENCY_INVALID")
    return _sha([item.__dict__ for item in sorted(records, key=lambda row: row.artifact_id)])


def plan_deletion(*, records: tuple[ArtifactRegistryRecord, ...], policy_hash: str, as_of: str, root_ids: frozenset[str]) -> dict[str, Any]:
    snapshot_hash = registry_snapshot(records); by_id = {row.artifact_id: row for row in records}
    protected = set(root_ids)
    changed = True
    while changed:
        changed = False
        for row in records:
            if row.artifact_id in protected:
                for dep in row.dependency_ids:
                    if dep not in protected: protected.add(dep); changed = True
    candidates = [row for row in sorted(records, key=lambda row: row.artifact_id) if row.artifact_id not in protected and not (row.locked or row.pinned or row.approved or row.retention_class in PROTECTED_RETENTION_CLASSES)]
    body = {"schema_version": "LIFECYCLE-DELETION-PLAN-V1", "policy_hash": policy_hash, "as_of": as_of, "registry_snapshot_hash": snapshot_hash, "protected_root_ids": sorted(protected), "candidates": [{"artifact_id": row.artifact_id, "content_hash": row.content_hash, "size_bytes": row.size_bytes, "reason": "UNREFERENCED_RETENTION_ELIGIBLE", "trash_token": "trash/" + row.artifact_hash[7:39]} for row in candidates], "reclaimable_bytes": sum(row.size_bytes for row in candidates)}
    plan_id, plan_hash = _identity("ldp_", body)
    return {"plan_id": plan_id, "plan_hash": plan_hash, **body}
