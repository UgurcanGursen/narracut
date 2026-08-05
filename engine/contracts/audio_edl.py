"""Deterministic Phase 3B 48 kHz audio-plan contract.

This module deliberately plans immutable audio events only.  It does not open
media, decode audio, allocate a mix buffer, or invoke a renderer.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import struct
import unicodedata
import weakref
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .audio import AudioArtifact, serialize_audio_artifact
from .edl import VideoEdlArtifact, serialize_video_edl
from .word_to_frame import WordToFrameArtifact, serialize_word_to_frame

AUDIO_EDL_V1 = "AUDIO-EDL-V1"
AUDIO_EDL_HASH_V1 = "AUDIO-EDL-HASH-V1"
AUDIO_SAMPLE_CLOCK_V1 = "AUDIO-SAMPLE-CLOCK-48KHZ-V1"
INTERNAL_AUDIO_SAMPLE_RATE_HZ = 48000
INTERNAL_AUDIO_CHANNEL_COUNT = 2
ZERO_CROSSING_SEARCH_SAMPLES = 240
MICROFADE_SAMPLES = 240
LONG_EDITORIAL_FADE_SAMPLES = 24000
MAX_SEAM_CHANNEL_DELTA = 1 / 64
_MAX_U32 = 2**32 - 1
_MIN_I32, _MAX_I32 = -(2**31), 2**31 - 1
_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID = re.compile(r"^[\x21-\x7e]{1,128}$")

__all__ = [
    "AUDIO_EDL_V1", "AUDIO_EDL_HASH_V1", "AUDIO_SAMPLE_CLOCK_V1",
    "INTERNAL_AUDIO_SAMPLE_RATE_HZ", "INTERNAL_AUDIO_CHANNEL_COUNT",
    "InternalPcmFormat", "AudioTrackRole", "AudioEventKind",
    "AudioBoundaryPolicy", "AudioTransitionKind", "AudioBoundaryPosition",
    "AudioCueWordRange", "AudioCueSampleRange", "ReplayPcmSource",
    "ReplayPcmEvidence", "AudioPlacementIntent", "AudioBoundaryIntent",
    "AudioPlannedSilence", "AudioBoundaryDecision", "EdlAudioEvent",
    "AudioEdlTrack", "AudioEdlArtifact", "AudioEdlRejectionReason",
    "AudioEdlContractError", "compile_audio_edl", "plan_audio_boundaries",
    "load_audio_edl", "serialize_audio_edl",
]

class InternalPcmFormat(str, Enum):
    PCM_F32LE = "PCM_F32LE"
    PCM_S24LE = "PCM_S24LE"
class AudioTrackRole(str, Enum):
    A1 = "A1"; A2 = "A2"; A3 = "A3"; A4 = "A4"; A5 = "A5"
class AudioEventKind(str, Enum):
    NARRATION = "NARRATION"; BGM = "BGM"; SFX = "SFX"; SOURCE_SPEECH = "SOURCE_SPEECH"; AMBIENCE = "AMBIENCE"
class AudioBoundaryPolicy(str, Enum):
    ZERO_CROSSING_MICROFADE = "ZERO_CROSSING_MICROFADE"; OVERLAP_CROSSFADE = "OVERLAP_CROSSFADE"; PRESERVE_SILENCE = "PRESERVE_SILENCE"; HARD_CUT_ZERO_CROSSING = "HARD_CUT_ZERO_CROSSING"; LONG_EDITORIAL_FADE = "LONG_EDITORIAL_FADE"
class AudioTransitionKind(str, Enum):
    NONE = "NONE"; FADE_IN = "FADE_IN"; FADE_OUT = "FADE_OUT"; CROSSFADE = "CROSSFADE"
class AudioBoundaryPosition(str, Enum):
    LEADING = "LEADING"; BETWEEN_EVENTS = "BETWEEN_EVENTS"; TRAILING = "TRAILING"
class AudioEdlRejectionReason(str, Enum):
    STRUCTURE_INVALID="STRUCTURE_INVALID"; UNSUPPORTED_VALUE="UNSUPPORTED_VALUE"; DEPENDENCY_CONTENT_DRIFT="DEPENDENCY_CONTENT_DRIFT"; DEPENDENCY_BINDING_INVALID="DEPENDENCY_BINDING_INVALID"; CUE_RESOLUTION_INVALID="CUE_RESOLUTION_INVALID"; ENCODER_COMPENSATION_INVALID="ENCODER_COMPENSATION_INVALID"; PCM_EVIDENCE_INVALID="PCM_EVIDENCE_INVALID"; TRACK_COLLISION="TRACK_COLLISION"; SPEECH_COLLISION="SPEECH_COLLISION"; SEQUENCE_BOUNDS_INVALID="SEQUENCE_BOUNDS_INVALID"; ORDERING_INVALID="ORDERING_INVALID"; BOUNDARY_POLICY_INVALID="BOUNDARY_POLICY_INVALID"; NON_CANONICAL_SERIALIZATION="NON_CANONICAL_SERIALIZATION"; IDENTITY_MISMATCH="IDENTITY_MISMATCH"; CONTENT_DRIFT="CONTENT_DRIFT"; NOT_MATERIALIZED="NOT_MATERIALIZED"

@dataclass(frozen=True)
class AudioCueWordRange:
    project_id: str; document_id: str; narration_revision_id: str; start_word_id: str; end_word_id: str
@dataclass(frozen=True)
class AudioCueSampleRange:
    project_id: str; document_id: str; narration_revision_id: str; start_word_id: str; end_word_id: str; start_sample: int; end_exclusive_sample: int
@dataclass(frozen=True)
class ReplayPcmSource:
    source_id: str; source_media_hash: str; normalized_pcm_evidence_hash: str; pcm_format: InternalPcmFormat; source_sample_rate_hz: int; source_channel_count: int; source_sample_frames: int; normalized_sample_frames: int; encoder_delay_samples: int; encoder_padding_samples: int
@dataclass(frozen=True)
class ReplayPcmEvidence:
    source_id: str; normalized_pcm_evidence_hash: str; pcm_format: InternalPcmFormat; sample_rate_hz: int; channel_count: int; sample_frames: int; interleaved_samples: tuple[float | int, ...]
@dataclass(frozen=True)
class AudioPlacementIntent:
    intent_id: str; track: AudioTrackRole; kind: AudioEventKind; cue: AudioCueWordRange; source: ReplayPcmSource; source_in_sample: int; source_out_exclusive_sample: int; gain_millibels: int; ordinal: int
@dataclass(frozen=True)
class AudioBoundaryIntent:
    boundary_intent_id: str; track: AudioTrackRole; ordinal: int; position: AudioBoundaryPosition; left_intent_id: str | None; right_intent_id: str | None; left_transition: AudioTransitionKind; right_transition: AudioTransitionKind; requested_crossfade_samples: int
@dataclass(frozen=True)
class AudioPlannedSilence:
    silence_id: str; track: AudioTrackRole; ordinal: int; left_intent_id: str | None; right_intent_id: str | None; start_sample: int; end_exclusive_sample: int
@dataclass(frozen=True)
class AudioBoundaryDecision:
    position: AudioBoundaryPosition; left_event_id: str | None; right_event_id: str | None; track: AudioTrackRole; policy: AudioBoundaryPolicy; transition: AudioTransitionKind; left_trim_samples: int; right_trim_samples: int; fade_in_samples: int; fade_out_samples: int; overlap_samples: int; protected_silence_samples: int
@dataclass(frozen=True)
class EdlAudioEvent:
    schema_version: str; hash_scope_version: str; event_id: str; event_hash: str; track: AudioTrackRole; kind: AudioEventKind; ordinal: int; intent_id: str; source_id: str; source_media_hash: str; normalized_pcm_evidence_hash: str; start_sample: int; end_exclusive_sample: int; source_in_sample: int; source_out_exclusive_sample: int; gain_millibels: int; cue_start_word_id: str; cue_end_word_id: str; cue_start_sample: int; cue_end_exclusive_sample: int
@dataclass(frozen=True)
class AudioEdlTrack:
    track: AudioTrackRole; priority: int; events: tuple[EdlAudioEvent, ...]
@dataclass(frozen=True)
class AudioEdlArtifact:
    schema_version: str; hash_scope_version: str; audio_edl_id: str; audio_edl_hash: str; video_edl_id: str; video_edl_hash: str; word_to_frame_id: str; word_to_frame_hash: str; narration_audio_id: str; narration_audio_hash: str; narration_audio_media_byte_hash: str; project_id: str; document_id: str; narration_revision_id: str; narration_revision_hash: str; sequence_id: str; sample_clock_version: str; sample_rate_hz: int; channel_count: int; internal_pcm_format: InternalPcmFormat; sources: tuple[ReplayPcmSource, ...]; pcm_evidence: tuple[ReplayPcmEvidence, ...]; duration_samples: int; tracks: tuple[AudioEdlTrack, ...]; boundary_intents: tuple[AudioBoundaryIntent, ...]; planned_silences: tuple[AudioPlannedSilence, ...]; boundary_decisions: tuple[AudioBoundaryDecision, ...]

class AudioEdlContractError(ValueError):
    def __init__(self, pointer: str, reason: AudioEdlRejectionReason, issue_code: str | None = None) -> None:
        if type(pointer) is not str or type(reason) is not AudioEdlRejectionReason: raise TypeError("invalid audio EDL error construction")
        super().__init__(f"Audio EDL rejected: {reason.value}")
        self.pointer, self.reason, self.issue_code = pointer, reason, issue_code
def _reject(pointer: str, reason: AudioEdlRejectionReason, issue: str | None = None) -> None: raise AudioEdlContractError(pointer, reason, issue)

_CUE_FIELDS=tuple(AudioCueWordRange.__dataclass_fields__); _SOURCE_FIELDS=tuple(ReplayPcmSource.__dataclass_fields__); _EVIDENCE_FIELDS=tuple(ReplayPcmEvidence.__dataclass_fields__); _INTENT_FIELDS=tuple(AudioPlacementIntent.__dataclass_fields__); _BINT_FIELDS=tuple(AudioBoundaryIntent.__dataclass_fields__); _SILENCE_FIELDS=tuple(AudioPlannedSilence.__dataclass_fields__); _DECISION_FIELDS=tuple(AudioBoundaryDecision.__dataclass_fields__); _EVENT_FIELDS=tuple(EdlAudioEvent.__dataclass_fields__); _TRACK_FIELDS=tuple(AudioEdlTrack.__dataclass_fields__); _ROOT_FIELDS=tuple(AudioEdlArtifact.__dataclass_fields__)
_REGISTRY: dict[int, tuple[weakref.ReferenceType[AudioEdlArtifact], bytes, tuple[int,...]]] = {}

def _canonical_bytes(value: Any) -> bytes:
    """Audio EDL JSON additionally admits validated binary32 PCM numbers.

    The shared Phase 2 encoder intentionally has no float domain.  PCM evidence
    has one, so this contract owns the narrow JSON encoding rather than widening
    a cross-phase primitive.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")

