from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import FIXED_PROJECT_ID, FIXED_TIME


def test_existing_project_status_is_canonical_without_fake_progress(
    client: TestClient,
    core_request: dict,
) -> None:
    assert client.post("/api/v1/projects", json=core_request).status_code == 201
    response = client.get(f"/api/v1/projects/{FIXED_PROJECT_ID}/status")
    assert response.status_code == 200
    assert response.json() == {
        "project_id": FIXED_PROJECT_ID,
        "status": "ready",
        "updated_at": FIXED_TIME,
        "version": 1,
        "domain": {
            "resolution_mode": "core_only",
            "domain_id": "core-generic",
            "domain_pack_version": "0.0.0",
            "profile_id": "dpf_core_default",
            "policy_snapshot_id": response.json()["domain"][
                "policy_snapshot_id"
            ],
        },
        "persistence_scope": "process_lifetime",
    }
    assert set(response.json()).isdisjoint(
        {"progress", "percent", "job_id", "workspace_root", "path"}
    )


def test_missing_project_has_structured_404(client: TestClient) -> None:
    response = client.get("/api/v1/projects/prj_missing_001/status")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


def test_invalid_project_id_has_structured_422(client: TestClient) -> None:
    response = client.get("/api/v1/projects/invalid/status")
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "REQUEST_VALIDATION_FAILED"
    assert payload["error"]["issues"][0]["json_pointer"] == "/project_id"
