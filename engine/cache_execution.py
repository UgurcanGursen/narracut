"""Phase 14 explicit cache-plan trash/restore execution; no background GC."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from engine.cache_lifecycle import (CacheEntryRecord, CachePayloadObject,
    RetentionPolicySnapshot, resolve_payload_object, validate_soft_quota_plan)
from engine.contracts._canonical_json import encode_canonical_json_bytes


def _hash(value: object) -> str:
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _transaction(body: Mapping[str, Any]) -> dict[str, Any]:
    digest = _hash(body)
    return {"transaction_id": "clt_" + digest[7:39], "transaction_hash": digest, **body}


def _ledger(root: Path) -> Path:
    return root / ".lifecycle" / "cache-lifecycle-transactions.jsonl"


def _append_transaction(root: Path, transaction: Mapping[str, Any]) -> None:
    path = _ledger(root); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as stream:
        stream.write(encode_canonical_json_bytes(dict(transaction)) + b"\n")
        stream.flush(); os.fsync(stream.fileno())


def load_cache_transactions(*, managed_root: Path) -> tuple[dict[str, Any], ...]:
    root = managed_root.resolve(strict=True); path = _ledger(root)
    if not path.exists(): return ()
    try:
        result = []
        for line in path.read_bytes().splitlines():
            value = json.loads(line); body = {key: item for key, item in value.items() if key not in {"transaction_id", "transaction_hash"}}
            expected = _transaction(body)
            if value != expected: raise ValueError
            result.append(value)
        return tuple(result)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("CACHE_TRANSACTION_LEDGER_INVALID") from exc


def execute_cache_plan(*, managed_root: Path, plan: Mapping[str, Any],
                       payloads: tuple[CachePayloadObject, ...],
                       entries: tuple[CacheEntryRecord, ...],
                       policy: RetentionPolicySnapshot,
                       timestamp_utc: str) -> dict[str, Any]:
    validate_soft_quota_plan(plan=plan, payloads=payloads, entries=entries, policy=policy)
    if plan.get("status") != "PLANNED" or not timestamp_utc.endswith("Z"):
        raise ValueError("CACHE_PLAN_EXECUTION_INVALID")
    root = managed_root.resolve(strict=True)
    payload_by_id = {item.payload_object_id: item for item in payloads}
    entry_by_id = {item.cache_entry_id: item for item in entries}
    retired: list[str] = []; prepared: list[tuple[CachePayloadObject, Path, Path]] = []
    for row in plan["rows"]:
        if row["kind"] == "RETIRE_CACHE_ENTRY":
            entry = entry_by_id.get(row.get("cache_entry_id"))
            if entry is None or entry.status != "ready" or row.get("payload_object_id") != entry.payload_object_id:
                raise ValueError("CACHE_PLAN_STALE")
            retired.append(entry.cache_entry_id)
        elif row["kind"] == "TRASH_CACHE_PAYLOAD":
            payload = payload_by_id.get(row.get("payload_object_id"))
            live = [item.cache_entry_id for item in entries if item.payload_object_id == row.get("payload_object_id") and item.status == "ready"]
            if payload is None or payload.status != "ready" or sorted(live) != sorted(retired) or row.get("payload_hash") != payload.payload_hash:
                raise ValueError("CACHE_PLAN_STALE")
            source = resolve_payload_object(managed_root=root, payload_hash=payload.payload_hash)
            target = (root / ".trash" / plan["plan_id"] / "sha256" / payload.payload_hash[7:9] / payload.payload_hash[9:]).resolve()
            if root not in target.parents or target.exists(): raise ValueError("CACHE_PLAN_STALE")
            target.parent.mkdir(parents=True, exist_ok=True); prepared.append((payload, source, target))
        else: raise ValueError("CACHE_PLAN_EXECUTION_INVALID")
    moved: list[tuple[CachePayloadObject, Path, Path]] = []
    try:
        for item in prepared:
            os.replace(item[1], item[2]); moved.append(item)
        body = {"schema_version": "CACHE-LIFECYCLE-TRANSACTION-V1", "kind": "retired",
                "plan_hash": plan["plan_hash"], "policy_hash": policy.policy_hash,
                "payload_snapshot_hash": plan["payload_snapshot_hash"], "entry_snapshot_hash": plan["entry_snapshot_hash"],
                "timestamp_utc": timestamp_utc, "retired_entry_ids": sorted(retired),
                "moved_payloads": [{"payload_object_id": item.payload_object_id, "payload_hash": item.payload_hash, "size_bytes": item.payload_size_bytes, "trash_token": "trash/" + plan["plan_id"] + "/sha256/" + item.payload_hash[7:9] + "/" + item.payload_hash[9:]} for item, _, _ in moved]}
        transaction = _transaction(body); _append_transaction(root, transaction); return transaction
    except BaseException:
        for _, source, target in reversed(moved):
            if target.is_file() and not source.exists(): os.replace(target, source)
        raise


def restore_cache_transaction(*, managed_root: Path, transaction: Mapping[str, Any], timestamp_utc: str) -> dict[str, Any]:
    body = {key: item for key, item in transaction.items() if key not in {"transaction_id", "transaction_hash"}}
    if transaction != _transaction(body) or body.get("kind") != "retired" or not timestamp_utc.endswith("Z"):
        raise ValueError("CACHE_RESTORE_INVALID")
    root = managed_root.resolve(strict=True); moved = []
    try:
        for item in body["moved_payloads"]:
            # The receipt's token is authoritative and still must stay in root.
            source = (root / ".trash" / item["trash_token"].removeprefix("trash/")).resolve()
            target = root / "sha256" / item["payload_hash"][7:9] / item["payload_hash"][9:]
            if root not in source.parents or target.exists() or not source.is_file() or "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest() != item["payload_hash"]:
                raise ValueError("CACHE_RESTORE_INVALID")
            target.parent.mkdir(parents=True, exist_ok=True); os.replace(source, target); moved.append((source, target))
        restored = _transaction({"schema_version": "CACHE-LIFECYCLE-TRANSACTION-V1", "kind": "restored", "receipt_transaction_hash": transaction["transaction_hash"], "timestamp_utc": timestamp_utc, "restored_entry_ids": body["retired_entry_ids"]})
        _append_transaction(root, restored)
        return restored
    except BaseException:
        for source, target in reversed(moved):
            if target.is_file() and not source.exists(): os.replace(target, source)
        raise