def _digest(value: Any) -> str: return hashlib.sha256(_canonical_bytes(value)).hexdigest()
def _ok_string(v: Any) -> bool: return type(v) is str and unicodedata.normalize("NFC",v)==v and not any(ord(c)<32 or 0xD800<=ord(c)<=0xDFFF for c in v)
def _id(v: Any, prefix: str | None = None) -> bool: return _ok_string(v) and _ID.fullmatch(v) is not None and (prefix is None or v.startswith(prefix))
def _hash(v: Any) -> bool: return type(v) is str and _HASH.fullmatch(v) is not None
def _u(v: Any) -> bool: return type(v) is int and 0 <= v <= _MAX_U32
def _i32(v: Any) -> bool: return type(v) is int and _MIN_I32 <= v <= _MAX_I32
def _enum(v: Any, t: type[Enum]) -> bool: return type(v) is t
_TRACK_PRIORITIES = {
    AudioTrackRole.A1: 10, AudioTrackRole.A2: 20, AudioTrackRole.A3: 30,
    AudioTrackRole.A4: 40, AudioTrackRole.A5: 50,
}
_TRACK_KINDS = {
    AudioTrackRole.A1: AudioEventKind.NARRATION,
    AudioTrackRole.A2: AudioEventKind.BGM,
    AudioTrackRole.A3: AudioEventKind.SFX,
    AudioTrackRole.A4: AudioEventKind.SOURCE_SPEECH,
    AudioTrackRole.A5: AudioEventKind.AMBIENCE,
}
def _track_priority(track: AudioTrackRole) -> int: return _TRACK_PRIORITIES[track]
def _kind(track: AudioTrackRole) -> AudioEventKind: return _TRACK_KINDS[track]
def _as(v: Any) -> Any:
    if isinstance(v, Enum): return v.value
    # The repository-wide canonical JSON contract intentionally has no float
    # primitive.  PCM_F32LE is therefore published as its exact IEEE-754
    # little-endian binary32 representation, not as a locale/precision
    # dependent decimal.  `_validate_evidence` has already rejected every
    # non-canonical float before this projection is reachable.
    if type(v) is float: return "f32le:" + struct.pack("<f", v).hex()
    if type(v) is tuple: return [_as(x) for x in v]
    if hasattr(v,"__dataclass_fields__"): return {f:_as(getattr(v,f)) for f in v.__dataclass_fields__}
    return v
def _source_dict(v: ReplayPcmSource)->dict[str,Any]: return _as(v)
def _evidence_dict(v: ReplayPcmEvidence)->dict[str,Any]: return _as(v)
def _intent_dict(v: AudioPlacementIntent)->dict[str,Any]: return _as(v)
def _event_dict(v: EdlAudioEvent)->dict[str,Any]: return _as(v)
def _track_dict(v: AudioEdlTrack)->dict[str,Any]: return _as(v)
def _artifact_dict(v: AudioEdlArtifact)->dict[str,Any]: return _as(v)
def _signature(v: AudioEdlArtifact)->tuple[int,...]:
    out=[id(v),id(v.sources),id(v.pcm_evidence),id(v.tracks),id(v.boundary_intents),id(v.planned_silences),id(v.boundary_decisions)]
    for track in v.tracks:
        out += [id(track),id(track.events)]+[id(x) for x in track.events]
    return tuple(out)
def _register(v: AudioEdlArtifact, data: bytes)->None:
    key=id(v)
    def gone(ref: weakref.ReferenceType[AudioEdlArtifact])->None:
        if _REGISTRY.get(key,(None,))[0] is ref: _REGISTRY.pop(key,None)
    ref=weakref.ref(v,gone); _REGISTRY[key]=(ref,bytes(data),_signature(v))

