from __future__ import annotations

from fastapi.testclient import TestClient

from kurgu_studio_api import create_app


EXPECTED_METHODS = {
    "/api/v1/projects": {"post"},
    "/api/v1/projects/{project_id}/status": {"get"},
    "/api/v1/projects/{project_id}/artifacts": {"get"},
}


def test_factory_returns_fresh_app_and_fresh_repository(core_request: dict) -> None:
    first = TestClient(create_app())
    second = TestClient(create_app())
    created = first.post("/api/v1/projects", json=core_request)
    project_id = created.json()["project"]["project_id"]
    assert created.status_code == 201
    assert first.get(f"/api/v1/projects/{project_id}/status").status_code == 200
    assert second.get(f"/api/v1/projects/{project_id}/status").status_code == 404


def test_factory_exposes_only_three_deterministic_business_endpoints() -> None:
    first = create_app().openapi()
    second = create_app().openapi()
    assert first == second
    assert {
        path: set(item)
        for path, item in first["paths"].items()
    } == EXPECTED_METHODS
    assert [
        first["paths"][path][method]["operationId"]
        for path, methods in EXPECTED_METHODS.items()
        for method in methods
    ] == [
        "createProject",
        "getProjectStatus",
        "listProjectArtifacts",
    ]
    assert "servers" not in first


def test_factory_has_no_public_docs_or_global_runtime() -> None:
    first = create_app()
    second = create_app()
    assert first.openapi_url is None
    assert first.docs_url is None
    assert first.redoc_url is None
    assert first.state.runtime is not second.state.runtime
    assert (
        first.state.runtime.project_repository
        is not second.state.runtime.project_repository
    )
