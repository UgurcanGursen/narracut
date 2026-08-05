"""Strict checked-in Phase 4A REPLAY fixture manifest resolver."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.contracts._canonical_json import encode_canonical_json_bytes


class FixtureAssetResolverError(ValueError):
    """Never includes a host path; callers map it to a public failure code."""

    def __init__(self, code: str, pointer: str) -> None:
        super().__init__(code)
        self.code, self.pointer = code, pointer


@dataclass(frozen=True)
class FixtureAsset:
    fixture_asset_id: str
    edl_source_ref: str
    relative_posix_path: str
    content_sha256: str
    media_type: str
    width: int
    height: int


@dataclass(frozen=True)
class FixtureAssetManifest:
    schema_version: str
    fixture_manifest_id: str
    fixture_manifest_hash: str
    assets: tuple[FixtureAsset, ...]
    visual_directives: tuple[Any, ...]


_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID = re.compile(r"^[\x21-\x7e]{1,160}$")
_ALLOWED_MEDIA = frozenset({"image/svg+xml", "image/png"})


def _failure(code: str, pointer: str) -> None:
    raise FixtureAssetResolverError(code, pointer)


def _hash(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _canonical_object(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes or raw.startswith(b"\xef\xbb\xbf"):
        _failure("ASSET_RESOLUTION_FAILED", "/")
    class Pairs(list):
        pass
    try:
        parsed = json.loads(raw.decode("utf-8"), object_pairs_hook=Pairs,
                            parse_float=lambda _: (_ for _ in ()).throw(ValueError()),
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except Exception:
        _failure("ASSET_RESOLUTION_FAILED", "/")
    def plain(value: Any) -> Any:
        if type(value) is Pairs:
            if len(value) != len({key for key, _ in value}):
                _failure("ASSET_RESOLUTION_FAILED", "/")
            return {key: plain(item) for key, item in value}
        if type(value) is list:
            return [plain(item) for item in value]
        if type(value) is float:
            _failure("ASSET_RESOLUTION_FAILED", "/")
        return value
    value = plain(parsed)
    # The public fixture envelope intentionally has its documented field order
    # (schema/id/hash/assets), while its identity projection uses shared
    # canonical JSON. Validate that shape in ``load``; do not re-order bytes.
    if type(value) is not dict:
        _failure("ASSET_RESOLUTION_FAILED", "/")
    return value


class FixtureAssetResolver:
    """Allowlist resolver. It deliberately has no discovery, cache, or fallback."""

    def __init__(self, fixture_root: Path, manifest: FixtureAssetManifest) -> None:
        self._root = fixture_root.resolve(strict=True)
        self.manifest = manifest
        self._by_source_ref = {row.edl_source_ref: row for row in manifest.assets}

    @classmethod
    def load(cls, fixture_root: Path, manifest_name: str = "fixture_asset_manifest.json") -> "FixtureAssetResolver":
        if not isinstance(fixture_root, Path) or type(manifest_name) is not str or "/" in manifest_name or "\\" in manifest_name:
            _failure("ASSET_RESOLUTION_FAILED", "/manifest")
        root = fixture_root.resolve(strict=True)
        raw = (root / manifest_name).read_bytes()
        value = _canonical_object(raw)
        fields = ("schema_version", "fixture_manifest_id", "fixture_manifest_hash", "assets", "visual_directives")
        if tuple(value) != fields or value.get("schema_version") != "FIXTURE-ASSET-MANIFEST-V1" or type(value["assets"]) is not list:
            _failure("ASSET_RESOLUTION_FAILED", "/")
        projection = {key: item for key, item in value.items() if key not in {"fixture_manifest_id", "fixture_manifest_hash"}}
        digest = _hash(encode_canonical_json_bytes(projection))
        if value["fixture_manifest_hash"] != digest or value["fixture_manifest_id"] != "fixman_" + digest[7:39]:
            _failure("ASSET_HASH_MISMATCH", "/")
        assets: list[FixtureAsset] = []
        seen_ids: set[str] = set(); seen_refs: set[str] = set(); seen_hashes: set[str] = set()
        row_fields = ("fixture_asset_id", "edl_source_ref", "relative_posix_path", "content_sha256", "media_type", "width", "height")
        for index, row in enumerate(value["assets"]):
            pointer = f"/assets/{index}"
            if type(row) is not dict or tuple(row) != row_fields or any(type(row[key]) is not str for key in row_fields[:5]) or any(type(row[key]) is not int or type(row[key]) is bool or row[key] < 1 for key in row_fields[5:]):
                _failure("ASSET_RESOLUTION_FAILED", pointer)
            if (not _ID.fullmatch(row["fixture_asset_id"]) or not _ID.fullmatch(row["edl_source_ref"]) or not _HASH.fullmatch(row["content_sha256"]) or row["media_type"] not in _ALLOWED_MEDIA or row["fixture_asset_id"] in seen_ids or row["edl_source_ref"] in seen_refs or row["content_sha256"] in seen_hashes):
                _failure("ASSET_RESOLUTION_FAILED", pointer)
            rel = row["relative_posix_path"]
            if not rel or "\\" in rel or ":" in rel or rel.startswith("/") or any(part in {"", ".", ".."} for part in rel.split("/")):
                _failure("ASSET_RESOLUTION_FAILED", pointer + "/relative_posix_path")
            target = (root.joinpath(*rel.split("/"))).resolve(strict=True)
            try:
                target.relative_to(root)
            except ValueError:
                _failure("ASSET_RESOLUTION_FAILED", pointer + "/relative_posix_path")
            if _hash(target.read_bytes()) != row["content_sha256"]:
                _failure("ASSET_HASH_MISMATCH", pointer)
            seen_ids.add(row["fixture_asset_id"]); seen_refs.add(row["edl_source_ref"]); seen_hashes.add(row["content_sha256"])
            assets.append(FixtureAsset(**row))
        if [item.fixture_asset_id for item in assets] != sorted(item.fixture_asset_id for item in assets):
            _failure("ASSET_RESOLUTION_FAILED", "/assets")
        from .visual_directives import validate_directive
        directives = tuple(validate_directive(row, f"/visual_directives/{index}") for index, row in enumerate(value["visual_directives"]))
        if [row.directive_id for row in directives] != sorted(row.directive_id for row in directives) or len({row.directive_id for row in directives}) != len(directives) or len({row.event_id for row in directives}) != len(directives):
            _failure("ASSET_RESOLUTION_FAILED", "/visual_directives")
        return cls(root, FixtureAssetManifest(value["schema_version"], value["fixture_manifest_id"], value["fixture_manifest_hash"], tuple(assets), directives))

    def resolve_source_ref(self, source_ref: str) -> FixtureAsset:
        if type(source_ref) is not str or source_ref not in self._by_source_ref:
            _failure("ASSET_RESOLUTION_FAILED", "/source_ref")
        asset = self._by_source_ref[source_ref]
        target = (self._root.joinpath(*asset.relative_posix_path.split("/"))).resolve(strict=True)
        try:
            target.relative_to(self._root)
        except ValueError:
            _failure("ASSET_RESOLUTION_FAILED", "/source_ref")
        if not target.is_file():
            _failure("ASSET_RESOLUTION_FAILED", "/source_ref")
        if _hash(target.read_bytes()) != asset.content_sha256:
            _failure("ASSET_HASH_MISMATCH", "/source_ref")
        return asset
