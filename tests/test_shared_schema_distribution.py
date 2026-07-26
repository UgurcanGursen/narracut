from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterator

import pytest
from jsonschema import Draft202012Validator

from engine.contracts import SchemaCatalog
from scripts import sync_shared_schemas as sync


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = REPO_ROOT / "schema" / "v3"
DISTRIBUTION_ROOT = REPO_ROOT / "shared-schemas" / "v3"
MANIFEST_PATH = REPO_ROOT / "shared-schemas" / "manifest.json"
PACKAGE_PATH = REPO_ROOT / "shared-schemas" / "package.json"
EXPECTED_SCHEMA_COUNT = 16
EXPECTED_REF_COUNT = 159


def _schema_paths(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(root.glob("*.schema.json"), key=lambda path: path.name))


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk_refs(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        if "$ref" in value:
            yield value["$ref"]
        for nested in value.values():
            yield from _walk_refs(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_refs(nested)


def _resolve_json_pointer(value: Any, fragment: str) -> Any:
    if not fragment:
        return value
    assert fragment.startswith("/")
    current = value
    for raw_part in fragment[1:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current


def _assert_ref_inventory_resolves(root: Path) -> int:
    documents = {path.name: _load(path) for path in _schema_paths(root)}
    count = 0
    for schema_name, document in documents.items():
        for reference in _walk_refs(document):
            count += 1
            target_name, separator, fragment = reference.partition("#")
            assert not target_name.startswith(("http://", "https://"))
            target = documents[target_name or schema_name]
            if separator:
                _resolve_json_pointer(target, fragment)
    return count


def test_canonical_and_distribution_inventory_are_exact() -> None:
    canonical = _schema_paths(CANONICAL_ROOT)
    distributed = _schema_paths(DISTRIBUTION_ROOT)
    assert len(canonical) == EXPECTED_SCHEMA_COUNT
    assert [path.name for path in canonical] == [path.name for path in distributed]
    assert all(
        source.read_bytes() == output.read_bytes()
        for source, output in zip(canonical, distributed, strict=True)
    )


def test_manifest_is_deterministic_complete_and_path_independent() -> None:
    manifest_bytes = MANIFEST_PATH.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    assert manifest["format_version"] == 1
    assert manifest["canonical_source"] == "schema/v3"
    assert manifest["distribution_root"] == "shared-schemas/v3"
    assert manifest["schema_count"] == EXPECTED_SCHEMA_COUNT
    entries = manifest["schemas"]
    assert [entry["name"] for entry in entries] == sorted(
        entry["name"] for entry in entries
    )
    assert len({entry["name"] for entry in entries}) == EXPECTED_SCHEMA_COUNT
    assert len({entry["schema_id"] for entry in entries}) == EXPECTED_SCHEMA_COUNT
    assert not re.search(rb"(?<![A-Za-z0-9])[A-Za-z]:[\\/]", manifest_bytes)
    assert b"generated_at" not in manifest_bytes
    assert b"timestamp" not in manifest_bytes
    assert not manifest_bytes.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in manifest_bytes
    assert manifest_bytes.endswith(b"\n")

    for entry in entries:
        canonical = REPO_ROOT / entry["canonical_path"]
        distributed = REPO_ROOT / entry["distribution_path"]
        canonical_value = _load(canonical)
        distributed_value = _load(distributed)
        digest = hashlib.sha256(canonical.read_bytes()).hexdigest()
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
        assert entry["sha256"] == digest
        assert canonical.read_bytes() == distributed.read_bytes()
        assert entry["schema_id"] == canonical_value["$id"]
        assert distributed_value["$id"] == canonical_value["$id"]
        assert list(_walk_refs(distributed_value)) == list(
            _walk_refs(canonical_value)
        )


def test_all_canonical_and_distributed_schemas_are_valid_and_refs_resolve() -> None:
    for root in (CANONICAL_ROOT, DISTRIBUTION_ROOT):
        for path in _schema_paths(root):
            Draft202012Validator.check_schema(_load(path))
        assert _assert_ref_inventory_resolves(root) == EXPECTED_REF_COUNT


def test_schema_catalog_remains_bound_to_canonical_root() -> None:
    catalog = SchemaCatalog(CANONICAL_ROOT)
    assert catalog.schema_root == CANONICAL_ROOT.resolve()
    assert catalog.schema_names == tuple(
        path.name for path in _schema_paths(CANONICAL_ROOT)
    )
    assert catalog.schema_root != DISTRIBUTION_ROOT.resolve()


def test_shared_package_exports_are_stable_and_dependency_free() -> None:
    package = _load(PACKAGE_PATH)
    assert package["name"] == "@kurgu/shared-schemas"
    assert package["private"] is True
    assert package["exports"] == {
        "./manifest.json": "./manifest.json",
        "./openapi/openapi.json": "./openapi/openapi.json",
        "./v3/*": "./v3/*",
    }
    assert "dependencies" not in package
    assert "devDependencies" not in package


def test_real_sync_check_command_is_read_only_and_passes() -> None:
    before = {
        path.relative_to(REPO_ROOT): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (
            *DISTRIBUTION_ROOT.glob("*"),
            MANIFEST_PATH,
        )
        if path.is_file()
    }
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-B", str(REPO_ROOT / "scripts" / "sync_shared_schemas.py"), "--check"],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"status": "PASS"' in result.stdout
    after = {
        path.relative_to(REPO_ROOT): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (
            *DISTRIBUTION_ROOT.glob("*"),
            MANIFEST_PATH,
        )
        if path.is_file()
    }
    assert after == before


@pytest.mark.parametrize("drift_kind", ["missing", "extra", "modified"])
def test_check_detects_isolated_schema_drift(
    tmp_path: Path, drift_kind: str
) -> None:
    canonical = tmp_path / "schema" / "v3"
    distributed = tmp_path / "shared-schemas" / "v3"
    manifest = tmp_path / "shared-schemas" / "manifest.json"
    shutil.copytree(CANONICAL_ROOT, canonical)
    shutil.copytree(DISTRIBUTION_ROOT, distributed)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MANIFEST_PATH, manifest)

    target = distributed / "artifact.schema.json"
    if drift_kind == "missing":
        target.unlink()
    elif drift_kind == "extra":
        (distributed / "stale.schema.json").write_bytes(b"{}\n")
    else:
        target.write_bytes(target.read_bytes() + b" ")

    with pytest.raises(sync.DistributionError):
        sync.check_distribution(canonical, distributed, manifest)


def test_check_detects_isolated_manifest_drift(tmp_path: Path) -> None:
    canonical = tmp_path / "schema" / "v3"
    distributed = tmp_path / "shared-schemas" / "v3"
    manifest = tmp_path / "shared-schemas" / "manifest.json"
    shutil.copytree(CANONICAL_ROOT, canonical)
    shutil.copytree(DISTRIBUTION_ROOT, distributed)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MANIFEST_PATH, manifest)
    value = _load(manifest)
    value["schema_count"] = 0
    manifest.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(sync.DistributionError):
        sync.check_distribution(canonical, distributed, manifest)


def test_write_fails_closed_without_deleting_stale_output(tmp_path: Path) -> None:
    canonical = tmp_path / "schema" / "v3"
    distributed = tmp_path / "shared-schemas" / "v3"
    manifest = tmp_path / "shared-schemas" / "manifest.json"
    shutil.copytree(CANONICAL_ROOT, canonical)
    shutil.copytree(DISTRIBUTION_ROOT, distributed)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MANIFEST_PATH, manifest)
    stale = distributed / "stale.schema.json"
    stale.write_bytes(b"{}\n")

    with pytest.raises(sync.DistributionError):
        sync.write_distribution(canonical, distributed, manifest)
    assert stale.read_bytes() == b"{}\n"
