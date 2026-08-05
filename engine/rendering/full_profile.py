"""Closed, checked-in Phase 4B render-profile admission boundary.

This loader intentionally validates catalogue and provenance *before* an
attempt directory or a child process exists.  It does not discover runtimes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from engine.contracts._canonical_json import encode_canonical_json_bytes
from .full_render import FullRenderError


def _sha(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _canonical(value: Any) -> bytes:
    return encode_canonical_json_bytes(value)


def _identity_hash(value: dict[str, Any]) -> str:
    return _sha(_canonical(value))


def default_profile_paths() -> tuple[Path, Path]:
    root = Path(__file__).resolve().parents[2]
    return (root / "renderer-remotion" / "profiles" / "full-render-profiles-v1.json",
            root / "tests" / "fixtures" / "phase4b" / "full-render-toolchain-provenance-v1.json")


def load_full_render_profile(*, profile_id: str, profile_hash: str,
                             catalog_path: Path | None = None,
                             provenance_path: Path | None = None) -> dict[str, Any]:
    """Resolve one exact checked-in profile, otherwise use one closed oracle."""
    catalog_path, provenance_path = (default_profile_paths() if catalog_path is None or provenance_path is None
                                     else (catalog_path, provenance_path))
    try:
        raw_catalog, raw_provenance = catalog_path.read_bytes(), provenance_path.read_bytes()
        catalog, provenance = json.loads(raw_catalog), json.loads(raw_provenance)
        if (raw_catalog not in {_canonical(catalog), _canonical(catalog) + b"\n"}
                or raw_provenance not in {_canonical(provenance), _canonical(provenance) + b"\n"}):
            raise ValueError
        if set(catalog) != {"schema_version", "profiles"} or catalog["schema_version"] != "FULL-RENDER-PROFILE-CATALOG-V1":
            raise ValueError
        profiles = catalog["profiles"]
        selected = [item for item in profiles if type(item) is dict and item.get("profile_id") == profile_id]
        if len(selected) != 1 or not isinstance(profile_hash, str):
            raise ValueError
        profile = selected[0]
        expected = _sha(_canonical({key: value for key, value in profile.items() if key not in {"profile_id", "profile_hash"}}))
        identity_keys = ("remotion_identity", "node_identity", "ffmpeg_identity", "ffprobe_identity")
        if profile.get("schema_version") != "FULL-RENDER-PROFILE-V1" or profile.get("profile_hash") != expected or expected != profile_hash:
            raise ValueError
        if any(type(profile.get(key)) is not dict for key in identity_keys):
            raise ValueError
        if (set(provenance) != {"schema_version", "provenance_fixture_id", "provenance_fixture_hash", "profile_catalog_sha256", "package_lock_sha256", "supported_platform", "runtime_trees"}
                or provenance.get("schema_version") != "FULL-RENDER-TOOLCHAIN-PROVENANCE-V1"
                or provenance.get("profile_catalog_sha256") != _sha(_canonical(catalog))
                or provenance.get("provenance_fixture_hash") != _sha(_canonical({key: value for key, value in provenance.items() if key not in {"provenance_fixture_id", "provenance_fixture_hash"}}))):
            raise ValueError
        rows = provenance["runtime_trees"]
        if type(rows) is not list or [row.get("kind") for row in rows if type(row) is dict] != ["node", "remotion", "ffmpeg", "ffprobe"]:
            raise ValueError
        for row, key in zip(rows, ("node_identity", "remotion_identity", "ffmpeg_identity", "ffprobe_identity"), strict=True):
            if row.get("identity_hash") != _identity_hash(profile[key]) or row.get("toolchain_root_relative_posix_path") != profile[key].get("toolchain_root_relative_posix_path"):
                raise ValueError
        return profile
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise FullRenderError("FULL_RENDER_PROFILE_INVALID") from exc


def profile_identity_hashes(profile: dict[str, Any]) -> dict[str, str]:
    return {
        "remotion_identity_hash": _identity_hash(profile["remotion_identity"]),
        "node_identity_hash": _identity_hash(profile["node_identity"]),
        "ffmpeg_identity_hash": _identity_hash(profile["ffmpeg_identity"]),
        "ffprobe_identity_hash": _identity_hash(profile["ffprobe_identity"]),
    }
