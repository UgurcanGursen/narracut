from __future__ import annotations

import json
import sys
import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
PYPROJECT = SCRIPT_PATH.parents[1] / "pyproject.toml"
LOCKFILE = SCRIPT_PATH.parents[1] / "requirements.lock"


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError as exc:
        raise AssertionError(f"missing package: {name}") from exc


def _pin_map() -> dict[str, str]:
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    pins: dict[str, str] = {}
    for requirement in (
        *project["dependencies"],
        *project["optional-dependencies"]["test"],
    ):
        package, exact = requirement.split("==", 1)
        pins[package.split("[", 1)[0].lower()] = exact
    return pins


def _lock_map() -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in LOCKFILE.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        package, exact = line.split("==", 1)
        pins[package.lower().replace("_", "-")] = exact
    return pins


def verify_versions() -> dict[str, str]:
    direct = _pin_map()
    locked = _lock_map()
    versions: dict[str, str] = {}
    for package, expected in sorted(direct.items()):
        installed = _package_version(package)
        assert installed == expected, f"{package}: {installed} != {expected}"
        assert locked[package] == expected, f"{package} missing from lock"
        versions[package] = installed
    for required in ("starlette", "jsonschema-specifications", "referencing"):
        versions[required] = _package_version(required)
        assert locked[required] == versions[required]
    return versions


def verify_fastapi_testclient() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.get("/toolchain-smoke")
    def toolchain_smoke() -> dict[str, str]:
        return {"status": "ok", "scope": "toolchain"}

    response = TestClient(app).get("/toolchain-smoke")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "scope": "toolchain"}


def verify_engine_contracts() -> tuple[str, ...]:
    sys.path.insert(0, str(REPO_ROOT))
    from engine.contracts import (
        DomainPackError,
        DomainPackRegistry,
        DomainPolicyResolver,
        SchemaCatalog,
        WorkspaceLoader,
        policy_snapshot_hash,
    )

    catalog = SchemaCatalog(REPO_ROOT / "schema" / "v3")
    assert "workspace.schema.json" in catalog.schema_names
    sample = json.loads(
        (REPO_ROOT / "samples" / "v3" / "minimal" / "workspace.json").read_text(
            encoding="utf-8"
        )
    )
    result = catalog.validate(sample, "workspace.schema.json", "minimal/workspace.json")
    assert result.is_valid, result.issues
    loaded = WorkspaceLoader(catalog).load(
        REPO_ROOT / "samples" / "v3" / "minimal" / "workspace.json"
    )
    assert loaded.validation.is_valid, loaded.validation.issues
    registry = DomainPackRegistry([REPO_ROOT / "domain-packs"], catalog)
    packs = registry.discover()
    assert packs
    DomainPolicyResolver(catalog)
    assert issubclass(DomainPackError, RuntimeError)
    assert policy_snapshot_hash({"schema_version": "3.0.0"}).startswith("sha256:")
    return tuple(sorted(f"{pack.manifest.domain_id}@{pack.manifest.domain_pack_version}" for pack in packs))


def main() -> int:
    try:
        versions = verify_versions()
        verify_fastapi_testclient()
        packs = verify_engine_contracts()
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "status": "PASS",
                "versions": versions,
                "domain_packs": packs,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
