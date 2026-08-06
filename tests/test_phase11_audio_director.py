from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.acquisition import AssetRecordV1, MediaType, SourceAudioStatus
from engine.audio_director import (
    SAMPLE_RATE_HZ,
    AudioDirectionPlanV1,
    AudioDirectorError,
    AudioDirectorService,
    ChapterAudioDirectionV1,
    SourceAudioAnalysisV1,
    SourceAudioMode,
    audio_director_policy_from_snapshot,
    canonical_audio_direction_json,
)
from engine.contracts import DomainPackRegistry, DomainPolicyResolver, SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]
HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64


def _snapshot(pack: str = "business-tech"):
    catalog = SchemaCatalog(ROOT / "shared-schemas" / "v3")
    registry = DomainPackRegistry(
        [ROOT / "domain-packs", ROOT / "tests" / "fixtures" / "domain-packs"],
        catalog,
    )
    registry.discover()
    if pack == "dummy":
        profile = {
            "schema_version": "3.0.0", "profile_id": "dpf_dummy",
            "domain_id": "dummy-domain", "domain_pack_version": "1.0.0",
            "enabled_extensions": [], "policy_overrides": {}, "status": "ready", "version": 1,
        }
        return DomainPolicyResolver(catalog).resolve(
            registry.get("dummy-domain", "1.0.0"), profile,
        )[0]
    profile = json.loads(
        (ROOT / "samples" / "v3" / "business-tech" / "workspace.json").read_text(encoding="utf-8"),
    )["domain"]["profile"]
    return DomainPolicyResolver(catalog).resolve(registry.get(pack, "0.1.0"), profile)[0]


def _asset(policy, *, status: SourceAudioStatus = SourceAudioStatus.ELIGIBLE, rights: bool = True) -> AssetRecordV1:
    return AssetRecordV1(
        asset_id="ast_phase11source", asset_hash=HASH_A, source_hash=HASH_B,
        source_byte_length=1, media_type=MediaType.VIDEO, media_facts={"has_audio": True},
        source_descriptor={}, fingerprint_evidence={}, visual_family_id="fam_phase11",
        subjects=(), actions=(), setting=None, mood=None, semantic_tags=(), avoid_contexts=(),
        domain_roles=(), domain_sensitivity_tags=(), selected_ranges=(),
        source_audio_eligibility={
            "status": status.value,
            "reason_tokens": ["rights_confirmed"] if rights else ["rights_unknown"],
            "evidence_ids": [], "policy_snapshot_id": policy.policy_snapshot_id,
            "policy_snapshot_hash": policy.policy_snapshot_hash,
        },
        duplicate_of_asset_id=None, duplicate_of_asset_hash=None,
    )


def _plan(policy, mode: SourceAudioMode = SourceAudioMode.CLEAN_SPEECH) -> AudioDirectionPlanV1:
    analysis = AudioDirectorService().analyze(
        asset=_asset(policy), policy=policy, source_audio_mode=mode,
        speech_presence_bps=9_000, music_contamination_bps=1_000,
        noise_bps=500, speech_intelligibility_bps=9_000, recommended_duration_ms=3_000,
    )
    row = analysis.data(policy)
    speech_events = ("music_start", "source_speech_in", "source_speech_out") if mode is SourceAudioMode.CLEAN_SPEECH else ("music_start",)
    direction = ChapterAudioDirectionV1(
        "chap_phase11", HASH_B, "medium", speech_events,
        ((str(row["analysis_id"]), str(row["analysis_hash"])),),
    )
    return AudioDirectionPlanV1("prj_phase11", policy, (direction,), (analysis,))


def test_audio_direction_plan_is_snapshot_bound_deterministic_and_pcm_48k() -> None:
    policy = audio_director_policy_from_snapshot(_snapshot())
    plan = _plan(policy)
    first, second = plan.data(), _plan(policy).data()
    assert first == second
    assert first["sample_rate_hz"] == SAMPLE_RATE_HZ == 48_000
    assert first["intermediate_format"] == "pcm"
    assert "edl" not in first and "renderer" not in first and "asset_selection" not in first
    assert canonical_audio_direction_json(plan) == canonical_audio_direction_json(_plan(policy))


