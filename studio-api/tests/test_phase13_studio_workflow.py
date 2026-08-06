from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from engine.contracts._canonical_json import encode_canonical_json_bytes
from kurgu_studio_api import create_app
from kurgu_studio_api.infrastructure.runtime import build_runtime


def _hash(value: dict) -> str:
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _business_request() -> dict:
    return {
        "title": "Phase 13 workflow",
        "domain": {
            "resolution_mode": "domain_pack",
            "domain_id": "business-tech",
            "domain_pack_version": "0.1.0",
            "profile": {
                "profile_id": "dpf_business_default",
                "enabled_extensions": [],
                "policy_overrides": {},
            },
        },
    }


def _project(client: TestClient) -> str:
    response = client.post("/api/v1/projects", json=_business_request())
    assert response.status_code == 201
    return response.json()["project"]["project_id"]


def test_task_creation_does_not_silently_fallback_from_core_only(tmp_path: Path) -> None:
    client = TestClient(create_app(build_runtime(database_path=tmp_path / "studio.sqlite3")))
    created = client.post("/api/v1/projects", json={"title": "Core", "domain": {"resolution_mode": "core_only"}})
    project_id = created.json()["project"]["project_id"]
    response = client.post(f"/api/v1/projects/{project_id}/tasks", json={"family": "research", "task_type": "source_discovery", "backend_mode": "manual_ui", "topic": "AI chips"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "TASK_UNAVAILABLE"


def _bound_snapshot(project_id: str, policy_id: str, policy_hash: str) -> dict:
    sequences = [
        {"executable_sequence_id": "eseq_alpha", "executable_sequence_hash": "sha256:" + "a" * 64},
        {"executable_sequence_id": "eseq_beta", "executable_sequence_hash": "sha256:" + "b" * 64},
    ]
    plan_body = {
        "schema_version": "PHASE12-EXECUTABLE-EDITORIAL-PLAN-V1",
        "project_id": project_id,
        "policy_snapshot_id": policy_id,
        "policy_snapshot_hash": policy_hash,
        "editorial_integration_policy_hash": "sha256:" + "c" * 64,
        "sequences": sequences,
    }
    plan_hash = _hash(plan_body)
    plan = {
        "executable_editorial_plan_id": "eeplan_" + plan_hash[7:27],
        "executable_editorial_plan_hash": plan_hash,
        **plan_body,
    }
    rows = [
        {
            **item,
            "video_edl_id": "vedl_" + item["executable_sequence_id"],
            "video_edl_hash": "sha256:" + ("d" if item["executable_sequence_id"] == "eseq_alpha" else "e") * 64,
            "audio_edl_id": "aedl_" + item["executable_sequence_id"],
            "audio_edl_hash": "sha256:" + ("f" if item["executable_sequence_id"] == "eseq_alpha" else "0") * 64,
        }
        for item in sequences
    ]
    bundle_body = {
        "schema_version": "PHASE12-FINAL-EDL-BUNDLE-V1",
        "executable_editorial_plan_id": plan["executable_editorial_plan_id"],
        "executable_editorial_plan_hash": plan_hash,
        "sequence_edls": rows,
    }
    bundle_hash = _hash(bundle_body)
    return {
        "executable_plan": plan,
        "final_edl_bundle": {
            "final_edl_bundle_id": "fedl_" + bundle_hash[7:27],
            "final_edl_bundle_hash": bundle_hash,
            **bundle_body,
        },
    }


def test_sqlite_project_reopens_after_new_runtime(tmp_path: Path) -> None:
    database_path = tmp_path / "studio.sqlite3"
    first = TestClient(create_app(build_runtime(database_path=database_path)))
    project_id = _project(first)
    assert first.get(f"/api/v1/projects/{project_id}/status").json()["persistence_scope"] == "local_sqlite"

    second = TestClient(create_app(build_runtime(database_path=database_path)))
    listing = second.get("/api/v1/projects")
    assert listing.status_code == 200
    assert [item["project_id"] for item in listing.json()["items"]] == [project_id]
    response = second.get(f"/api/v1/projects/{project_id}/status")
    assert response.status_code == 200
    assert response.json()["project_id"] == project_id


def test_manual_task_validation_repair_and_approval_are_api_only(tmp_path: Path) -> None:
    client = TestClient(create_app(build_runtime(database_path=tmp_path / "studio.sqlite3")))
    project_id = _project(client)
    created = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={
            "family": "research",
            "task_type": "source_discovery",
            "backend_mode": "manual_ui",
            "topic": "AI chips",
        },
    )
    assert created.status_code == 201
    task = created.json()
    assert task["status"] == "waiting"
    assert "path" not in task["context_package"]

    invalid = client.post(
        f"/api/v1/projects/{project_id}/tasks/{task['task_id']}/response",
        json={"payload": {"invalid": True}},
    )
    assert invalid.status_code == 200
    assert invalid.json()["status"] == "repair_required"
    assert invalid.json()["validation_issues"] == ["RESPONSE_INVALID"]

    repair = client.post(f"/api/v1/projects/{project_id}/tasks/{task['task_id']}/repair")
    assert repair.status_code == 201
    assert repair.json()["task_type"] == "repair"
    assert repair.json()["parent_task_id"] == task["task_id"]

    valid_task = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={
            "family": "research",
            "task_type": "source_discovery",
            "backend_mode": "manual_ui",
            "topic": "AI chips",
        },
    ).json()
    valid_payload = {
        "schema_version": "PHASE9-LLM-RESPONSE-V1",
        "task_id": valid_task["task_id"],
        "task_hash": valid_task["task_hash"],
        "task_type": valid_task["task_type"],
        "policy_snapshot_id": valid_task["policy_snapshot_id"],
        "policy_snapshot_hash": valid_task["policy_snapshot_hash"],
        "result": {"candidates": []},
    }
    valid = client.post(
        f"/api/v1/projects/{project_id}/tasks/{valid_task['task_id']}/response",
        json={"payload": valid_payload},
    )
    assert valid.status_code == 200
    assert valid.json()["status"] == "valid"
    approved = client.post(f"/api/v1/projects/{project_id}/tasks/{valid_task['task_id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"


def test_phase12_bound_review_snapshot_is_hash_locked(tmp_path: Path) -> None:
    client = TestClient(create_app(build_runtime(database_path=tmp_path / "studio.sqlite3")))
    project_id = _project(client)
    status = client.get(f"/api/v1/projects/{project_id}/status").json()
    snapshot = _bound_snapshot(project_id, status["domain"]["policy_snapshot_id"], "sha256:" + "1" * 64)
    # A foreign policy hash cannot become a review snapshot.
    rejected = client.post(f"/api/v1/projects/{project_id}/review-snapshots", json=snapshot)
    assert rejected.status_code == 422

    snapshot = _bound_snapshot(project_id, status["domain"]["policy_snapshot_id"], status["domain"]["policy_snapshot_id"].replace("dps_", "sha256:").ljust(71, "0"))
    # The actual policy hash is deliberately obtained from a generated task, not caller input.
    task = client.post(f"/api/v1/projects/{project_id}/tasks", json={"family": "research", "task_type": "source_discovery", "backend_mode": "replay", "topic": "AI chips"}).json()
    snapshot = _bound_snapshot(project_id, task["policy_snapshot_id"], task["policy_snapshot_hash"])
    registered = client.post(f"/api/v1/projects/{project_id}/review-snapshots", json=snapshot)
    assert registered.status_code == 201
    review = client.get(f"/api/v1/projects/{project_id}/review/sequences/eseq_alpha")
    assert review.status_code == 200
    decision = client.post(f"/api/v1/projects/{project_id}/review/sequences/eseq_alpha/decision", json={"action": "approve", "replacement_kind": None})
    assert decision.status_code == 200
    assert decision.json()["video_edl_hash"] == "sha256:" + "d" * 64
    assert client.post(f"/api/v1/projects/{project_id}/review/sequences/eseq_alpha/decision", json={"action": "replacement_requested", "replacement_kind": "asset_change"}).status_code == 409
