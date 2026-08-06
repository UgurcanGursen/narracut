"""Phase 14 deterministic cache identity and read-only storage reporting."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from dataclasses import dataclass
from engine.contracts._canonical_json import encode_canonical_json_bytes


@dataclass(frozen=True)
class CacheEntry:
    key: str
    payload: bytes
    payload_hash: str

def cache_key(*, profile: str, inputs: dict) -> str:
    if profile not in {"preview", "production"}: raise ValueError("CACHE_PROFILE_INVALID")
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes({"profile":profile,"inputs":inputs})).hexdigest()

def storage_usage(root: Path) -> dict[str, int]:
    if not isinstance(root, Path): raise ValueError("STORAGE_ROOT_INVALID")
    resolved = root.resolve()
    if not resolved.exists(): return {"file_count": 0, "bytes": 0}
    if not resolved.is_dir(): raise ValueError("STORAGE_ROOT_INVALID")
    return {"file_count":sum(1 for item in resolved.rglob("*") if item.is_file()),"bytes":sum(item.stat().st_size for item in resolved.rglob("*") if item.is_file())}

def quota_status(*, used_bytes: int, soft_limit_bytes: int, hard_limit_bytes: int) -> str:
    if not 0 <= soft_limit_bytes <= hard_limit_bytes or used_bytes < 0: raise ValueError("QUOTA_POLICY_INVALID")
    return "HARD_LIMIT" if used_bytes >= hard_limit_bytes else "SOFT_LIMIT" if used_bytes >= soft_limit_bytes else "OK"

def render_admission(*, used_bytes: int, estimated_bytes: int, hard_limit_bytes: int) -> str:
    if min(used_bytes, estimated_bytes, hard_limit_bytes) < 0: raise ValueError("QUOTA_POLICY_INVALID")
    return "BLOCKED_HARD_QUOTA" if used_bytes + estimated_bytes > hard_limit_bytes else "ADMITTED"

def performance_receipt(*, baseline_hash: str, candidate_hash: str, baseline_ms: int, candidate_ms: int) -> dict[str, object]:
    if min(baseline_ms, candidate_ms) < 0 or not baseline_hash.startswith("sha256:") or not candidate_hash.startswith("sha256:"): raise ValueError("PERFORMANCE_RECEIPT_INVALID")
    return {"quality_preserved": baseline_hash == candidate_hash, "improved": candidate_ms <= baseline_ms, "baseline_ms":baseline_ms,"candidate_ms":candidate_ms}

def _target(root: Path, key: str) -> Path:
    if type(key) is not str or not key.startswith("sha256:") or len(key) != 71:
        raise ValueError("CACHE_KEY_INVALID")
    return root / "sha256" / key[7:9] / key[9:]


def _metadata_target(target: Path) -> Path:
    return target.with_name(target.name + ".metadata.json")


def _write_atomic(target: Path, payload: bytes) -> None:
    """Atomically install one private file; clean staging on every failure."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(mode="xb", dir=target.parent, prefix=".staging-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def cache_put(root: Path, key: str, payload: bytes) -> CacheEntry:
    target = _target(root, key)
    if type(payload) is not bytes: raise ValueError("CACHE_PAYLOAD_INVALID")
    payload_hash = "sha256:" + hashlib.sha256(payload).hexdigest()
    metadata = encode_canonical_json_bytes({"cache_key": key, "payload_hash": payload_hash})
    metadata_target = _metadata_target(target)
    if target.exists() or metadata_target.exists():
        existing = cache_get(root, key)
        if existing is None or existing.payload != payload:
            raise ValueError("CACHE_COLLISION")
        return existing
    _write_atomic(target, payload)
    try:
        _write_atomic(metadata_target, metadata)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return CacheEntry(key=key, payload=payload, payload_hash=payload_hash)

def cache_get(root: Path, key: str) -> CacheEntry | None:
    target = _target(root, key); metadata_target = _metadata_target(target)
    if not target.exists() and not metadata_target.exists(): return None
    if not target.is_file() or not metadata_target.is_file():
        raise ValueError("CACHE_ENTRY_INVALID")
    try:
        metadata = json.loads(metadata_target.read_bytes().decode("utf-8"))
        payload = target.read_bytes()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("CACHE_ENTRY_INVALID") from exc
    payload_hash = "sha256:" + hashlib.sha256(payload).hexdigest()
    if metadata != {"cache_key": key, "payload_hash": payload_hash}:
        raise ValueError("CACHE_ENTRY_INVALID")
    return CacheEntry(key=key, payload=payload, payload_hash=payload_hash)

def incremental_action(*, previous_key: str | None, current_key: str) -> str:
    if not current_key.startswith("sha256:"): raise ValueError("CACHE_KEY_INVALID")
    return "REUSE" if previous_key == current_key else "REBUILD"
