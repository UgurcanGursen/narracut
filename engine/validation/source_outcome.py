"""Phase 15 validation of existing Phase 6 source outcomes; no transport."""
from __future__ import annotations

from engine.acquisition.source_engine import (
    ACCESS_STATUS_FALLBACKS, AccessStatus, FallbackMode, SourceCapturePlan,
    SourcePriorityPolicy, _validate_capture_plan,
)
from engine.validation.run_evidence import EvidenceReference, RunObservation, build_observation


def _fail(code: str) -> None: raise ValueError(code)


def source_capture_reference(*, run_id: str, plan: SourceCapturePlan) -> EvidenceReference:
    try: value = _validate_capture_plan(plan)
    except Exception as exc: raise ValueError("SOURCE_OUTCOME_PLAN_INVALID") from exc
    return EvidenceReference("PHASE15-EVIDENCE-REFERENCE-V1", "source_capture", value.source_capture_plan_id, value.source_capture_plan_hash, run_id)


def validate_source_outcome(*, run_id: str, timestamp_utc: str, plan: SourceCapturePlan,
                            policy: SourcePriorityPolicy, expected_policy_snapshot_id: str,
                            expected_policy_snapshot_hash: str, execution_mode: str,
                            first_ordinal: int = 1) -> tuple[RunObservation, RunObservation]:
    if type(run_id) is not str or not run_id or type(timestamp_utc) is not str or type(first_ordinal) is not int or first_ordinal < 1:
        _fail("SOURCE_OUTCOME_REQUEST_INVALID")
    try: plan = _validate_capture_plan(plan)
    except Exception as exc: raise ValueError("SOURCE_OUTCOME_PLAN_INVALID") from exc
    if (type(policy) is not SourcePriorityPolicy or (policy.policy_snapshot_id, policy.policy_snapshot_hash) != (expected_policy_snapshot_id, expected_policy_snapshot_hash)):
        _fail("SOURCE_OUTCOME_POLICY_MISMATCH")
    if ACCESS_STATUS_FALLBACKS.get(plan.access_status) is not plan.fallback_mode:
        _fail("SOURCE_OUTCOME_FALLBACK_INVALID")
    if plan.access_status is AccessStatus.SNAPSHOT_AVAILABLE and plan.snapshot_hash is None:
        _fail("SOURCE_OUTCOME_SNAPSHOT_MISSING")
    blocked = plan.access_status in {AccessStatus.CHALLENGE_DETECTED, AccessStatus.PAYWALL_DETECTED, AccessStatus.COOKIE_WALL_DETECTED, AccessStatus.AUTHENTICATION_REQUIRED, AccessStatus.MANUAL_CAPTURE_REQUIRED}
    if blocked and (plan.snapshot_hash is not None or plan.fallback_mode is not FallbackMode.MANUAL_CAPTURE_PACKAGE):
        _fail("SOURCE_OUTCOME_CHALLENGE_FORBIDDEN")
    ref = source_capture_reference(run_id=run_id, plan=plan)
    if execution_mode not in {"REPLAY", "MANUAL_UI", "DISABLED"}:
        transport = build_observation(run_id=run_id, ordinal=first_ordinal, timestamp_utc=timestamp_utc, category="transport", event="mode_declared", status="UNSUPPORTED", producer="phase15", evidence_references=())
        check = build_observation(run_id=run_id, ordinal=first_ordinal + 1, timestamp_utc=timestamp_utc, category="quality_gate", event="check_evaluated", status="UNSUPPORTED", producer="phase15", evidence_references=(ref,), check_id="source_outcome", policy_hash=policy.policy_snapshot_hash, public_code="SOURCE_OUTCOME_MODE_UNSUPPORTED")
        return transport, check
    if blocked:
        status, code = "NOT_READY", "MANUAL_CAPTURE_REQUIRED"
    elif plan.access_status is AccessStatus.UNAVAILABLE:
        status, code = "FAILED", "SOURCE_UNAVAILABLE"
    elif plan.access_status is AccessStatus.TEXT_NOT_FOUND:
        status, code = "WARNING", "TEXT_ONLY_EVIDENCE"
    else:
        status, code = "PASSED", None
    transport = build_observation(run_id=run_id, ordinal=first_ordinal, timestamp_utc=timestamp_utc, category="transport", event="mode_declared", status=execution_mode, producer="phase15", evidence_references=())
    check = build_observation(run_id=run_id, ordinal=first_ordinal + 1, timestamp_utc=timestamp_utc, category="quality_gate", event="check_evaluated", status=status, producer="phase15", evidence_references=(ref,), check_id="source_outcome", policy_hash=policy.policy_snapshot_hash, public_code=code)
    return transport, check
