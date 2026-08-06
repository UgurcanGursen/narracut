"""Phase 14 durable, non-destructive artifact lifecycle planning."""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.artifacts import PROTECTED_RETENTION_CLASSES


def _sha(value: object) -> str:
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1_048_576), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _managed_artifact_path(root: Path, artifact_id: str) -> Path:
    if type(artifact_id) is not str or re.fullmatch(r"[a-z][a-z0-9_]*", artifact_id) is None:
        raise ValueError("LIFECYCLE_ARTIFACT_ID_INVALID")
    path = (root / artifact_id).resolve()
    if root not in path.parents:
        raise ValueError("LIFECYCLE_MANAGED_ROOT_ESCAPE")
    return path


def _receipt_path(root: Path) -> Path:
    return root / ".lifecycle" / "trash-receipts.jsonl"


def _append_receipt(*, root: Path, receipt: Mapping[str, Any]) -> None:
    path = _receipt_path(root); path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("ab") as stream:
            stream.write(encode_canonical_json_bytes(dict(receipt)) + b"\n")
            stream.flush(); os.fsync(stream.fileno())
    except OSError as exc:
        raise ValueError("LIFECYCLE_RECEIPT_PERSIST_FAILED") from exc


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
    visiting: set[str] = set(); visited: set[str] = set()
    def visit(identifier: str) -> None:
        if identifier in visiting: raise ValueError("ARTIFACT_REGISTRY_CYCLE")
        if identifier in visited: return
        visiting.add(identifier)
        for dependency in by_id[identifier].dependency_ids: visit(dependency)
        visiting.remove(identifier); visited.add(identifier)
    for identifier in by_id: visit(identifier)
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


def validate_deletion_plan(*, plan: Mapping[str, Any], records: tuple[ArtifactRegistryRecord, ...], policy_hash: str) -> None:
    body = {key: value for key, value in plan.items() if key not in {"plan_id", "plan_hash"}}
    plan_id, plan_hash = _identity("ldp_", body)
    if plan.get("plan_id") != plan_id or plan.get("plan_hash") != plan_hash: raise ValueError("LIFECYCLE_PLAN_IDENTITY_INVALID")
    if plan.get("policy_hash") != policy_hash or plan.get("registry_snapshot_hash") != registry_snapshot(records): raise ValueError("LIFECYCLE_PLAN_STALE")


def execute_trash_plan(*, managed_root: Path, plan: Mapping[str, Any], records: tuple[ArtifactRegistryRecord, ...], policy_hash: str) -> dict[str, Any]:
    validate_deletion_plan(plan=plan, records=records, policy_hash=policy_hash)
    root = managed_root.resolve(strict=True)
    prepared: list[tuple[Mapping[str, Any], Path, Path]] = []
    for candidate in plan["candidates"]:
        source = _managed_artifact_path(root, candidate["artifact_id"])
        if not source.is_file() or _file_sha(source) != candidate["content_hash"]:
            raise ValueError("LIFECYCLE_TRASH_SOURCE_INVALID")
        target = (root / ".trash" / plan["plan_id"] / candidate["artifact_id"]).resolve()
        if root not in target.parents:
            raise ValueError("LIFECYCLE_MANAGED_ROOT_ESCAPE")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists(): raise ValueError("LIFECYCLE_TRASH_COLLISION")
        prepared.append((candidate, source, target))
    moved: list[dict[str, Any]] = []
    try:
        for candidate, source, target in prepared:
            os.replace(source, target)
            moved.append({"artifact_id": candidate["artifact_id"], "trash_token": candidate["trash_token"], "content_hash": candidate["content_hash"], "size_bytes": candidate["size_bytes"]})
        body = {"schema_version":"LIFECYCLE-TRASH-RECEIPT-V1","plan_hash":plan["plan_hash"],"moved":moved}
        receipt_id, receipt_hash = _identity("ltr_", body)
        receipt = {"receipt_id":receipt_id,"receipt_hash":receipt_hash,**body}
        _append_receipt(root=root, receipt=receipt)
        return receipt
    except BaseException:
        # A receipt is not emitted until every move is durable.  If a later
        # move or receipt write fails, restore only entries moved in this call.
        for item in reversed(moved):
            source = root / ".trash" / plan["plan_id"] / item["artifact_id"]
            target = _managed_artifact_path(root, item["artifact_id"])
            if source.is_file() and not target.exists():
                os.replace(source, target)
        raise


