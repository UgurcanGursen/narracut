from __future__ import annotations

import json
import tomllib
from importlib.metadata import version
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from engine.contracts import (
    DomainPackError,
    DomainPackRegistry,
    DomainPolicyResolver,
    SchemaCatalog,
    WorkspaceLoader,
    policy_snapshot_hash,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
STUDIO_API_ROOT = REPO_ROOT / "studio-api"


def _pyproject_direct_pins() -> dict[str, str]:
    project = tomllib.loads((STUDIO_API_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    pins: dict[str, str] = {}
    for requirement in (
        *project["dependencies"],
        *project["optional-dependencies"]["test"],
    ):
        package, exact = requirement.split("==", 1)
        pins[package.split("[", 1)[0].lower()] = exact
    return pins


def _lock_pins() -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in (STUDIO_API_ROOT / "requirements.lock").read_text(encoding="utf-8").splitlines():
        if line.strip():
            package, exact = line.split("==", 1)
            pins[package.lower().replace("_", "-")] = exact
    return pins


def test_direct_dependency_versions_match_pyproject_and_lock() -> None:
    direct = _pyproject_direct_pins()
    locked = _lock_pins()
    assert set(direct).issubset(locked)
    for package, expected in direct.items():
        assert version(package) == expected
        assert locked[package] == expected
    assert "starlette" in locked
    assert version("starlette") == locked["starlette"]


def test_fastapi_testclient_runtime_smoke() -> None:
    app = FastAPI()

    @app.get("/toolchain-smoke")
    def toolchain_smoke() -> dict[str, str]:
        return {"status": "ok", "scope": "toolchain"}

    response = TestClient(app).get("/toolchain-smoke")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "scope": "toolchain"}


def test_public_engine_contract_imports_and_schema_smoke() -> None:
    catalog = SchemaCatalog(REPO_ROOT / "schema" / "v3")
    sample = json.loads(
        (REPO_ROOT / "samples" / "v3" / "minimal" / "workspace.json").read_text(
            encoding="utf-8"
        )
    )
    schema_result = catalog.validate(
        sample,
        "workspace.schema.json",
        "minimal/workspace.json",
    )
    assert schema_result.is_valid, schema_result.issues
    loaded = WorkspaceLoader(catalog).load(
        REPO_ROOT / "samples" / "v3" / "minimal" / "workspace.json"
    )
    assert loaded.validation.is_valid, loaded.validation.issues

    registry = DomainPackRegistry([REPO_ROOT / "domain-packs"], catalog)
    packs = registry.discover()
    assert {pack.manifest.domain_id for pack in packs}
    DomainPolicyResolver(catalog)
    assert issubclass(DomainPackError, RuntimeError)
    assert policy_snapshot_hash({"schema_version": "3.0.0"}).startswith("sha256:")
