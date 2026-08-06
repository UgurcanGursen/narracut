"""Phase 15 registry/deletion-plan integrity validation; no filesystem access."""
from __future__ import annotations

import hashlib
from typing import Mapping

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.lifecycle import ArtifactRegistryRecord, plan_deletion, registry_snapshot
from engine.validation.run_evidence import EvidenceReference, RunObservation, build_observation


def _fail(code: str) -> None:
    raise ValueError(code)


def _hash(value: object) -> str:
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _inputs(*, records: object, project_id: object, expected_output_id: object,
            expected_output_content_hash: object, deletion_policy_hash: object,
            protected_root_ids: object, plan: object) -> tuple[tuple[ArtifactRegistryRecord, ...], str, str, str, str, frozenset[str], Mapping[str, object]]:
    if (type(records) is not tuple or not records or any(type(item) is not ArtifactRegistryRecord for item in records)
            or any(type(item) is not str or not item for item in (project_id, expected_output_id, expected_output_content_hash, deletion_policy_hash))
            or type(protected_root_ids) is not frozenset or not protected_root_ids
            or not all(type(item) is str and item for item in protected_root_ids)
            or not isinstance(plan, Mapping) or type(plan.get("as_of")) is not str):
        _fail("ARTIFACT_INTEGRITY_INPUT_INVALID")
    try:
        registry_snapshot(records)
    except Exception as exc:
        raise ValueError("ARTIFACT_INTEGRITY_REGISTRY_INVALID") from exc
    if any(item.project_id != project_id for item in records):
        _fail("ARTIFACT_INTEGRITY_PROJECT_MISMATCH")
    return records, project_id, expected_output_id, expected_output_content_hash, deletion_policy_hash, protected_root_ids, plan


def artifact_integrity_reference(*, run_id: str, records: tuple[ArtifactRegistryRecord, ...],
                                 project_id: str, expected_output_id: str,
                                 expected_output_content_hash: str,
                                 deletion_policy_hash: str, protected_root_ids: frozenset[str],
                                 plan: Mapping[str, object]) -> EvidenceReference:
    snapshot = registry_snapshot(records)
    value = {
        "registry_snapshot_hash": snapshot, "project_id": project_id,
        "expected_output_id": expected_output_id,
        "expected_output_content_hash": expected_output_content_hash,
        "deletion_policy_hash": deletion_policy_hash,
        "protected_root_ids": sorted(protected_root_ids),
        "plan_id": plan.get("plan_id"), "plan_hash": plan.get("plan_hash"),
    }
    digest = _hash(value)
    return EvidenceReference("PHASE15-EVIDENCE-REFERENCE-V1", "artifact_integrity",
                             "integrity_" + digest[7:39], digest, run_id)


def validate_artifact_integrity(*, run_id: str, timestamp_utc: str,
                                records: tuple[ArtifactRegistryRecord, ...], project_id: str,
                                expected_output_id: str, expected_output_content_hash: str,
                                deletion_policy_hash: str, protected_root_ids: frozenset[str],
                                plan: Mapping[str, object], first_ordinal: int = 1) -> RunObservation:
    """Return one registry-bound quality check without reading or changing files."""
    if type(run_id) is not str or not run_id or type(timestamp_utc) is not str or type(first_ordinal) is not int or first_ordinal < 1:
        _fail("ARTIFACT_INTEGRITY_REQUEST_INVALID")
    records, project_id, expected_output_id, expected_output_content_hash, deletion_policy_hash, protected_root_ids, plan = _inputs(
        records=records, project_id=project_id, expected_output_id=expected_output_id,
        expected_output_content_hash=expected_output_content_hash, deletion_policy_hash=deletion_policy_hash,
        protected_root_ids=protected_root_ids, plan=plan)
    reference = artifact_integrity_reference(run_id=run_id, records=records, project_id=project_id,
        expected_output_id=expected_output_id, expected_output_content_hash=expected_output_content_hash,
        deletion_policy_hash=deletion_policy_hash, protected_root_ids=protected_root_ids, plan=plan)
    output = next((item for item in records if item.artifact_id == expected_output_id), None)
    if output is None or output.content_hash != expected_output_content_hash:
        code = "ARTIFACT_OUTPUT_UNREGISTERED"
    else:
        try:
            expected = plan_deletion(records=records, policy_hash=deletion_policy_hash,
                                     as_of=plan["as_of"], root_ids=protected_root_ids)
            code = None if dict(plan) == expected else "ARTIFACT_DELETION_PLAN_INVALID"
        except Exception:
            code = "ARTIFACT_DELETION_PLAN_INVALID"
    return build_observation(run_id=run_id, ordinal=first_ordinal, timestamp_utc=timestamp_utc,
        category="quality_gate", event="check_evaluated", status="PASSED" if code is None else "FAILED",
        producer="phase15", evidence_references=(reference,), check_id="artifact_integrity",
        policy_hash=deletion_policy_hash, public_code=code)
