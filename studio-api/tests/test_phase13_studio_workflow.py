from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.rendering import FixtureAssetResolver
from engine.rendering.bridge import renderer_version
from tests.test_render_bridge import build_phase4a_rich_replay_inputs
from kurgu_studio_api import create_app
from kurgu_studio_api.infrastructure.runtime import build_runtime
from kurgu_studio_api.infrastructure.preview_adapters import CanonicalReplayInputFactory
from kurgu_studio_api.application.models import PreviewExecutionResult, RenderInputSnapshotRecord


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


class _FixedProjectIdFactory:
    def new_project_id(self) -> str:
        return "prj_fx34"


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


def _canonical_bound_snapshot(project_id: str, policy_id: str, policy_hash: str, inputs: list[dict[str, object]]) -> dict:
    sequences = [{"executable_sequence_id": value["video_edl"].sequence_id, "executable_sequence_hash": "sha256:" + chr(97 + ordinal) * 64} for ordinal, value in enumerate(inputs)]
    plan_body = {"schema_version": "PHASE12-EXECUTABLE-EDITORIAL-PLAN-V1", "project_id": project_id, "policy_snapshot_id": policy_id, "policy_snapshot_hash": policy_hash, "editorial_integration_policy_hash": "sha256:" + "c" * 64, "sequences": sequences}
    plan_hash = _hash(plan_body)
    plan = {"executable_editorial_plan_id": "eeplan_" + plan_hash[7:27], "executable_editorial_plan_hash": plan_hash, **plan_body}
    rows = [{**sequence, "video_edl_id": value["video_edl"].video_edl_id, "video_edl_hash": value["video_edl"].video_edl_hash, "audio_edl_id": value["audio_edl"].audio_edl_id, "audio_edl_hash": value["audio_edl"].audio_edl_hash} for sequence, value in zip(sequences, inputs, strict=True)]
    bundle_body = {"schema_version": "PHASE12-FINAL-EDL-BUNDLE-V1", "executable_editorial_plan_id": plan["executable_editorial_plan_id"], "executable_editorial_plan_hash": plan_hash, "sequence_edls": rows}
    bundle_hash = _hash(bundle_body)
    return {"executable_plan": plan, "final_edl_bundle": {"final_edl_bundle_id": "fedl_" + bundle_hash[7:27], "final_edl_bundle_hash": bundle_hash, **bundle_body}}


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


class _SuccessfulPreviewExecutor:
    def execute(self, snapshot: RenderInputSnapshotRecord, *, timestamp_utc: str) -> PreviewExecutionResult:
        del snapshot, timestamp_utc
        manifest = b'{"frames":[{"frame_index":0}]}'
        return PreviewExecutionResult("succeeded", "sha256:" + "2" * 64, manifest, {0: b"png"})


class _FixedInputResolver:
    def __init__(self, value: RenderInputSnapshotRecord) -> None:
        self.value = value

    def resolve(self, *, project_id: str, sequence_id: str, review_snapshot: object) -> RenderInputSnapshotRecord | None:
        del review_snapshot
        return self.value if (project_id, sequence_id) == (self.value.project_id, self.value.executable_sequence_id) else None


