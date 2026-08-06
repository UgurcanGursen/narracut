"""Phase 14 deterministic cache identity and read-only storage reporting."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
from engine.contracts._canonical_json import encode_canonical_json_bytes

def cache_key(*, profile: str, inputs: dict) -> str:
    if profile not in {"preview", "production"}: raise ValueError("CACHE_PROFILE_INVALID")
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes({"profile":profile,"inputs":inputs})).hexdigest()

def storage_usage(root: Path) -> dict[str, int]:
    resolved = root.resolve(strict=True)
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

def cache_put(root: Path, key: str, payload: bytes) -> Path:
    if not key.startswith("sha256:"): raise ValueError("CACHE_KEY_INVALID")
    target = root / "sha256" / key[7:9] / key[9:]
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_bytes() != payload: raise ValueError("CACHE_COLLISION")
    temporary = target.with_suffix(".staging")
    with temporary.open("xb") as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, target); return target

def cache_get(root: Path, key: str) -> bytes | None:
    target = root / "sha256" / key[7:9] / key[9:]
    return target.read_bytes() if target.is_file() else None

def incremental_action(*, previous_key: str | None, current_key: str) -> str:
    if not current_key.startswith("sha256:"): raise ValueError("CACHE_KEY_INVALID")
    return "REUSE" if previous_key == current_key else "REBUILD"
