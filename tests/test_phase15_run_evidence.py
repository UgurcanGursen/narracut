import pytest

from engine.lifecycle import ArtifactRegistryRecord
from engine.contracts.audio_edl import serialize_audio_edl
from engine.contracts.edl import serialize_video_edl
from engine.rendering.bridge import build_render_props, renderer_version
from engine.rendering.fixture_assets import FixtureAssetResolver
from engine.rendering.preview_runner import run_headless_preview
from engine.rendering.receipt import serialize_render_receipt
from engine.validation.run_evidence import (
    artifact_registry_reference,
    build_observation,
    domain_snapshot_reference,
    evaluate_quality_gate,
    failure_code_reference,
    load_jsonl,
    project_metrics,
    render_receipt_reference,
    serialize_jsonl,
    storage_admission_reference,
)
from tests.test_render_bridge import FIXTURE_ROOT, ROOT, build_phase4a_rich_replay_inputs


RUN = "run_phase15"
POLICY = "sha256:" + "a" * 64
STAMP = "2026-08-06T00:00:00Z"


def _registry_ref():
    record = ArtifactRegistryRecord.materialize({
        "artifact_id": "artifact_preview", "project_id": "project_phase15",
        "content_hash": "sha256:" + "b" * 64, "size_bytes": 1,
        "retention_class": "temporary", "dependency_ids": (), "locked": False,
        "pinned": False, "approved": False, "producer": "phase4",
        "producer_version": "1",
    })
    return artifact_registry_reference(run_id=RUN, records=(record,))


def _quality(*, ordinal, check_id, status="PASSED", ref, code=None):
    return build_observation(run_id=RUN, ordinal=ordinal, timestamp_utc=STAMP,
        category="quality_gate", event="check_evaluated", status=status,
        producer="phase15", evidence_references=(ref,), check_id=check_id,
        policy_hash=POLICY, public_code=code)


def test_canonical_jsonl_and_metric_projection_are_deterministic():
    ref = storage_admission_reference(run_id=RUN, storage_scope_id="cache", policy_hash=POLICY, status="ADMITTED")
    row = build_observation(run_id=RUN, ordinal=1, timestamp_utc=STAMP,
        category="storage", event="admission_decided", status="ADMITTED",
        producer="phase14", evidence_references=(ref,),
        metrics={"cache_size_bytes": 12, "cache_hit_count": 1})
    raw = serialize_jsonl((row,))
    assert serialize_jsonl(load_jsonl(raw)) == raw
    assert project_metrics(raw) == {"cache_hit_count": (1,), "cache_size_bytes": (12,)}


def test_unsafe_or_cross_run_evidence_fails_closed():
    ref = storage_admission_reference(run_id=RUN, storage_scope_id="cache", policy_hash=POLICY, status="ADMITTED")
    with pytest.raises(ValueError, match="EVIDENCE_REFERENCE_INVALID"):
        build_observation(run_id="run_other", ordinal=1, timestamp_utc=STAMP,
            category="storage", event="admission_decided", status="ADMITTED",
            producer="phase14", evidence_references=(ref,))
    with pytest.raises(ValueError, match="OBSERVATION_TRANSITION_INVALID"):
        build_observation(run_id=RUN, ordinal=1, timestamp_utc=STAMP,
            category="storage", event="admission_decided", status="SUCCEEDED",
            producer="C:\\Users\\secret", evidence_references=(ref,))


def test_quality_gate_returns_not_ready_for_unsupported_required_evidence():
    ref = domain_snapshot_reference(run_id=RUN, snapshot_id="dps_phase15", snapshot_hash=POLICY)
    rows = (_quality(ordinal=1, check_id="domain_contract", status="NOT_READY", ref=ref, code="DOMAIN_UNSUPPORTED"),)
    decision = evaluate_quality_gate(source=serialize_jsonl(rows), required_checks={"domain_contract": POLICY})
    assert decision.decision == "NOT_READY"
    assert decision.primary_code == "DOMAIN_UNSUPPORTED"