def _install_preview_input(client: TestClient, project_id: str) -> tuple[object, dict]:
    runtime = client.app.state.runtime
    task = client.post(f"/api/v1/projects/{project_id}/tasks", json={"family": "research", "task_type": "source_discovery", "backend_mode": "replay", "topic": "AI chips"}).json()
    bound = _bound_snapshot(project_id, task["policy_snapshot_id"], task["policy_snapshot_hash"])
    assert client.post(f"/api/v1/projects/{project_id}/review-snapshots", json=bound).status_code == 201
    sequence = bound["executable_plan"]["sequences"][0]
    record = RenderInputSnapshotRecord(
        snapshot_id="risnap_test_alpha", snapshot_hash="sha256:" + "3" * 64,
        project_id=project_id, executable_sequence_id=sequence["executable_sequence_id"], executable_sequence_hash=sequence["executable_sequence_hash"],
        domain_pack_version="0.1.0", policy_snapshot_id=task["policy_snapshot_id"], policy_snapshot_hash=task["policy_snapshot_hash"],
        executable_plan_id=bound["executable_plan"]["executable_editorial_plan_id"], executable_plan_hash=bound["executable_plan"]["executable_editorial_plan_hash"],
        final_edl_bundle_id=bound["final_edl_bundle"]["final_edl_bundle_id"], final_edl_bundle_hash=bound["final_edl_bundle"]["final_edl_bundle_hash"],
        video_edl_id="vedl_test", video_edl_hash="sha256:" + "6" * 64, video_edl_bytes=b"{}", audio_edl_id="aedl_test", audio_edl_hash="sha256:" + "7" * 64, audio_edl_bytes=b"{}", render_props_bytes=b"{}", render_props_id="rprops_test", render_props_hash="sha256:" + "4" * 64,
        fixture_manifest_id="fixman_test", fixture_manifest_hash="sha256:" + "5" * 64, mode="preview_replay", created_at="2026-08-06T00:00:00Z", producer="test", producer_version="0",
    )
    assert runtime.workflow_service is not None
    runtime.workflow_service.render_inputs = _FixedInputResolver(record)
    runtime.workflow_service.preview_executor = _SuccessfulPreviewExecutor()
    return runtime, sequence


def test_preview_api_rejects_absent_trusted_input(tmp_path: Path) -> None:
    client = TestClient(create_app(build_runtime(database_path=tmp_path / "studio.sqlite3")))
    project_id = _project(client)
    response = client.post(f"/api/v1/projects/{project_id}/sequences/eseq_alpha/preview-renders")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "REVIEW_BINDING_INVALID"


def test_canonical_two_sequence_snapshots_are_verified_before_sqlite_persistence(tmp_path: Path) -> None:
    database_path = tmp_path / "studio.sqlite3"
    runtime = build_runtime(database_path=database_path)
    runtime.project_service.project_id_factory = _FixedProjectIdFactory()
    client = TestClient(create_app(runtime))
    project_id = _project(client)
    task = client.post(f"/api/v1/projects/{project_id}/tasks", json={"family": "research", "task_type": "source_discovery", "backend_mode": "replay", "topic": "AI chips"}).json()
    inputs = [build_phase4a_rich_replay_inputs(sequence_id="eseq_replaya"), build_phase4a_rich_replay_inputs(sequence_id="eseq_replayb")]
    bound = _canonical_bound_snapshot(project_id, task["policy_snapshot_id"], task["policy_snapshot_hash"], inputs)
    assert client.post(f"/api/v1/projects/{project_id}/review-snapshots", json=bound).status_code == 201
    factory = CanonicalReplayInputFactory()
    fixture_assets = FixtureAssetResolver.load(Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "phase4a")
    version = renderer_version((Path(__file__).resolve().parents[2] / "renderer-remotion" / "package-lock.json").read_bytes())
    records = []
    for sequence, value in zip(bound["executable_plan"]["sequences"], inputs, strict=True):
        record = factory.build(project_id=project_id, executable_sequence_hash=sequence["executable_sequence_hash"], domain_pack_version="0.1.0", policy_snapshot_id=task["policy_snapshot_id"], policy_snapshot_hash=task["policy_snapshot_hash"], executable_plan_id=bound["executable_plan"]["executable_editorial_plan_id"], executable_plan_hash=bound["executable_plan"]["executable_editorial_plan_hash"], final_edl_bundle_id=bound["final_edl_bundle"]["final_edl_bundle_id"], final_edl_bundle_hash=bound["final_edl_bundle"]["final_edl_bundle_hash"], video_edl=value["video_edl"], audio_edl=value["audio_edl"], fixture_assets=fixture_assets, renderer_version=version, created_at="2026-08-06T00:00:00Z")
        runtime.project_repository.put_render_input(record)
        records.append(record)
    reopened = build_runtime(database_path=database_path)
    for record in records:
        loaded = reopened.project_repository.get_render_input(project_id, record.executable_sequence_id)
        assert loaded == record

    # This is deliberately an API-level execution of both independently bound
    # Phase 4 REPLAY sequences.  Do not substitute a fake PreviewExecutionPort:
    # the asserted delivery bytes must come from the checked-in Remotion runner.
    for record in records:
        created = client.post(
            f"/api/v1/projects/{project_id}/sequences/{record.executable_sequence_id}/preview-renders"
        )
        assert created.status_code == 201, created.text
        job = created.json()
        assert job["state"] == "succeeded"
        events = client.get(f"/api/v1/projects/{project_id}/preview-renders/{job['job_id']}/events")
        assert [event["state"] for event in events.json()["items"]] == ["requested", "admitted", "running", "succeeded"]
        manifest = json.loads(client.get(f"/api/v1/projects/{project_id}/preview-renders/{job['job_id']}/manifest").content)
        frame_indices = [item["frame_index"] for item in manifest["frames"]]
        assert len(frame_indices) == 5
        assert frame_indices == sorted(set(frame_indices))
        for frame_index in frame_indices:
            assert client.get(f"/api/v1/projects/{project_id}/preview-renders/{job['job_id']}/frames/{frame_index}").content.startswith(b"\x89PNG")


