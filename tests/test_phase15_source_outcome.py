from engine.acquisition.source_engine import (
    AccessStatus, AccessibleHtmlAdapter, AcquisitionAdapterId, DOMRegion,
    ReplaySourcePackage, SourceAdapterRegistry, SourcePriorityPolicy, SourceType,
)
from engine.validation.run_evidence import evaluate_quality_gate, serialize_jsonl
from engine.validation.source_outcome import validate_source_outcome


HASH = "sha256:" + "a" * 64
POLICY = SourcePriorityPolicy("SOURCE-PRIORITY-POLICY-V1", (SourceType.OFFICIAL_REPORT,), (), "dps_phase15", HASH)


def _plan(status):
    package = ReplaySourcePackage("source_phase15", SourceType.OFFICIAL_REPORT, AcquisitionAdapterId.ACCESSIBLE_HTML,
        "https://example.test/report", status, "Report", "2026-08-06", "headline", "headline", None,
        (DOMRegion("/html/body/h1", "headline", 0, 0, 1_000_000, 1_000_000),))
    return SourceAdapterRegistry((AccessibleHtmlAdapter(),)).acquire(package)


def test_replay_success_and_challenge_are_truthful():
    success = validate_source_outcome(run_id="run_source", timestamp_utc="2026-08-06T00:00:00Z", plan=_plan(AccessStatus.ACCESSIBLE), policy=POLICY, expected_policy_snapshot_id="dps_phase15", expected_policy_snapshot_hash=HASH, execution_mode="REPLAY")
    assert evaluate_quality_gate(source=serialize_jsonl(success), required_checks={"source_outcome": HASH}).decision == "PASS"
    challenge = validate_source_outcome(run_id="run_source", timestamp_utc="2026-08-06T00:00:00Z", plan=_plan(AccessStatus.CHALLENGE_DETECTED), policy=POLICY, expected_policy_snapshot_id="dps_phase15", expected_policy_snapshot_hash=HASH, execution_mode="REPLAY")
    assert evaluate_quality_gate(source=serialize_jsonl(challenge), required_checks={"source_outcome": HASH}).decision == "NOT_READY"


def test_unsupported_mode_never_passes():
    rows = validate_source_outcome(run_id="run_source", timestamp_utc="2026-08-06T00:00:00Z", plan=_plan(AccessStatus.ACCESSIBLE), policy=POLICY, expected_policy_snapshot_id="dps_phase15", expected_policy_snapshot_hash=HASH, execution_mode="API")
    assert evaluate_quality_gate(source=serialize_jsonl(rows), required_checks={"source_outcome": HASH}).decision == "NOT_READY"
