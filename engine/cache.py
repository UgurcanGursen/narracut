"""Phase 14 deterministic cache identity and read-only storage reporting."""
from __future__ import annotations
import hashlib
from pathlib import Path
from engine.contracts._canonical_json import encode_canonical_json_bytes

def cache_key(*, profile: str, inputs: dict) -> str:
    if profile not in {"preview", "production"}: raise ValueError("CACHE_PROFILE_INVALID")
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes({"profile":profile,"inputs":inputs})).hexdigest()

def storage_usage(root: Path) -> dict[str, int]:
    resolved = root.resolve(strict=True)
    return {"file_count":sum(1 for item in resolved.rglob("*") if item.is_file()),"bytes":sum(item.stat().st_size for item in resolved.rglob("*") if item.is_file())}
