"""Bounded Phase 14 storage pressure, quota facade and FULL journal bridge."""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from engine.cache import storage_usage
from engine.cache_execution import execute_cache_plan
from engine.cache_lifecycle import (CacheEntryRecord, CachePayloadObject,
    RetentionPolicySnapshot, plan_soft_quota, storage_report)
from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.lifecycle import ArtifactRegistryRecord, append_registry_records


@dataclass(frozen=True)
class StoragePressurePolicy:
    storage_scope_id: str
    hard_limit_bytes: int
    minimum_free_bytes: int

    def validate(self) -> None:
        if not self.storage_scope_id or min(self.hard_limit_bytes, self.minimum_free_bytes) < 0:
            raise ValueError("STORAGE_PRESSURE_POLICY_INVALID")


def storage_pressure_admission(*, managed_root: Path, policy: StoragePressurePolicy,
                               estimated_bytes: int) -> str:
    policy.validate()
    if type(estimated_bytes) is not int or estimated_bytes < 0: raise ValueError("STORAGE_PRESSURE_POLICY_INVALID")
    root = managed_root.resolve(strict=True)
    if storage_usage(root)["bytes"] + estimated_bytes > policy.hard_limit_bytes:
        return "BLOCKED_HARD_QUOTA"
    if shutil.disk_usage(root).free - estimated_bytes < policy.minimum_free_bytes:
        return "BLOCKED_MIN_FREE_DISK"
    return "ADMITTED"


class StorageQuotaManager:
    """Explicit local facade; never schedules or silently executes cleanup."""
    def analyze(self, *, payloads: tuple[CachePayloadObject, ...], entries: tuple[CacheEntryRecord, ...]) -> dict[str, int]:
        return storage_report(payloads=payloads, entries=entries)
    def plan(self, *, policy: RetentionPolicySnapshot, payloads: tuple[CachePayloadObject, ...], entries: tuple[CacheEntryRecord, ...], retained_artifact_ids: frozenset[str]) -> dict[str, Any]:
        return plan_soft_quota(payloads=payloads, entries=entries, policy=policy, retained_artifact_ids=retained_artifact_ids)
    def execute(self, *, managed_root: Path, plan: Mapping[str, Any], payloads: tuple[CachePayloadObject, ...], entries: tuple[CacheEntryRecord, ...], policy: RetentionPolicySnapshot, timestamp_utc: str) -> dict[str, Any]:
        return execute_cache_plan(managed_root=managed_root, plan=plan, payloads=payloads, entries=entries, policy=policy, timestamp_utc=timestamp_utc)


def register_committed_full_artifacts(*, project_root: Path, transaction_id: str,
                                      registry_path: Path,
                                      policy_by_kind: Mapping[str, Mapping[str, object]]) -> None:
    journal_path = project_root / "artifacts" / "transactions" / f"{transaction_id}.json"
    try:
        raw = journal_path.read_bytes(); journal = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("FULL_LIFECYCLE_TRANSACTION_INVALID") from exc
    if encode_canonical_json_bytes(journal) != raw or journal.get("transaction_id") != transaction_id or type(journal.get("receipt")) is not dict or type(journal.get("artifact_rows")) is not list:
        raise ValueError("FULL_LIFECYCLE_TRANSACTION_INVALID")
    receipt_hash = journal["receipt"].get("receipt_hash")
    marker_found = False
    try:
        for line in (project_root / "artifacts" / "registry.jsonl").read_bytes().splitlines():
            row = json.loads(line)
            if row == {"schema_version": "FULL-RENDER-REGISTRY-ROW-V1", "transaction_id": transaction_id, "marker": "COMMITTED", "receipt_hash": receipt_hash}:
                marker_found = True
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("FULL_LIFECYCLE_TRANSACTION_INVALID") from exc
    if not marker_found: raise ValueError("FULL_LIFECYCLE_TRANSACTION_UNCOMMITTED")
    records = []
    for row in journal["artifact_rows"]:
        rule = policy_by_kind.get(row.get("kind"))
        if not isinstance(rule, Mapping) or (row.get("kind") == "final_output" and rule.get("retention_class") != "final"):
            raise ValueError("FULL_LIFECYCLE_POLICY_INVALID")
        records.append(ArtifactRegistryRecord.materialize({"artifact_id": row["artifact_id"], "project_id": row["project_id"], "content_hash": row["content_sha256"], "size_bytes": row["byte_length"], "retention_class": rule.get("retention_class"), "dependency_ids": (), "locked": rule.get("locked"), "pinned": rule.get("pinned"), "approved": rule.get("approved"), "producer": row["producer"], "producer_version": rule.get("producer_version")}))
    append_registry_records(registry_path=registry_path, records=tuple(records))


def finalize_full_lifecycle(*, project_root: Path, terminal_receipt: Mapping[str, object],
                            registry_path: Path,
                            policy_by_kind: Mapping[str, Mapping[str, object]]) -> None:
    """Explicit terminal seam: committed receipt -> durable Phase 14 registry."""
    transaction_id = terminal_receipt.get("transaction_id")
    if type(transaction_id) is not str or not transaction_id:
        raise ValueError("FULL_LIFECYCLE_TRANSACTION_INVALID")
    register_committed_full_artifacts(project_root=project_root,
        transaction_id=transaction_id, registry_path=registry_path,
        policy_by_kind=policy_by_kind)


def finalize_full_outcome(*, project_root: Path, outcome: object,
                          registry_path: Path,
                          policy_by_kind: Mapping[str, Mapping[str, object]]) -> object:
    """Phase 14 production terminal boundary; no registry import, no success."""
    receipt = getattr(outcome, "receipt", None)
    if type(receipt) is not dict:
        raise ValueError("FULL_LIFECYCLE_TERMINAL_RECEIPT_REQUIRED")
    finalize_full_lifecycle(project_root=project_root, terminal_receipt=receipt,
        registry_path=registry_path, policy_by_kind=policy_by_kind)
    return outcome
