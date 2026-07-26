from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from engine.contracts import SchemaCatalog

from conftest import FIXED_PROJECT_ID, FIXED_TIME, REPO_ROOT


def test_core_only_create_is_canonical_and_readable(
    client: TestClient,
    core_request: dict,
) -> None:
    response = client.post("/api/v1/projects", json=core_request)
    assert response.status_code == 201
    payload = response.json()
    assert payload["persistence_scope"] == "process_lifetime"
    assert payload["project"] == {
        "schema_version": "3.0.0",
        "project_id": FIXED_PROJECT_ID,
        "title": core_request["title"],
        "created_at": FIXED_TIME,
        "updated_at": FIXED_TIME,
        "domain_id": "core-generic",
        "domain_pack_version": "0.0.0",
        "policy_snapshot_id": payload["domain"]["policy_snapshot_id"],
        "status": "ready",
        "version": 1,
    }
    assert payload["domain"]["resolution_mode"] == "core_only"
    assert payload["domain"]["profile_id"] == "dpf_core_default"
    assert response.headers["location"] == (
        f"/api/v1/projects/{FIXED_PROJECT_ID}/status"
    )
    result = SchemaCatalog(REPO_ROOT / "schema" / "v3").validate(
        payload["project"],
        "project.schema.json",
        "<api-test>",
    )
    assert result.is_valid, result.issues


@pytest.mark.parametrize(
    "field,value",
    [
        ("project_id", "prj_client_controlled"),
        ("schema_version", "3.0.0"),
        ("status", "ready"),
        ("workspace_root", "C:/private"),
        ("output_dir", "../output"),
        ("path", "project.json"),
    ],
)
def test_client_controlled_server_or_path_fields_are_rejected(
    client: TestClient,
    core_request: dict,
    field: str,
    value: str,
) -> None:
    request = {**core_request, field: value}
    response = client.post("/api/v1/projects", json=request)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"


def test_core_only_rejects_domain_pack_fields(
    client: TestClient,
    core_request: dict,
) -> None:
    request = {
        **core_request,
        "domain": {
            **core_request["domain"],
            "domain_id": "business-tech",
        },
    }
    response = client.post("/api/v1/projects", json=request)
    assert response.status_code == 422


@pytest.mark.parametrize("title", ["", "x" * 241])
def test_title_uses_canonical_length_boundary(
    client: TestClient,
    core_request: dict,
    title: str,
) -> None:
    response = client.post(
        "/api/v1/projects",
        json={**core_request, "title": title},
    )
    assert response.status_code == 422


def test_invalid_resolution_mode_is_fail_closed(
    client: TestClient,
    core_request: dict,
) -> None:
    request = {
        **core_request,
        "domain": {"resolution_mode": "automatic"},
    }
    response = client.post("/api/v1/projects", json=request)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"


def test_failed_create_leaves_no_repository_residue(
    client: TestClient,
    core_request: dict,
) -> None:
    failed = client.post(
        "/api/v1/projects",
        json={**core_request, "title": ""},
    )
    assert failed.status_code == 422
    assert (
        client.get(f"/api/v1/projects/{FIXED_PROJECT_ID}/status").status_code
        == 404
    )


def test_server_generated_collision_is_structured_409(
    core_request: dict,
) -> None:
    from conftest import make_runtime
    from kurgu_studio_api import create_app

    runtime = make_runtime(project_ids=(FIXED_PROJECT_ID, FIXED_PROJECT_ID))
    client = TestClient(create_app(runtime))
    first = client.post("/api/v1/projects", json=core_request)
    second = client.post("/api/v1/projects", json=core_request)
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "PROJECT_ID_COLLISION"
    assert (
        runtime.project_repository.get(FIXED_PROJECT_ID).project["title"]
        == core_request["title"]
    )