def test_source_speech_requires_phase8_eligible_rights_confirmed_asset() -> None:
    policy = audio_director_policy_from_snapshot(_snapshot())
    service = AudioDirectorService()
    with pytest.raises(AudioDirectorError, match="SOURCE_AUDIO_ELIGIBILITY_DENIED"):
        service.analyze(
            asset=_asset(policy, status=SourceAudioStatus.INELIGIBLE), policy=policy,
            source_audio_mode=SourceAudioMode.CLEAN_SPEECH, speech_presence_bps=9_000,
            music_contamination_bps=0, noise_bps=0, speech_intelligibility_bps=9_000,
            recommended_duration_ms=3_000,
        )
    with pytest.raises(AudioDirectorError, match="SOURCE_AUDIO_ELIGIBILITY_DENIED"):
        service.analyze(
            asset=_asset(policy, rights=False), policy=policy,
            source_audio_mode=SourceAudioMode.CLEAN_SPEECH, speech_presence_bps=9_000,
            music_contamination_bps=0, noise_bps=0, speech_intelligibility_bps=9_000,
            recommended_duration_ms=3_000,
        )


def test_speech_audio_requires_pause_and_hard_duck_or_mute() -> None:
    policy = audio_director_policy_from_snapshot(_snapshot())
    invalid = SourceAudioAnalysisV1(
        "ast_phase11source", HASH_A, SourceAudioMode.CLEAN_SPEECH, 9_000, 0, 0, 9_000,
        3_000, "none", "none",
    )
    with pytest.raises(AudioDirectorError, match="SOURCE_AUDIO_SPEECH_POLICY_INVALID"):
        invalid.data(policy)
    too_long = SourceAudioAnalysisV1(
        "ast_phase11source", HASH_A, SourceAudioMode.CLEAN_SPEECH, 9_000, 0, 0, 9_000,
        6_001, "pause", "hard_duck",
    )
    with pytest.raises(AudioDirectorError, match="SOURCE_AUDIO_SPEECH_POLICY_INVALID"):
        too_long.data(policy)
    with pytest.raises(AudioDirectorError, match="SOURCE_AUDIO_ANALYSIS_INVALID"):
        AudioDirectorService().analyze(
            asset=_asset(policy), policy=policy, source_audio_mode=SourceAudioMode.CLEAN_SPEECH,
            speech_presence_bps="9000",  # type: ignore[arg-type]
            music_contamination_bps=0, noise_bps=0, speech_intelligibility_bps=9_000,
            recommended_duration_ms=3_000,
        )


def test_embedded_music_cannot_emit_source_speech_events() -> None:
    policy = audio_director_policy_from_snapshot(_snapshot())
    plan = _plan(policy, SourceAudioMode.EMBEDDED_MUSIC)
    analysis = plan.analyses[0].data(policy)
    invalid = AudioDirectionPlanV1(
        "prj_phase11", policy,
        (ChapterAudioDirectionV1(
            "chap_phase11", HASH_B, "medium", ("source_speech_in", "source_speech_out"),
            ((str(analysis["analysis_id"]), str(analysis["analysis_hash"])),),
        ),),
        plan.analyses,
    )
    with pytest.raises(AudioDirectorError, match="SOURCE_SPEECH_ELIGIBILITY_REQUIRED"):
        invalid.data()


def test_unsupported_event_and_mutable_artifact_inputs_fail_closed() -> None:
    policy = audio_director_policy_from_snapshot(_snapshot())
    analysis = _plan(policy).analyses[0].data(policy)
    unsupported_event = ChapterAudioDirectionV1(
        "chap_phase11", HASH_B, "medium", ("unsupported",),
        ((str(analysis["analysis_id"]), str(analysis["analysis_hash"])),),
    )
    with pytest.raises(AudioDirectorError, match="CHAPTER_AUDIO_DIRECTION_INVALID"):
        unsupported_event.data(policy, {str(analysis["analysis_id"]): analysis})
    mutable_events = ChapterAudioDirectionV1(
        "chap_phase11", HASH_B, "medium", ["music_start"],  # type: ignore[arg-type]
        ((str(analysis["analysis_id"]), str(analysis["analysis_hash"])),),
    )
    with pytest.raises(AudioDirectorError, match="CHAPTER_AUDIO_DIRECTION_IMMUTABLE_INPUT_REQUIRED"):
        mutable_events.data(policy, {str(analysis["analysis_id"]): analysis})


def test_dummy_domain_pack_uses_the_same_core_audio_contract() -> None:
    business = audio_director_policy_from_snapshot(_snapshot())
    dummy = audio_director_policy_from_snapshot(_snapshot("dummy"))
    business_plan, dummy_plan = _plan(business).data(), _plan(dummy).data()
    assert business_plan["schema_version"] == dummy_plan["schema_version"]
    assert sorted(business_plan) == sorted(dummy_plan)
