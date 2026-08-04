"""Deterministic sparse Phase 2 caption-preview contract."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import weakref
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ._canonical_json import encode_canonical_json_bytes
from .caption_groups import CaptionGroupsArtifact, serialize_caption_groups
from .emphasis_events import EmphasisEventsArtifact, EmphasisIntensity, serialize_emphasis_events
from .temporal import STABLE_ISSUE_CODE_SET
from .word_to_frame import WordToFrameArtifact, TemporalFrameSpanKind, serialize_word_to_frame


CAPTION_PREVIEW_V1 = "CAPTION-PREVIEW-V1"
CAPTION_PREVIEW_HASH_V1 = "CAPTION-PREVIEW-HASH-V1"
CAPTION_PREVIEW_POLICY_V1 = "CAPTION-PREVIEW-POLICY-V1"
_CANVAS = 1_000_000
_HEX = re.compile(r"^[0-9a-f]{64}$")
_PTR = re.compile(r"^/scenes/(?:0|[1-9][0-9]*)$")
_ROOT_FIELDS = (
    "schema_version", "hash_scope_version", "caption_preview_id", "caption_preview_hash",
    "project_id", "document_id", "narration_revision_id", "narration_revision_hash",
    "caption_groups_id", "caption_groups_hash", "emphasis_events_id", "emphasis_events_hash",
    "word_to_frame_id", "word_to_frame_hash", "layout_policy", "layout_policy_snapshot_hash",
    "canvas_units", "safe_rect", "scenes",
)
_RECT_FIELDS = ("left", "top", "right", "bottom")
_POLICY_FIELDS = ("policy_version", "safe_rect", "v5_rect", "v6_rect")
_SCENE_FIELDS = (
    "schema_version", "hash_scope_version", "preview_scene_id", "preview_scene_hash", "track",
    "ordinal", "source_id", "start_frame", "end_exclusive_frame", "rect", "semantic_proxy_label",
)
_MATERIALIZED: dict[int, tuple[weakref.ReferenceType["CaptionPreviewArtifact"], bytes, tuple[int, ...]]] = {}

__all__ = [
    "CAPTION_PREVIEW_V1", "CAPTION_PREVIEW_HASH_V1", "CAPTION_PREVIEW_POLICY_V1",
    "PreviewTrack", "PreviewRect", "CaptionPreviewLayoutPolicy", "PreviewScene",
    "CaptionPreviewArtifact", "CaptionPreviewRejectionReason", "CaptionPreviewContractError",
    "compile_caption_preview", "load_caption_preview", "serialize_caption_preview",
    "render_caption_preview_diagnostic_svg",
]


class _Pairs(list):
    pass


class PreviewTrack(str, Enum):
    V5 = "V5"
    V6 = "V6"


class CaptionPreviewRejectionReason(str, Enum):
    STRUCTURE_INVALID = "STRUCTURE_INVALID"
    UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
    DEPENDENCY_CONTENT_DRIFT = "DEPENDENCY_CONTENT_DRIFT"
    DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
    FRAME_BINDING_INVALID = "FRAME_BINDING_INVALID"
    GEOMETRY_INVALID = "GEOMETRY_INVALID"
    NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    CONTENT_DRIFT = "CONTENT_DRIFT"
    NOT_MATERIALIZED = "NOT_MATERIALIZED"


@dataclass(frozen=True)
class PreviewRect:
    left: int
    top: int
    right: int
    bottom: int


@dataclass(frozen=True)
class CaptionPreviewLayoutPolicy:
    policy_version: str
    safe_rect: PreviewRect
    v5_rect: PreviewRect
    v6_rect: PreviewRect


@dataclass(frozen=True)
class PreviewScene:
    schema_version: str
    hash_scope_version: str
    preview_scene_id: str
    preview_scene_hash: str
    track: PreviewTrack
    ordinal: int
    source_id: str
    start_frame: int
    end_exclusive_frame: int
    rect: PreviewRect
    semantic_proxy_label: str


@dataclass(frozen=True)
class CaptionPreviewArtifact:
    schema_version: str
    hash_scope_version: str
    caption_preview_id: str
    caption_preview_hash: str
    project_id: str
    document_id: str
    narration_revision_id: str
    narration_revision_hash: str
    caption_groups_id: str
    caption_groups_hash: str
    emphasis_events_id: str
    emphasis_events_hash: str
    word_to_frame_id: str
    word_to_frame_hash: str
    layout_policy: CaptionPreviewLayoutPolicy
    layout_policy_snapshot_hash: str
    canvas_units: int
    safe_rect: PreviewRect
    scenes: tuple[PreviewScene, ...]


class CaptionPreviewContractError(ValueError):
    def __init__(self, pointer: str, reason: CaptionPreviewRejectionReason, issue_code: str | None = None) -> None:
        if type(pointer) is not str or (pointer not in {"/", "/caption_groups", "/emphasis_events", "/word_to_frame", "/scenes", "/safe_rect", "/layout_policy"} and _PTR.fullmatch(pointer) is None):
            raise TypeError("invalid caption preview error construction")
        if type(reason) is not CaptionPreviewRejectionReason or (issue_code is not None and (type(issue_code) is not str or issue_code not in STABLE_ISSUE_CODE_SET)):
            raise TypeError("invalid caption preview error construction")
        super().__init__(f"Caption preview rejected: {reason.value}")
        self.pointer, self.reason, self.issue_code = pointer, reason, issue_code


def _reject(pointer: str, reason: CaptionPreviewRejectionReason, issue: str | None = None) -> None:
    raise CaptionPreviewContractError(pointer, reason, issue)


def _digest(value: Any) -> str:
    return hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _rect_dict(value: PreviewRect) -> dict[str, int]:
    return {name: getattr(value, name) for name in _RECT_FIELDS}


def _policy_dict(value: CaptionPreviewLayoutPolicy) -> dict[str, Any]:
    return {"policy_version": value.policy_version, "safe_rect": _rect_dict(value.safe_rect), "v5_rect": _rect_dict(value.v5_rect), "v6_rect": _rect_dict(value.v6_rect)}


def _scene_dict(value: PreviewScene) -> dict[str, Any]:
    return {"schema_version": value.schema_version, "hash_scope_version": value.hash_scope_version, "preview_scene_id": value.preview_scene_id, "preview_scene_hash": value.preview_scene_hash, "track": value.track.value, "ordinal": value.ordinal, "source_id": value.source_id, "start_frame": value.start_frame, "end_exclusive_frame": value.end_exclusive_frame, "rect": _rect_dict(value.rect), "semantic_proxy_label": value.semantic_proxy_label}


def _artifact_dict(value: CaptionPreviewArtifact) -> dict[str, Any]:
    return {name: (_policy_dict(value.layout_policy) if name == "layout_policy" else _rect_dict(value.safe_rect) if name == "safe_rect" else [_scene_dict(x) for x in value.scenes] if name == "scenes" else getattr(value, name)) for name in _ROOT_FIELDS}


def _valid_rect(value: Any) -> bool:
    return type(value) is PreviewRect and all(type(getattr(value, x)) is int for x in _RECT_FIELDS) and 0 <= value.left < value.right <= _CANVAS and 0 <= value.top < value.bottom <= _CANVAS


def _validate_policy(value: Any) -> CaptionPreviewLayoutPolicy:
    if type(value) is not CaptionPreviewLayoutPolicy or value.policy_version != CAPTION_PREVIEW_POLICY_V1 or not all(_valid_rect(getattr(value, n)) for n in ("safe_rect", "v5_rect", "v6_rect")):
        _reject("/layout_policy", CaptionPreviewRejectionReason.GEOMETRY_INVALID)
    return value


def _dependency_bytes(value: Any, expected: type, serializer: Any, pointer: str) -> bytes:
    if type(value) is not expected:
        raise TypeError(f"{pointer[1:]} must be an exact dependency")
    try:
        return serializer(value)
    except Exception:
        _reject(pointer, CaptionPreviewRejectionReason.DEPENDENCY_CONTENT_DRIFT)


def _text(value: str) -> str:
    if type(value) is not str or unicodedata.normalize("NFC", value) != value or any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ValueError
    return value


def _signature(value: CaptionPreviewArtifact) -> tuple[int, ...]:
    result = [id(value), id(value.layout_policy), id(value.safe_rect), id(value.scenes)]
    for scene in value.scenes:
        result.extend((id(scene), id(scene.rect), id(scene.track), id(scene.semantic_proxy_label)))
    return tuple(result)


def _register(value: CaptionPreviewArtifact, envelope: bytes) -> None:
    key = id(value)
    if key in _MATERIALIZED and _MATERIALIZED[key][0]() is not None:
        raise RuntimeError("caption preview registry collision")
    def gone(ref: weakref.ReferenceType[CaptionPreviewArtifact]) -> None:
        if _MATERIALIZED.get(key, (None,))[0] is ref:
            _MATERIALIZED.pop(key, None)
    ref = weakref.ref(value, gone)
    entry = (ref, bytes(envelope), _signature(value))
    _MATERIALIZED[key] = entry
    if _MATERIALIZED.get(key) is not entry:
        _MATERIALIZED.pop(key, None)
        raise RuntimeError("caption preview registration failed")


def _compile(*, caption_groups: CaptionGroupsArtifact, emphasis_events: EmphasisEventsArtifact, word_to_frame: WordToFrameArtifact, layout_policy: CaptionPreviewLayoutPolicy) -> CaptionPreviewArtifact:
    policy = _validate_policy(layout_policy)
    _dependency_bytes(caption_groups, CaptionGroupsArtifact, serialize_caption_groups, "/caption_groups")
    _dependency_bytes(emphasis_events, EmphasisEventsArtifact, serialize_emphasis_events, "/emphasis_events")
    _dependency_bytes(word_to_frame, WordToFrameArtifact, serialize_word_to_frame, "/word_to_frame")
    if (caption_groups.project_id, caption_groups.document_id, caption_groups.narration_revision_id, caption_groups.narration_revision_hash) != (emphasis_events.project_id, emphasis_events.document_id, emphasis_events.narration_revision_id, emphasis_events.narration_revision_hash) or (caption_groups.caption_groups_id, caption_groups.caption_groups_hash) != (word_to_frame.caption_groups_id, word_to_frame.caption_groups_hash) or (emphasis_events.emphasis_events_id, emphasis_events.emphasis_events_hash) != (word_to_frame.emphasis_events_id, word_to_frame.emphasis_events_hash):
        _reject("/word_to_frame", CaptionPreviewRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    caps = {x.source_id: x for x in word_to_frame.caption_frames if x.source_kind is TemporalFrameSpanKind.CAPTION_GROUP}
    emps = {x.source_id: x for x in word_to_frame.emphasis_frames if x.source_kind is TemporalFrameSpanKind.EMPHASIS_EVENT}
    if len(caps) != len(caption_groups.caption_groups) or len(emps) != len(emphasis_events.emphasis_events):
        _reject("/word_to_frame", CaptionPreviewRejectionReason.FRAME_BINDING_INVALID, "CANONICAL_COVERAGE_BLOCKER")
    scenes: list[PreviewScene] = []
    for event in emphasis_events.emphasis_events:
        span = emps.get(event.emphasis_event_id)
        if span is None or (span.ordinal, span.start_word_ordinal, span.end_exclusive_word_ordinal, span.start_ms, span.end_ms, span.start_word_id, span.end_word_id) != (event.ordinal, event.start_word_ordinal, event.end_exclusive_word_ordinal, event.start_ms, event.end_ms, event.start_word_id, event.end_word_id):
            _reject("/word_to_frame", CaptionPreviewRejectionReason.FRAME_BINDING_INVALID, "CANONICAL_COVERAGE_BLOCKER")
        raw = {"schema_version": CAPTION_PREVIEW_V1, "hash_scope_version": CAPTION_PREVIEW_HASH_V1, "track": "V5", "ordinal": len(scenes), "source_id": event.emphasis_event_id, "start_frame": span.start_frame, "end_exclusive_frame": span.end_exclusive_frame, "rect": _rect_dict(policy.v5_rect), "semantic_proxy_label": "[EMPHASIS:" + event.intensity.value + "]"}
        h = _digest(raw); scenes.append(PreviewScene(CAPTION_PREVIEW_V1, CAPTION_PREVIEW_HASH_V1, "pscn_" + h[:32], h, PreviewTrack.V5, len(scenes), event.emphasis_event_id, span.start_frame, span.end_exclusive_frame, policy.v5_rect, raw["semantic_proxy_label"]))
    for group in caption_groups.caption_groups:
        span = caps.get(group.caption_group_id)
        if span is None or (span.ordinal, span.start_word_ordinal, span.end_exclusive_word_ordinal, span.start_ms, span.end_ms, span.start_word_id, span.end_word_id) != (group.ordinal, group.start_word_ordinal, group.end_exclusive_word_ordinal, group.start_ms, group.end_ms, group.start_word_id, group.end_word_id):
            _reject("/word_to_frame", CaptionPreviewRejectionReason.FRAME_BINDING_INVALID, "CANONICAL_COVERAGE_BLOCKER")
        try: label = _text(group.display_text)
        except ValueError: _reject("/caption_groups", CaptionPreviewRejectionReason.DEPENDENCY_CONTENT_DRIFT)
        raw = {"schema_version": CAPTION_PREVIEW_V1, "hash_scope_version": CAPTION_PREVIEW_HASH_V1, "track": "V6", "ordinal": len(scenes), "source_id": group.caption_group_id, "start_frame": span.start_frame, "end_exclusive_frame": span.end_exclusive_frame, "rect": _rect_dict(policy.v6_rect), "semantic_proxy_label": label}
        h = _digest(raw); scenes.append(PreviewScene(CAPTION_PREVIEW_V1, CAPTION_PREVIEW_HASH_V1, "pscn_" + h[:32], h, PreviewTrack.V6, len(scenes), group.caption_group_id, span.start_frame, span.end_exclusive_frame, policy.v6_rect, label))
    ph = "sha256:" + _digest(_policy_dict(policy))
    raw_root = {"schema_version": CAPTION_PREVIEW_V1, "hash_scope_version": CAPTION_PREVIEW_HASH_V1, "project_id": caption_groups.project_id, "document_id": caption_groups.document_id, "narration_revision_id": caption_groups.narration_revision_id, "narration_revision_hash": caption_groups.narration_revision_hash, "caption_groups_id": caption_groups.caption_groups_id, "caption_groups_hash": caption_groups.caption_groups_hash, "emphasis_events_id": emphasis_events.emphasis_events_id, "emphasis_events_hash": emphasis_events.emphasis_events_hash, "word_to_frame_id": word_to_frame.word_to_frame_id, "word_to_frame_hash": word_to_frame.word_to_frame_hash, "layout_policy": _policy_dict(policy), "layout_policy_snapshot_hash": ph, "canvas_units": _CANVAS, "safe_rect": _rect_dict(policy.safe_rect), "scenes": [_scene_dict(x) for x in scenes]}
    h = _digest(raw_root)
    return CaptionPreviewArtifact(CAPTION_PREVIEW_V1, CAPTION_PREVIEW_HASH_V1, "cprev_" + h[:32], h, raw_root["project_id"], raw_root["document_id"], raw_root["narration_revision_id"], raw_root["narration_revision_hash"], raw_root["caption_groups_id"], raw_root["caption_groups_hash"], raw_root["emphasis_events_id"], raw_root["emphasis_events_hash"], raw_root["word_to_frame_id"], raw_root["word_to_frame_hash"], policy, ph, _CANVAS, policy.safe_rect, tuple(scenes))


def compile_caption_preview(*, caption_groups: CaptionGroupsArtifact, emphasis_events: EmphasisEventsArtifact, word_to_frame: WordToFrameArtifact, layout_policy: CaptionPreviewLayoutPolicy) -> CaptionPreviewArtifact:
    value = _compile(caption_groups=caption_groups, emphasis_events=emphasis_events, word_to_frame=word_to_frame, layout_policy=layout_policy); _register(value, encode_canonical_json_bytes(_artifact_dict(value))); return value


def load_caption_preview(source: bytes, *, caption_groups: CaptionGroupsArtifact, emphasis_events: EmphasisEventsArtifact, word_to_frame: WordToFrameArtifact, layout_policy: CaptionPreviewLayoutPolicy) -> CaptionPreviewArtifact:
    expected = _compile(caption_groups=caption_groups, emphasis_events=emphasis_events, word_to_frame=word_to_frame, layout_policy=layout_policy)
    if type(source) is not bytes: raise TypeError("source must be exact bytes")
    try:
        if source.startswith(b"\xef\xbb\xbf"): raise ValueError
        value = json.loads(source.decode("utf-8"), object_pairs_hook=_Pairs, parse_float=lambda _: (_ for _ in ()).throw(ValueError()), parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except Exception: _reject("/", CaptionPreviewRejectionReason.NON_CANONICAL_SERIALIZATION)
    def convert(item: Any) -> Any:
        if type(item) is _Pairs:
            if len(item) != len({key for key, _ in item}):
                _reject("/", CaptionPreviewRejectionReason.NON_CANONICAL_SERIALIZATION)
            return {key: convert(nested) for key, nested in item}
        if type(item) is list:
            return [convert(nested) for nested in item]
        return item
    value = convert(value)
    if type(value) is not dict or set(value) != set(_ROOT_FIELDS): _reject("/", CaptionPreviewRejectionReason.STRUCTURE_INVALID)
    root_strings = ("schema_version", "hash_scope_version", "caption_preview_id", "caption_preview_hash", "project_id", "document_id", "narration_revision_id", "narration_revision_hash", "caption_groups_id", "caption_groups_hash", "emphasis_events_id", "emphasis_events_hash", "word_to_frame_id", "word_to_frame_hash", "layout_policy_snapshot_hash")
    if any(type(value[field]) is not str for field in root_strings) or type(value["canvas_units"]) is not int or type(value["scenes"]) is not list:
        _reject("/", CaptionPreviewRejectionReason.STRUCTURE_INVALID)
    def exact_rect(candidate: Any, pointer: str) -> None:
        if type(candidate) is not dict or set(candidate) != set(_RECT_FIELDS) or any(type(candidate[field]) is not int for field in _RECT_FIELDS):
            _reject(pointer, CaptionPreviewRejectionReason.STRUCTURE_INVALID)
    exact_rect(value["safe_rect"], "/safe_rect")
    policy_value = value["layout_policy"]
    if type(policy_value) is not dict or set(policy_value) != set(_POLICY_FIELDS) or type(policy_value["policy_version"]) is not str:
        _reject("/layout_policy", CaptionPreviewRejectionReason.STRUCTURE_INVALID)
    for field in ("safe_rect", "v5_rect", "v6_rect"):
        exact_rect(policy_value[field], "/layout_policy")
    for index, scene in enumerate(value["scenes"]):
        pointer = f"/scenes/{index}"
        if type(scene) is not dict or set(scene) != set(_SCENE_FIELDS): _reject(pointer, CaptionPreviewRejectionReason.STRUCTURE_INVALID)
        if any(type(scene[field]) is not str for field in ("schema_version", "hash_scope_version", "preview_scene_id", "preview_scene_hash", "track", "source_id", "semantic_proxy_label")) or any(type(scene[field]) is not int for field in ("ordinal", "start_frame", "end_exclusive_frame")):
            _reject(pointer, CaptionPreviewRejectionReason.STRUCTURE_INVALID)
        exact_rect(scene["rect"], pointer)
    wanted = _artifact_dict(expected)
    if value.get("schema_version") != CAPTION_PREVIEW_V1 or value.get("hash_scope_version") != CAPTION_PREVIEW_HASH_V1:
        _reject("/", CaptionPreviewRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
    for field in ("project_id", "document_id", "narration_revision_id", "narration_revision_hash", "caption_groups_id", "caption_groups_hash", "emphasis_events_id", "emphasis_events_hash", "word_to_frame_id", "word_to_frame_hash", "layout_policy", "layout_policy_snapshot_hash"):
        if value.get(field) != wanted[field]:
            _reject("/word_to_frame" if field.startswith("word_to_frame") else "/caption_groups" if field.startswith("caption_groups") else "/emphasis_events" if field.startswith("emphasis_events") else "/", CaptionPreviewRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    if value.get("canvas_units") != _CANVAS or value.get("safe_rect") != wanted["safe_rect"]:
        _reject("/safe_rect", CaptionPreviewRejectionReason.GEOMETRY_INVALID)
    scenes = value.get("scenes")
    if type(scenes) is not list or len(scenes) != len(wanted["scenes"]):
        _reject("/scenes", CaptionPreviewRejectionReason.FRAME_BINDING_INVALID, "CANONICAL_COVERAGE_BLOCKER")
    for index, (actual, reference) in enumerate(zip(scenes, wanted["scenes"])):
        pointer = f"/scenes/{index}"
        if actual.get("schema_version") != CAPTION_PREVIEW_V1 or actual.get("hash_scope_version") != CAPTION_PREVIEW_HASH_V1 or actual.get("track") not in {item.value for item in PreviewTrack}:
            _reject(pointer, CaptionPreviewRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
        if actual.get("rect") != reference["rect"]:
            _reject(pointer, CaptionPreviewRejectionReason.GEOMETRY_INVALID)
        for field in ("track", "ordinal", "source_id", "start_frame", "end_exclusive_frame", "semantic_proxy_label"):
            if actual.get(field) != reference[field]:
                _reject(pointer, CaptionPreviewRejectionReason.FRAME_BINDING_INVALID, "CANONICAL_COVERAGE_BLOCKER")
        child_projection = {field: actual[field] for field in _SCENE_FIELDS if field not in {"preview_scene_id", "preview_scene_hash"}}
        digest = _digest(child_projection)
        if actual.get("preview_scene_hash") != digest or actual.get("preview_scene_id") != "pscn_" + digest[:32]:
            _reject(pointer, CaptionPreviewRejectionReason.IDENTITY_MISMATCH)
    root_projection = {field: value[field] for field in _ROOT_FIELDS if field not in {"caption_preview_id", "caption_preview_hash"}}
    digest = _digest(root_projection)
    if value.get("caption_preview_hash") != digest or value.get("caption_preview_id") != "cprev_" + digest[:32]:
        _reject("/", CaptionPreviewRejectionReason.IDENTITY_MISMATCH)
    envelope = encode_canonical_json_bytes(wanted)
    if source != envelope: _reject("/", CaptionPreviewRejectionReason.NON_CANONICAL_SERIALIZATION)
    _register(expected, envelope); return expected


def serialize_caption_preview(artifact: CaptionPreviewArtifact) -> bytes:
    if type(artifact) is not CaptionPreviewArtifact: raise TypeError("artifact must be exact CaptionPreviewArtifact")
    entry = _MATERIALIZED.get(id(artifact))
    if entry is None or entry[0]() is not artifact: _reject("/", CaptionPreviewRejectionReason.NOT_MATERIALIZED)
    try: current = encode_canonical_json_bytes(_artifact_dict(artifact))
    except Exception: _reject("/", CaptionPreviewRejectionReason.CONTENT_DRIFT)
    if _signature(artifact) != entry[2] or current != entry[1]: _reject("/", CaptionPreviewRejectionReason.CONTENT_DRIFT)
    return bytes(entry[1])


def _escape(value: str) -> str:
    _text(value)
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")


def render_caption_preview_diagnostic_svg(artifact: CaptionPreviewArtifact) -> str:
    serialize_caption_preview(artifact)
    safe = artifact.safe_rect
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" width="1000" height="1000">', f'<rect data-kind="safe-area" x="{safe.left//1000}" y="{safe.top//1000}" width="{(safe.right-safe.left)//1000}" height="{(safe.bottom-safe.top)//1000}" fill="none" stroke="#111111"/>']
    for scene in artifact.scenes:
        r, color = scene.rect, "#E8A317" if scene.track is PreviewTrack.V5 else "#2C7BE5"
        parts.append(f'<rect data-track="{scene.track.value}" data-scene-id="{scene.preview_scene_id}" x="{r.left//1000}" y="{r.top//1000}" width="{(r.right-r.left)//1000}" height="{(r.bottom-r.top)//1000}" fill="{color}"/>')
        parts.append(f'<text data-scene-id="{scene.preview_scene_id}" x="{r.left//1000}" y="{r.top//1000}">{_escape(scene.semantic_proxy_label)}</text>')
    return "".join(parts) + "</svg>"
