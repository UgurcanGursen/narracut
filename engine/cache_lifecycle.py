"""Phase 14 cache-reference, payload and soft-quota planning primitives."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from engine.contracts._canonical_json import encode_canonical_json_bytes


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _identity(prefix: str, values: Mapping[str, Any]) -> tuple[str, str]:
    digest = _digest(values)
    return prefix + digest[7:39], digest


def _utc(value: str) -> datetime:
    if type(value) is not str or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", value):
        raise ValueError("CACHE_LIFECYCLE_TIMESTAMP_INVALID")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _hash(value: str) -> None:
    if type(value) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None:
        raise ValueError("CACHE_LIFECYCLE_HASH_INVALID")


@dataclass(frozen=True)
class CachePayloadObject:
    payload_object_id: str
    payload_object_hash: str
    storage_scope_id: str
    payload_hash: str
    payload_size_bytes: int
    created_at: str
    status: str

    @classmethod
    def materialize(cls, value: Mapping[str, Any]) -> "CachePayloadObject":
        required = {"payload_object_id", "storage_scope_id", "payload_hash", "payload_size_bytes", "created_at", "status"}
        if set(value) - (required | {"payload_object_hash"}) or not required <= set(value):
            raise ValueError("CACHE_PAYLOAD_FIELDS_INVALID")
        if type(value["payload_size_bytes"]) is not int or value["payload_size_bytes"] < 0:
            raise ValueError("CACHE_PAYLOAD_FIELDS_INVALID")
        _hash(value["payload_hash"]); _utc(value["created_at"])
        body = {key: value[key] for key in required if key != "payload_object_id"}
        identifier, digest = _identity("cpo_", body)
        if value["payload_object_id"] != identifier or value.get("payload_object_hash") not in (None, digest):
            raise ValueError("CACHE_PAYLOAD_IDENTITY_INVALID")
        return cls(payload_object_id=identifier, payload_object_hash=digest, **body)


@dataclass(frozen=True)
class CacheEntryRecord:
    cache_entry_id: str
    cache_entry_hash: str
    storage_scope_id: str
    cache_key: str
    profile: str
    payload_object_id: str
    producer_input_hash: str
    producer_version: str
    created_at: str
    last_accessed_at: str
    registry_artifact_ids: tuple[str, ...]
    status: str

    @classmethod
    def materialize(cls, value: Mapping[str, Any]) -> "CacheEntryRecord":
        required = {"cache_entry_id", "storage_scope_id", "cache_key", "profile", "payload_object_id", "producer_input_hash", "producer_version", "created_at", "last_accessed_at", "registry_artifact_ids", "status"}
        if set(value) - (required | {"cache_entry_hash"}) or not required <= set(value):
            raise ValueError("CACHE_ENTRY_FIELDS_INVALID")
        if value["profile"] not in {"preview", "production"} or not isinstance(value["registry_artifact_ids"], (tuple, list)) or len(set(value["registry_artifact_ids"])) != len(value["registry_artifact_ids"]):
            raise ValueError("CACHE_ENTRY_FIELDS_INVALID")
        _hash(value["producer_input_hash"]); _utc(value["created_at"]); _utc(value["last_accessed_at"])
        body = {key: value[key] for key in required if key not in {"registry_artifact_ids", "cache_entry_id"}}
        body["registry_artifact_ids"] = tuple(value["registry_artifact_ids"])
        identifier, digest = _identity("cen_", body)
        if value["cache_entry_id"] != identifier or value.get("cache_entry_hash") not in (None, digest):
            raise ValueError("CACHE_ENTRY_IDENTITY_INVALID")
        return cls(cache_entry_id=identifier, cache_entry_hash=digest, **body)


def cache_write_lifecycle_metadata(*, storage_scope_id: str, cache_key: str,
                                   profile: str, payload_hash: str,
                                   payload_size_bytes: int,
                                   producer_version: str,
                                   timestamp_utc: str,
                                   registry_artifact_ids: tuple[str, ...] = ()) -> dict[str, object]:
    """Create verified, path-free cache lifecycle rows for one cache write."""
    _hash(cache_key); _hash(payload_hash); _utc(timestamp_utc)
    payload_body = {
        "storage_scope_id": storage_scope_id, "payload_hash": payload_hash,
        "payload_size_bytes": payload_size_bytes, "created_at": timestamp_utc,
        "status": "ready",
    }
    payload_id, _ = _identity("cpo_", payload_body)
    payload = CachePayloadObject.materialize({"payload_object_id": payload_id, **payload_body})
    entry_body = {
        "storage_scope_id": storage_scope_id, "cache_key": cache_key,
        "profile": profile, "payload_object_id": payload.payload_object_id,
        "producer_input_hash": cache_key, "producer_version": producer_version,
        "created_at": timestamp_utc, "last_accessed_at": timestamp_utc,
        "registry_artifact_ids": registry_artifact_ids, "status": "ready",
    }
    entry_id, _ = _identity("cen_", entry_body)
    entry = CacheEntryRecord.materialize({"cache_entry_id": entry_id, **entry_body})
    return {"cache_entry": entry.__dict__, "payload_object": payload.__dict__}


@dataclass(frozen=True)
class RetentionPolicySnapshot:
    policy_hash: str
    storage_scope_id: str
    soft_limit_bytes: int
    hard_limit_bytes: int
    cache_ttl_seconds: int
    as_of: str

    def validate(self) -> None:
        _hash(self.policy_hash); _utc(self.as_of)
        if type(self.soft_limit_bytes) is not int or type(self.hard_limit_bytes) is not int or type(self.cache_ttl_seconds) is not int or not 0 <= self.soft_limit_bytes <= self.hard_limit_bytes or self.cache_ttl_seconds < 0:
            raise ValueError("CACHE_POLICY_INVALID")


def resolve_payload_object(*, managed_root: Path, payload_hash: str) -> Path:
    """Resolve only a verified SHA-256 fan-out object under a trusted root."""
    _hash(payload_hash)
    root = managed_root.resolve(strict=True)
    candidate = root / "sha256" / payload_hash[7:9] / payload_hash[9:]
    current = root
    for part in candidate.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("CACHE_OBJECT_RESOLUTION_INVALID")
    path = candidate.resolve(strict=True)
    if root not in path.parents or not path.is_file():
        raise ValueError("CACHE_OBJECT_RESOLUTION_INVALID")
    if path.stat().st_size < 0 or "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest() != payload_hash:
        raise ValueError("CACHE_OBJECT_INTEGRITY_INVALID")
    return path


def storage_report(*, payloads: tuple[CachePayloadObject, ...], entries: tuple[CacheEntryRecord, ...]) -> dict[str, int]:
    by_id = {item.payload_object_id: item for item in payloads}
    if len(by_id) != len(payloads) or any(entry.payload_object_id not in by_id or entry.storage_scope_id != by_id[entry.payload_object_id].storage_scope_id for entry in entries):
        raise ValueError("CACHE_REFERENCE_INVALID")
    logical = sum(by_id[entry.payload_object_id].payload_size_bytes for entry in entries if entry.status == "ready")
    physical = sum(item.payload_size_bytes for item in payloads if item.status == "ready")
    return {"logical_bytes": logical, "physical_bytes": physical, "dedup_saved_bytes": logical - physical}


def plan_soft_quota(*, payloads: tuple[CachePayloadObject, ...], entries: tuple[CacheEntryRecord, ...], policy: RetentionPolicySnapshot, retained_artifact_ids: frozenset[str]) -> dict[str, Any]:
    policy.validate()
    if any(item.storage_scope_id != policy.storage_scope_id for item in (*payloads, *entries)):
        raise ValueError("CACHE_SCOPE_INVALID")
    report = storage_report(payloads=payloads, entries=entries)
    payload_by_id = {item.payload_object_id: item for item in payloads}
    as_of = _utc(policy.as_of)
    rows: list[dict[str, Any]] = []; reclaim = 0
    for payload in sorted(payloads, key=lambda item: (item.created_at, item.payload_object_id)):
        refs = [entry for entry in entries if entry.payload_object_id == payload.payload_object_id and entry.status == "ready"]
        if payload.status != "ready" or any(set(entry.registry_artifact_ids) & retained_artifact_ids for entry in refs):
            continue
        if refs and any(as_of < max(_utc(entry.created_at), _utc(entry.last_accessed_at)) + timedelta(seconds=policy.cache_ttl_seconds) for entry in refs):
            continue
        for entry in sorted(refs, key=lambda item: (item.last_accessed_at, item.created_at, item.cache_entry_id)):
            rows.append({"kind": "RETIRE_CACHE_ENTRY", "cache_entry_id": entry.cache_entry_id, "payload_object_id": payload.payload_object_id, "reclaimable_bytes": 0})
        rows.append({"kind": "TRASH_CACHE_PAYLOAD", "payload_object_id": payload.payload_object_id, "payload_hash": payload.payload_hash, "size_bytes": payload.payload_size_bytes, "reclaimable_bytes": payload.payload_size_bytes})
        reclaim += payload.payload_size_bytes
        if report["physical_bytes"] - reclaim <= policy.soft_limit_bytes:
            break
    body = {"schema_version": "CACHE-SOFT-QUOTA-PLAN-V1", "policy_hash": policy.policy_hash, "storage_scope_id": policy.storage_scope_id, "as_of": policy.as_of, "payload_snapshot_hash": _digest([item.__dict__ for item in sorted(payloads, key=lambda item: item.payload_object_id)]), "entry_snapshot_hash": _digest([item.__dict__ for item in sorted(entries, key=lambda item: item.cache_entry_id)]), "observed_physical_bytes": report["physical_bytes"], "target_physical_bytes": policy.soft_limit_bytes, "reclaimable_bytes": reclaim, "status": "PLANNED" if report["physical_bytes"] - reclaim <= policy.soft_limit_bytes else "INSUFFICIENT_ELIGIBLE_RECLAIM", "rows": rows}
    plan_id, plan_hash = _identity("csqp_", body)
    return {"plan_id": plan_id, "plan_hash": plan_hash, **body}


def validate_soft_quota_plan(*, plan: Mapping[str, Any], payloads: tuple[CachePayloadObject, ...], entries: tuple[CacheEntryRecord, ...], policy: RetentionPolicySnapshot) -> None:
    """Reject a plan whenever its immutable cache/policy evidence has drifted."""
    policy.validate()
    body = {key: value for key, value in plan.items() if key not in {"plan_id", "plan_hash"}}
    plan_id, plan_hash = _identity("csqp_", body)
    if plan.get("plan_id") != plan_id or plan.get("plan_hash") != plan_hash:
        raise ValueError("CACHE_PLAN_IDENTITY_INVALID")
    if (body.get("policy_hash") != policy.policy_hash or body.get("storage_scope_id") != policy.storage_scope_id
            or body.get("payload_snapshot_hash") != _digest([item.__dict__ for item in sorted(payloads, key=lambda item: item.payload_object_id)])
            or body.get("entry_snapshot_hash") != _digest([item.__dict__ for item in sorted(entries, key=lambda item: item.cache_entry_id)])):
        raise ValueError("CACHE_PLAN_STALE")
