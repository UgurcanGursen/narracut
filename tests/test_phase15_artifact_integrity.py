from __future__ import annotations

import pytest

from engine.lifecycle import ArtifactRegistryRecord, plan_deletion
from engine.validation.artifact_integrity import validate_artifact_integrity
from engine.validation.run_evidence import evaluate_quality_gate, serialize_jsonl


HASH = "sha256:" + "a" * 64
RUN = "run_artifact_integrity"
STAMP = "2026-08-06T00:00:00Z"


def _record(identifier: str, *, dependencies: tuple[str, ...] = (), content_hash: str = HASH) -> ArtifactRegistryRecord:
    return ArtifactRegistryRecord.materialize({"artifact_id": identifier, "project_id": "prj_phase15",
        "content_hash": content_hash, "size_bytes": 1, "retention_class": "temporary",
        "dependency_ids": dependencies, "locked": False, "pinned": False, "approved": False,
        "producer": "phase14", "producer_version": "1"})


def _inputs():
    dependency = _record("art_dependency")
    output = _record("art_output", dependencies=("art_dependency",))
    free = _record("art_free", content_hash="sha256:" + "b" * 64)
    records = (dependency, output, free)
    roots = frozenset({"art_output"})
    plan = plan_deletion(records=records, policy_hash=HASH, as_of=STAMP, root_ids=roots)
    return records, roots, plan


def _validate(records, roots, plan, *, output_id="art_output", output_hash=HASH):
    return validate_artifact_integrity(run_id=RUN, timestamp_utc=STAMP, records=records,
        project_id="prj_phase15", expected_output_id=output_id, expected_output_content_hash=output_hash,
        deletion_policy_hash=HASH, protected_root_ids=roots, plan=plan)


def test_registry_bound_output_and_canonical_protected_plan_pass():
    records, roots, plan = _inputs()
    observation = _validate(records, roots, plan)
    assert observation.status == "PASSED"
    assert [row["artifact_id"] for row in plan["candidates"]] == ["art_free"]
    assert evaluate_quality_gate(source=serialize_jsonl((observation,)),
        required_checks={"artifact_integrity": HASH}).decision == "PASS"


def test_unregistered_output_and_forged_plan_cannot_pass():
    records, roots, plan = _inputs()
    missing = _validate(records, roots, plan, output_id="art_missing")
    assert (missing.status, missing.public_code) == ("FAILED", "ARTIFACT_OUTPUT_UNREGISTERED")
    forged = dict(plan); forged["candidates"] = []
    invalid = _validate(records, roots, forged)
    assert (invalid.status, invalid.public_code) == ("FAILED", "ARTIFACT_DELETION_PLAN_INVALID")


def test_protected_transitive_dependency_in_candidate_cannot_pass():
    records, roots, plan = _inputs()
    forged = dict(plan); forged["candidates"] = [dict(plan["candidates"][0]), {
        "artifact_id": "art_dependency", "content_hash": HASH, "size_bytes": 1,
        "reason": "UNREFERENCED_RETENTION_ELIGIBLE", "trash_token": "trash/forged"}]
    observation = _validate(records, roots, forged)
    assert (observation.status, observation.public_code) == ("FAILED", "ARTIFACT_DELETION_PLAN_INVALID")


def test_cross_project_or_invalid_inputs_fail_closed():
    records, roots, plan = _inputs()
    other = ArtifactRegistryRecord.materialize({"artifact_id": "art_other", "project_id": "prj_other",
        "content_hash": HASH, "size_bytes": 1, "retention_class": "temporary", "dependency_ids": (),
        "locked": False, "pinned": False, "approved": False, "producer": "phase14", "producer_version": "1"})
    with pytest.raises(ValueError, match="PROJECT_MISMATCH"):
        _validate(records + (other,), roots, plan)
    with pytest.raises(ValueError, match="INPUT_INVALID"):
        validate_artifact_integrity(run_id=RUN, timestamp_utc=STAMP, records=records,
            project_id="prj_phase15", expected_output_id="art_output", expected_output_content_hash=HASH,
            deletion_policy_hash=HASH, protected_root_ids=frozenset(), plan=plan)
