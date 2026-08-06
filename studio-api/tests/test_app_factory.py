from __future__ import annotations

from fastapi.testclient import TestClient

from kurgu_studio_api import create_app


EXPECTED_METHODS = {
    "/api/v1/projects": {"get", "post"},
    "/api/v1/projects/{project_id}/status": {"get"},
    "/api/v1/projects/{project_id}/artifacts": {"get"},
    "/api/v1/projects/{project_id}/tasks": {"get", "post"},
    "/api/v1/projects/{project_id}/tasks/{task_id}": {"get"},
    "/api/v1/projects/{project_id}/tasks/{task_id}/response": {"post"},
    "/api/v1/projects/{project_id}/tasks/{task_id}/approve": {"post"},
    "/api/v1/projects/{project_id}/tasks/{task_id}/repair": {"post"},
    "/api/v1/projects/{project_id}/review-snapshots": {"post"},
    "/api/v1/projects/{project_id}/review": {"get"},
    "/api/v1/projects/{project_id}/review/sequences/{sequence_id}": {"get"},
    "/api/v1/projects/{project_id}/review/sequences/{sequence_id}/decision": {"post"},
    "/api/v1/projects/{project_id}/sequences/{sequence_id}/preview-renders": {"post"},
    "/api/v1/projects/{project_id}/preview-renders/{job_id}": {"get"},
    "/api/v1/projects/{project_id}/preview-renders/{job_id}/events": {"get"},
    "/api/v1/projects/{project_id}/preview-renders/{job_id}/events/stream": {"get"},
    "/api/v1/projects/{project_id}/preview-renders/{job_id}/manifest": {"get"},
    "/api/v1/projects/{project_id}/preview-renders/{job_id}/frames/{frame_index}": {"get"},
}


def test_factory_reopens_local_sqlite_project_across_fresh_apps(core_request: dict) -> None:
    first = TestClient(create_app())
    second = TestClient(create_app())
    created = first.post("/api/v1/projects", json=core_request)
    project_id = created.json()["project"]["project_id"]
    assert created.status_code == 201
    assert first.get(f"/api/v1/projects/{project_id}/status").status_code == 200
    assert second.get(f"/api/v1/projects/{project_id}/status").status_code == 200


def test_factory_exposes_only_deterministic_phase13_business_endpoints() -> None:
    first = create_app().openapi()
    second = create_app().openapi()
    assert first == second
    assert {
        path: set(item)
        for path, item in first["paths"].items()
    } == EXPECTED_METHODS
    assert [
        first["paths"][path][method]["operationId"]
        for path in sorted(EXPECTED_METHODS)
        for method in sorted(EXPECTED_METHODS[path])
    ] == [
        first["paths"][path][method]["operationId"]
        for path in sorted(EXPECTED_METHODS)
        for method in sorted(EXPECTED_METHODS[path])
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
