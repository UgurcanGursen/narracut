from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import FIXED_PROJECT_ID


def test_business_pack_uses_real_registry_and_resolver(
    client: TestClient,
    runtime,
    business_request: dict,
) -> None:
    response = client.post("/api/v1/projects", json=business_request)
    assert response.status_code == 201
    payload = response.json()
    assert payload["domain"] == {
        "resolution_mode": "domain_pack",
        "domain_id": "business-tech",
        "domain_pack_version": "0.1.0",
        "profile_id": "dpf_business_default",
        "policy_snapshot_id": "dps_d18e9981c3f4bcca8e3f",
    }
    stored = runtime.project_repository.get(FIXED_PROJECT_ID)
    assert stored is not None
    assert stored.domain.policy_snapshot["canonical_hash"] == (
        "sha256:d18e9981c3f4bcca8e3f5a8f62c838d0e0ecbd14e6cd229e2702c08e2a3f3f2c"
    )
    assert stored.domain.policy_snapshot["resolved_policy"][
        "policy_bundles"
    ][0]["ref"] == "policies/skeleton.json"


def test_business_policy_snapshot_is_deterministic(
    business_request: dict,
) -> None:
    from conftest import make_runtime
    from kurgu_studio_api import create_app

    first = TestClient(create_app(make_runtime())).post(
        "/api/v1/projects",
        json=business_request,
    )
    second = TestClient(create_app(make_runtime())).post(
        "/api/v1/projects",
        json=business_request,
    )
    assert first.status_code == second.status_code == 201
    assert first.json()["domain"] == second.json()["domain"]


def test_unknown_domain_and_version_are_fail_closed(
    client: TestClient,
    business_request: dict,
) -> None:
    for changes in (
        {"domain_id": "unknown-domain"},
        {"domain_pack_version": "9.9.9"},
    ):
        domain = {**business_request["domain"], **changes}
        response = client.post(
            "/api/v1/projects",
            json={**business_request, "domain": domain},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "DOMAIN_UNKNOWN"


def test_missing_domain_pack_configuration_has_specific_error(
    client: TestClient,
    business_request: dict,
) -> None:
    domain = dict(business_request["domain"])
    domain.pop("profile")
    response = client.post(
        "/api/v1/projects",
        json={**business_request, "domain": domain},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "DOMAIN_CONFIGURATION_REQUIRED"


def test_invalid_profile_contract_is_fail_closed(
    client: TestClient,
    business_request: dict,
) -> None:
    domain = {
        **business_request["domain"],
        "profile": {
            **business_request["domain"]["profile"],
            "profile_id": "not-a-profile-id",
        },
    }
    response = client.post(
        "/api/v1/projects",
        json={**business_request, "domain": domain},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CONTRACT_VALIDATION_FAILED"


def test_client_cannot_submit_a_mismatched_profile_domain(
    client: TestClient,
    business_request: dict,
) -> None:
    profile = {
        **business_request["domain"]["profile"],
        "domain_id": "core-generic",
        "domain_pack_version": "0.0.0",
    }
    domain = {**business_request["domain"], "profile": profile}
    response = client.post(
        "/api/v1/projects",
        json={**business_request, "domain": domain},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"
