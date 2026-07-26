from __future__ import annotations

import hashlib
import json
from pathlib import Path

from kurgu_studio_api import create_app
from kurgu_studio_api.openapi_export import _render_openapi_bytes


REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = REPO_ROOT / "shared-schemas" / "openapi" / "openapi.json"
EXPECTED = {
    "/api/v1/projects": {"post": "createProject"},
    "/api/v1/projects/{project_id}/status": {"get": "getProjectStatus"},
    "/api/v1/projects/{project_id}/artifacts": {
        "get": "listProjectArtifacts"
    },
}


def test_openapi_has_exact_project_path_and_operation_inventory() -> None:
    document = create_app().openapi()
    assert set(document["paths"]) == set(EXPECTED)
    assert {
        path: {
            method: document["paths"][path][method]["operationId"]
            for method in methods
        }
        for path, methods in EXPECTED.items()
    } == EXPECTED
    operation_ids = [
        operation
        for methods in EXPECTED.values()
        for operation in methods.values()
    ]
    assert len(operation_ids) == len(set(operation_ids))
    assert "servers" not in document


def test_openapi_components_include_stable_request_response_and_error_models() -> None:
    schemas = create_app().openapi()["components"]["schemas"]
    expected = {
        "ProjectCreateRequestDTO",
        "ProjectCreateResponseDTO",
        "ProjectStatusResponseDTO",
        "ProjectArtifactsResponseDTO",
        "CoreOnlyDomainCreateDTO",
        "DomainPackDomainCreateDTO",
        "ErrorEnvelopeDTO",
        "ArtifactDTO",
    }
    assert expected.issubset(schemas)
    assert "HTTPValidationError" not in schemas


def test_openapi_runtime_is_deterministic_and_matches_committed_artifact() -> None:
    first = _render_openapi_bytes()
    second = _render_openapi_bytes()
    assert first == second
    assert first == OPENAPI_PATH.read_bytes()
    document = json.loads(first)
    assert set(document["paths"]) == set(EXPECTED)
    assert hashlib.sha256(first).hexdigest()
