"""Canonical Phase 3A readable provenance index for a materialized video EDL."""
from __future__ import annotations

import hashlib
import json
import weakref
from dataclasses import dataclass
from typing import Any

from ._canonical_json import encode_canonical_json_bytes
from .edl import VIDEO_CLOCK_V1, TimelineTrack, VideoEdlArtifact, VideoEdlContractError, serialize_video_edl
from enum import Enum

TIMELINE_DEBUG_V1 = "TIMELINE-DEBUG-V1"
TIMELINE_DEBUG_HASH_V1 = "TIMELINE-DEBUG-HASH-V1"
__all__ = [
    "TIMELINE_DEBUG_V1", "TIMELINE_DEBUG_HASH_V1", "TimelineDebugEntry",
    "TimelineDebugArtifact", "TimelineDebugRejectionReason",
    "TimelineDebugContractError", "compile_timeline_debug", "load_timeline_debug",
    "serialize_timeline_debug",
]


class TimelineDebugRejectionReason(str, Enum):
    STRUCTURE_INVALID="STRUCTURE_INVALID"; UNSUPPORTED_VALUE="UNSUPPORTED_VALUE"
    DEPENDENCY_CONTENT_DRIFT="DEPENDENCY_CONTENT_DRIFT"; DEPENDENCY_BINDING_INVALID="DEPENDENCY_BINDING_INVALID"
    ENTRY_INVALID="ENTRY_INVALID"; NON_CANONICAL_SERIALIZATION="NON_CANONICAL_SERIALIZATION"
    IDENTITY_MISMATCH="IDENTITY_MISMATCH"; CONTENT_DRIFT="CONTENT_DRIFT"; NOT_MATERIALIZED="NOT_MATERIALIZED"


@dataclass(frozen=True)
class TimelineDebugEntry:
    ordinal: int
    event_id: str
    track: TimelineTrack
    priority: int
    start_frame: int
    end_exclusive_frame: int
    start_word_id: str
    end_word_id: str
    intent_id: str


@dataclass(frozen=True)
class TimelineDebugArtifact:
    schema_version: str
    hash_scope_version: str
    timeline_debug_id: str
    timeline_debug_hash: str
    video_edl_id: str
    video_edl_hash: str
    clock_version: str
    fps_numerator: int
    fps_denominator: int
    duration_frames: int
    entries: tuple[TimelineDebugEntry, ...]


_ROOT = tuple(TimelineDebugArtifact.__dataclass_fields__)
_ENTRY = tuple(TimelineDebugEntry.__dataclass_fields__)
_REGISTRY: dict[int, tuple[weakref.ReferenceType[TimelineDebugArtifact], bytes, tuple[int, ...]]] = {}


class TimelineDebugContractError(ValueError):
    def __init__(self, pointer: str, reason: TimelineDebugRejectionReason, issue_code: str | None = None) -> None:
        if type(pointer) is not str or type(reason) is not TimelineDebugRejectionReason: raise TypeError("invalid timeline debug error construction")
        super().__init__(f"Timeline debug rejected: {reason.value}")
        self.pointer, self.reason, self.issue_code = pointer, reason, issue_code


def _reject(pointer: str, reason: TimelineDebugRejectionReason, issue: str | None = None) -> None: raise TimelineDebugContractError(pointer, reason, issue)
def _digest(value: Any) -> str: return hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()
def _entry_dict(value: TimelineDebugEntry) -> dict[str, Any]: return {**{x:getattr(value,x) for x in _ENTRY if x != "track"}, "track":value.track.value}
def _dict(value: TimelineDebugArtifact) -> dict[str, Any]:
    d={x:getattr(value,x) for x in _ROOT if x != "entries"}; d["entries"]=[_entry_dict(x) for x in value.entries]; return d
def _signature(value: TimelineDebugArtifact) -> tuple[int,...]: return (id(value),id(value.entries),*(id(x) for x in value.entries))
def _register(value: TimelineDebugArtifact, data: bytes) -> None:
    key=id(value)
    def gone(ref: weakref.ReferenceType[TimelineDebugArtifact]) -> None:
        if _REGISTRY.get(key,(None,))[0] is ref: _REGISTRY.pop(key,None)
    ref=weakref.ref(value,gone); _REGISTRY[key]=(ref,bytes(data),_signature(value))


