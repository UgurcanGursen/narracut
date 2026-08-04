"""Deterministic, sparse Phase 3A video EDL contract.

This module deliberately compiles only video-frame scheduling.  It neither
opens media nor allocates a frame buffer; Phase 4 is the first consumer that
may render these bytes.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
import weakref
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ._canonical_json import encode_canonical_json_bytes
from .caption_groups import CaptionGroupsArtifact, serialize_caption_groups
from .caption_preview import CaptionPreviewArtifact, PreviewTrack, serialize_caption_preview
from .emphasis_events import EmphasisEventsArtifact, EmphasisIntensity, EmphasisTypeRef, serialize_emphasis_events
from .v5_v6_collision import V5V6CollisionReport, serialize_v5_v6_collision_report
from .word_to_frame import WordToFrameArtifact, serialize_word_to_frame

VIDEO_EDL_V1 = "VIDEO-EDL-V1"
VIDEO_EDL_HASH_V1 = "VIDEO-EDL-HASH-V1"
VIDEO_CLOCK_V1 = "VIDEO-FRAME-CLOCK-V1"
_MAX = 2**32 - 1
_ID = re.compile(r"^[\x21-\x7e]{1,128}$")

__all__ = [
    "VIDEO_EDL_V1", "VIDEO_EDL_HASH_V1", "VIDEO_CLOCK_V1",
    "TimelineTrack", "EdlTrackKind", "EdlPayloadKind", "SourcePlaybackMode",
    "SourceFitMode", "CueWordRange", "SourceDescriptor", "VideoEditIntent",
    "EdlRenderPayload", "EdlVideoEvent", "EdlTrack", "VideoEdlArtifact",
    "VideoEdlRejectionReason", "VideoEdlContractError", "compile_video_edl",
    "load_video_edl", "serialize_video_edl",
]


class TimelineTrack(str, Enum):
    V1 = "V1"; V2 = "V2"; V3 = "V3"; V4 = "V4"; V5 = "V5"; V6 = "V6"; V7 = "V7"
    A1 = "A1"; A2 = "A2"; A3 = "A3"; A4 = "A4"; A5 = "A5"


class EdlTrackKind(str, Enum):
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"


class EdlPayloadKind(str, Enum):
    CALLER_SOURCE = "CALLER_SOURCE"
    KINETIC_EMPHASIS = "KINETIC_EMPHASIS"
    CAPTION = "CAPTION"


class SourcePlaybackMode(str, Enum):
    HOLD = "HOLD"
    LOOP = "LOOP"
    FIT = "FIT"


class SourceFitMode(str, Enum):
    CONTAIN = "CONTAIN"
    COVER = "COVER"
    STRETCH = "STRETCH"


class VideoEdlRejectionReason(str, Enum):
    STRUCTURE_INVALID = "STRUCTURE_INVALID"; UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
    DEPENDENCY_CONTENT_DRIFT = "DEPENDENCY_CONTENT_DRIFT"; DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
    CUE_RESOLUTION_INVALID = "CUE_RESOLUTION_INVALID"; TRACK_COLLISION = "TRACK_COLLISION"
    V5_V6_COLLISION_BLOCKED = "V5_V6_COLLISION_BLOCKED"; NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"; CONTENT_DRIFT = "CONTENT_DRIFT"; NOT_MATERIALIZED = "NOT_MATERIALIZED"


@dataclass(frozen=True)
class CueWordRange:
    project_id: str
    document_id: str
    narration_revision_id: str
    start_word_id: str
    end_word_id: str


@dataclass(frozen=True)
class SourceDescriptor:
    source_ref: str
    source_fps_numerator: int
    source_fps_denominator: int
    source_in_frame: int
    source_out_exclusive_frame: int
    playback_mode: SourcePlaybackMode
    fit_mode: SourceFitMode
    crop_left_millionths: int
    crop_top_millionths: int
    crop_right_millionths: int
    crop_bottom_millionths: int
    opacity_millionths: int
    bound_start_word_id: str
    bound_end_word_id: str


@dataclass(frozen=True)
class VideoEditIntent:
    intent_id: str
    track: TimelineTrack
    cue: CueWordRange
    source: SourceDescriptor
    editorial_role: str
    ordinal: int


@dataclass(frozen=True)
class EdlRenderPayload:
    kind: EdlPayloadKind
    source: SourceDescriptor | None
    source_artifact_id: str | None
    source_artifact_hash: str | None
    source_record_id: str | None
    source_record_hash: str | None
    source_record_ordinal: int | None
    preview_scene_id: str | None
    preview_scene_hash: str | None
    preview_left_millionths: int | None
    preview_top_millionths: int | None
    preview_right_millionths: int | None
    preview_bottom_millionths: int | None
    text: str | None
    emphasis_type_ref: EmphasisTypeRef | None
    emphasis_intensity: Any | None


@dataclass(frozen=True)
class EdlVideoEvent:
    schema_version: str
    hash_scope_version: str
    event_id: str
    event_hash: str
    track: TimelineTrack
    ordinal: int
    intent_id: str
    editorial_role: str
    start_frame: int
    end_exclusive_frame: int
    start_word_id: str
    end_word_id: str
    payload: EdlRenderPayload


@dataclass(frozen=True)
class EdlTrack:
    track: TimelineTrack
    kind: EdlTrackKind
    priority: int
    events: tuple[EdlVideoEvent, ...]


@dataclass(frozen=True)
class VideoEdlArtifact:
    schema_version: str
    hash_scope_version: str
    video_edl_id: str
    video_edl_hash: str
    project_id: str
    document_id: str
    narration_revision_id: str
    narration_revision_hash: str
    sequence_id: str
    sequence_start_word_id: str
    sequence_end_word_id: str
    sequence_start_frame: int
    sequence_content_end_exclusive_frame: int
    trailing_silence_frames: int
    sequence_end_exclusive_frame: int
    word_to_frame_id: str
    word_to_frame_hash: str
    caption_preview_id: str
    caption_preview_hash: str
    v5_v6_collision_report_id: str
    v5_v6_collision_report_hash: str
    clock_version: str
    fps_numerator: int
    fps_denominator: int
    duration_frames: int
    tracks: tuple[EdlTrack, ...]


_ROOT_FIELDS = tuple(VideoEdlArtifact.__dataclass_fields__)
_EVENT_FIELDS = tuple(EdlVideoEvent.__dataclass_fields__)
_TRACK_FIELDS = tuple(EdlTrack.__dataclass_fields__)
_PAYLOAD_FIELDS = tuple(EdlRenderPayload.__dataclass_fields__)
_CUE_FIELDS = tuple(CueWordRange.__dataclass_fields__)
_SOURCE_FIELDS = tuple(SourceDescriptor.__dataclass_fields__)
_REGISTRY: dict[int, tuple[weakref.ReferenceType[VideoEdlArtifact], bytes, tuple[int, ...]]] = {}


class VideoEdlContractError(ValueError):
    def __init__(self, pointer: str, reason: VideoEdlRejectionReason, issue_code: str | None = None) -> None:
        if type(pointer) is not str or type(reason) is not VideoEdlRejectionReason:
            raise TypeError("invalid video EDL error construction")
        super().__init__(f"Video EDL rejected: {reason.value}")
        self.pointer, self.reason, self.issue_code = pointer, reason, issue_code


def _reject(pointer: str, reason: VideoEdlRejectionReason, issue: str | None = None) -> None:
    raise VideoEdlContractError(pointer, reason, issue)


def _digest(value: Any) -> str:
    return hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _cue_dict(value: CueWordRange) -> dict[str, Any]: return {f: getattr(value, f) for f in _CUE_FIELDS}
def _source_dict(value: SourceDescriptor) -> dict[str, Any]:
    d = {f: getattr(value, f) for f in _SOURCE_FIELDS}; d["playback_mode"] = value.playback_mode.value; d["fit_mode"] = value.fit_mode.value; return d
def _etype_dict(value: EmphasisTypeRef | None) -> Any:
    return None if value is None else {"domain_id": value.domain_id, "name": value.name, "version": value.version}
def _payload_dict(value: EdlRenderPayload) -> dict[str, Any]:
    d = {f: getattr(value, f) for f in _PAYLOAD_FIELDS}; d["kind"] = value.kind.value; d["source"] = None if value.source is None else _source_dict(value.source); d["emphasis_type_ref"] = _etype_dict(value.emphasis_type_ref); d["emphasis_intensity"] = None if value.emphasis_intensity is None else value.emphasis_intensity.value; return d
def _event_dict(value: EdlVideoEvent) -> dict[str, Any]:
    d = {f: getattr(value, f) for f in _EVENT_FIELDS}; d["track"] = value.track.value; d["payload"] = _payload_dict(value.payload); return d
def _track_dict(value: EdlTrack) -> dict[str, Any]: return {"track": value.track.value, "kind": value.kind.value, "priority": value.priority, "events": [_event_dict(x) for x in value.events]}
def _artifact_dict(value: VideoEdlArtifact) -> dict[str, Any]:
    d = {f: getattr(value, f) for f in _ROOT_FIELDS}; d["tracks"] = [_track_dict(x) for x in value.tracks]; return d


def _signature(value: VideoEdlArtifact) -> tuple[int, ...]:
    result = [id(value), id(value.tracks)]
    for t in value.tracks:
        result.extend((id(t), id(t.events)))
        for e in t.events: result.extend((id(e), id(e.payload), id(e.track)))
    return tuple(result)


def _register(value: VideoEdlArtifact, data: bytes) -> None:
    key = id(value)
    def gone(ref: weakref.ReferenceType[VideoEdlArtifact]) -> None:
        if _REGISTRY.get(key, (None,))[0] is ref: _REGISTRY.pop(key, None)
    ref = weakref.ref(value, gone); _REGISTRY[key] = (ref, bytes(data), _signature(value))


def _dep(value: Any, expected: type, serializer: Any, pointer: str) -> bytes:
    if type(value) is not expected: raise TypeError(f"{pointer[1:]} must be a genuine exact dependency")
    try: return bytes(serializer(value))
    except Exception: _reject(pointer, VideoEdlRejectionReason.DEPENDENCY_CONTENT_DRIFT)


def _valid_id(value: Any) -> bool: return type(value) is str and _ID.fullmatch(value) is not None
def _video_tracks() -> tuple[TimelineTrack, ...]: return tuple(list(TimelineTrack)[:7])
def _priority(track: TimelineTrack) -> int:
    """Registry priority is per media kind: V1/V7 and A1/A5 both start at 10."""
    index = list(TimelineTrack).index(track)
    return ((index if track in _video_tracks() else index - 7) + 1) * 10


def _check_rate(n: Any, d: Any) -> None:
    if type(n) is not int or type(d) is not int or not 1 <= n <= _MAX or not 1 <= d <= _MAX or math.gcd(n, d) != 1:
        _reject("/word_to_frame", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)


def _validate_source(source: Any, cue: CueWordRange) -> None:
    if type(source) is not SourceDescriptor or not _valid_id(source.source_ref): _reject("/intents", VideoEdlRejectionReason.CUE_RESOLUTION_INVALID)
    _check_rate(source.source_fps_numerator, source.source_fps_denominator)
    if (
        not all(
            type(getattr(source, field)) is int and 0 <= getattr(source, field) <= _MAX
            for field in ("source_in_frame", "source_out_exclusive_frame")
        )
        or not all(
            type(getattr(source, field)) is int and 0 <= getattr(source, field) <= 1_000_000
            for field in (
                "crop_left_millionths", "crop_top_millionths", "crop_right_millionths",
                "crop_bottom_millionths", "opacity_millionths",
            )
        )
        or source.source_in_frame >= source.source_out_exclusive_frame
        or not source.crop_left_millionths < source.crop_right_millionths
        or not source.crop_top_millionths < source.crop_bottom_millionths
        or source.opacity_millionths <= 0
        or source.bound_start_word_id != cue.start_word_id
        or source.bound_end_word_id != cue.end_word_id
    ):
        _reject("/intents", VideoEdlRejectionReason.CUE_RESOLUTION_INVALID)
    if type(source.playback_mode) is not SourcePlaybackMode or type(source.fit_mode) is not SourceFitMode: _reject("/intents", VideoEdlRejectionReason.UNSUPPORTED_VALUE)


def _source_playback_frame(
    source: SourceDescriptor, *, timeline_offset_frames: int,
    event_duration_frames: int, edl_fps_numerator: int, edl_fps_denominator: int,
) -> int:
    """Apply the declared sparse source-playback mapping without media access."""
    if (
        type(timeline_offset_frames) is not int or timeline_offset_frames < 0
        or type(event_duration_frames) is not int or event_duration_frames <= 0
        or type(edl_fps_numerator) is not int or type(edl_fps_denominator) is not int
        or edl_fps_numerator <= 0 or edl_fps_denominator <= 0
    ):
        raise ValueError("invalid source playback mapping inputs")
    span = source.source_out_exclusive_frame - source.source_in_frame
    if source.playback_mode is SourcePlaybackMode.FIT:
        return source.source_in_frame + (timeline_offset_frames * span // event_duration_frames)
    increment = (
        timeline_offset_frames * source.source_fps_numerator * edl_fps_denominator
        // (source.source_fps_denominator * edl_fps_numerator)
    )
    if source.playback_mode is SourcePlaybackMode.HOLD:
        return min(source.source_out_exclusive_frame - 1, source.source_in_frame + increment)
    if source.playback_mode is SourcePlaybackMode.LOOP:
        return source.source_in_frame + (increment % span)
    raise ValueError("unsupported source playback mode")


def _word_index(word_to_frame: WordToFrameArtifact) -> dict[str, Any]:
    rows = word_to_frame.word_frames
    result = {x.source_id: x for x in rows}
    if len(result) != len(rows): _reject("/word_to_frame", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    return result


def _span(words: dict[str, Any], cue: CueWordRange) -> tuple[int, int]:
    if type(cue) is not CueWordRange or not all(_valid_id(getattr(cue, x)) for x in _CUE_FIELDS): _reject("/intents", VideoEdlRejectionReason.CUE_RESOLUTION_INVALID)
    a, b = words.get(cue.start_word_id), words.get(cue.end_word_id)
    if a is None or b is None or a.ordinal > b.ordinal: _reject("/intents", VideoEdlRejectionReason.CUE_RESOLUTION_INVALID)
    return a.start_frame, b.end_exclusive_frame


def _valid_editorial_role(value: Any) -> bool:
    return (
        type(value) is str and bool(value) and len(value) <= 128
        and unicodedata.normalize("NFC", value) == value
        and not any(ord(character) < 0x20 or 0xD800 <= ord(character) <= 0xDFFF for character in value)
    )


def _event(track: TimelineTrack, ordinal: int, intent_id: str, role: str, start: int, end: int, start_word: str, end_word: str, payload: EdlRenderPayload) -> EdlVideoEvent:
    raw = {"schema_version": VIDEO_EDL_V1, "hash_scope_version": VIDEO_EDL_HASH_V1, "track": track.value, "ordinal": ordinal, "intent_id": intent_id, "editorial_role": role, "start_frame": start, "end_exclusive_frame": end, "start_word_id": start_word, "end_word_id": end_word, "payload": _payload_dict(payload)}
    h = _digest(raw)
    return EdlVideoEvent(VIDEO_EDL_V1, VIDEO_EDL_HASH_V1, "vevt_" + h[:32], h, track, ordinal, intent_id, role, start, end, start_word, end_word, payload)


def _compile(*, intents: tuple[VideoEditIntent, ...], sequence_id: str, sequence_start_word_id: str, sequence_end_word_id: str, caption_groups: CaptionGroupsArtifact, emphasis_events: EmphasisEventsArtifact, word_to_frame: WordToFrameArtifact, caption_preview: CaptionPreviewArtifact, v5_v6_collision_report: V5V6CollisionReport, fps_numerator: int, fps_denominator: int) -> VideoEdlArtifact:
    if type(intents) is not tuple: raise TypeError("intents must be exact tuple")
    for value, cls, fn, ptr in ((caption_groups, CaptionGroupsArtifact, serialize_caption_groups, "/caption_groups"), (emphasis_events, EmphasisEventsArtifact, serialize_emphasis_events, "/emphasis_events"), (word_to_frame, WordToFrameArtifact, serialize_word_to_frame, "/word_to_frame"), (caption_preview, CaptionPreviewArtifact, serialize_caption_preview, "/caption_preview"), (v5_v6_collision_report, V5V6CollisionReport, serialize_v5_v6_collision_report, "/v5_v6_collision_report")): _dep(value, cls, fn, ptr)
    _check_rate(fps_numerator, fps_denominator)
    if (word_to_frame.frame_rate.numerator, word_to_frame.frame_rate.denominator) != (fps_numerator, fps_denominator): _reject("/word_to_frame", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    lineage = (caption_groups.project_id, caption_groups.document_id, caption_groups.narration_revision_id, caption_groups.narration_revision_hash)
    if lineage != (emphasis_events.project_id, emphasis_events.document_id, emphasis_events.narration_revision_id, emphasis_events.narration_revision_hash) or lineage != (word_to_frame.project_id, word_to_frame.document_id, word_to_frame.narration_revision_id, word_to_frame.narration_revision_hash) or lineage != (caption_preview.project_id, caption_preview.document_id, caption_preview.narration_revision_id, caption_preview.narration_revision_hash): _reject("/word_to_frame", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    if (caption_preview.caption_groups_id, caption_preview.caption_groups_hash, caption_preview.emphasis_events_id, caption_preview.emphasis_events_hash, caption_preview.word_to_frame_id, caption_preview.word_to_frame_hash) != (caption_groups.caption_groups_id, caption_groups.caption_groups_hash, emphasis_events.emphasis_events_id, emphasis_events.emphasis_events_hash, word_to_frame.word_to_frame_id, word_to_frame.word_to_frame_hash): _reject("/caption_preview", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    if (v5_v6_collision_report.caption_preview_id, v5_v6_collision_report.caption_preview_hash) != (caption_preview.caption_preview_id, caption_preview.caption_preview_hash): _reject("/v5_v6_collision_report", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    if not _valid_id(sequence_id) or not _valid_id(sequence_start_word_id) or not _valid_id(sequence_end_word_id): _reject("/intents", VideoEdlRejectionReason.CUE_RESOLUTION_INVALID)
    words = _word_index(word_to_frame); start_global, content_end_global = _span(words, CueWordRange(lineage[0],lineage[1],lineage[2],sequence_start_word_id,sequence_end_word_id))
    rows: dict[TimelineTrack, list[tuple[int, int, str, str, str, str, EdlRenderPayload]]] = {track: [] for track in _video_tracks()}
    seen: set[str] = set()
    previous_caller_key: tuple[int, int, str] | None = None
    for index, intent in enumerate(intents):
        if type(intent) is not VideoEditIntent or type(intent.ordinal) is not int or intent.ordinal != index or not _valid_id(intent.intent_id) or intent.intent_id in seen or intent.intent_id.startswith(("emphasis:", "caption:")) or type(intent.track) is not TimelineTrack or intent.track not in {TimelineTrack.V1, TimelineTrack.V2, TimelineTrack.V3, TimelineTrack.V4, TimelineTrack.V7} or not _valid_editorial_role(intent.editorial_role) or type(intent.cue) is not CueWordRange: _reject("/intents", VideoEdlRejectionReason.CUE_RESOLUTION_INVALID)
        if (intent.cue.project_id, intent.cue.document_id, intent.cue.narration_revision_id) != lineage[:3]: _reject("/intents", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
        _validate_source(intent.source, intent.cue); gs, ge = _span(words, intent.cue)
        if gs < start_global or ge > content_end_global: _reject("/intents", VideoEdlRejectionReason.CUE_RESOLUTION_INVALID)
        caller_key = (gs, ge, intent.intent_id)
        if previous_caller_key is not None and caller_key <= previous_caller_key:
            _reject(f"/intents/{index}", VideoEdlRejectionReason.CUE_RESOLUTION_INVALID)
        previous_caller_key = caller_key
        p = EdlRenderPayload(EdlPayloadKind.CALLER_SOURCE, intent.source, None, None, intent.intent_id, None, intent.ordinal, None, None, None, None, None, None, None, None, None)
        rows[intent.track].append((gs-start_global, ge-start_global, intent.intent_id, intent.editorial_role, intent.cue.start_word_id, intent.cue.end_word_id, p)); seen.add(intent.intent_id)
    scenes = caption_preview.scenes
    if len(scenes) != len(emphasis_events.emphasis_events) + len(caption_groups.caption_groups): _reject("/caption_preview", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    for i, event in enumerate(emphasis_events.emphasis_events):
        scene = scenes[i]; gs, ge = _span(words, CueWordRange(lineage[0],lineage[1],lineage[2],event.start_word_id,event.end_word_id))
        if scene.track is not PreviewTrack.V5 or scene.ordinal != i or scene.source_id != event.emphasis_event_id or (scene.start_frame,scene.end_exclusive_frame)!=(gs,ge): _reject("/caption_preview", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
        if gs < start_global or ge > content_end_global: _reject("/caption_preview", VideoEdlRejectionReason.CUE_RESOLUTION_INVALID)
        p=EdlRenderPayload(EdlPayloadKind.KINETIC_EMPHASIS,None,emphasis_events.emphasis_events_id,emphasis_events.emphasis_events_hash,event.emphasis_event_id,event.emphasis_event_hash,event.ordinal,scene.preview_scene_id,scene.preview_scene_hash,scene.rect.left,scene.rect.top,scene.rect.right,scene.rect.bottom,scene.semantic_proxy_label,event.emphasis_type_ref,event.intensity)
        rows[TimelineTrack.V5].append((gs-start_global,ge-start_global,"emphasis:"+event.emphasis_event_id,"kinetic_emphasis",event.start_word_id,event.end_word_id,p))
    offset=len(emphasis_events.emphasis_events)
    for j, group in enumerate(caption_groups.caption_groups):
        scene=scenes[offset+j]; gs,ge=_span(words,CueWordRange(lineage[0],lineage[1],lineage[2],group.start_word_id,group.end_word_id))
        if scene.track is not PreviewTrack.V6 or scene.ordinal != offset+j or scene.source_id != group.caption_group_id or (scene.start_frame,scene.end_exclusive_frame)!=(gs,ge) or scene.semantic_proxy_label != group.display_text: _reject("/caption_preview", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
        if gs < start_global or ge > content_end_global: _reject("/caption_preview", VideoEdlRejectionReason.CUE_RESOLUTION_INVALID)
        p=EdlRenderPayload(EdlPayloadKind.CAPTION,None,caption_groups.caption_groups_id,caption_groups.caption_groups_hash,group.caption_group_id,group.caption_group_hash,group.ordinal,scene.preview_scene_id,scene.preview_scene_hash,scene.rect.left,scene.rect.top,scene.rect.right,scene.rect.bottom,group.display_text,None,None)
        rows[TimelineTrack.V6].append((gs-start_global,ge-start_global,"caption:"+group.caption_group_id,"readable_subtitle",group.start_word_id,group.end_word_id,p))
    tracks=[]
    for track in TimelineTrack:
        vals=rows.get(track,[])
        if any(
            vals[k - 1][0] > v[0] or vals[k - 1][1] > v[0]
            for k, v in enumerate(vals) if k
        ):
            _reject("/tracks", VideoEdlRejectionReason.TRACK_COLLISION)
        events=tuple(
            _event(track, i, v[2], v[3], v[0], v[1], v[4], v[5], v[6])
            for i, v in enumerate(vals)
        )
        tracks.append(EdlTrack(track, EdlTrackKind.VIDEO if track in _video_tracks() else EdlTrackKind.AUDIO, _priority(track), events))
    # The report is a Phase 3A admission gate, but only after all requested
    # sequence/cue and same-track scheduling checks have had their row-6 turn.
    # This preserves the loader's specified precedence for multi-fault input.
    if v5_v6_collision_report.finding_count != 0 or v5_v6_collision_report.blocker_count != 0:
        _reject("/v5_v6_collision_report", VideoEdlRejectionReason.V5_V6_COLLISION_BLOCKED)
    duration=content_end_global-start_global
    base=VideoEdlArtifact(VIDEO_EDL_V1,VIDEO_EDL_HASH_V1,"","",*lineage,sequence_id,sequence_start_word_id,sequence_end_word_id,start_global,content_end_global,0,duration,word_to_frame.word_to_frame_id,word_to_frame.word_to_frame_hash,caption_preview.caption_preview_id,caption_preview.caption_preview_hash,v5_v6_collision_report.v5_v6_collision_report_id,v5_v6_collision_report.v5_v6_collision_report_hash,VIDEO_CLOCK_V1,fps_numerator,fps_denominator,duration,tuple(tracks))
    projection=_artifact_dict(base); projection.pop("video_edl_id"); projection.pop("video_edl_hash"); h=_digest(projection)
    return VideoEdlArtifact(base.schema_version,base.hash_scope_version,"vedl_"+h[:32],h,*tuple(getattr(base,f) for f in _ROOT_FIELDS[4:]))


def compile_video_edl(
    *, intents: tuple[VideoEditIntent, ...], sequence_id: str,
    sequence_start_word_id: str, sequence_end_word_id: str,
    caption_groups: CaptionGroupsArtifact, emphasis_events: EmphasisEventsArtifact,
    word_to_frame: WordToFrameArtifact, caption_preview: CaptionPreviewArtifact,
    v5_v6_collision_report: V5V6CollisionReport, fps_numerator: int,
    fps_denominator: int,
) -> VideoEdlArtifact:
    value = _compile(
        intents=intents, sequence_id=sequence_id,
        sequence_start_word_id=sequence_start_word_id,
        sequence_end_word_id=sequence_end_word_id, caption_groups=caption_groups,
        emphasis_events=emphasis_events, word_to_frame=word_to_frame,
        caption_preview=caption_preview,
        v5_v6_collision_report=v5_v6_collision_report,
        fps_numerator=fps_numerator, fps_denominator=fps_denominator,
    )
    _register(value, encode_canonical_json_bytes(_artifact_dict(value)))
    return value


def load_video_edl(
    source: bytes, *, intents: tuple[VideoEditIntent, ...], sequence_id: str,
    sequence_start_word_id: str, sequence_end_word_id: str,
    caption_groups: CaptionGroupsArtifact, emphasis_events: EmphasisEventsArtifact,
    word_to_frame: WordToFrameArtifact, caption_preview: CaptionPreviewArtifact,
    v5_v6_collision_report: V5V6CollisionReport, fps_numerator: int,
    fps_denominator: int,
) -> VideoEdlArtifact:
    if type(source) is not bytes: raise TypeError("source must be bytes")
    class Pairs(list): pass
    try:
        if source.startswith(b"\xef\xbb\xbf"): raise ValueError
        parsed=json.loads(source.decode("utf-8"), object_pairs_hook=Pairs, parse_float=lambda _: (_ for _ in ()).throw(ValueError()), parse_int=lambda text: int(text) if text == str(int(text)) else (_ for _ in ()).throw(ValueError()), parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except Exception: _reject("/",VideoEdlRejectionReason.NON_CANONICAL_SERIALIZATION)
    def plain(item: Any) -> Any:
        if type(item) is Pairs:
            if len(item) != len({key for key, _ in item}): _reject("/", VideoEdlRejectionReason.NON_CANONICAL_SERIALIZATION)
            return {key: plain(nested) for key, nested in item}
        if type(item) is list: return [plain(nested) for nested in item]
        return item
    value = plain(parsed)
    try: canonical=encode_canonical_json_bytes(value)
    except Exception: _reject("/",VideoEdlRejectionReason.NON_CANONICAL_SERIALIZATION)
    if source != canonical: _reject("/",VideoEdlRejectionReason.NON_CANONICAL_SERIALIZATION)
    if type(value) is not dict or set(value) != set(_ROOT_FIELDS): _reject("/",VideoEdlRejectionReason.STRUCTURE_INVALID)
    if (any(type(value[x]) is not str for x in ("schema_version", "hash_scope_version", "video_edl_id", "video_edl_hash", "project_id", "document_id", "narration_revision_id", "narration_revision_hash", "sequence_id", "sequence_start_word_id", "sequence_end_word_id", "word_to_frame_id", "word_to_frame_hash", "caption_preview_id", "caption_preview_hash", "v5_v6_collision_report_id", "v5_v6_collision_report_hash", "clock_version")) or any(type(value[x]) is not int for x in ("sequence_start_frame", "sequence_content_end_exclusive_frame", "trailing_silence_frames", "sequence_end_exclusive_frame", "fps_numerator", "fps_denominator", "duration_frames")) or type(value["tracks"]) is not list): _reject("/",VideoEdlRejectionReason.STRUCTURE_INVALID)
    if len(value["tracks"]) != 12:
        _reject("/tracks", VideoEdlRejectionReason.STRUCTURE_INVALID)
    for index, track in enumerate(value["tracks"]):
        pointer=f"/tracks/{index}"
        if type(track) is not dict or set(track) != set(_TRACK_FIELDS) or type(track.get("track")) is not str or type(track.get("kind")) is not str or type(track.get("priority")) is not int or type(track.get("events")) is not list: _reject(pointer,VideoEdlRejectionReason.STRUCTURE_INVALID)
        if track["track"] not in {x.value for x in TimelineTrack} or track["kind"] not in {x.value for x in EdlTrackKind}: _reject(pointer,VideoEdlRejectionReason.UNSUPPORTED_VALUE)
        for event_index, event in enumerate(track["events"]):
            ep=f"{pointer}/events/{event_index}"
            if type(event) is not dict or set(event) != set(_EVENT_FIELDS): _reject(ep,VideoEdlRejectionReason.STRUCTURE_INVALID)
            if (any(type(event.get(name)) is not str for name in ("schema_version", "hash_scope_version", "event_id", "event_hash", "track", "intent_id", "editorial_role", "start_word_id", "end_word_id"))
                    or any(type(event.get(name)) is not int for name in ("ordinal", "start_frame", "end_exclusive_frame"))
                    or type(event.get("payload")) is not dict): _reject(ep,VideoEdlRejectionReason.STRUCTURE_INVALID)
            if event["schema_version"] != VIDEO_EDL_V1 or event["hash_scope_version"] != VIDEO_EDL_HASH_V1:
                _reject(ep, VideoEdlRejectionReason.UNSUPPORTED_VALUE)
            if event["track"] not in {x.value for x in TimelineTrack}: _reject(ep,VideoEdlRejectionReason.UNSUPPORTED_VALUE)
            payload = event["payload"]
            if set(payload) != set(_PAYLOAD_FIELDS) or type(payload.get("kind")) is not str: _reject(ep,VideoEdlRejectionReason.STRUCTURE_INVALID)
            if payload["kind"] not in {x.value for x in EdlPayloadKind}: _reject(ep,VideoEdlRejectionReason.UNSUPPORTED_VALUE)
            if (any(payload.get(name) is not None and type(payload.get(name)) is not str for name in ("source_artifact_id", "source_artifact_hash", "source_record_id", "source_record_hash", "preview_scene_id", "preview_scene_hash", "text"))
                    or any(payload.get(name) is not None and type(payload.get(name)) is not int for name in ("source_record_ordinal", "preview_left_millionths", "preview_top_millionths", "preview_right_millionths", "preview_bottom_millionths"))): _reject(ep,VideoEdlRejectionReason.STRUCTURE_INVALID)
            source_value = payload["source"]
            if source_value is not None:
                if type(source_value) is not dict or set(source_value) != set(_SOURCE_FIELDS): _reject(ep, VideoEdlRejectionReason.STRUCTURE_INVALID)
                if (type(source_value["source_ref"]) is not str
                        or any(type(source_value[name]) is not int for name in ("source_fps_numerator", "source_fps_denominator", "source_in_frame", "source_out_exclusive_frame", "crop_left_millionths", "crop_top_millionths", "crop_right_millionths", "crop_bottom_millionths", "opacity_millionths"))
                        or any(type(source_value[name]) is not str for name in ("playback_mode", "fit_mode", "bound_start_word_id", "bound_end_word_id"))): _reject(ep, VideoEdlRejectionReason.STRUCTURE_INVALID)
                if source_value["playback_mode"] not in {item.value for item in SourcePlaybackMode} or source_value["fit_mode"] not in {item.value for item in SourceFitMode}: _reject(ep, VideoEdlRejectionReason.UNSUPPORTED_VALUE)
            ref = payload["emphasis_type_ref"]
            if ref is not None and (type(ref) is not dict or set(ref) != {"domain_id", "name", "version"} or any(type(ref[name]) is not str for name in ("domain_id", "name", "version"))): _reject(ep, VideoEdlRejectionReason.STRUCTURE_INVALID)
            intensity = payload["emphasis_intensity"]
            if intensity is not None and (type(intensity) is not str or intensity not in {item.value for item in EmphasisIntensity}): _reject(ep, VideoEdlRejectionReason.UNSUPPORTED_VALUE)
    if value.get("schema_version") != VIDEO_EDL_V1 or value.get("hash_scope_version") != VIDEO_EDL_HASH_V1 or value.get("clock_version") != VIDEO_CLOCK_V1: _reject("/",VideoEdlRejectionReason.UNSUPPORTED_VALUE)
    # Row 5 must bind the serialized dependency references to the dependencies
    # supplied by the caller before compilation.  In particular, _compile can
    # reject a supplied collision report with findings; that row-7 admission
    # result must not mask the earlier fact that a different preview/report was
    # supplied for this serialized EDL.
    if type(caption_preview) is not CaptionPreviewArtifact:
        _reject("/caption_preview", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    if type(v5_v6_collision_report) is not V5V6CollisionReport:
        _reject("/v5_v6_collision_report", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    if (value["caption_preview_id"], value["caption_preview_hash"]) != (
        caption_preview.caption_preview_id, caption_preview.caption_preview_hash,
    ):
        _reject("/caption_preview", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    if (value["v5_v6_collision_report_id"], value["v5_v6_collision_report_hash"]) != (
        v5_v6_collision_report.v5_v6_collision_report_id,
        v5_v6_collision_report.v5_v6_collision_report_hash,
    ):
        _reject("/v5_v6_collision_report", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    if (
        v5_v6_collision_report.caption_preview_id,
        v5_v6_collision_report.caption_preview_hash,
    ) != (caption_preview.caption_preview_id, caption_preview.caption_preview_hash):
        _reject("/v5_v6_collision_report", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    expected=_compile(
        intents=intents, sequence_id=sequence_id, sequence_start_word_id=sequence_start_word_id,
        sequence_end_word_id=sequence_end_word_id, caption_groups=caption_groups,
        emphasis_events=emphasis_events, word_to_frame=word_to_frame, caption_preview=caption_preview,
        v5_v6_collision_report=v5_v6_collision_report, fps_numerator=fps_numerator,
        fps_denominator=fps_denominator,
    )
    wanted = _artifact_dict(expected)
    # Row 5: root lineage and the requested video rate are bindings to the
    # supplied timing dependency, not untrusted EDL metadata.  Check these
    # before any event/cue comparison so they cannot be masked by a later
    # identity mismatch.
    if (
        tuple(value[name] for name in (
            "project_id", "document_id", "narration_revision_id",
            "narration_revision_hash",
        ))
        != tuple(wanted[name] for name in (
            "project_id", "document_id", "narration_revision_id",
            "narration_revision_hash",
        ))
        or (value["fps_numerator"], value["fps_denominator"])
        != (wanted["fps_numerator"], wanted["fps_denominator"])
    ):
        _reject("/word_to_frame", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    if value["word_to_frame_id"] != wanted["word_to_frame_id"] or value["word_to_frame_hash"] != wanted["word_to_frame_hash"]: _reject("/word_to_frame", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    if value["caption_preview_id"] != wanted["caption_preview_id"] or value["caption_preview_hash"] != wanted["caption_preview_hash"]: _reject("/caption_preview", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    if value["v5_v6_collision_report_id"] != wanted["v5_v6_collision_report_id"] or value["v5_v6_collision_report_hash"] != wanted["v5_v6_collision_report_hash"]: _reject("/v5_v6_collision_report", VideoEdlRejectionReason.DEPENDENCY_BINDING_INVALID)
    # Row 6 starts with the sequence request and its local frame bounds.  The
    # report's nonzero-finding gate is intentionally reached only after this
    # section through _compile above.
    if any(
        value[name] != wanted[name]
        for name in (
            "sequence_id", "sequence_start_word_id", "sequence_end_word_id",
            "sequence_start_frame", "sequence_content_end_exclusive_frame",
            "trailing_silence_frames", "sequence_end_exclusive_frame",
            "duration_frames",
        )
    ):
        _reject("/intents", VideoEdlRejectionReason.CUE_RESOLUTION_INVALID)
    for track_index, (actual_track, expected_track) in enumerate(zip(value["tracks"], wanted["tracks"], strict=True)):
        track_pointer = f"/tracks/{track_index}"
        if actual_track["track"] != expected_track["track"] or actual_track["kind"] != expected_track["kind"] or actual_track["priority"] != expected_track["priority"] or len(actual_track["events"]) != len(expected_track["events"]): _reject(track_pointer, VideoEdlRejectionReason.CUE_RESOLUTION_INVALID)
        previous_end = 0
        for event_index, (actual_event, expected_event) in enumerate(zip(actual_track["events"], expected_track["events"], strict=True)):
            event_pointer = f"{track_pointer}/events/{event_index}"
            if actual_event["start_frame"] < previous_end: _reject(event_pointer, VideoEdlRejectionReason.TRACK_COLLISION)
            previous_end = actual_event["end_exclusive_frame"]
            actual_projection = {key: item for key, item in actual_event.items() if key not in {"event_id", "event_hash"}}
            expected_projection = {key: item for key, item in expected_event.items() if key not in {"event_id", "event_hash"}}
            if actual_projection != expected_projection: _reject(event_pointer, VideoEdlRejectionReason.CUE_RESOLUTION_INVALID)
            if actual_event["event_id"] != expected_event["event_id"] or actual_event["event_hash"] != expected_event["event_hash"]: _reject(event_pointer, VideoEdlRejectionReason.IDENTITY_MISMATCH)
    root_projection = {key: item for key, item in value.items() if key not in {"video_edl_id", "video_edl_hash"}}
    expected_root_projection = {key: item for key, item in wanted.items() if key not in {"video_edl_id", "video_edl_hash"}}
    if root_projection != expected_root_projection: _reject("/", VideoEdlRejectionReason.CUE_RESOLUTION_INVALID)
    if value["video_edl_id"] != wanted["video_edl_id"] or value["video_edl_hash"] != wanted["video_edl_hash"]: _reject("/",VideoEdlRejectionReason.IDENTITY_MISMATCH)
    _register(expected,source); return expected


def serialize_video_edl(artifact: VideoEdlArtifact) -> bytes:
    if type(artifact) is not VideoEdlArtifact: raise TypeError("artifact must be exact VideoEdlArtifact")
    entry=_REGISTRY.get(id(artifact))
    if entry is None or entry[0]() is not artifact: _reject("/",VideoEdlRejectionReason.NOT_MATERIALIZED)
    try: current=encode_canonical_json_bytes(_artifact_dict(artifact))
    except Exception: _reject("/",VideoEdlRejectionReason.CONTENT_DRIFT)
    if entry[2] != _signature(artifact) or current != entry[1]: _reject("/",VideoEdlRejectionReason.CONTENT_DRIFT)
    return bytes(entry[1])
