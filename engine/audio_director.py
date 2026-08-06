"""Phase 11 policy-bound audio direction; not an EDL or audio renderer."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from engine.acquisition import AssetRecordV1, MediaType, SourceAudioStatus
from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.domain import policy_snapshot_hash
from engine.contracts.models import DomainPolicySnapshot


AUDIO_DIRECTOR_POLICY_V1 = "AUDIO-DIRECTOR-POLICY-V1"
AUDIO_DIRECTION_PLAN_V1 = "PHASE11-AUDIO-DIRECTION-PLAN-V1"
SAMPLE_RATE_HZ = 48_000


class AudioDirectorError(ValueError):
    pass


def _fail(code: str) -> None:
    raise AudioDirectorError(code)


def _token(value: object) -> str:
    if type(value) is not str or not value or value != value.strip() or value != value.lower():
        _fail("AUDIO_DIRECTOR_TOKEN_INVALID")
    return value


def _tokens(value: object, *, empty: bool = False) -> tuple[str, ...]:
    if type(value) not in (tuple, list): _fail("AUDIO_DIRECTOR_TOKEN_INVALID")
    result = tuple(_token(item) for item in value)
    if (not empty and not result) or len(set(result)) != len(result): _fail("AUDIO_DIRECTOR_TOKEN_INVALID")
    return result


def _hash(value: object) -> str:
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _hash_ok(value: object) -> bool:
    return type(value) is str and len(value) == 71 and value.startswith("sha256:") and all(item in "0123456789abcdef" for item in value[7:])


def _id(value: object, prefix: str) -> bool:
    return type(value) is str and value.startswith(prefix) and len(value) > len(prefix)


class SourceAudioMode(str, Enum):
    CLEAN_SPEECH = "clean_speech"
    SPEECH_WITH_AMBIENCE = "speech_with_ambience"
    EMBEDDED_MUSIC = "embedded_music"
    AMBIENCE_ONLY = "ambience_only"
    UNUSABLE = "unusable"
    DISABLED = "disabled"


@dataclass(frozen=True)
class AudioDirectorPolicyV1:
    manifest_hash: str
    policy_snapshot_id: str
    policy_snapshot_hash: str
    allowed_source_audio_modes: tuple[str, ...]
    allowed_music_intensities: tuple[str, ...]
    allowed_event_types: tuple[str, ...]
    source_speech_allowed_modes: tuple[str, ...]
    source_speech_min_duration_ms: int
    source_speech_max_duration_ms: int

    @property
    def policy_hash(self) -> str:
        value = {name: list(getattr(self, name)) if name.startswith("allowed_") or name.endswith("_modes") else getattr(self, name) for name in self.__dataclass_fields__}
        return _hash(value)


def audio_director_policy_from_snapshot(snapshot: DomainPolicySnapshot) -> AudioDirectorPolicyV1:
    if type(snapshot) is not DomainPolicySnapshot or not snapshot.immutable: _fail("AUDIO_DIRECTOR_POLICY_SNAPSHOT_INVALID")
    raw_snapshot = {field: getattr(snapshot, field) for field in snapshot.__dataclass_fields__}
    if snapshot.canonical_hash != policy_snapshot_hash(raw_snapshot): _fail("AUDIO_DIRECTOR_POLICY_SNAPSHOT_INVALID")
    bundles = snapshot.resolved_policy.get("policy_bundles") if type(snapshot.resolved_policy) is dict else None
    matches = [bundle["policy"]["audio"]["audio_director_policy"] for bundle in bundles or () if type(bundle) is dict and type(bundle.get("policy")) is dict and type(bundle["policy"].get("audio")) is dict and "audio_director_policy" in bundle["policy"]["audio"]]
    required = {"policy_version", "allowed_source_audio_modes", "allowed_music_intensities", "allowed_event_types", "source_speech_allowed_modes", "source_speech_min_duration_ms", "source_speech_max_duration_ms"}
    if len(matches) != 1 or type(matches[0]) is not dict or set(matches[0]) != required or matches[0]["policy_version"] != AUDIO_DIRECTOR_POLICY_V1: _fail("AUDIO_DIRECTOR_POLICY_MISSING")
    raw = matches[0]
    modes = _tokens(raw["allowed_source_audio_modes"]); intensities = _tokens(raw["allowed_music_intensities"]); events = _tokens(raw["allowed_event_types"]); speech = _tokens(raw["source_speech_allowed_modes"])
    if set(modes) != {item.value for item in SourceAudioMode} or not set(speech).issubset(set(modes)) or set(speech) != {SourceAudioMode.CLEAN_SPEECH.value, SourceAudioMode.SPEECH_WITH_AMBIENCE.value}: _fail("AUDIO_DIRECTOR_POLICY_MODE_INVALID")
    minimum, maximum = raw["source_speech_min_duration_ms"], raw["source_speech_max_duration_ms"]
    if type(minimum) is not int or type(maximum) is not int or minimum < 1 or minimum > maximum: _fail("AUDIO_DIRECTOR_POLICY_RANGE_INVALID")
    return AudioDirectorPolicyV1(snapshot.manifest_hash, snapshot.snapshot_id, snapshot.canonical_hash, modes, intensities, events, speech, minimum, maximum)


@dataclass(frozen=True)
class SourceAudioAnalysisV1:
    asset_id: str
    asset_hash: str
    source_audio_mode: SourceAudioMode
    speech_presence_bps: int
    music_contamination_bps: int
    noise_bps: int
    speech_intelligibility_bps: int
    recommended_duration_ms: int
    narration_conflict_policy: str
    bgm_conflict_policy: str

    def data(self, policy: AudioDirectorPolicyV1) -> dict[str, object]:
        if type(policy) is not AudioDirectorPolicyV1 or not _id(self.asset_id, "ast_") or not _hash_ok(self.asset_hash) or type(self.source_audio_mode) is not SourceAudioMode or self.source_audio_mode.value not in policy.allowed_source_audio_modes or any(type(value) is not int or not 0 <= value <= 10_000 for value in (self.speech_presence_bps, self.music_contamination_bps, self.noise_bps, self.speech_intelligibility_bps)):
            _fail("SOURCE_AUDIO_ANALYSIS_INVALID")
        speech = self.source_audio_mode.value in policy.source_speech_allowed_modes
        if speech:
            if type(self.recommended_duration_ms) is not int or not policy.source_speech_min_duration_ms <= self.recommended_duration_ms <= policy.source_speech_max_duration_ms or self.narration_conflict_policy != "pause" or self.bgm_conflict_policy not in {"hard_duck", "mute"}: _fail("SOURCE_AUDIO_SPEECH_POLICY_INVALID")
        elif self.recommended_duration_ms != 0 or self.narration_conflict_policy != "none" or self.bgm_conflict_policy != "none":
            _fail("SOURCE_AUDIO_MODE_POLICY_INVALID")
        value = {"asset_id": self.asset_id, "asset_hash": self.asset_hash, "source_audio_mode": self.source_audio_mode.value, "speech_presence_bps": self.speech_presence_bps, "music_contamination_bps": self.music_contamination_bps, "noise_bps": self.noise_bps, "speech_intelligibility_bps": self.speech_intelligibility_bps, "recommended_duration_ms": self.recommended_duration_ms, "narration_conflict_policy": self.narration_conflict_policy, "bgm_conflict_policy": self.bgm_conflict_policy, "policy_snapshot_id": policy.policy_snapshot_id, "policy_snapshot_hash": policy.policy_snapshot_hash, "audio_director_policy_hash": policy.policy_hash}
        digest = _hash(value)
        return {"analysis_id": "saa_" + digest[7:27], "analysis_hash": digest, **value}


@dataclass(frozen=True)
class ChapterAudioDirectionV1:
    chapter_brief_id: str
    chapter_brief_hash: str
    music_intensity: str
    event_type_tokens: tuple[str, ...]
    source_analysis_id_hash_pairs: tuple[tuple[str, str], ...]

    def data(self, policy: AudioDirectorPolicyV1, analyses: dict[str, dict[str, object]]) -> dict[str, object]:
        if type(analyses) is not dict or type(self.event_type_tokens) is not tuple or type(self.source_analysis_id_hash_pairs) is not tuple:
            _fail("CHAPTER_AUDIO_DIRECTION_IMMUTABLE_INPUT_REQUIRED")
        events = _tokens(self.event_type_tokens, empty=True)
        pairs = tuple(self.source_analysis_id_hash_pairs)
        if not _id(self.chapter_brief_id, "chap_") or not _hash_ok(self.chapter_brief_hash) or self.music_intensity not in policy.allowed_music_intensities or any(item not in policy.allowed_event_types for item in events) or len(set(events)) != len(events) or any(type(pair) is not tuple or len(pair) != 2 or not _id(pair[0], "saa_") or not _hash_ok(pair[1]) or analyses.get(pair[0], {}).get("analysis_hash") != pair[1] for pair in pairs) or len({pair[0] for pair in pairs}) != len(pairs):
            _fail("CHAPTER_AUDIO_DIRECTION_INVALID")
        source_speech_events = {"source_speech_in", "source_speech_out"}
        present_source_speech_events = set(events) & source_speech_events
        if present_source_speech_events and present_source_speech_events != source_speech_events:
            _fail("SOURCE_SPEECH_EVENT_PAIR_REQUIRED")
        if present_source_speech_events and not any(
            analyses[pair[0]]["source_audio_mode"] in policy.source_speech_allowed_modes
            for pair in pairs
        ):
            _fail("SOURCE_SPEECH_ELIGIBILITY_REQUIRED")
        value = {"chapter_brief_id": self.chapter_brief_id, "chapter_brief_hash": self.chapter_brief_hash, "music_intensity": self.music_intensity, "event_type_tokens": list(events), "source_analysis_id_hash_pairs": [list(pair) for pair in pairs]}
        digest = _hash(value)
        return {"chapter_audio_direction_id": "cad_" + digest[7:27], "chapter_audio_direction_hash": digest, **value}


@dataclass(frozen=True)
class AudioDirectionPlanV1:
    project_id: str
    policy: AudioDirectorPolicyV1
    directions: tuple[ChapterAudioDirectionV1, ...]
    analyses: tuple[SourceAudioAnalysisV1, ...]

    def data(self) -> dict[str, object]:
        if not _id(self.project_id, "prj_") or type(self.policy) is not AudioDirectorPolicyV1 or type(self.directions) is not tuple or type(self.analyses) is not tuple or any(type(item) is not ChapterAudioDirectionV1 for item in self.directions) or any(type(item) is not SourceAudioAnalysisV1 for item in self.analyses): _fail("AUDIO_DIRECTION_PLAN_INVALID")
        analysis_rows = tuple(item.data(self.policy) for item in self.analyses)
        if len({item["analysis_id"] for item in analysis_rows}) != len(analysis_rows): _fail("AUDIO_DIRECTION_PLAN_INVALID")
        by_id = {str(item["analysis_id"]): item for item in analysis_rows}
        direction_rows = tuple(item.data(self.policy, by_id) for item in self.directions)
        if not direction_rows or len({item["chapter_brief_id"] for item in direction_rows}) != len(direction_rows): _fail("AUDIO_DIRECTION_PLAN_INVALID")
        value = {"schema_version": AUDIO_DIRECTION_PLAN_V1, "project_id": self.project_id, "policy_snapshot_id": self.policy.policy_snapshot_id, "policy_snapshot_hash": self.policy.policy_snapshot_hash, "audio_director_policy_hash": self.policy.policy_hash, "sample_rate_hz": SAMPLE_RATE_HZ, "intermediate_format": "pcm", "analyses": list(analysis_rows), "chapter_directions": list(direction_rows)}
        digest = _hash(value)
        return {"audio_direction_plan_id": "adp_" + digest[7:27], "audio_direction_plan_hash": digest, **value}


class AudioDirectorService:
    """Creates source analyses only from accepted Phase 8 asset metadata."""

    def analyze(self, *, asset: AssetRecordV1, policy: AudioDirectorPolicyV1, source_audio_mode: SourceAudioMode, speech_presence_bps: int, music_contamination_bps: int, noise_bps: int, speech_intelligibility_bps: int, recommended_duration_ms: int = 0) -> SourceAudioAnalysisV1:
        if type(asset) is not AssetRecordV1 or type(policy) is not AudioDirectorPolicyV1 or type(source_audio_mode) is not SourceAudioMode: _fail("SOURCE_AUDIO_ASSET_INVALID")
        if any(type(value) is not int or not 0 <= value <= 10_000 for value in (speech_presence_bps, music_contamination_bps, noise_bps, speech_intelligibility_bps)) or type(recommended_duration_ms) is not int:
            _fail("SOURCE_AUDIO_ANALYSIS_INVALID")
        eligibility = asset.source_audio_eligibility
        if type(eligibility) is not dict or (eligibility.get("policy_snapshot_id"), eligibility.get("policy_snapshot_hash")) != (policy.policy_snapshot_id, policy.policy_snapshot_hash) or type(eligibility.get("reason_tokens")) is not list or any(type(token) is not str for token in eligibility["reason_tokens"]): _fail("SOURCE_AUDIO_ASSET_INVALID")
        speech_mode = source_audio_mode.value in policy.source_speech_allowed_modes
        if speech_mode:
            if asset.media_type not in {MediaType.VIDEO, MediaType.AUDIO} or asset.media_facts.get("has_audio") is not True or eligibility.get("status") != SourceAudioStatus.ELIGIBLE.value or "rights_confirmed" not in eligibility["reason_tokens"]: _fail("SOURCE_AUDIO_ELIGIBILITY_DENIED")
            if source_audio_mode is SourceAudioMode.CLEAN_SPEECH and (music_contamination_bps > 1_500 or speech_intelligibility_bps < 7_000): _fail("SOURCE_AUDIO_ANALYSIS_DENIED")
            if source_audio_mode is SourceAudioMode.SPEECH_WITH_AMBIENCE and (music_contamination_bps > 3_000 or speech_intelligibility_bps < 5_000): _fail("SOURCE_AUDIO_ANALYSIS_DENIED")
            narration, bgm = "pause", "hard_duck"
        else:
            recommended_duration_ms, narration, bgm = 0, "none", "none"
        result = SourceAudioAnalysisV1(asset.asset_id, asset.asset_hash, source_audio_mode, speech_presence_bps, music_contamination_bps, noise_bps, speech_intelligibility_bps, recommended_duration_ms, narration, bgm)
        result.data(policy)
        return result


def canonical_audio_direction_json(plan: AudioDirectionPlanV1) -> bytes:
    if type(plan) is not AudioDirectionPlanV1: _fail("AUDIO_DIRECTION_PLAN_INVALID")
    return encode_canonical_json_bytes(plan.data())
