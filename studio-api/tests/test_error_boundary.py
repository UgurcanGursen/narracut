from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from kurgu_studio_api import create_app


def test_request_validation_does_not_echo_raw_input(
    client: TestClient,
) -> None:
    marker = "secret-marker-must-not-return"
    response = client.post(
        "/api/v1/projects",
        json={
            "title": marker,
            "domain": {"resolution_mode": "core_only"},
            "password": marker,
        },
    )
    assert response.status_code == 422
    assert marker.encode() not in response.content
    assert "input" not in response.json()["error"]


def test_domain_error_has_no_exception_or_local_path(
    client: TestClient,
    business_request: dict,
) -> None:
    domain = {**business_request["domain"], "domain_id": "unknown-domain"}
    response = client.post(
        "/api/v1/projects",
        json={**business_request, "domain": domain},
    )
    content = response.content.lower()
    assert response.status_code == 422
    assert b"domainpackerror" not in content
    assert b"traceback" not in content
    assert b"c:\\\\" not in content
    assert b"domain-packs" not in content


class ExplodingService:
    def create_project(self, command):
        del command
        raise RuntimeError(
            "secret-marker C:\\private\\repository domain-packs/manifest.json"
        )


def test_unexpected_exception_is_generic_and_sanitized() -> None:
    runtime = SimpleNamespace(project_service=ExplodingService())
    client = TestClient(create_app(runtime), raise_server_exceptions=False)
    response = client.post(
        "/api/v1/projects",
        json={
            "title": "Internal failure",
            "domain": {"resolution_mode": "core_only"},
        },
    )
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An internal error occurred.",
            "issues": [
                {
                    "code": "INTERNAL_ERROR",
                    "json_pointer": "",
                    "message": "An internal error occurred.",
                }
            ],
        }
    }
