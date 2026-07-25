"""Declarative domain-pack discovery and deterministic policy resolution."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .models import (
    DomainPackManifest,
    DomainPolicySnapshot,
    DomainProfile,
)
from .paths import resolve_relative
from .validation import SchemaCatalog, ValidationIssue


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: Any) -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def policy_snapshot_hash(snapshot_data: Mapping[str, Any]) -> str:
    payload = {
        key: value
        for key, value in snapshot_data.items()
        if key not in {"snapshot_id", "canonical_hash"}
    }
    return _sha256(payload)


class DomainPackError(RuntimeError):
    def __init__(self, message: str, issues: tuple[ValidationIssue, ...] = ()):
        super().__init__(message)
        self.issues = issues


@dataclass(frozen=True)
class DomainPack:
    manifest: DomainPackManifest
    raw_manifest: Mapping[str, Any]
    pack_dir: Path


class DomainPackRegistry:
    """Fail-closed registry for JSON-only domain packs."""

    def __init__(
        self,
        roots: tuple[Path | str, ...] | list[Path | str],
        catalog: SchemaCatalog,
    ):
        self.roots = tuple(Path(root).resolve() for root in roots)
        self.catalog = catalog
        self._packs: dict[tuple[str, str], DomainPack] = {}

    def discover(self) -> tuple[DomainPack, ...]:
        discovered: dict[tuple[str, str], DomainPack] = {}
        manifest_paths = sorted(
            {
                path.resolve()
                for root in self.roots
                for path in root.rglob("manifest.json")
            },
            key=lambda path: path.as_posix(),
        )

        for manifest_path in manifest_paths:
            containing_roots = [
                root for root in self.roots if manifest_path.is_relative_to(root)
            ]
            if not containing_roots:
                raise DomainPackError(
                    f"Manifest escapes configured roots: {manifest_path}"
                )
            try:
                raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                issue = ValidationIssue(
                    str(manifest_path), "", "DOMAIN_MANIFEST_READ_ERROR", str(exc)
                )
                raise DomainPackError(str(exc), (issue,)) from exc

            result = self.catalog.validate(
                raw, "domain_pack.schema.json", manifest_path
            )
            if not result.is_valid:
                raise DomainPackError(
                    f"Invalid domain manifest: {manifest_path}", result.issues
                )

            model = DomainPackManifest.from_dict(raw)
            key = (model.domain_id, model.domain_pack_version)
            if key in discovered:
                issue = ValidationIssue(
                    str(manifest_path),
                    "",
                    "DOMAIN_DUPLICATE_VERSION",
                    f"Duplicate domain/version: {key[0]} {key[1]}",
                )
                raise DomainPackError(issue.message, (issue,))

            pack_dir = manifest_path.parent
            for raw_ref in (
                *model.policy_bundle_refs,
                *model.prompt_bundle_refs,
            ):
                try:
                    referenced = resolve_relative(pack_dir, raw_ref)
                except ValueError as exc:
                    issue = ValidationIssue(
                        str(manifest_path),
                        "",
                        "DOMAIN_PATH_TRAVERSAL",
                        str(exc),
                    )
                    raise DomainPackError(str(exc), (issue,)) from exc
                if not referenced.is_file():
                    issue = ValidationIssue(
                        str(manifest_path),
                        "",
                        "DOMAIN_MISSING_BUNDLE",
                        f"Referenced bundle does not exist: {raw_ref}",
                    )
                    raise DomainPackError(issue.message, (issue,))

            discovered[key] = DomainPack(model, raw, pack_dir)

        self._packs = dict(sorted(discovered.items()))
        return tuple(self._packs.values())

    def get(self, domain_id: str, version: str) -> DomainPack:
        try:
            return self._packs[(domain_id, version)]
        except KeyError as exc:
            issue = ValidationIssue(
                "<domain-registry>",
                "",
                "DOMAIN_UNKNOWN",
                f"Unknown domain/version: {domain_id} {version}",
            )
            raise DomainPackError(issue.message, (issue,)) from exc


class DomainPolicyResolver:
    """Resolves JSON policy bundles into a reproducible immutable snapshot."""

    def __init__(self, catalog: SchemaCatalog):
        self.catalog = catalog

    def resolve(
        self,
        pack: DomainPack,
        profile_data: Mapping[str, Any],
    ) -> tuple[DomainPolicySnapshot, dict[str, Any]]:
        result = self.catalog.validate(
            profile_data,
            "domain_profile.schema.json",
            "<domain-profile>",
        )
        if not result.is_valid:
            raise DomainPackError("Invalid domain profile", result.issues)

        profile = DomainProfile.from_dict(profile_data)
        manifest = pack.manifest
        if (
            profile.domain_id != manifest.domain_id
            or profile.domain_pack_version != manifest.domain_pack_version
        ):
            issue = ValidationIssue(
                "<domain-profile>",
                "",
                "DOMAIN_PROFILE_MISMATCH",
                "Profile domain_id/version does not match the selected pack.",
            )
            raise DomainPackError(issue.message, (issue,))

        bundles = []
        for raw_ref in sorted(manifest.policy_bundle_refs):
            try:
                path = resolve_relative(pack.pack_dir, raw_ref)
                bundle = json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, OSError, json.JSONDecodeError) as exc:
                issue = ValidationIssue(
                    str(pack.pack_dir / raw_ref),
                    "",
                    "DOMAIN_POLICY_READ_ERROR",
                    str(exc),
                )
                raise DomainPackError(str(exc), (issue,)) from exc
            if not isinstance(bundle, dict):
                issue = ValidationIssue(
                    str(path),
                    "",
                    "DOMAIN_POLICY_TYPE",
                    "Policy bundle root must be an object.",
                )
                raise DomainPackError(issue.message, (issue,))
            bundles.append({"ref": raw_ref, "policy": bundle})

        resolved_policy = {
            "policy_bundles": bundles,
            "extensions": pack.raw_manifest["extensions"],
            "enabled_extensions": list(profile_data["enabled_extensions"]),
            "overrides": profile_data["policy_overrides"],
        }
        manifest_hash = _sha256(pack.raw_manifest)
        hash_payload = {
            "schema_version": "3.0.0",
            "domain_id": manifest.domain_id,
            "domain_pack_version": manifest.domain_pack_version,
            "profile_id": profile.profile_id,
            "manifest_hash": manifest_hash,
            "resolved_policy": resolved_policy,
            "immutable": True,
            "created_at": manifest.published_at,
            "version": 1,
        }
        canonical_hash = policy_snapshot_hash(hash_payload)
        snapshot_data = {
            **hash_payload,
            "snapshot_id": "dps_" + canonical_hash.removeprefix("sha256:")[:20],
            "canonical_hash": canonical_hash,
        }
        snapshot_result = self.catalog.validate(
            snapshot_data,
            "domain_policy_snapshot.schema.json",
            "<resolved-domain-policy>",
        )
        if not snapshot_result.is_valid:
            raise DomainPackError(
                "Resolved policy snapshot is invalid", snapshot_result.issues
            )
        return DomainPolicySnapshot.from_dict(snapshot_data), snapshot_data
