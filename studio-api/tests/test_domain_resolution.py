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
    runtime,
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
        assert runtime.project_repository.get(FIXED_PROJECT_ID) is None


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
    runtime,
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
    assert {
        issue["code"] for issue in response.json()["error"]["issues"]
    } == {"SCHEMA_PATTERN"}
    assert runtime.project_repository.get(FIXED_PROJECT_ID) is None


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


def test_real_profile_mismatch_is_sanitized_and_leaves_no_residue(
    client: TestClient,
    runtime,
    business_request: dict,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runtime.domain_resolution.registry,
        "get",
        lambda *args: (_ for _ in ()).throw(
            AssertionError("registry lookup must follow profile eligibility")
        ),
    )
    profile_id = "dpf_core_default"
    domain = {
        **business_request["domain"],
        "profile": {
            **business_request["domain"]["profile"],
            "profile_id": profile_id,
        },
    }
    response = client.post(
        "/api/v1/projects",
        json={
            **business_request,
            "title": "Profile mismatch",
            "domain": domain,
        },
    )
    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "DOMAIN_PROFILE_MISMATCH",
            "message": "The profile does not match the selected domain pack.",
            "issues": [
                {
                    "code": "DOMAIN_PROFILE_MISMATCH",
                    "json_pointer": "/domain/profile/profile_id",
                    "message": (
                        "The profile does not match the selected domain pack."
                    ),
                }
            ],
        }
    }
    assert profile_id.encode() not in response.content
    assert b"dpf_business_default" not in response.content
    assert runtime.project_repository.get(FIXED_PROJECT_ID) is None
    assert (
        client.get(f"/api/v1/projects/{FIXED_PROJECT_ID}/status").status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/projects/{FIXED_PROJECT_ID}/artifacts"
        ).status_code
        == 404
    )


def test_discovered_ineligible_pack_is_publicly_unknown_and_has_no_residue(
    business_request: dict,
    monkeypatch,
) -> None:
    from conftest import make_runtime
    from kurgu_studio_api import create_app

    monkeypatch.setenv(
        "KURGU_PROJECT_API_ELIGIBLE_DOMAINS",
        "true-crime-legal@0.0.1-contract",
    )
    runtime = make_runtime()
    monkeypatch.setattr(
        runtime.domain_resolution.registry,
        "get",
        lambda *args: (_ for _ in ()).throw(
            AssertionError("registry lookup must follow domain eligibility")
        ),
    )
    client = TestClient(create_app(runtime))
    ineligible = {
        "title": "Ineligible pack",
        "domain": {
            "resolution_mode": "domain_pack",
            "domain_id": "true-crime-legal",
            "domain_pack_version": "0.0.1-contract",
            "profile": {
                "profile_id": "dpf_true_crime_default",
                "enabled_extensions": [],
                "policy_overrides": {},
            },
        },
    }
    response = client.post("/api/v1/projects", json=ineligible)
    client_override = {
        **ineligible,
        "domain": {
            **ineligible["domain"],
            "allowed_profile_ids": ["dpf_true_crime_default"],
        },
    }
    override_response = client.post(
        "/api/v1/projects",
        json=client_override,
    )
    unknown = {
        **business_request,
        "domain": {
            **business_request["domain"],
            "domain_id": "unknown-domain",
            "profile": {
                **business_request["domain"]["profile"],
                "profile_id": "dpf_unknown_default",
            },
        },
    }
    unknown_response = client.post("/api/v1/projects", json=unknown)

    assert response.status_code == unknown_response.status_code == 422
    assert response.json() == unknown_response.json()
    assert response.json()["error"]["code"] == "DOMAIN_UNKNOWN"
    assert override_response.status_code == 422
    assert (
        override_response.json()["error"]["code"]
        == "REQUEST_VALIDATION_FAILED"
    )
    lowered = response.content.lower()
    for forbidden in (
        b"true-crime",
        b"contract_example",
        b"contract-example",
        b"manifest",
        b"domain-packs",
        b"eligible",
        b"traceback",
        b"c:\\\\",
    ):
        assert forbidden not in lowered
    assert runtime.project_repository.get(FIXED_PROJECT_ID) is None
    assert (
        client.get(f"/api/v1/projects/{FIXED_PROJECT_ID}/status").status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/projects/{FIXED_PROJECT_ID}/artifacts"
        ).status_code
        == 404
    )
