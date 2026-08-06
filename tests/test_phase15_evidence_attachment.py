import json
from pathlib import Path

import pytest

from engine.contracts import DomainPackRegistry, DomainPolicyResolver, SchemaCatalog
from engine.contracts.audio_edl import serialize_audio_edl
from engine.contracts.edl import serialize_video_edl
from engine.lifecycle import ArtifactRegistryRecord
from engine.rendering.bridge import build_render_props, renderer_version, serialize_render_props
from engine.rendering.fixture_assets import FixtureAssetResolver
from engine.rendering.preview_runner import run_headless_preview
from engine.rendering.receipt import serialize_render_receipt
from engine.validation.evidence_attachment import attach_evidence
from engine.validation.run_evidence import evaluate_quality_gate, serialize_jsonl
from tests.test_render_bridge import FIXTURE_ROOT, ROOT, build_phase4a_rich_replay_inputs


RUN = "run_attachment"
STAMP = "2026-08-06T00:00:00Z"


def _snapshot():
    catalog = SchemaCatalog(ROOT / "shared-schemas" / "v3")
    registry = DomainPackRegistry([ROOT / "domain-packs", ROOT / "tests" / "fixtures" / "domain-packs"], catalog)
    registry.discover()
    profile = json.loads((ROOT / "samples" / "v3" / "business-tech" / "workspace.json").read_text(encoding="utf-8"))["domain"]["profile"]
    return DomainPolicyResolver(catalog).resolve(registry.get("business-tech", "0.1.0"), profile)[0]


def _run(tmp_path):
    replay = build_phase4a_rich_replay_inputs()
    props = build_render_props(video_edl=replay["video_edl"], audio_edl=replay["audio_edl"],
        fixture_assets=FixtureAssetResolver.load(FIXTURE_ROOT),
        renderer_version_value=renderer_version((ROOT / "renderer-remotion" / "package-lock.json").read_bytes()))
    outcome = run_headless_preview(props=props, video_edl_bytes=serialize_video_edl(replay["video_edl"]),
        audio_edl_bytes=serialize_audio_edl(replay["audio_edl"]), fixture_root=FIXTURE_ROOT,
        output_root=tmp_path / "output", work_root=tmp_path, timestamp_utc=STAMP)
    record = ArtifactRegistryRecord.materialize({"artifact_id": outcome.receipt.output_artifact_id,
        "project_id": props.project_id, "content_hash": outcome.receipt.output_sha256,
        "size_bytes": outcome.receipt.output_size_bytes, "retention_class": "review",
        "dependency_ids": (), "locked": False, "pinned": False, "approved": False,
        "producer": "phase4", "producer_version": "1"})
    return props, outcome, (record,)


def test_actual_phase4_phase14_domain_evidence_attaches_and_passes(tmp_path):
    props, outcome, records = _run(tmp_path); snapshot = _snapshot()
    rows = attach_evidence(run_id=RUN, timestamp_utc=STAMP, project_id=props.project_id,
        render_props_bytes=serialize_render_props(props), render_receipt_bytes=serialize_render_receipt(outcome.receipt),
        registry_records=records, storage_scope_id="cache", storage_policy_hash="sha256:" + "a" * 64,
        storage_admission="ADMITTED", domain_snapshot=snapshot,
        expected_policy_snapshot_id=snapshot.snapshot_id, expected_policy_snapshot_hash=snapshot.canonical_hash)
    raw = serialize_jsonl(rows)
    decision = evaluate_quality_gate(source=raw, required_checks={key: snapshot.canonical_hash for key in ("render_path", "artifact_lifecycle", "storage_pressure", "domain_contract")})
    assert decision.decision == "PASS"
    other = ArtifactRegistryRecord.materialize({"artifact_id": "artifact_other",
        "project_id": props.project_id, "content_hash": outcome.receipt.output_sha256,
        "size_bytes": outcome.receipt.output_size_bytes, "retention_class": "review",
        "dependency_ids": (), "locked": False, "pinned": False, "approved": False,
        "producer": "phase4", "producer_version": "1"})
    with pytest.raises(ValueError, match="ARTIFACT_OUTPUT_UNREGISTERED"):
        attach_evidence(run_id=RUN, timestamp_utc=STAMP, project_id=props.project_id,
            render_props_bytes=serialize_render_props(props), render_receipt_bytes=serialize_render_receipt(outcome.receipt),
            registry_records=(other,), storage_scope_id="cache", storage_policy_hash="sha256:" + "a" * 64,
            storage_admission="ADMITTED", domain_snapshot=snapshot,
            expected_policy_snapshot_id=snapshot.snapshot_id, expected_policy_snapshot_hash=snapshot.canonical_hash)
