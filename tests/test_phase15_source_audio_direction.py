from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from engine.acquisition import AssetRecordV1, MediaType, SourceAudioStatus
from engine.audio_director import (
    AudioDirectionPlanV1, AudioDirectorService, ChapterAudioDirectionV1,
    SourceAudioAnalysisV1, SourceAudioMode, audio_director_policy_from_snapshot,
)
from engine.contracts import DomainPackRegistry, DomainPolicyResolver, SchemaCatalog
from engine.validation.run_evidence import (
    EvidenceReference, build_observation, evaluate_quality_gate, serialize_jsonl,
)
from engine.validation.source_audio_direction import (
    source_audio_direction_reference, validate_source_audio_direction,
)


ROOT = Path(__file__).resolve().parents[1]
HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64
RUN = "run_source_audio"
TIMESTAMP = "2026-08-06T00:00:00Z"


def _snapshot():
    catalog = SchemaCatalog(ROOT / "shared-schemas" / "v3")
    registry = DomainPackRegistry([ROOT / "domain-packs", ROOT / "tests" / "fixtures" / "domain-packs"], catalog)
    registry.discover()
    profile = json.loads((ROOT / "samples" / "v3" / "business-tech" / "workspace.json").read_text(encoding="utf-8"))["domain"]["profile"]
    return DomainPolicyResolver(catalog).resolve(registry.get("business-tech", "0.1.0"), profile)[0]


def _asset(policy, *, status: SourceAudioStatus = SourceAudioStatus.ELIGIBLE, rights: bool = True) -> AssetRecordV1:
    return AssetRecordV1(
        "ast_phase15source", HASH_A, HASH_B, 1, MediaType.VIDEO, {"has_audio": True},
        {}, {}, "fam_phase15", (), (), None, None, (), (), (), (), (),
        {"status": status.value, "reason_tokens": ["rights_confirmed"] if rights else ["rights_unknown"],
         "evidence_ids": [], "policy_snapshot_id": policy.policy_snapshot_id,
         "policy_snapshot_hash": policy.policy_snapshot_hash},
        None, None,
    )


def _plan(policy, *, mode: SourceAudioMode = SourceAudioMode.CLEAN_SPEECH,
          source_speech: bool = True, analysis: SourceAudioAnalysisV1 | None = None) -> AudioDirectionPlanV1:
    row = analysis or AudioDirectorService().analyze(
        asset=_asset(policy), policy=policy, source_audio_mode=mode,
        speech_presence_bps=9_000, music_contamination_bps=1_000, noise_bps=500,
        speech_intelligibility_bps=9_000, recommended_duration_ms=3_000,
    )
    data = row.data(policy)
    events = ("music_start", "source_speech_in", "source_speech_out") if source_speech else ("music_start",)
    direction = ChapterAudioDirectionV1("chap_phase15", HASH_B, "medium", events,
        ((str(data["analysis_id"]), str(data["analysis_hash"])),))
    return AudioDirectionPlanV1("prj_phase15", policy, (direction,), (row,))


def _validate(policy, plan, assets):
    snapshot = _snapshot()
    return validate_source_audio_direction(
        run_id=RUN, timestamp_utc=TIMESTAMP, assets=assets, plan=plan,
        domain_snapshot=snapshot, expected_policy_snapshot_id=snapshot.snapshot_id,
        expected_policy_snapshot_hash=snapshot.canonical_hash,
    )


def test_eligible_clean_speech_is_hash_bound_and_passes_narrow_gate():
    snapshot = _snapshot(); policy = audio_director_policy_from_snapshot(snapshot)
    plan = _plan(policy)
    observation = _validate(policy, plan, (_asset(policy),))
    assert observation.check_id == "source_audio_safety"
    assert observation.evidence_references[0] == source_audio_direction_reference(run_id=RUN, plan=plan)
    assert evaluate_quality_gate(source=serialize_jsonl((observation,)),
        required_checks={"source_audio_safety": policy.policy_hash}).decision == "PASS"


@pytest.mark.parametrize("asset", [
    lambda policy: _asset(policy, status=SourceAudioStatus.INELIGIBLE),
    lambda policy: _asset(policy, rights=False),
])
def test_ineligible_or_no_rights_source_material_cannot_pass(asset):
    snapshot = _snapshot(); policy = audio_director_policy_from_snapshot(snapshot)
    observation = _validate(policy, _plan(policy), (asset(policy),))
    decision = evaluate_quality_gate(source=serialize_jsonl((observation,)),
        required_checks={"source_audio_safety": policy.policy_hash})
    assert (observation.status, observation.public_code, decision.decision) == (
        "FAILED", "SOURCE_AUDIO_ANALYSIS_DENIED", "FAIL")


def test_forged_clean_speech_contamination_cannot_bypass_service_recomputation():
    snapshot = _snapshot(); policy = audio_director_policy_from_snapshot(snapshot)
    forged = SourceAudioAnalysisV1("ast_phase15source", HASH_A, SourceAudioMode.CLEAN_SPEECH,
        9_000, 9_000, 0, 9_000, 3_000, "pause", "hard_duck")
    observation = _validate(policy, _plan(policy, analysis=forged), (_asset(policy),))
    assert observation.status == "FAILED"
    assert observation.public_code == "SOURCE_AUDIO_ANALYSIS_DENIED"


def test_non_speech_direction_is_only_a_narrow_policy_pass():
    snapshot = _snapshot(); policy = audio_director_policy_from_snapshot(snapshot)
    plan = _plan(policy, mode=SourceAudioMode.EMBEDDED_MUSIC, source_speech=False)
    observation = _validate(policy, plan, (_asset(policy),))
    assert observation.status == "PASSED" and observation.public_code is None


def test_embedded_music_and_mismatched_assets_cannot_pass():
    snapshot = _snapshot(); policy = audio_director_policy_from_snapshot(snapshot)
    with pytest.raises(ValueError, match="PLAN_INVALID"):
        _validate(policy, _plan(policy, mode=SourceAudioMode.EMBEDDED_MUSIC), (_asset(policy),))
    observation = _validate(policy, _plan(policy), (replace(_asset(policy), asset_id="ast_other"),))
    assert (observation.status, observation.public_code) == ("FAILED", "SOURCE_AUDIO_ASSET_MISMATCH")


def test_mismatched_snapshot_and_unknown_reference_kind_fail_closed():
    snapshot = _snapshot(); policy = audio_director_policy_from_snapshot(snapshot)
    with pytest.raises(ValueError, match="POLICY_MISMATCH"):
        validate_source_audio_direction(run_id=RUN, timestamp_utc=TIMESTAMP,
            assets=(_asset(policy),), plan=_plan(policy), domain_snapshot=snapshot,
            expected_policy_snapshot_id="dps_wrong", expected_policy_snapshot_hash=snapshot.canonical_hash)
    reference = EvidenceReference("PHASE15-EVIDENCE-REFERENCE-V1", "unknown", "ref", HASH_A, RUN)
    with pytest.raises(ValueError, match="EVIDENCE_REFERENCE_INVALID"):
        build_observation(run_id=RUN, ordinal=1, timestamp_utc=TIMESTAMP,
            category="quality_gate", event="check_evaluated", status="PASSED",
            producer="phase15", evidence_references=(reference,),
            check_id="source_audio_safety", policy_hash=policy.policy_hash)