def restore_trash_receipt(*, managed_root: Path, plan_id: str, receipt: Mapping[str, Any]) -> None:
    body = {key: value for key, value in receipt.items() if key not in {"receipt_id", "receipt_hash"}}
    receipt_id, receipt_hash = _identity("ltr_", body)
    if receipt.get("receipt_id") != receipt_id or receipt.get("receipt_hash") != receipt_hash: raise ValueError("LIFECYCLE_RECEIPT_INVALID")
    root = managed_root.resolve(strict=True)
    for item in receipt["moved"]:
        source = (root / ".trash" / plan_id / item["artifact_id"]).resolve(); target = _managed_artifact_path(root, item["artifact_id"])
        if root not in source.parents or not source.is_file() or target.exists() or _file_sha(source) != item.get("content_hash"):
            raise ValueError("LIFECYCLE_RESTORE_INVALID")
        os.replace(source, target)


def append_registry_record(*, registry_path: Path, record: ArtifactRegistryRecord) -> None:
    """Durably append a verified record; never writes content or deletes files."""
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_registry(registry_path=registry_path)
    if any(item.artifact_id == record.artifact_id for item in existing):
        raise ValueError("ARTIFACT_REGISTRY_DUPLICATE")
    payload = {**record.__dict__}
    try:
        with registry_path.open("ab") as stream:
            stream.write(encode_canonical_json_bytes(payload) + b"\n")
            stream.flush(); os.fsync(stream.fileno())
    except OSError as exc:
        raise ValueError("ARTIFACT_REGISTRY_PERSIST_FAILED") from exc


def append_registry_records(*, registry_path: Path, records: tuple[ArtifactRegistryRecord, ...]) -> None:
    """Idempotently persist a verified batch, rejecting identity drift.

    Renderer attempts repeat their immutable input nodes.  An exact existing
    record is therefore safe to reuse, while an ID with different immutable
    identity is always a hard failure.
    """
    existing = {item.artifact_id: item for item in load_registry(registry_path=registry_path)}
    pending: dict[str, ArtifactRegistryRecord] = {}
    for record in records:
        prior = existing.get(record.artifact_id)
        if prior is not None and prior != record:
            raise ValueError("ARTIFACT_REGISTRY_IDENTITY_CONFLICT")
        if record.artifact_id in pending and pending[record.artifact_id] != record:
            raise ValueError("ARTIFACT_REGISTRY_IDENTITY_CONFLICT")
        if prior is None:
            pending[record.artifact_id] = record
    registry_snapshot(tuple(existing.values()) + tuple(pending.values()))
    # Do not assume a producer happened to yield a topological ordering.  Each
    # append remains durable, while this loop admits a node only after all of
    # its dependencies are already registered.
    while pending:
        ready = [record for record in pending.values()
                 if all(dependency in existing for dependency in record.dependency_ids)]
        if not ready:
            raise ValueError("ARTIFACT_REGISTRY_DEPENDENCY_INVALID")
        for record in sorted(ready, key=lambda row: row.artifact_id):
            append_registry_record(registry_path=registry_path, record=record)
            existing[record.artifact_id] = record
            del pending[record.artifact_id]


def load_registry(*, registry_path: Path) -> tuple[ArtifactRegistryRecord, ...]:
    if not registry_path.exists(): return ()
    try:
        rows = tuple(ArtifactRegistryRecord.materialize(json.loads(line)) for line in registry_path.read_bytes().splitlines() if line)
        registry_snapshot(rows)
        return rows
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("ARTIFACT_REGISTRY_PERSIST_INVALID") from exc


def import_verified_artifact_rows(rows: tuple[Mapping[str, Any], ...]) -> tuple[ArtifactRegistryRecord, ...]:
    records = tuple(ArtifactRegistryRecord.materialize({key: row[key] for key in ("artifact_id","project_id","content_hash","size_bytes","retention_class","dependency_ids","locked","pinned","approved","producer","producer_version")}) for row in rows)
    registry_snapshot(records)
    return records
