from __future__ import annotations

from fastapi.testclient import TestClient

from kurgu_studio_api import create_app
from kurgu_studio_api.application.models import (
    CoreOnlyDomainCommand,
    ProjectAggregate,
)

from conftest import (
    FIXED_PROJECT_ID,
    FIXED_TIME,
    make_runtime,
)


def _artifact() -> dict:
    return {
        "schema_version": "3.0.0",
        "artifact_id": "art_api_contract_001",
        "artifact_type": "source_media",
        "project_id": FIXED_PROJECT_ID,
        "sequence_id": None,
        "created_at": FIXED_TIME,
        "last_accessed_at": FIXED_TIME,
        "content_hash": "sha256:" + ("a" * 64),
        "size_bytes": 1024,
        "retention_class": "provenance",
        "dependency_ids": [],
        "locked": False,
        "pinned": False,
        "approved": True,
        "cleanup_candidate": False,
        "producer": "test-fixture",
        "producer_version": "1.0.0",
        "job_id": None,
        "status": "approved",
        "version": 1,
    }


def test_new_project_has_real_empty_artifact_collection(
    client: TestClient,
    core_request: dict,
) -> None:
    assert client.post("/api/v1/projects", json=core_request).status_code == 201
    response = client.get(f"/api/v1/projects/{FIXED_PROJECT_ID}/artifacts")
    assert response.status_code == 200
    assert response.json() == {
        "project_id": FIXED_PROJECT_ID,
        "items": [],
        "count": 0,
        "persistence_scope": "process_lifetime",
    }


def test_missing_project_artifacts_has_structured_404(client: TestClient) -> None:
    response = client.get("/api/v1/projects/prj_missing_001/artifacts")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


def test_valid_injected_artifact_is_canonical_and_has_no_path_leak() -> None:
    runtime = make_runtime()
    resolved = runtime.domain_resolution.resolve(
        CoreOnlyDomainCommand(),
        created_at=FIXED_TIME,
    )
    project = {
        "schema_version": "3.0.0",
        "project_id": FIXED_PROJECT_ID,
        "title": "Seeded Project",
        "created_at": FIXED_TIME,
        "updated_at": FIXED_TIME,
        "domain_id": resolved.domain_id,
        "domain_pack_version": resolved.domain_pack_version,
        "policy_snapshot_id": resolved.policy_snapshot_id,
        "status": "ready",
        "version": 1,
    }
    artifact = _artifact()
    runtime.contract_validation.validate_project(project)
    runtime.contract_validation.validate_artifacts(
        (artifact,),
        project_id=FIXED_PROJECT_ID,
    )
    runtime.project_repository.create(
        ProjectAggregate(
            project=project,
            domain=resolved,
            artifacts=(artifact,),
        )
    )
    response = TestClient(create_app(runtime)).get(
        f"/api/v1/projects/{FIXED_PROJECT_ID}/artifacts"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == len(payload["items"]) == 1
    assert payload["items"][0] == artifact
    serialized = response.content.lower()
    assert b"c:\\\\" not in serialized
    assert b"file://" not in serialized
    assert b"provider_uri" not in serialized


def test_invalid_injected_artifact_fails_before_repository_insert() -> None:
    runtime = make_runtime()
    invalid = {**_artifact(), "content_hash": "not-a-hash"}
    try:
        runtime.contract_validation.validate_artifacts(
            (invalid,),
            project_id=FIXED_PROJECT_ID,
        )
    except Exception as exc:
        assert getattr(exc, "code", None) == "CONTRACT_VALIDATION_FAILED"
    else:
        raise AssertionError("Invalid artifact was accepted.")
    assert runtime.project_repository.get(FIXED_PROJECT_ID) is None