def test_preview_api_persists_ordered_safe_events_and_declared_delivery_only(tmp_path: Path) -> None:
    database_path = tmp_path / "studio.sqlite3"
    client = TestClient(create_app(build_runtime(database_path=database_path)))
    project_id = _project(client)
    _, sequence = _install_preview_input(client, project_id)
    created = client.post(f"/api/v1/projects/{project_id}/sequences/{sequence['executable_sequence_id']}/preview-renders")
    assert created.status_code == 201
    job = created.json()
    assert job["state"] == "succeeded"
    assert job["attempt_ordinal"] == 1
    events = client.get(f"/api/v1/projects/{project_id}/preview-renders/{job['job_id']}/events").json()
    assert [event["state"] for event in events["items"]] == ["requested", "admitted", "running", "succeeded"]
    assert [event["ordinal"] for event in events["items"]] == [1, 2, 3, 4]
    streamed = client.get(f"/api/v1/projects/{project_id}/preview-renders/{job['job_id']}/events/stream?after=2")
    assert streamed.headers["content-type"].startswith("text/event-stream")
    assert "id: 3" in streamed.text and "id: 4" in streamed.text
    assert client.get(f"/api/v1/projects/{project_id}/preview-renders/{job['job_id']}/manifest").content == b'{"frames":[{"frame_index":0}]}'
    assert client.get(f"/api/v1/projects/{project_id}/preview-renders/{job['job_id']}/frames/0").content == b"png"
    assert client.get(f"/api/v1/projects/{project_id}/preview-renders/{job['job_id']}/frames/1").status_code == 404
    second = client.post(f"/api/v1/projects/{project_id}/sequences/{sequence['executable_sequence_id']}/preview-renders")
    assert second.status_code == 201
    assert second.json()["job_id"] != job["job_id"]
    assert second.json()["attempt_ordinal"] == 2
    other_project = _project(client)
    assert client.get(f"/api/v1/projects/{other_project}/preview-renders/{job['job_id']}").status_code == 404
    reopened = TestClient(create_app(build_runtime(database_path=database_path)))
    replay = reopened.get(f"/api/v1/projects/{project_id}/preview-renders/{job['job_id']}/events?after=2")
    assert [event["ordinal"] for event in replay.json()["items"]] == [3, 4]
    assert reopened.get(f"/api/v1/projects/{project_id}/preview-renders/{job['job_id']}/manifest").status_code == 409
