"""Fail-closed attachment of accepted Phase 4/14/domain evidence to Phase 15."""
from __future__ import annotations

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.domain import policy_snapshot_hash
from engine.contracts.models import DomainPolicySnapshot
from engine.lifecycle import ArtifactRegistryRecord, registry_snapshot
from engine.rendering.bridge import load_render_props
from engine.rendering.receipt import RenderStatus, load_render_receipt
from engine.storage_manager import StoragePressurePolicy
from engine.validation.run_evidence import (
    RunObservation, artifact_registry_reference, build_observation,
    domain_snapshot_reference, failure_code_reference, render_receipt_reference,
    storage_admission_reference,
)


def _fail(code: str) -> None:
    raise ValueError(code)


def _snapshot_hash(snapshot: DomainPolicySnapshot) -> str:
    data = {name: getattr(snapshot, name) for name in DomainPolicySnapshot.__dataclass_fields__}
    return policy_snapshot_hash(data)


def _storage_policy_hash(policy: StoragePressurePolicy) -> str:
    if type(policy) is not StoragePressurePolicy:
        _fail("STORAGE_EVIDENCE_INVALID")
    policy.validate()
    import hashlib
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes({
        "storage_scope_id": policy.storage_scope_id,
        "hard_limit_bytes": policy.hard_limit_bytes,
        "minimum_free_bytes": policy.minimum_free_bytes,
    })).hexdigest()