def _derive(video_edl: VideoEdlArtifact) -> TimelineDebugArtifact:
    if type(video_edl) is not VideoEdlArtifact: raise TypeError("video_edl must be a genuine exact dependency")
    try: serialize_video_edl(video_edl)
    except VideoEdlContractError as error:
        if error.reason.value == "NOT_MATERIALIZED": raise TypeError("video_edl must be a genuine exact dependency") from None
        _reject("/video_edl",TimelineDebugRejectionReason.DEPENDENCY_CONTENT_DRIFT)
    # Each compiler-produced track is already a chronological, non-overlapping
    # stream.  The registry has a fixed 12 tracks, so scanning the current head
    # of every stream is a constant-width linear merge, never an O(O log O)
    # sort of an untrusted event list.
    cursors = [0] * len(video_edl.tracks)
    ordered: list[tuple[Any, Any]] = []
    while True:
        candidate: tuple[tuple[int, int, int, str], int] | None = None
        for index, track in enumerate(video_edl.tracks):
            cursor = cursors[index]
            if cursor >= len(track.events):
                continue
            event = track.events[cursor]
            key = (event.start_frame, event.end_exclusive_frame, track.priority, event.event_id)
            if candidate is None or key < candidate[0]:
                candidate = (key, index)
        if candidate is None:
            break
        track = video_edl.tracks[candidate[1]]
        event = track.events[cursors[candidate[1]]]
        ordered.append((event, track))
        cursors[candidate[1]] += 1
    entries=tuple(TimelineDebugEntry(i,event.event_id,event.track,track.priority,event.start_frame,event.end_exclusive_frame,event.start_word_id,event.end_word_id,event.intent_id) for i,(event,track) in enumerate(ordered))
    body={"schema_version":TIMELINE_DEBUG_V1,"hash_scope_version":TIMELINE_DEBUG_HASH_V1,"video_edl_id":video_edl.video_edl_id,"video_edl_hash":video_edl.video_edl_hash,"clock_version":video_edl.clock_version,"fps_numerator":video_edl.fps_numerator,"fps_denominator":video_edl.fps_denominator,"duration_frames":video_edl.duration_frames,"entries":[_entry_dict(x) for x in entries]}
    h=_digest(body)
    return TimelineDebugArtifact(TIMELINE_DEBUG_V1,TIMELINE_DEBUG_HASH_V1,"tdbg_"+h[:32],h,video_edl.video_edl_id,video_edl.video_edl_hash,video_edl.clock_version,video_edl.fps_numerator,video_edl.fps_denominator,video_edl.duration_frames,entries)


def compile_timeline_debug(*, video_edl: VideoEdlArtifact) -> TimelineDebugArtifact:
    value=_derive(video_edl); _register(value,encode_canonical_json_bytes(_dict(value))); return value