def _dep(value: Any, cls: type, serializer: Any, pointer: str)->None:
    if type(value) is not cls: _reject(pointer,AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    try: serializer(value)
    except AudioEdlContractError: raise
    except Exception: _reject(pointer,AudioEdlRejectionReason.DEPENDENCY_CONTENT_DRIFT)

def _sample_at_frame(video: VideoEdlArtifact, frame: int) -> int:
    if not _u(frame): _reject("/video_edl",AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    return frame * INTERNAL_AUDIO_SAMPLE_RATE_HZ * video.fps_denominator // video.fps_numerator

def _validate_source(source: ReplayPcmSource, index: int, *, pointer_prefix: str = "/sources")->None:
    """Validate the complete delay-compensated source geometry.

    The public boundary helper is also an ingress: it receives sources through
    placement intents rather than the artifact's ``sources`` snapshot.  Keep
    the same validator for both paths, but retain an honest pointer for each
    caller.
    """
    p=f"{pointer_prefix}/{index}"
    if type(source) is not ReplayPcmSource or not _id(source.source_id) or not _hash(source.source_media_hash) or not _hash(source.normalized_pcm_evidence_hash) or not _enum(source.pcm_format,InternalPcmFormat): _reject(p,AudioEdlRejectionReason.PCM_EVIDENCE_INVALID)
    if not all(_u(getattr(source,x)) for x in ("source_sample_rate_hz","source_channel_count","source_sample_frames","normalized_sample_frames","encoder_delay_samples","encoder_padding_samples")): _reject(p,AudioEdlRejectionReason.PCM_EVIDENCE_INVALID)
    if source.source_sample_rate_hz<1 or source.source_channel_count<1 or source.source_sample_frames<1 or source.normalized_sample_frames<1 or source.encoder_delay_samples+source.encoder_padding_samples >= source.normalized_sample_frames: _reject(p,AudioEdlRejectionReason.ENCODER_COMPENSATION_INVALID)
def _validate_evidence(e: ReplayPcmEvidence,index:int)->None:
    p=f"/pcm_evidence/{index}"
    if type(e) is not ReplayPcmEvidence or not _id(e.source_id) or not _hash(e.normalized_pcm_evidence_hash) or not _enum(e.pcm_format,InternalPcmFormat) or e.sample_rate_hz!=48000 or e.channel_count!=2 or not _u(e.sample_frames) or type(e.interleaved_samples) is not tuple or len(e.interleaved_samples)!=e.sample_frames*2: _reject(p,AudioEdlRejectionReason.PCM_EVIDENCE_INVALID)
    raw=bytearray()
    for x in e.interleaved_samples:
        if e.pcm_format is InternalPcmFormat.PCM_F32LE:
            if type(x) is not float or not math.isfinite(x) or x==0.0 and math.copysign(1.0,x)<0: _reject(p,AudioEdlRejectionReason.PCM_EVIDENCE_INVALID)
            try: packed=struct.pack("<f",x); unpacked=struct.unpack("<f",packed)[0]
            except (OverflowError,struct.error): _reject(p,AudioEdlRejectionReason.PCM_EVIDENCE_INVALID)
            if not math.isfinite(unpacked) or unpacked != x: _reject(p,AudioEdlRejectionReason.PCM_EVIDENCE_INVALID)
            raw.extend(packed)
        elif type(x) is not int or not -(2**23)<=x<2**23: _reject(p,AudioEdlRejectionReason.PCM_EVIDENCE_INVALID)
        else: raw.extend(int(x).to_bytes(3,"little",signed=True))
    if "sha256:"+hashlib.sha256(bytes(raw)).hexdigest() != e.normalized_pcm_evidence_hash:
        _reject(p,AudioEdlRejectionReason.PCM_EVIDENCE_INVALID)

def _cue_span(intent: AudioPlacementIntent, words: dict[str,Any], video: VideoEdlArtifact)->AudioCueSampleRange:
    cue=intent.cue
    if type(cue) is not AudioCueWordRange or not all(_id(getattr(cue,f)) for f in _CUE_FIELDS): _reject(f"/intents/{intent.ordinal}",AudioEdlRejectionReason.CUE_RESOLUTION_INVALID)
    a,b=words.get(cue.start_word_id),words.get(cue.end_word_id)
    if a is None or b is None or a.ordinal>b.ordinal: _reject(f"/intents/{intent.ordinal}",AudioEdlRejectionReason.CUE_RESOLUTION_INVALID)
    return AudioCueSampleRange(cue.project_id,cue.document_id,cue.narration_revision_id,cue.start_word_id,cue.end_word_id,_sample_at_frame(video,a.start_frame-video.sequence_start_frame),_sample_at_frame(video,b.end_exclusive_frame-video.sequence_start_frame))

def _event(intent: AudioPlacementIntent, span: AudioCueSampleRange)->EdlAudioEvent:
    start=span.start_sample; end=start+(intent.source_out_exclusive_sample-intent.source_in_sample)
    raw={"schema_version":AUDIO_EDL_V1,"hash_scope_version":AUDIO_EDL_HASH_V1,"track":intent.track.value,"kind":intent.kind.value,"ordinal":intent.ordinal,"intent_id":intent.intent_id,"source_id":intent.source.source_id,"source_media_hash":intent.source.source_media_hash,"normalized_pcm_evidence_hash":intent.source.normalized_pcm_evidence_hash,"start_sample":start,"end_exclusive_sample":end,"source_in_sample":intent.source_in_sample,"source_out_exclusive_sample":intent.source_out_exclusive_sample,"gain_millibels":intent.gain_millibels,"cue_start_word_id":span.start_word_id,"cue_end_word_id":span.end_word_id,"cue_start_sample":span.start_sample,"cue_end_exclusive_sample":span.end_exclusive_sample}
    h=_digest(raw)
    return EdlAudioEvent(AUDIO_EDL_V1,AUDIO_EDL_HASH_V1,"aevt_"+h[:32],h,intent.track,intent.kind,intent.ordinal,intent.intent_id,intent.source.source_id,intent.source.source_media_hash,intent.source.normalized_pcm_evidence_hash,start,end,intent.source_in_sample,intent.source_out_exclusive_sample,intent.gain_millibels,span.start_word_id,span.end_word_id,span.start_sample,span.end_exclusive_sample)

def _validate_event_integrity(event: EdlAudioEvent, intent: AudioPlacementIntent, pointer: str) -> None:
    """Validate a supplied immutable planner event without object identity state.

    ``plan_audio_boundaries`` is public, so it cannot rely on a private weak
    registry populated by the compiler.  Its accepted event tuple instead has
    to prove the complete immutable event projection: contract versions,
    canonical event hash/ID, intent/source binding, cue coordinates, and the
    source-duration relation.  Cue-word-to-frame resolution remains the
    compiler's responsibility; this helper deliberately verifies the already
    supplied sample projection rather than fabricating a second clock ingress.
    """
    if type(event) is not EdlAudioEvent or event.schema_version != AUDIO_EDL_V1 or event.hash_scope_version != AUDIO_EDL_HASH_V1:
        _reject(pointer, AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
    if not all(_u(getattr(event, name)) for name in ("ordinal", "start_sample", "end_exclusive_sample", "source_in_sample", "source_out_exclusive_sample", "cue_start_sample", "cue_end_exclusive_sample")):
        _reject(pointer, AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
    if (not _id(event.event_id, "aevt_") or type(event.event_hash) is not str or re.fullmatch(r"[0-9a-f]{64}", event.event_hash) is None or not _id(event.intent_id)
            or not _id(event.source_id) or not _hash(event.source_media_hash)
            or not _hash(event.normalized_pcm_evidence_hash) or not _i32(event.gain_millibels)
            or not _id(event.cue_start_word_id) or not _id(event.cue_end_word_id)
            or event.start_sample >= event.end_exclusive_sample
            or event.source_in_sample >= event.source_out_exclusive_sample
            or event.cue_start_sample >= event.cue_end_exclusive_sample):
        _reject(pointer, AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
    if (event.track,event.kind,event.ordinal,event.intent_id,event.source_id,event.source_media_hash,event.normalized_pcm_evidence_hash,event.source_in_sample,event.source_out_exclusive_sample,event.gain_millibels,event.cue_start_word_id,event.cue_end_word_id) != (intent.track,intent.kind,intent.ordinal,intent.intent_id,intent.source.source_id,intent.source.source_media_hash,intent.source.normalized_pcm_evidence_hash,intent.source_in_sample,intent.source_out_exclusive_sample,intent.gain_millibels,intent.cue.start_word_id,intent.cue.end_word_id):
        _reject(pointer, AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    if event.start_sample != event.cue_start_sample or event.end_exclusive_sample - event.start_sample != event.source_out_exclusive_sample - event.source_in_sample:
        _reject(pointer, AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
    raw={"schema_version":event.schema_version,"hash_scope_version":event.hash_scope_version,"track":event.track.value if _enum(event.track,AudioTrackRole) else None,"kind":event.kind.value if _enum(event.kind,AudioEventKind) else None,"ordinal":event.ordinal,"intent_id":event.intent_id,"source_id":event.source_id,"source_media_hash":event.source_media_hash,"normalized_pcm_evidence_hash":event.normalized_pcm_evidence_hash,"start_sample":event.start_sample,"end_exclusive_sample":event.end_exclusive_sample,"source_in_sample":event.source_in_sample,"source_out_exclusive_sample":event.source_out_exclusive_sample,"gain_millibels":event.gain_millibels,"cue_start_word_id":event.cue_start_word_id,"cue_end_word_id":event.cue_end_word_id,"cue_start_sample":event.cue_start_sample,"cue_end_exclusive_sample":event.cue_end_exclusive_sample}
    digest=_digest(raw)
    if event.event_hash != digest or event.event_id != "aevt_"+digest[:32]:
        _reject(pointer, AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)

def _crossing(evidence: ReplayPcmEvidence, source: ReplayPcmSource, event: EdlAudioEvent, trailing: bool) -> int | None:
    """Return a bounded effective-coordinate trim at an exact stereo crossing."""
    # An exact physical edge-zero is itself the requested seam.  It is not a
    # sign-change at an interior sample, so include it before the bounded scan.
    edge=source.encoder_delay_samples + (event.source_out_exclusive_sample-1 if trailing else event.source_in_sample)
    if 0 <= edge and edge*2+1 < len(evidence.interleaved_samples) and evidence.interleaved_samples[edge*2] == 0 and evidence.interleaved_samples[edge*2+1] == 0:
        return 0
    lo=max(1, event.source_in_sample)
    hi=min(event.source_out_exclusive_sample-1, event.source_in_sample+ZERO_CROSSING_SEARCH_SAMPLES) if not trailing else max(event.source_in_sample+1,event.source_out_exclusive_sample-ZERO_CROSSING_SEARCH_SAMPLES)
    candidates=range(lo,hi+1) if not trailing else range(event.source_out_exclusive_sample-1,hi-1,-1)
    best: int | None=None
    for p in candidates:
        # edge values belong to physical normalized PCM coordinates (delay included).
        left=(source.encoder_delay_samples+p-1)*2; right=(source.encoder_delay_samples+p)*2
        if left<0 or right+1>=len(evidence.interleaved_samples): continue
        a0,a1=evidence.interleaved_samples[left],evidence.interleaved_samples[left+1]
        b0,b1=evidence.interleaved_samples[right],evidence.interleaved_samples[right+1]
        if a0 == 0 and a1 == 0 or b0 == 0 and b1 == 0 or (a0 < 0 < b0 or b0 < 0 < a0) and (a1 < 0 < b1 or b1 < 0 < a1):
            trim=(event.source_out_exclusive_sample-p) if trailing else (p-event.source_in_sample)
            if 0 <= trim <= ZERO_CROSSING_SEARCH_SAMPLES and (best is None or trim<best): best=trim
    return best

def _boundary_key(track: AudioTrackRole, position: AudioBoundaryPosition, left: str | None, right: str | None)->tuple[str,str,str,str]:
    return track.value,position.value,left or "",right or ""

def _boundary_order_key(row: AudioBoundaryIntent, events: dict[str, EdlAudioEvent]) -> tuple[int, int, int, str, str, str]:
    """Return the caller-owned, already-materialized boundary ordering key."""
    if row.position is AudioBoundaryPosition.LEADING:
        anchor = events[row.right_intent_id].start_sample  # validated shape below
    else:
        anchor = events[row.left_intent_id].end_exclusive_sample
    rank = {
        AudioBoundaryPosition.LEADING: 0,
        AudioBoundaryPosition.BETWEEN_EVENTS: 1,
        AudioBoundaryPosition.TRAILING: 2,
    }[row.position]
    return (_track_priority(row.track), anchor, rank, row.left_intent_id or "", row.right_intent_id or "", row.boundary_intent_id)

def _validate_boundary_rows(boundaries: tuple[AudioBoundaryIntent,...], tracks: tuple[AudioEdlTrack,...], intents: tuple[AudioPlacementIntent,...], event_intents: dict[str, EdlAudioEvent])->dict[tuple[str,str,str,str], AudioBoundaryIntent]:
    if type(boundaries) is not tuple: raise TypeError("boundary_intents must be exact tuple")
    # `event_intents` is built by the public helper after it has proved event
    # identity uniqueness.  Keep the expected boundary relation indexed: this
    # is both fail-closed for forged IDs and linear in the event/boundary count.
    expected: set[tuple[AudioTrackRole,AudioBoundaryPosition,str|None,str|None]]=set()
    for track in tracks:
        ids=[e.intent_id for e in track.events]
        if ids:
            expected.add((track.track,AudioBoundaryPosition.LEADING,None,ids[0]))
            expected.update((track.track,AudioBoundaryPosition.BETWEEN_EVENTS,a,b) for a,b in zip(ids,ids[1:]))
            expected.add((track.track,AudioBoundaryPosition.TRAILING,ids[-1],None))
    output={}; ids=set(); previous: tuple[int, int, int, str, str, str] | None = None
    for i,row in enumerate(boundaries):
        p=f"/boundary_intents/{i}"
        if type(row) is not AudioBoundaryIntent or not _id(row.boundary_intent_id,"abint_") or not _enum(row.track,AudioTrackRole) or not _u(row.ordinal) or row.ordinal != i or not _enum(row.position,AudioBoundaryPosition) or not _enum(row.left_transition,AudioTransitionKind) or not _enum(row.right_transition,AudioTransitionKind) or not _u(row.requested_crossfade_samples): _reject(p,AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
        key=_boundary_key(row.track,row.position,row.left_intent_id,row.right_intent_id)
        if key in output: _reject(p,AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
        if (row.track,row.position,row.left_intent_id,row.right_intent_id) not in expected: _reject(p,AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
        if row.position is AudioBoundaryPosition.LEADING: valid=(row.left_transition is AudioTransitionKind.NONE and row.right_transition in (AudioTransitionKind.NONE,AudioTransitionKind.FADE_IN))
        elif row.position is AudioBoundaryPosition.TRAILING: valid=(row.left_transition in (AudioTransitionKind.NONE,AudioTransitionKind.FADE_OUT) and row.right_transition is AudioTransitionKind.NONE)
        else: valid=(row.left_transition,row.right_transition) in ((AudioTransitionKind.NONE,AudioTransitionKind.NONE),(AudioTransitionKind.CROSSFADE,AudioTransitionKind.CROSSFADE),(AudioTransitionKind.FADE_OUT,AudioTransitionKind.FADE_IN))
        if not valid or ((row.left_transition is AudioTransitionKind.CROSSFADE) != (row.requested_crossfade_samples>0)): _reject(p,AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
        order=_boundary_order_key(row,event_intents)
        if row.boundary_intent_id in ids or previous is not None and order <= previous:
            _reject(p,AudioEdlRejectionReason.ORDERING_INVALID)
        ids.add(row.boundary_intent_id); previous=order
        output[key]=row
    if len(output)!=len(expected): _reject("/boundary_intents/0" if boundaries else "/boundary_intents/0",AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
    return output

def _validate_silences(silences: tuple[AudioPlannedSilence,...], tracks: tuple[AudioEdlTrack,...], duration: int, events: dict[str, EdlAudioEvent], locations: dict[str, tuple[AudioTrackRole, int]])->tuple[dict[tuple[str,str,str,str],AudioPlannedSilence],dict[tuple[str,str,str,str],int]]:
    if type(silences) is not tuple: raise TypeError("planned_silences must be exact tuple")
    by_track={t.track:t.events for t in tracks}; ret={}; indices={}; ids=set(); previous: tuple[Any,...]|None=None
    for i,s in enumerate(silences):
        p=f"/planned_silences/{i}"
        if type(s) is not AudioPlannedSilence or not _id(s.silence_id,"sil_") or not _enum(s.track,AudioTrackRole) or not _u(s.ordinal) or s.ordinal!=i or not _u(s.start_sample) or not _u(s.end_exclusive_sample) or s.start_sample>=s.end_exclusive_sample or (s.left_intent_id is None and s.right_intent_id is None): _reject(p,AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
        key=(_track_priority(s.track),s.start_sample,s.end_exclusive_sample,s.left_intent_id or "",s.right_intent_id or "",s.silence_id)
        if previous is not None and key<=previous: _reject(p,AudioEdlRejectionReason.ORDERING_INVALID)
        if s.silence_id in ids: _reject(p,AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
        ids.add(s.silence_id); previous=key
        left=events.get(s.left_intent_id) if s.left_intent_id is not None else None; right=events.get(s.right_intent_id) if s.right_intent_id is not None else None
        if (left and left.track is not s.track) or (right and right.track is not s.track): _reject(p,AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
        if left is None and (s.start_sample!=0 or right is None or right.start_sample!=s.end_exclusive_sample): _reject(p,AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
        if right is None and (s.end_exclusive_sample!=duration or left is None or left.end_exclusive_sample!=s.start_sample): _reject(p,AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
        if left and right and (left.end_exclusive_sample!=s.start_sample or right.start_sample!=s.end_exclusive_sample): _reject(p,AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
        stream=by_track.get(s.track)
        if stream is None: _reject(p,AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
        if left is None:
            if stream[0] is not right: _reject(p,AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
        elif right is None:
            if stream[-1] is not left: _reject(p,AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
        else:
            left_location=locations.get(left.intent_id); right_location=locations.get(right.intent_id)
            if left_location is None or right_location is None or left_location[0] is not s.track or right_location[0] is not s.track or left_location[1]+1 != right_location[1]:
                _reject(p,AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
        bkey=_boundary_key(s.track,AudioBoundaryPosition.LEADING if left is None else AudioBoundaryPosition.TRAILING if right is None else AudioBoundaryPosition.BETWEEN_EVENTS,s.left_intent_id,s.right_intent_id)
        if bkey in ret: _reject(p,AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
        ret[bkey]=s; indices[bkey]=i
    return ret,indices

def _validate_same_track_overlap_authorization(tracks: tuple[AudioEdlTrack,...], boundary_intents: tuple[AudioBoundaryIntent,...])->None:
    """Reject every public-helper overlap except its exact crossfade authority.

    ``plan_audio_boundaries`` is public, so it cannot rely on ``_compile`` to
    reject a forged event stream later.  This deliberately precedes generic
    boundary-row validation: a malformed or missing authorization row must not
    downgrade a positive same-track collision into a boundary-metadata error.
    """
    # Do not rescan every caller boundary for each adjacent event pair.  This
    # helper is public ingress, so malformed duplicate rows are still allowed
    # to reach the later strict boundary validator; for collision purposes the
    # old ``any(...)`` semantics are exactly whether at least one row carries
    # the crossfade authority for this relation.
    authorized_crossfade_samples_by_key: dict[tuple[str, str, str, str], set[int]] = {}
    for row in boundary_intents:
        if type(row) is not AudioBoundaryIntent:
            continue
        key = _boundary_key(row.track, row.position, row.left_intent_id, row.right_intent_id)
        if (
            row.position is AudioBoundaryPosition.BETWEEN_EVENTS
            and row.left_transition is AudioTransitionKind.CROSSFADE
            and row.right_transition is AudioTransitionKind.CROSSFADE
        ):
            authorized_crossfade_samples_by_key.setdefault(key, set()).add(row.requested_crossfade_samples)
    for track_index, track in enumerate(tracks):
        # The public helper receives an already materialized EDL track.  A
        # temporal inversion cannot be swept deterministically and is not a
        # valid track order.
        previous_start: int | None = None
        prior_nonadjacent_end: int | None = None
        for event_index, (left, right) in enumerate(zip(track.events, track.events[1:])):
            if previous_start is None:
                previous_start = left.start_sample
            if right.start_sample < previous_start:
                _reject(f"/tracks/{track_index}/events/{event_index + 1}", AudioEdlRejectionReason.ORDERING_INVALID)
            previous_start = right.start_sample
            # An adjacent crossfade is the sole legal same-track overlap.
            # A running pre-adjacent maximum catches triple/nested and any
            # non-adjacent overlap without a quadratic pair scan.
            if event_index:
                prior_nonadjacent_end = max(prior_nonadjacent_end or 0, track.events[event_index - 1].end_exclusive_sample)
            if prior_nonadjacent_end is not None and right.start_sample < prior_nonadjacent_end:
                _reject(f"/tracks/{track_index}/events/{event_index + 1}", AudioEdlRejectionReason.TRACK_COLLISION)
            overlap = left.end_exclusive_sample - right.start_sample
            if overlap <= 0:
                continue
            authorized = (
                overlap in authorized_crossfade_samples_by_key.get(
                    _boundary_key(track.track, AudioBoundaryPosition.BETWEEN_EVENTS, left.intent_id, right.intent_id),
                    set(),
                )
                and overlap >= 2
                and left.kind not in (AudioEventKind.NARRATION, AudioEventKind.SOURCE_SPEECH)
                and right.kind not in (AudioEventKind.NARRATION, AudioEventKind.SOURCE_SPEECH)
                and right.end_exclusive_sample > left.end_exclusive_sample
            )
            if not authorized:
                _reject(
                    f"/tracks/{track_index}/events/{event_index + 1}",
                    AudioEdlRejectionReason.TRACK_COLLISION,
                )

def plan_audio_boundaries(*, tracks: tuple[AudioEdlTrack,...], intents: tuple[AudioPlacementIntent,...], boundary_intents: tuple[AudioBoundaryIntent,...], planned_silences: tuple[AudioPlannedSilence,...], pcm_evidence: tuple[ReplayPcmEvidence,...], duration_samples: int)->tuple[AudioBoundaryDecision,...]:
    if type(tracks) is not tuple or not _u(duration_samples): raise TypeError("tracks and duration_samples must be exact contract values")
    if type(intents) is not tuple or type(pcm_evidence) is not tuple:
        raise TypeError("intents and pcm_evidence must be exact tuples")
    # The public planner consumes the same closed A1--A5 registry as a
    # materialized AudioEdlArtifact.  Accepting a subset here would let a
    # caller obtain decisions from a different contract shape than the one
    # compiler/loader later publish.
    if len(tracks) != len(AudioTrackRole):
        _reject("/tracks", AudioEdlRejectionReason.STRUCTURE_INVALID)
    for track_index, expected_role in enumerate(AudioTrackRole):
        track = tracks[track_index]
        if type(track) is not AudioEdlTrack or type(track.events) is not tuple:
            _reject(f"/tracks/{track_index}", AudioEdlRejectionReason.STRUCTURE_INVALID)
        if track.track is not expected_role:
            _reject(f"/tracks/{track_index}", AudioEdlRejectionReason.ORDERING_INVALID)
        if track.priority != _track_priority(expected_role):
            _reject(f"/tracks/{track_index}", AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
    # This public API is intentionally as strict as the compiler ingress.  It
    # must not trust a caller to hand it internally generated events: every
    # event, intent, source and PCM evidence record is bound below before any
    # seam decision is made.  All lookups are pre-indexed to keep large REPLAY
    # plans O(W + I + S + B), apart from the explicitly bounded crossing scan.
    intent_by_id: dict[str, AudioPlacementIntent] = {}
    source_by_id: dict[str, ReplayPcmSource] = {}
    for index, intent in enumerate(intents):
        p=f"/intents/{index}"
        if type(intent) is not AudioPlacementIntent or not _id(intent.intent_id) or intent.intent_id in intent_by_id or not _enum(intent.track,AudioTrackRole) or not _enum(intent.kind,AudioEventKind) or intent.kind is not _kind(intent.track) or not _u(intent.ordinal) or intent.ordinal != index or not _i32(intent.gain_millibels) or not -96000 <= intent.gain_millibels <= 24000 or type(intent.source) is not ReplayPcmSource:
            _reject(p,AudioEdlRejectionReason.CUE_RESOLUTION_INVALID)
        # The helper is not a source-ingress validator (the compiler owns
        # source schema validation), but it does require one exact immutable
        # source value for every source ID used by its event stream.
        _validate_source(intent.source, index, pointer_prefix="/intents")
        # Placement coordinates live on the delay/padding-compensated source
        # timeline.  A structurally valid source can still have less usable
        # material than a caller claims: reject that forged extent before it
        # is bound to an event or allowed to influence a seam decision.
        effective_source_frames = (
            intent.source.normalized_sample_frames
            - intent.source.encoder_delay_samples
            - intent.source.encoder_padding_samples
        )
        if (
            not _u(intent.source_in_sample)
            or not _u(intent.source_out_exclusive_sample)
            or intent.source_in_sample >= intent.source_out_exclusive_sample
            or intent.source_out_exclusive_sample > effective_source_frames
        ):
            _reject(p, AudioEdlRejectionReason.ENCODER_COMPENSATION_INVALID)
        prior=source_by_id.get(intent.source.source_id)
        if prior is not None and prior != intent.source: _reject(p,AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
        intent_by_id[intent.intent_id]=intent; source_by_id[intent.source.source_id]=intent.source
    evidence_by_source: dict[str, ReplayPcmEvidence] = {}
    for index, evidence in enumerate(pcm_evidence):
        _validate_evidence(evidence,index)
        if evidence.source_id in evidence_by_source: _reject(f"/pcm_evidence/{index}",AudioEdlRejectionReason.PCM_EVIDENCE_INVALID)
        source=source_by_id.get(evidence.source_id)
        if source is None or (source.normalized_pcm_evidence_hash,source.pcm_format,source.normalized_sample_frames)!=(evidence.normalized_pcm_evidence_hash,evidence.pcm_format,evidence.sample_frames):
            _reject(f"/pcm_evidence/{index}",AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
        evidence_by_source[evidence.source_id]=evidence
    if set(source_by_id) != set(evidence_by_source): _reject("/pcm_evidence/0",AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    event_by_intent: dict[str, EdlAudioEvent] = {}
    locations: dict[str, tuple[AudioTrackRole,int]] = {}
    # The helper is public and therefore must not turn a forged event extent
    # into a terminal decision outside the caller-provided sequence bound.
    for track_index, track in enumerate(tracks):
        if type(track) is not AudioEdlTrack or not _enum(track.track, AudioTrackRole) or track.priority != _track_priority(track.track) or type(track.events) is not tuple:
            _reject(f"/tracks/{track_index}/events/0",AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
        for event_index, event in enumerate(track.events):
            if type(event) is not EdlAudioEvent or event.track is not track.track or event.end_exclusive_sample > duration_samples:
                _reject(f"/tracks/{track_index}/events/{event_index}",AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
            intent=intent_by_id.get(event.intent_id)
            if intent is None or event.intent_id in event_by_intent:
                _reject(f"/tracks/{track_index}/events/{event_index}",AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
            _validate_event_integrity(event,intent,f"/tracks/{track_index}/events/{event_index}")
            if event.source_id not in evidence_by_source: _reject(f"/tracks/{track_index}/events/{event_index}",AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
            event_by_intent[event.intent_id]=event; locations[event.intent_id]=(track.track,event_index)
    if set(event_by_intent) != set(intent_by_id): _reject("/tracks/0/events/0",AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    _validate_same_track_overlap_authorization(tracks, boundary_intents)
    bmap=_validate_boundary_rows(boundary_intents,tracks,intents,event_by_intent)
    smap,silence_indices=_validate_silences(planned_silences,tracks,duration_samples,event_by_intent,locations)
    result=[]
    for track in tracks:
        events=track.events
        if not events: continue
        pairs=[(AudioBoundaryPosition.LEADING,None,events[0]),*[(AudioBoundaryPosition.BETWEEN_EVENTS,a,b) for a,b in zip(events,events[1:])],(AudioBoundaryPosition.TRAILING,events[-1],None)]
        for position,left,right in pairs:
            key=_boundary_key(track.track,position,left.intent_id if left else None,right.intent_id if right else None); row=bmap[key]; silence=smap.get(key)
            if silence:
                if row.left_transition is not AudioTransitionKind.NONE or row.right_transition is not AudioTransitionKind.NONE:
                    _reject(f"/boundary_intents/{row.ordinal}",AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
                # PRESERVE_SILENCE is physical: every bound source edge is exactly
                # stereo zero at its effective (delay compensated) PCM frame.
                for event,trailing in ((left,True),(right,False)):
                    if event is None: continue
                    src=source_by_id.get(event.source_id); ev=evidence_by_source.get(event.source_id)
                    frame=src.encoder_delay_samples+(event.source_out_exclusive_sample-1 if trailing else event.source_in_sample) if src else -1
                    offset=frame*2
                    if ev is None or offset < 0 or offset+1 >= len(ev.interleaved_samples) or ev.interleaved_samples[offset] != 0 or ev.interleaved_samples[offset+1] != 0:
                        _reject(f"/planned_silences/{silence_indices[key]}",AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
                decision=AudioBoundaryDecision(position,left.event_id if left else None,right.event_id if right else None,track.track,AudioBoundaryPolicy.PRESERVE_SILENCE,AudioTransitionKind.NONE,0,0,0,0,0,silence.end_exclusive_sample-silence.start_sample)
            elif position is AudioBoundaryPosition.BETWEEN_EVENTS and row.left_transition is AudioTransitionKind.CROSSFADE:
                if left is None or right is None or left.kind in (AudioEventKind.NARRATION,AudioEventKind.SOURCE_SPEECH) or right.kind in (AudioEventKind.NARRATION,AudioEventKind.SOURCE_SPEECH) or left.end_exclusive_sample-right.start_sample != row.requested_crossfade_samples or right.end_exclusive_sample<=left.end_exclusive_sample or row.requested_crossfade_samples<2: _reject(f"/boundary_intents/{row.ordinal}",AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
                decision=AudioBoundaryDecision(position,left.event_id,right.event_id,track.track,AudioBoundaryPolicy.OVERLAP_CROSSFADE,AudioTransitionKind.CROSSFADE,0,0,row.requested_crossfade_samples,row.requested_crossfade_samples,row.requested_crossfade_samples,0)
            elif (position is AudioBoundaryPosition.LEADING and row.right_transition is AudioTransitionKind.FADE_IN) or (position is AudioBoundaryPosition.TRAILING and row.left_transition is AudioTransitionKind.FADE_OUT) or (position is AudioBoundaryPosition.BETWEEN_EVENTS and row.left_transition is AudioTransitionKind.FADE_OUT):
                if track.track not in (AudioTrackRole.A2,AudioTrackRole.A5): _reject(f"/boundary_intents/{row.ordinal}",AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
                if (left and left.end_exclusive_sample-left.start_sample<LONG_EDITORIAL_FADE_SAMPLES) or (right and right.end_exclusive_sample-right.start_sample<LONG_EDITORIAL_FADE_SAMPLES): _reject(f"/boundary_intents/{row.ordinal}",AudioEdlRejectionReason.BOUNDARY_POLICY_INVALID)
                transition=(AudioTransitionKind.FADE_IN if position is AudioBoundaryPosition.LEADING else AudioTransitionKind.FADE_OUT if position is AudioBoundaryPosition.TRAILING else AudioTransitionKind.NONE)
                decision=AudioBoundaryDecision(position,left.event_id if left else None,right.event_id if right else None,track.track,AudioBoundaryPolicy.LONG_EDITORIAL_FADE,transition,0,0,LONG_EDITORIAL_FADE_SAMPLES if row.right_transition is AudioTransitionKind.FADE_IN else 0,LONG_EDITORIAL_FADE_SAMPLES if row.left_transition is AudioTransitionKind.FADE_OUT else 0,0,0)
            elif position is AudioBoundaryPosition.BETWEEN_EVENTS and left and right and track.track in (AudioTrackRole.A3,AudioTrackRole.A5):
                ls=source_by_id.get(left.source_id); rs=source_by_id.get(right.source_id); le=evidence_by_source.get(left.source_id); re=evidence_by_source.get(right.source_id)
                if ls is None or rs is None or le is None or re is None: _reject(f"/boundary_intents/{row.ordinal}",AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
                a=_crossing(le,ls,left,True) if le else None; b=_crossing(re,rs,right,False) if re else None
                if a==0 and b==0: decision=AudioBoundaryDecision(position,left.event_id,right.event_id,track.track,AudioBoundaryPolicy.HARD_CUT_ZERO_CROSSING,AudioTransitionKind.NONE,0,0,0,0,0,0)
                else: decision=AudioBoundaryDecision(position,left.event_id,right.event_id,track.track,AudioBoundaryPolicy.ZERO_CROSSING_MICROFADE,AudioTransitionKind.NONE,a or 0,b or 0,0 if a is not None else MICROFADE_SAMPLES,0 if b is not None else MICROFADE_SAMPLES,0,0)
            else:
                def seam(event: EdlAudioEvent | None, trailing: bool) -> tuple[int, int]:
                    if event is None: return 0, 0
                    source=source_by_id.get(event.source_id); evidence=evidence_by_source.get(event.source_id)
                    if source is None or evidence is None: _reject("/tracks/0/events/0",AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
                    trim=_crossing(evidence,source,event,trailing) if evidence else None
                    if event.track is AudioTrackRole.A1:
                        return 0, 0 if trim == 0 else MICROFADE_SAMPLES
                    return trim or 0, 0 if trim is not None else MICROFADE_SAMPLES
                left_trim,left_fade=seam(left,True); right_trim,right_fade=seam(right,False)
                decision=AudioBoundaryDecision(position,left.event_id if left else None,right.event_id if right else None,track.track,AudioBoundaryPolicy.ZERO_CROSSING_MICROFADE,AudioTransitionKind.NONE,left_trim,right_trim,right_fade,left_fade,0,0)
            result.append(decision)
    return tuple(result)

def _compile(*, video_edl: VideoEdlArtifact, word_to_frame: WordToFrameArtifact, narration_audio: AudioArtifact, intents: tuple[AudioPlacementIntent,...], boundary_intents: tuple[AudioBoundaryIntent,...], sources: tuple[ReplayPcmSource,...], pcm_evidence: tuple[ReplayPcmEvidence,...], planned_silences: tuple[AudioPlannedSilence,...], internal_pcm_format: InternalPcmFormat)->AudioEdlArtifact:
    _dep(video_edl,VideoEdlArtifact,serialize_video_edl,"/video_edl"); _dep(word_to_frame,WordToFrameArtifact,serialize_word_to_frame,"/word_to_frame"); _dep(narration_audio,AudioArtifact,serialize_audio_artifact,"/narration_audio")
    if type(intents) is not tuple or type(sources) is not tuple or type(pcm_evidence) is not tuple or type(internal_pcm_format) is not InternalPcmFormat: raise TypeError("audio EDL collections and format must be exact contract types")
    if (video_edl.word_to_frame_id,video_edl.word_to_frame_hash)!=(word_to_frame.word_to_frame_id,word_to_frame.word_to_frame_hash) or (video_edl.project_id,video_edl.document_id,video_edl.narration_revision_id,video_edl.narration_revision_hash)!=(word_to_frame.project_id,word_to_frame.document_id,word_to_frame.narration_revision_id,word_to_frame.narration_revision_hash): _reject("/video_edl",AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    if (video_edl.fps_numerator,video_edl.fps_denominator)!=(word_to_frame.frame_rate.numerator,word_to_frame.frame_rate.denominator): _reject("/video_edl",AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    lineage=(video_edl.project_id,video_edl.document_id,video_edl.narration_revision_id,video_edl.narration_revision_hash)
    if lineage != (narration_audio.project_id,narration_audio.document_id,narration_audio.narration_revision_id,narration_audio.narration_revision_hash): _reject("/narration_audio",AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    duration=_sample_at_frame(video_edl,video_edl.duration_frames)
    smap:dict[str,ReplayPcmSource]={}; emap:dict[str,ReplayPcmEvidence]={}
    prev=None
    for i,s in enumerate(sources):
        _validate_source(s,i)
        if s.pcm_format is not internal_pcm_format or s.source_id in smap: _reject(f"/sources/{i}",AudioEdlRejectionReason.PCM_EVIDENCE_INVALID)
        if prev is not None and s.source_id<=prev: _reject(f"/sources/{i}",AudioEdlRejectionReason.ORDERING_INVALID)
        prev=s.source_id; smap[s.source_id]=s
    prev=None
    for i,e in enumerate(pcm_evidence):
        _validate_evidence(e,i)
        if e.pcm_format is not internal_pcm_format or e.source_id in emap: _reject(f"/pcm_evidence/{i}",AudioEdlRejectionReason.PCM_EVIDENCE_INVALID)
        if prev is not None and e.source_id<=prev: _reject(f"/pcm_evidence/{i}",AudioEdlRejectionReason.ORDERING_INVALID)
        prev=e.source_id; emap[e.source_id]=e
        s=smap.get(e.source_id)
        if s is None or (s.normalized_pcm_evidence_hash,s.pcm_format,s.normalized_sample_frames)!=(e.normalized_pcm_evidence_hash,e.pcm_format,e.sample_frames): _reject(f"/pcm_evidence/{i}",AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    if len(smap)!=len(emap): _reject("/sources/0" if sources else "/pcm_evidence/0",AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    if any(source.source_id != evidence.source_id for source,evidence in zip(sources,pcm_evidence,strict=True)):
        _reject("/pcm_evidence/0",AudioEdlRejectionReason.ORDERING_INVALID)
    words={x.source_id:x for x in word_to_frame.word_frames}
    if len(words)!=len(word_to_frame.word_frames): _reject("/word_to_frame",AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    rows:dict[AudioTrackRole,list[EdlAudioEvent]]={x:[] for x in AudioTrackRole}; seen=set(); previous:tuple[Any,...]|None=None
    for index,intent in enumerate(intents):
        p=f"/intents/{index}"
        if type(intent) is not AudioPlacementIntent or not _id(intent.intent_id) or intent.intent_id in seen or not _enum(intent.track,AudioTrackRole) or not _enum(intent.kind,AudioEventKind) or intent.kind is not _kind(intent.track) or not _u(intent.ordinal) or intent.ordinal!=index or not _i32(intent.gain_millibels) or not -96000<=intent.gain_millibels<=24000 or type(intent.source) is not ReplayPcmSource: _reject(p,AudioEdlRejectionReason.CUE_RESOLUTION_INVALID)
        if intent.source != smap.get(intent.source.source_id): _reject(p,AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
        if not _u(intent.source_in_sample) or not _u(intent.source_out_exclusive_sample) or not intent.source_in_sample<intent.source_out_exclusive_sample or intent.source_out_exclusive_sample > intent.source.normalized_sample_frames-intent.source.encoder_delay_samples-intent.source.encoder_padding_samples: _reject(p,AudioEdlRejectionReason.ENCODER_COMPENSATION_INVALID)
        if (intent.cue.project_id,intent.cue.document_id,intent.cue.narration_revision_id)!=lineage[:3]: _reject(p,AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
        span=_cue_span(intent,words,video_edl); event=_event(intent,span)
        if not 0<=event.start_sample<event.end_exclusive_sample<=duration: _reject(p,AudioEdlRejectionReason.SEQUENCE_BOUNDS_INVALID)
        if intent.track is AudioTrackRole.A1 and (event.start_sample,event.end_exclusive_sample)!=(span.start_sample,span.end_exclusive_sample): _reject(p,AudioEdlRejectionReason.CUE_RESOLUTION_INVALID)
        # Caller order is part of the canonical ingress contract.  Track
        # priority comes first so concurrent A1..A5 intent streams do not
        # depend on their incidental cue timestamps.
        key=(_track_priority(intent.track),event.start_sample,event.end_exclusive_sample,intent.intent_id)
        if previous is not None and key<=previous: _reject(p,AudioEdlRejectionReason.ORDERING_INVALID)
        previous=key; seen.add(intent.intent_id); rows[intent.track].append(event)
    if {intent.source.source_id for intent in intents} != set(smap):
        _reject("/sources/0",AudioEdlRejectionReason.PCM_EVIDENCE_INVALID)
    tracks=[]
    for role in AudioTrackRole:
        events=rows[role]
        for i,event in enumerate(events):
            if i and events[i-1].end_exclusive_sample>event.start_sample:
                # overlap is admitted only by the later authoritative boundary row.
                pass
        tracks.append(AudioEdlTrack(role,_track_priority(role),tuple(events)))
    # A1 narration source metadata is a separate hard binding.
    a1=rows[AudioTrackRole.A1]
    if a1:
        matched=[s for s in sources if s.source_id==narration_audio.audio_artifact_id]
        if len(matched)!=1 or any(e.source_id!=matched[0].source_id for e in a1) or (matched[0].source_media_hash,matched[0].source_sample_rate_hz,matched[0].source_channel_count,matched[0].source_sample_frames)!=(narration_audio.media_byte_hash,narration_audio.decoded_metadata.sample_rate_hz,narration_audio.decoded_metadata.channel_count,narration_audio.decoded_metadata.sample_frame_count): _reject("/narration_audio",AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    # Boundary validation needs the event stream; it also admits only declared overlaps.
    decisions=plan_audio_boundaries(tracks=tuple(tracks),intents=intents,boundary_intents=boundary_intents,planned_silences=planned_silences,pcm_evidence=pcm_evidence,duration_samples=duration)
    overlap_rows={(row.left_intent_id,row.right_intent_id):row for row in boundary_intents}
    for track in tracks:
        for left,right in zip(track.events,track.events[1:]):
            if left.end_exclusive_sample>right.start_sample:
                row=overlap_rows.get((left.intent_id,right.intent_id))
                if row is None or row.left_transition is not AudioTransitionKind.CROSSFADE: _reject(f"/tracks/{_TRACK_PRIORITIES[track.track] // 10 - 1}/events/1",AudioEdlRejectionReason.TRACK_COLLISION)
    for a1event in rows[AudioTrackRole.A1]:
        for speech in rows[AudioTrackRole.A4]:
            if max(a1event.start_sample,speech.start_sample)<min(a1event.end_exclusive_sample,speech.end_exclusive_sample): _reject("/tracks/3/events/0",AudioEdlRejectionReason.SPEECH_COLLISION)
    base=AudioEdlArtifact(AUDIO_EDL_V1,AUDIO_EDL_HASH_V1,"","",video_edl.video_edl_id,video_edl.video_edl_hash,word_to_frame.word_to_frame_id,word_to_frame.word_to_frame_hash,narration_audio.audio_artifact_id,narration_audio.audio_artifact_hash,narration_audio.media_byte_hash,*lineage,video_edl.sequence_id,AUDIO_SAMPLE_CLOCK_V1,48000,2,internal_pcm_format,sources,pcm_evidence,duration,tuple(tracks),boundary_intents,planned_silences,decisions)
    value=_artifact_dict(base); value.pop("audio_edl_id"); value.pop("audio_edl_hash"); h=_digest(value)
    return AudioEdlArtifact(base.schema_version,base.hash_scope_version,"aedl_"+h[:32],h,*tuple(getattr(base,x) for x in _ROOT_FIELDS[4:]))

def compile_audio_edl(*, video_edl: VideoEdlArtifact, word_to_frame: WordToFrameArtifact, narration_audio: AudioArtifact, intents: tuple[AudioPlacementIntent,...], boundary_intents: tuple[AudioBoundaryIntent,...], sources: tuple[ReplayPcmSource,...], pcm_evidence: tuple[ReplayPcmEvidence,...], planned_silences: tuple[AudioPlannedSilence,...], internal_pcm_format: InternalPcmFormat)->AudioEdlArtifact:
    value=_compile(video_edl=video_edl,word_to_frame=word_to_frame,narration_audio=narration_audio,intents=intents,boundary_intents=boundary_intents,sources=sources,pcm_evidence=pcm_evidence,planned_silences=planned_silences,internal_pcm_format=internal_pcm_format)
    _register(value,_canonical_bytes(_artifact_dict(value))); return value

def _parse(source: bytes)->Any:
    if type(source) is not bytes: raise TypeError("source must be exact bytes")
    class Pairs(list): pass
    try:
        if source.startswith(b"\xef\xbb\xbf"): raise ValueError
        parsed=json.loads(source.decode("utf-8"),object_pairs_hook=Pairs,parse_float=float,parse_int=lambda text: int(text) if text==str(int(text)) else (_ for _ in ()).throw(ValueError()),parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except Exception: _reject("/",AudioEdlRejectionReason.NON_CANONICAL_SERIALIZATION)
    def plain(v:Any)->Any:
        if type(v) is Pairs:
            if len(v)!=len({k for k,_ in v}): _reject("/",AudioEdlRejectionReason.NON_CANONICAL_SERIALIZATION)
            return {k:plain(x) for k,x in v}
        if type(v) is list:return [plain(x) for x in v]
        return v
    value=plain(parsed)
    try: canonical=_canonical_bytes(value)
    except Exception: _reject("/",AudioEdlRejectionReason.NON_CANONICAL_SERIALIZATION)
    if canonical!=source:_reject("/",AudioEdlRejectionReason.NON_CANONICAL_SERIALIZATION)
    return value

def _shape(value:Any, expected:Any, pointer:str="/")->None:
    """Exact recursive JSON shape check before trusted recompilation."""
    if type(expected) is dict:
        if type(value) is not dict or set(value)!=set(expected): _reject(pointer,AudioEdlRejectionReason.STRUCTURE_INVALID)
        for key,item in expected.items(): _shape(value[key],item,pointer)
    elif type(expected) is list:
        if type(value) is not list or len(value)!=len(expected): _reject(pointer,AudioEdlRejectionReason.STRUCTURE_INVALID)
        for item,wanted in zip(value,expected,strict=True): _shape(item,wanted,pointer)
    elif expected is None:
        if value is not None:_reject(pointer,AudioEdlRejectionReason.STRUCTURE_INVALID)
    elif type(expected) is bool:
        if type(value) is not bool:_reject(pointer,AudioEdlRejectionReason.STRUCTURE_INVALID)
    elif type(expected) is int:
        if type(value) is not int:_reject(pointer,AudioEdlRejectionReason.STRUCTURE_INVALID)
    elif type(expected) is float:
        if type(value) not in (int,float) or type(value) is bool:_reject(pointer,AudioEdlRejectionReason.STRUCTURE_INVALID)
    elif type(expected) is str:
        if type(value) is not str:_reject(pointer,AudioEdlRejectionReason.STRUCTURE_INVALID)

def load_audio_edl(source: bytes, *, video_edl: VideoEdlArtifact, word_to_frame: WordToFrameArtifact, narration_audio: AudioArtifact, intents: tuple[AudioPlacementIntent,...], boundary_intents: tuple[AudioBoundaryIntent,...], sources: tuple[ReplayPcmSource,...], pcm_evidence: tuple[ReplayPcmEvidence,...], planned_silences: tuple[AudioPlannedSilence,...], internal_pcm_format: InternalPcmFormat)->AudioEdlArtifact:
    value=_parse(source)
    expected=_compile(video_edl=video_edl,word_to_frame=word_to_frame,narration_audio=narration_audio,intents=intents,boundary_intents=boundary_intents,sources=sources,pcm_evidence=pcm_evidence,planned_silences=planned_silences,internal_pcm_format=internal_pcm_format)
    wanted=_artifact_dict(expected); _shape(value,wanted)
    # Dependency/root bindings win over semantic comparison and identity.
    for fields,pointer in ((("video_edl_id","video_edl_hash"),"/video_edl"),(("word_to_frame_id","word_to_frame_hash"),"/word_to_frame"),(("narration_audio_id","narration_audio_hash","narration_audio_media_byte_hash"),"/narration_audio")):
        if any(value[x]!=wanted[x] for x in fields): _reject(pointer,AudioEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    for name,pointer in (("sources","/sources/0"),("pcm_evidence","/pcm_evidence/0"),("boundary_intents","/boundary_intents/0"),("planned_silences","/planned_silences/0")):
        if value[name]!=wanted[name]: _reject(pointer,AudioEdlRejectionReason.DEPENDENCY_CONTENT_DRIFT)
    if value.get("schema_version")!=AUDIO_EDL_V1 or value.get("hash_scope_version")!=AUDIO_EDL_HASH_V1 or value.get("sample_clock_version")!=AUDIO_SAMPLE_CLOCK_V1: _reject("/",AudioEdlRejectionReason.UNSUPPORTED_VALUE)
    if value["boundary_decisions"]!=wanted["boundary_decisions"]: _reject("/boundary_decisions/0",AudioEdlRejectionReason.DEPENDENCY_CONTENT_DRIFT)
    if value["tracks"]!=wanted["tracks"]: _reject("/tracks/0/events/0",AudioEdlRejectionReason.CUE_RESOLUTION_INVALID)
    projection={k:v for k,v in value.items() if k not in {"audio_edl_id","audio_edl_hash"}}
    computed=_digest(projection)
    if value["audio_edl_hash"]!=computed or value["audio_edl_id"]!="aedl_"+computed[:32]: _reject("/",AudioEdlRejectionReason.IDENTITY_MISMATCH)
    if value != wanted:_reject("/",AudioEdlRejectionReason.IDENTITY_MISMATCH)
    _register(expected,source); return expected

def serialize_audio_edl(artifact: AudioEdlArtifact)->bytes:
    if type(artifact) is not AudioEdlArtifact: raise TypeError("artifact must be exact AudioEdlArtifact")
    entry=_REGISTRY.get(id(artifact))
    if entry is None or entry[0]() is not artifact: _reject("/",AudioEdlRejectionReason.NOT_MATERIALIZED)
    try: current=_canonical_bytes(_artifact_dict(artifact))
    except Exception: _reject("/",AudioEdlRejectionReason.CONTENT_DRIFT)
    if entry[2]!=_signature(artifact) or current!=entry[1]: _reject("/",AudioEdlRejectionReason.CONTENT_DRIFT)
    return bytes(entry[1])