def attach_evidence(*, run_id: str, timestamp_utc: str, project_id: str,
                    render_props_bytes: bytes, render_receipt_bytes: bytes,
                    registry_records: tuple[ArtifactRegistryRecord, ...],
                    storage_pressure_policy: StoragePressurePolicy,
                    storage_admission: str, domain_snapshot: DomainPolicySnapshot,
                    expected_policy_snapshot_id: str,
                    expected_policy_snapshot_hash: str,
                    first_ordinal: int = 1) -> tuple[RunObservation, ...]:
    """Return complete, ordered attachments or fail before emitting any row."""
    if (type(run_id) is not str or not run_id or type(project_id) is not str or not project_id
            or type(timestamp_utc) is not str or type(first_ordinal) is not int or first_ordinal < 1):
        _fail("ATTACHMENT_REQUEST_INVALID")
    try:
        props = load_render_props(render_props_bytes)
        receipt = load_render_receipt(render_receipt_bytes)
    except Exception as exc:
        raise ValueError("RENDER_EVIDENCE_INVALID") from exc
    if (props.project_id != project_id or receipt.render_request_id != props.render_request_id
            or receipt.render_props_id != props.render_props_id
            or receipt.render_props_hash != props.render_props_hash
            or receipt.video_edl_id != props.video_edl_id or receipt.video_edl_hash != props.video_edl_hash
            or receipt.audio_edl_id != props.audio_edl_id or receipt.audio_edl_hash != props.audio_edl_hash):
        _fail("RENDER_EVIDENCE_PROJECT_MISMATCH")
    try:
        registry_snapshot(registry_records)
    except Exception as exc:
        raise ValueError("ARTIFACT_EVIDENCE_INVALID") from exc
    if not registry_records or any(record.project_id != project_id for record in registry_records):
        _fail("ARTIFACT_EVIDENCE_INVALID")
    if receipt.status is RenderStatus.SUCCEEDED and receipt.output_artifact_id not in {record.artifact_id for record in registry_records}:
        _fail("ARTIFACT_OUTPUT_UNREGISTERED")
    if type(domain_snapshot) is not DomainPolicySnapshot:
        _fail("DOMAIN_CONTRACT_EVIDENCE_INVALID")
    if (domain_snapshot.snapshot_id != expected_policy_snapshot_id
            or domain_snapshot.canonical_hash != expected_policy_snapshot_hash
            or _snapshot_hash(domain_snapshot) != domain_snapshot.canonical_hash):
        _fail("DOMAIN_CONTRACT_MISMATCH")
    try:
        render_ref = render_receipt_reference(run_id=run_id, source=render_receipt_bytes)
        artifact_ref = artifact_registry_reference(run_id=run_id, records=registry_records)
        storage_policy_hash = _storage_policy_hash(storage_pressure_policy)
        storage_ref = storage_admission_reference(run_id=run_id, storage_scope_id=storage_pressure_policy.storage_scope_id,
            policy_hash=storage_policy_hash, status=storage_admission)
        domain_ref = domain_snapshot_reference(run_id=run_id, snapshot_id=domain_snapshot.snapshot_id,
            snapshot_hash=domain_snapshot.canonical_hash)
    except Exception as exc:
        raise ValueError("STORAGE_EVIDENCE_INVALID") from exc
    policy_hash = domain_snapshot.canonical_hash
    ordinal = first_ordinal
    rows: list[RunObservation] = []
    if receipt.status is RenderStatus.SUCCEEDED:
        rows.append(build_observation(run_id=run_id, ordinal=ordinal, timestamp_utc=timestamp_utc,
            category="render", event="attempt_finished", status="SUCCEEDED", producer="phase4",
            evidence_references=(render_ref,))); ordinal += 1
    else:
        code = receipt.failure_code or "RENDER_EVIDENCE_INVALID"
        rows.append(build_observation(run_id=run_id, ordinal=ordinal, timestamp_utc=timestamp_utc,
            category="render", event="attempt_finished", status=receipt.status.value, producer="phase4",
            evidence_references=(render_ref,), public_code=code)); ordinal += 1
    rows.append(build_observation(run_id=run_id, ordinal=ordinal, timestamp_utc=timestamp_utc,
        category="artifact", event="registry_verified", status="SUCCEEDED", producer="phase14",
        evidence_references=(artifact_ref,))); ordinal += 1
    storage_status = "ADMITTED" if storage_admission == "ADMITTED" else "NOT_APPLICABLE" if storage_admission == "NOT_APPLICABLE" else "BLOCKED"
    rows.append(build_observation(run_id=run_id, ordinal=ordinal, timestamp_utc=timestamp_utc,
        category="storage", event="admission_decided", status=storage_status, producer="phase14",
        evidence_references=(storage_ref,))); ordinal += 1
    rows.append(build_observation(run_id=run_id, ordinal=ordinal, timestamp_utc=timestamp_utc,
        category="domain", event="contract_resolved", status="SUCCEEDED", producer="domain_pack",
        evidence_references=(domain_ref,))); ordinal += 1
    for check_id, ref, status, code in (
        ("render_path", render_ref, "PASSED" if receipt.status is RenderStatus.SUCCEEDED else "FAILED", receipt.failure_code),
        ("artifact_lifecycle", artifact_ref, "PASSED", None),
        ("storage_pressure", storage_ref, "PASSED" if storage_status != "BLOCKED" else "FAILED", "STORAGE_ADMISSION_BLOCKED" if storage_status == "BLOCKED" else None),
        ("domain_contract", domain_ref, "PASSED", None),
    ):
        rows.append(build_observation(run_id=run_id, ordinal=ordinal, timestamp_utc=timestamp_utc,
            category="quality_gate", event="check_evaluated", status=status, producer="phase15",
            evidence_references=(ref,), check_id=check_id, policy_hash=policy_hash, public_code=code)); ordinal += 1
    if receipt.status is not RenderStatus.SUCCEEDED:
        failure_ref = failure_code_reference(run_id=run_id, code=receipt.failure_code or "RENDER_EVIDENCE_INVALID")
        rows.append(build_observation(run_id=run_id, ordinal=ordinal, timestamp_utc=timestamp_utc,
            category="quality_gate", event="check_evaluated", status="PASSED", producer="phase15",
            evidence_references=(failure_ref,), check_id="failure_provenance", policy_hash=policy_hash))
    return tuple(rows)
