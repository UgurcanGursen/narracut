"""Small fail-closed journal primitives for the Phase 4B render lifecycle.

This module deliberately does not discover artifacts or make a render succeed.
It only persists explicitly supplied, canonical rows after a complete prepare
journal exists.  It is the narrow file-backed seam used by the full-render
orchestrator; broader recovery/GC belongs to later work.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from engine.contracts._canonical_json import encode_canonical_json_bytes

from .full_render import FullRenderError, TARGET_RECORD_V1

REGISTRY_ROW_V1 = "FULL-RENDER-REGISTRY-ROW-V1"
TRANSACTION_V1 = "FULL-RENDER-TRANSACTION-V1"
ATTEMPT_MANIFEST_V1 = "FULL-ATTEMPT-MANIFEST-V1"
CLEANUP_REPORT_V1 = "FULL-CLEANUP-REPORT-V1"
TERMINAL_RECEIPT_V1 = "FULL-RENDER-TERMINAL-RECEIPT-V1"


def _canonical(value: Any) -> bytes:
    return encode_canonical_json_bytes(value)


def _sha(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _identity(prefix: str, value: dict[str, Any], *excluded: str) -> tuple[str, str]:
    projected = {key: item for key, item in value.items() if key not in excluded}
    digest = _sha(_canonical(projected))
    return prefix + digest[7:39], digest


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        return [json.loads(line) for line in path.read_bytes().splitlines() if line]
    except Exception as exc:
        raise FullRenderError("ARTIFACT_PERSIST_FAILED") from exc


def _append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("ab") as stream:
            stream.write(_canonical(row) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise FullRenderError("ARTIFACT_PERSIST_FAILED") from exc


class _RegistryLock:
    """Exclusive lockfile suitable for the single local REPLAY writer."""
    def __init__(self, project_root: Path) -> None:
        self._path = project_root / "artifacts" / ".phase4b-registry.lock"
        self._fd: int | None = None

    def __enter__(self) -> "_RegistryLock":
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._fd = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise FullRenderError("ARTIFACT_PERSIST_FAILED") from exc
        return self

    def __exit__(self, *_: object) -> None:
        if self._fd is not None:
            os.close(self._fd)
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass


def _validate_target(row: dict[str, Any]) -> None:
    required = {
        "schema_version", "output_target_id", "project_id", "sequence_id",
        "trusted_publish_relative_path", "locked", "approved",
        "current_output_artifact_id", "current_output_content_sha256",
        "replacement_policy", "revision", "previous_output_target_record_id",
        "previous_output_target_record_hash", "output_target_record_id",
        "output_target_record_hash",
    }
    if set(row) != required or row.get("schema_version") != TARGET_RECORD_V1:
        raise FullRenderError("ARTIFACT_PERSIST_FAILED")
    expected_id, expected_hash = _identity(
        "outr_", row, "output_target_record_id", "output_target_record_hash"
    )
    if (row.get("output_target_record_id"), row.get("output_target_record_hash")) != (expected_id, expected_hash):
        raise FullRenderError("ARTIFACT_PERSIST_FAILED")


def resolve_target_head(*, project_root: Path, output_target_id: str) -> dict[str, Any]:
    """Read and validate one linear append-only target family."""
    path = project_root / "artifacts" / "output-targets.jsonl"
    if not path.is_file():
        raise FullRenderError("OUTPUT_TARGET_CONFLICT")
    rows = [row for row in _read_jsonl(path) if row.get("output_target_id") == output_target_id]
    if not rows:
        raise FullRenderError("OUTPUT_TARGET_CONFLICT")
    previous: dict[str, Any] | None = None
    for expected_revision, row in enumerate(rows, start=1):
        _validate_target(row)
        if row["revision"] != expected_revision:
            raise FullRenderError("ARTIFACT_PERSIST_FAILED")
        if previous is None:
            if row["previous_output_target_record_id"] is not None or row["previous_output_target_record_hash"] is not None:
                raise FullRenderError("ARTIFACT_PERSIST_FAILED")
        elif (row["previous_output_target_record_id"], row["previous_output_target_record_hash"], row["locked"], row["approved"]) != (
            previous["output_target_record_id"], previous["output_target_record_hash"], previous["locked"], previous["approved"]
        ):
            raise FullRenderError("ARTIFACT_PERSIST_FAILED")
        previous = row
    assert previous is not None
    return previous


def next_target_revision(*, base: dict[str, Any], output_artifact_id: str | None,
                         output_content_sha256: str | None,
                         replacement_policy: str | None) -> dict[str, Any]:
    """Create (but never append) the sole valid next target revision."""
    _validate_target(base)
    if (output_artifact_id is None) != (output_content_sha256 is None):
        raise FullRenderError("OVERWRITE_POLICY_INVALID")
    if output_artifact_id is not None and replacement_policy not in {None, "REPLACE_UNAPPROVED_V1"}:
        raise FullRenderError("OVERWRITE_POLICY_INVALID")
    if base["current_output_artifact_id"] is not None and replacement_policy != "REPLACE_UNAPPROVED_V1":
        raise FullRenderError("OVERWRITE_POLICY_INVALID")
    row = {
        **{key: base[key] for key in ("output_target_id", "project_id", "sequence_id", "trusted_publish_relative_path", "locked", "approved")},
        "schema_version": TARGET_RECORD_V1,
        "current_output_artifact_id": output_artifact_id,
        "current_output_content_sha256": output_content_sha256,
        "replacement_policy": replacement_policy,
        "revision": base["revision"] + 1,
        "previous_output_target_record_id": base["output_target_record_id"],
        "previous_output_target_record_hash": base["output_target_record_hash"],
        "output_target_record_id": "", "output_target_record_hash": "",
    }
    identity, digest = _identity("outr_", row, "output_target_record_id", "output_target_record_hash")
    return row | {"output_target_record_id": identity, "output_target_record_hash": digest}


@dataclass(frozen=True)
class AttemptManifest:
    attempt_id: str
    cleanup_state: str
    files: tuple[dict[str, Any], ...]
    manifest_id: str
    manifest_hash: str

    def row(self) -> dict[str, Any]:
        return {"schema_version": ATTEMPT_MANIFEST_V1, **asdict(self), "files": list(self.files)}


def snapshot_attempt(*, attempt_root: Path, attempt_id: str, cleanup_state: str,
                     retention_by_relative_path: dict[str, str] | None = None) -> AttemptManifest:
    """Exact, no-symlink inventory; callers cannot hide orphan attempt files."""
    if cleanup_state not in {"PRE_CLEANUP", "POST_CLEANUP"} or not attempt_root.is_dir():
        raise FullRenderError("ARTIFACT_PERSIST_FAILED")
    files: list[dict[str, Any]] = []
    for path in sorted(attempt_root.rglob("*"), key=lambda item: item.relative_to(attempt_root).as_posix()):
        if path.is_symlink():
            raise FullRenderError("ARTIFACT_PERSIST_FAILED")
        if not path.is_file():
            continue
        relative = path.relative_to(attempt_root).as_posix()
        raw = path.read_bytes()
        files.append({"relative_path": relative, "artifact_id": "art_attempt_" + hashlib.sha256(relative.encode()).hexdigest()[:32], "byte_length": len(raw), "content_sha256": _sha(raw), "retention_class": (retention_by_relative_path or {}).get(relative, "ephemeral")})
    base = {"schema_version": ATTEMPT_MANIFEST_V1, "attempt_id": attempt_id, "cleanup_state": cleanup_state, "files": files, "manifest_id": "", "manifest_hash": ""}
    ident, digest = _identity("atman_", base, "manifest_id", "manifest_hash")
    return AttemptManifest(attempt_id, cleanup_state, tuple(files), ident, digest)


def cleanup_attempt(*, attempt_root: Path, pre_cleanup: AttemptManifest) -> AttemptManifest:
    """Delete only inventory-listed ephemeral files and prove the remaining set."""
    if pre_cleanup.cleanup_state != "PRE_CLEANUP":
        raise FullRenderError("ARTIFACT_PERSIST_FAILED")
    observed = snapshot_attempt(attempt_root=attempt_root, attempt_id=pre_cleanup.attempt_id, cleanup_state="PRE_CLEANUP")
    if observed.files != pre_cleanup.files:
        raise FullRenderError("ARTIFACT_PERSIST_FAILED")
    for item in pre_cleanup.files:
        if item["retention_class"] == "ephemeral":
            (attempt_root / item["relative_path"]).unlink()
    for directory in sorted((item for item in attempt_root.rglob("*") if item.is_dir()), reverse=True):
        try: directory.rmdir()
        except OSError: pass
    return snapshot_attempt(attempt_root=attempt_root, attempt_id=pre_cleanup.attempt_id, cleanup_state="POST_CLEANUP")


def commit_transaction(*, project_root: Path, transaction_id: str, base_target: dict[str, Any],
                       target_revision: dict[str, Any] | None, artifact_rows: tuple[dict[str, Any], ...],
                       terminal_status: str, receipt_payload: dict[str, Any], pre_cleanup: AttemptManifest,
                       post_cleanup: AttemptManifest) -> dict[str, Any]:
    """Prepare then atomically append the bounded terminal journal evidence."""
    if terminal_status not in {"SUCCEEDED", "FAILED", "CANCELLED"}:
        raise FullRenderError("ARTIFACT_PERSIST_FAILED")
    _validate_target(base_target)
    if terminal_status != "SUCCEEDED" and target_revision is not None:
        raise FullRenderError("ARTIFACT_PERSIST_FAILED")
    if target_revision is not None:
        _validate_target(target_revision)
        if target_revision["previous_output_target_record_id"] != base_target["output_target_record_id"]:
            raise FullRenderError("ARTIFACT_PERSIST_FAILED")
    receipt = {"schema_version": TERMINAL_RECEIPT_V1, "transaction_id": transaction_id, "status": terminal_status, "pre_cleanup_manifest_id": pre_cleanup.manifest_id, "pre_cleanup_manifest_hash": pre_cleanup.manifest_hash, "post_cleanup_manifest_id": post_cleanup.manifest_id, "post_cleanup_manifest_hash": post_cleanup.manifest_hash, "payload": receipt_payload, "receipt_id": "", "receipt_hash": ""}
    receipt_id, receipt_hash = _identity("frrc_", receipt, "receipt_id", "receipt_hash")
    receipt |= {"receipt_id": receipt_id, "receipt_hash": receipt_hash}
    prepared = {"schema_version": TRANSACTION_V1, "transaction_id": transaction_id, "base_target_record_id": base_target["output_target_record_id"], "base_target_record_hash": base_target["output_target_record_hash"], "target_revision": target_revision, "artifact_rows": list(artifact_rows), "pre_cleanup": pre_cleanup.row(), "post_cleanup": post_cleanup.row(), "receipt": receipt}
    transaction_path = project_root / "artifacts" / "transactions" / f"{transaction_id}.json"
    transaction_path.parent.mkdir(parents=True, exist_ok=True)
    if transaction_path.exists():
        raise FullRenderError("ARTIFACT_PERSIST_FAILED")
    try:
        with transaction_path.open("xb") as stream:
            stream.write(_canonical(prepared)); stream.flush(); os.fsync(stream.fileno())
    except OSError as exc:
        raise FullRenderError("ARTIFACT_PERSIST_FAILED") from exc
    with _RegistryLock(project_root):
        current = resolve_target_head(project_root=project_root, output_target_id=base_target["output_target_id"])
        if (current["output_target_record_id"], current["output_target_record_hash"]) != (base_target["output_target_record_id"], base_target["output_target_record_hash"]):
            raise FullRenderError("OUTPUT_TARGET_CONFLICT")
        registry = project_root / "artifacts" / "registry.jsonl"
        for row in artifact_rows:
            _append(registry, row)
        _append(registry, pre_cleanup.row()); _append(registry, post_cleanup.row()); _append(registry, receipt)
        if target_revision is not None:
            _append(project_root / "artifacts" / "output-targets.jsonl", target_revision)
        _append(registry, {"schema_version": REGISTRY_ROW_V1, "transaction_id": transaction_id, "marker": "COMMITTED", "receipt_hash": receipt_hash})
    return receipt