def load_timeline_debug(source: bytes, *, video_edl: VideoEdlArtifact) -> TimelineDebugArtifact:
    if type(source) is not bytes: raise TypeError("source must be bytes")
    class Pairs(list): pass
    try:
        if source.startswith(b"\xef\xbb\xbf"): raise ValueError
        parsed=json.loads(source.decode("utf-8"), object_pairs_hook=Pairs, parse_float=lambda _:(_ for _ in ()).throw(ValueError()), parse_int=lambda text: int(text) if text == str(int(text)) else (_ for _ in ()).throw(ValueError()), parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
    except Exception: _reject("/",TimelineDebugRejectionReason.NON_CANONICAL_SERIALIZATION)
    def plain(item: Any) -> Any:
        if type(item) is Pairs:
            if len(item) != len({key for key, _ in item}): _reject("/", TimelineDebugRejectionReason.NON_CANONICAL_SERIALIZATION)
            return {key: plain(nested) for key, nested in item}
        if type(item) is list: return [plain(nested) for nested in item]
        return item
    value = plain(parsed)
    try:
        if source != encode_canonical_json_bytes(value): raise ValueError
    except Exception: _reject("/",TimelineDebugRejectionReason.NON_CANONICAL_SERIALIZATION)
    if type(value) is not dict or set(value)!=set(_ROOT) or type(value.get("entries")) is not list: _reject("/",TimelineDebugRejectionReason.STRUCTURE_INVALID)
    if (any(type(value.get(name)) is not str for name in ("schema_version", "hash_scope_version", "timeline_debug_id", "timeline_debug_hash", "video_edl_id", "video_edl_hash", "clock_version"))
            or any(type(value.get(name)) is not int for name in ("fps_numerator", "fps_denominator", "duration_frames"))): _reject("/",TimelineDebugRejectionReason.STRUCTURE_INVALID)
    for index, entry in enumerate(value["entries"]):
        pointer = f"/entries/{index}"
        if type(entry) is not dict or set(entry) != set(_ENTRY): _reject(pointer, TimelineDebugRejectionReason.STRUCTURE_INVALID)
        if (any(type(entry.get(name)) is not str for name in ("event_id", "track", "start_word_id", "end_word_id", "intent_id"))
                or any(type(entry.get(name)) is not int for name in ("ordinal", "priority", "start_frame", "end_exclusive_frame"))): _reject(pointer, TimelineDebugRejectionReason.STRUCTURE_INVALID)
        if entry["track"] not in {track.value for track in TimelineTrack}: _reject(pointer, TimelineDebugRejectionReason.UNSUPPORTED_VALUE)
    if value.get("schema_version")!=TIMELINE_DEBUG_V1 or value.get("hash_scope_version")!=TIMELINE_DEBUG_HASH_V1 or value.get("clock_version") != VIDEO_CLOCK_V1: _reject("/",TimelineDebugRejectionReason.UNSUPPORTED_VALUE)
    expected=_derive(video_edl); wanted=_dict(expected)
    if value.get("video_edl_id")!=wanted["video_edl_id"] or value.get("video_edl_hash")!=wanted["video_edl_hash"]: _reject("/video_edl",TimelineDebugRejectionReason.DEPENDENCY_BINDING_INVALID)
    if value["clock_version"] != wanted["clock_version"] or value["fps_numerator"] != wanted["fps_numerator"] or value["fps_denominator"] != wanted["fps_denominator"] or value["duration_frames"] != wanted["duration_frames"] or len(value["entries"]) != len(wanted["entries"]): _reject("/entries",TimelineDebugRejectionReason.ENTRY_INVALID)
    for index, (actual, expected_entry) in enumerate(zip(value["entries"], wanted["entries"], strict=True)):
        if actual != expected_entry: _reject(f"/entries/{index}", TimelineDebugRejectionReason.ENTRY_INVALID)
    root_projection = {key: item for key, item in value.items() if key not in {"timeline_debug_id", "timeline_debug_hash"}}
    expected_root_projection = {key: item for key, item in wanted.items() if key not in {"timeline_debug_id", "timeline_debug_hash"}}
    if root_projection != expected_root_projection: _reject("/entries", TimelineDebugRejectionReason.ENTRY_INVALID)
    if value["timeline_debug_id"] != wanted["timeline_debug_id"] or value["timeline_debug_hash"] != wanted["timeline_debug_hash"]: _reject("/",TimelineDebugRejectionReason.IDENTITY_MISMATCH)
    _register(expected,source); return expected


def serialize_timeline_debug(artifact: TimelineDebugArtifact) -> bytes:
    if type(artifact) is not TimelineDebugArtifact: raise TypeError("artifact must be exact TimelineDebugArtifact")
    entry=_REGISTRY.get(id(artifact))
    if entry is None or entry[0]() is not artifact: _reject("/",TimelineDebugRejectionReason.NOT_MATERIALIZED)
    try: current=encode_canonical_json_bytes(_dict(artifact))
    except Exception: _reject("/",TimelineDebugRejectionReason.CONTENT_DRIFT)
    if _signature(artifact)!=entry[2] or current!=entry[1]: _reject("/",TimelineDebugRejectionReason.CONTENT_DRIFT)
    return bytes(entry[1])
