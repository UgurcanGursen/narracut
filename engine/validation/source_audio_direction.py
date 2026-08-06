"""Phase 15 validation of Phase 8/11 source-audio direction; no mixing."""
from __future__ import annotations

from engine.acquisition import AssetRecordV1
from engine.audio_director import (
    AudioDirectionPlanV1, AudioDirectorError, AudioDirectorService,
    AudioDirectorPolicyV1, SourceAudioMode, audio_director_policy_from_snapshot,
    canonical_audio_direction_json,
)
from engine.contracts.models import DomainPolicySnapshot
from engine.validation.run_evidence import EvidenceReference, RunObservation, build_observation


def _fail(code: str) -> None:
    raise ValueError(code)


def source_audio_direction_reference(*, run_id: str, plan: AudioDirectionPlanV1) -> EvidenceReference:
    if type(plan) is not AudioDirectionPlanV1:
        _fail("SOURCE_AUDIO_DIRECTION_PLAN_INVALID")
    try:
        data = plan.data()
        canonical_audio_direction_json(plan)
    except Exception as exc:
        raise ValueError("SOURCE_AUDIO_DIRECTION_PLAN_INVALID") from exc
    return EvidenceReference(
        "PHASE15-EVIDENCE-REFERENCE-V1",
        "source_audio_direction",
        str(data["audio_direction_plan_id"]),
        str(data["audio_direction_plan_hash"]),
        run_id,
    )


def _policy(*, snapshot: DomainPolicySnapshot, expected_id: str, expected_hash: str) -> AudioDirectorPolicyV1:
    if type(snapshot) is not DomainPolicySnapshot:
        _fail("SOURCE_AUDIO_SNAPSHOT_INVALID")
    if (snapshot.snapshot_id, snapshot.canonical_hash) != (expected_id, expected_hash):
        _fail("SOURCE_AUDIO_POLICY_MISMATCH")
    try:
        return audio_director_policy_from_snapshot(snapshot)
    except Exception as exc:
        raise ValueError("SOURCE_AUDIO_SNAPSHOT_INVALID") from exc


def _assets(value: object) -> dict[tuple[str, str], AssetRecordV1]:
    if type(value) is not tuple or not value or any(type(item) is not AssetRecordV1 for item in value):
        _fail("SOURCE_AUDIO_ASSETS_INVALID")
    result = {(item.asset_id, item.asset_hash): item for item in value}
    if len(result) != len(value):
        _fail("SOURCE_AUDIO_ASSETS_INVALID")
    return result


def _recompute(*, plan: AudioDirectionPlanV1, policy: AudioDirectorPolicyV1,
               assets: dict[tuple[str, str], AssetRecordV1]) -> str | None:
    if plan.policy != policy:
        _fail("SOURCE_AUDIO_POLICY_MISMATCH")
    try:
        plan.data()
        canonical_audio_direction_json(plan)
    except Exception as exc:
        raise ValueError("SOURCE_AUDIO_DIRECTION_PLAN_INVALID") from exc
    by_id: dict[str, object] = {}
    for analysis in plan.analyses:
        asset = assets.get((analysis.asset_id, analysis.asset_hash))
        if asset is None:
            return "SOURCE_AUDIO_ASSET_MISMATCH"
        try:
            reconstructed = AudioDirectorService().analyze(
                asset=asset, policy=policy, source_audio_mode=analysis.source_audio_mode,
                speech_presence_bps=analysis.speech_presence_bps,
                music_contamination_bps=analysis.music_contamination_bps,
                noise_bps=analysis.noise_bps,
                speech_intelligibility_bps=analysis.speech_intelligibility_bps,
                recommended_duration_ms=analysis.recommended_duration_ms,
            )
            if reconstructed.data(policy) != analysis.data(policy):
                return "SOURCE_AUDIO_ANALYSIS_MISMATCH"
            row = analysis.data(policy)
        except AudioDirectorError:
            return "SOURCE_AUDIO_ANALYSIS_DENIED"
        by_id[str(row["analysis_id"])] = analysis
    for direction in plan.directions:
        events = set(direction.event_type_tokens)
        if not events.intersection({"source_speech_in", "source_speech_out"}):
            continue
        speech = [by_id.get(pair[0]) for pair in direction.source_analysis_id_hash_pairs]
        speech = [item for item in speech if getattr(item, "source_audio_mode", None) in {
            SourceAudioMode.CLEAN_SPEECH, SourceAudioMode.SPEECH_WITH_AMBIENCE,
        }]
        if not speech:
            return "SOURCE_AUDIO_DIRECTION_DENIED"
        if any(item.narration_conflict_policy != "pause" or item.bgm_conflict_policy not in {"hard_duck", "mute"} for item in speech):
            return "SOURCE_AUDIO_DIRECTION_DENIED"
    return None


def validate_source_audio_direction(*, run_id: str, timestamp_utc: str,
                                    assets: tuple[AssetRecordV1, ...],
                                    plan: AudioDirectionPlanV1,
                                    domain_snapshot: DomainPolicySnapshot,
                                    expected_policy_snapshot_id: str,
                                    expected_policy_snapshot_hash: str,
                                    first_ordinal: int = 1) -> RunObservation:
    """Emit one narrow policy-direction check; it never opens or mixes media."""
    if (type(run_id) is not str or not run_id or type(timestamp_utc) is not str
            or type(first_ordinal) is not int or first_ordinal < 1):
        _fail("SOURCE_AUDIO_REQUEST_INVALID")
    policy = _policy(snapshot=domain_snapshot, expected_id=expected_policy_snapshot_id,
                     expected_hash=expected_policy_snapshot_hash)
    asset_map = _assets(assets)
    reference = source_audio_direction_reference(run_id=run_id, plan=plan)
    code = _recompute(plan=plan, policy=policy, assets=asset_map)
    return build_observation(
        run_id=run_id, ordinal=first_ordinal, timestamp_utc=timestamp_utc,
        category="quality_gate", event="check_evaluated",
        status="PASSED" if code is None else "FAILED", producer="phase15",
        evidence_references=(reference,), check_id="source_audio_safety",
        policy_hash=policy.policy_hash, public_code=code,
    )