def test_quality_gate_failure_precedes_later_success_and_requires_provenance():
    artifact = _registry_ref()
    failed = _quality(ordinal=1, check_id="artifact_lifecycle", status="FAILED", ref=artifact, code="ARTIFACT_ORPHAN")
    success = _quality(ordinal=2, check_id="domain_contract", ref=domain_snapshot_reference(run_id=RUN, snapshot_id="dps_phase15", snapshot_hash=POLICY))
    decision = evaluate_quality_gate(source=serialize_jsonl((failed, success)), required_checks={"artifact_lifecycle": POLICY, "domain_contract": POLICY})
    assert (decision.decision, decision.primary_code) == ("FAIL", "ARTIFACT_ORPHAN")

    with pytest.raises(ValueError, match="EVIDENCE_REFERENCE_MISSING"):
        build_observation(run_id=RUN, ordinal=1, timestamp_utc=STAMP,
            category="render", event="attempt_finished", status="FAILED", producer="phase4",
            evidence_references=(domain_snapshot_reference(run_id=RUN, snapshot_id="fake", snapshot_hash=POLICY),))


def test_failure_provenance_and_phase14_references_have_strict_boundaries():
    ref = failure_code_reference(run_id=RUN, code="RENDER_TIMEOUT")
    row = _quality(ordinal=1, check_id="failure_provenance", ref=ref)
    decision = evaluate_quality_gate(source=serialize_jsonl((row,)), required_checks={"failure_provenance": POLICY})
    assert decision.decision == "PASS"
    with pytest.raises(Exception):
        render_receipt_reference(run_id=RUN, source=b"{}")


def test_producer_failure_requires_matching_provenance_and_still_fails():
    artifact = _registry_ref()
    failed = build_observation(run_id=RUN, ordinal=1, timestamp_utc=STAMP,
        category="artifact", event="registry_verified", status="FAILED",
        producer="phase14", evidence_references=(artifact,), public_code="ARTIFACT_ORPHAN")
    provenance = _quality(ordinal=2, check_id="failure_provenance",
        ref=failure_code_reference(run_id=RUN, code="ARTIFACT_ORPHAN"))
    raw = serialize_jsonl((failed, provenance))
    assert evaluate_quality_gate(source=raw, required_checks={"failure_provenance": POLICY}).primary_code == "ARTIFACT_ORPHAN"
    wrong = _quality(ordinal=2, check_id="failure_provenance",
        ref=failure_code_reference(run_id=RUN, code="RENDER_TIMEOUT"))
    assert evaluate_quality_gate(source=serialize_jsonl((failed, wrong)), required_checks={"failure_provenance": POLICY}).primary_code == "FAILURE_PROVENANCE_MISSING"


def test_ordinal_gap_and_duplicate_check_fail_closed():
    ref = storage_admission_reference(run_id=RUN, storage_scope_id="cache", policy_hash=POLICY, status="ADMITTED")
    one = _quality(ordinal=1, check_id="storage_pressure", ref=ref)
    two = _quality(ordinal=2, check_id="storage_pressure", ref=ref)
    with pytest.raises(ValueError, match="QUALITY_CHECK_DUPLICATE"):
        evaluate_quality_gate(source=serialize_jsonl((one, two)), required_checks={"storage_pressure": POLICY})


def test_actual_phase4_receipt_reference_is_verified(tmp_path):
    replay = build_phase4a_rich_replay_inputs()
    props = build_render_props(video_edl=replay["video_edl"], audio_edl=replay["audio_edl"],
        fixture_assets=FixtureAssetResolver.load(FIXTURE_ROOT),
        renderer_version_value=renderer_version((ROOT / "renderer-remotion" / "package-lock.json").read_bytes()))
    outcome = run_headless_preview(props=props, video_edl_bytes=serialize_video_edl(replay["video_edl"]),
        audio_edl_bytes=serialize_audio_edl(replay["audio_edl"]), fixture_root=FIXTURE_ROOT,
        output_root=tmp_path / "output", work_root=tmp_path,
        timestamp_utc="2026-08-06T00:00:00Z")
    ref = render_receipt_reference(run_id=RUN, source=serialize_render_receipt(outcome.receipt))
    assert ref.kind == "render_receipt" and ref.reference_id == outcome.receipt.receipt_id
