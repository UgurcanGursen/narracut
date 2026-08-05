"""Canonical Phase 3 -> Phase 4A RenderProps binding; never a scheduler."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.audio_edl import AudioEdlArtifact, serialize_audio_edl
from engine.contracts.edl import VideoEdlArtifact, serialize_video_edl

from .fixture_assets import FixtureAssetResolver, FixtureAssetResolverError


RENDER_PROPS_V1 = "RENDER-PROPS-V1"
RENDER_PROPS_HASH_V1 = "RENDER-PROPS-HASH-V1"
RENDER_REQUEST_ID_V1 = "RENDER-REQUEST-ID-V1"
BRIDGE_SEMVER = "0.1.0"
COMPOSITION_ID = "sequence-preview-v1"
DESIGN_SYSTEM_VERSION = "DESIGN-TOKENS-V1"
PREVIEW_WIDTH, PREVIEW_HEIGHT = 1280, 720
PIXEL_FORMAT = "rgba"


class RenderMode(str, Enum):
    PREVIEW = "PREVIEW"
    FULL = "FULL"


class RenderFailureCode(str, Enum):
    UPSTREAM_NOT_MATERIALIZED = "UPSTREAM_NOT_MATERIALIZED"
    DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
    NON_CANONICAL_PROPS = "NON_CANONICAL_PROPS"
    UNSUPPORTED_COMPOSITION = "UNSUPPORTED_COMPOSITION"
    ASSET_RESOLUTION_FAILED = "ASSET_RESOLUTION_FAILED"
    ASSET_HASH_MISMATCH = "ASSET_HASH_MISMATCH"
    MODE_NOT_AUTHORIZED = "MODE_NOT_AUTHORIZED"
    VISUAL_DIRECTIVE_INVALID = "VISUAL_DIRECTIVE_INVALID"
    REMOTION_UNAVAILABLE = "REMOTION_UNAVAILABLE"
    RENDER_TIMEOUT = "RENDER_TIMEOUT"
    RENDER_EXIT_NONZERO = "RENDER_EXIT_NONZERO"
    RECEIPT_INVALID = "RECEIPT_INVALID"
    PREVIEW_MANIFEST_INVALID = "PREVIEW_MANIFEST_INVALID"
    PREVIEW_FRAME_HASH_MISMATCH = "PREVIEW_FRAME_HASH_MISMATCH"
    ARTIFACT_REGISTRATION_FAILED = "ARTIFACT_REGISTRATION_FAILED"
    OUTPUT_TARGET_EXISTS = "OUTPUT_TARGET_EXISTS"
    CANCELLED_BY_PARENT = "CANCELLED_BY_PARENT"


class RenderBridgeError(ValueError):
    def __init__(self, code: RenderFailureCode, pointer: str) -> None:
        super().__init__(f"Renderer bridge rejected: {code.value}")
        self.code, self.pointer = code, pointer


@dataclass(frozen=True)
class RenderProps:
    schema_version: str
    hash_scope_version: str
    render_props_id: str
    render_props_hash: str
    render_request_id: str
    mode: RenderMode
    renderer_version: str
    project_id: str
    document_id: str
    narration_revision_id: str
    sequence_id: str
    video_edl_id: str
    video_edl_hash: str
    audio_edl_id: str
    audio_edl_hash: str
    word_to_frame_id: str
    word_to_frame_hash: str
    fps_numerator: int
    fps_denominator: int
    duration_frames: int
    duration_samples: int
    width: int
    height: int
    pixel_format: str
    composition_id: str
    design_system_version: str
    fixture_manifest_id: str
    fixture_manifest_hash: str
    video_tracks: tuple[dict[str, Any], ...]
    audio_tracks: tuple[dict[str, Any], ...]
    audio_boundary_decisions: tuple[dict[str, Any], ...]
    asset_bindings: tuple[dict[str, Any], ...]
    visual_directives: tuple[dict[str, Any], ...]


def _fail(code: RenderFailureCode, pointer: str) -> None:
    raise RenderBridgeError(code, pointer)


def _sha(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _strict_json(raw: bytes, code: RenderFailureCode, pointer: str) -> dict[str, Any]:
    if type(raw) is not bytes or raw.startswith(b"\xef\xbb\xbf"):
        _fail(code, pointer)
    class Pairs(list):
        pass
    try:
        parsed = json.loads(raw.decode("utf-8"), object_pairs_hook=Pairs,
                            parse_float=lambda _: (_ for _ in ()).throw(ValueError()),
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except Exception:
        _fail(code, pointer)
    def plain(value: Any) -> Any:
        if type(value) is Pairs:
            if len(value) != len({name for name, _ in value}):
                _fail(code, pointer)
            return {name: plain(item) for name, item in value}
        if type(value) is list:
            return [plain(item) for item in value]
        if type(value) is float:
            _fail(code, pointer)
        return value
    value = plain(parsed)
    if type(value) is not dict:
        _fail(code, pointer)
    try:
        if encode_canonical_json_bytes(value) != raw:
            _fail(code, pointer)
    except Exception:
        _fail(code, pointer)
    return value


def renderer_version(package_lock_bytes: bytes) -> str:
    """Return the only permitted version representation from checked-in lock bytes."""
    if type(package_lock_bytes) is not bytes or not package_lock_bytes:
        _fail(RenderFailureCode.REMOTION_UNAVAILABLE, "/package_lock")
    return f"RRV1|bridge={BRIDGE_SEMVER}|package_lock_sha256={hashlib.sha256(package_lock_bytes).hexdigest()}"


def _trusted_renderer_version() -> str:
    """Bind props to the checked-in renderer lock, never caller text.

    Phase 4A is a fixture-only bridge.  The lock file is consequently part of
    its trusted local implementation, rather than an ingress parameter that a
    caller can replace while preserving a syntactically valid version string.
    """
    lock_path = Path(__file__).resolve().parents[2] / "renderer-remotion" / "package-lock.json"
    try:
        return renderer_version(lock_path.read_bytes())
    except OSError:
        _fail(RenderFailureCode.REMOTION_UNAVAILABLE, "/renderer-remotion/package-lock.json")


def _props_data(value: RenderProps, *, identity: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for name in RenderProps.__dataclass_fields__:
        item = getattr(value, name)
        data[name] = item.value if isinstance(item, Enum) else list(item) if isinstance(item, tuple) else item
    if identity:
        for name in ("render_props_id", "render_props_hash", "render_request_id"):
            data.pop(name)
    return data


def _request_id(props_hash: str, composition_id: str, version: str, manifest_hash: str) -> str:
    value = {"schema_version": RENDER_REQUEST_ID_V1, "render_props_hash": props_hash,
             "composition_id": composition_id, "renderer_version": version,
             "fixture_manifest_hash": manifest_hash}
    return "rrq_" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()[:32]


def _project_tracks(video: dict[str, Any], audio: dict[str, Any], resolver: FixtureAssetResolver) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...], tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    video_tracks: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    seen_events: set[str] = set()
    required = ("schema_version", "hash_scope_version", "event_id", "event_hash", "track", "ordinal", "intent_id", "editorial_role", "start_frame", "end_exclusive_frame", "start_word_id", "end_word_id", "payload")
    if len(video["tracks"]) != 12:
        _fail(RenderFailureCode.DEPENDENCY_BINDING_INVALID, "/video_edl/tracks")
    for index, track in enumerate(video["tracks"][:7]):
        if track["track"] != f"V{index + 1}":
            _fail(RenderFailureCode.DEPENDENCY_BINDING_INVALID, "/video_edl/tracks")
        rows: list[dict[str, Any]] = []
        for event in track["events"]:
            if set(event) != set(required):
                _fail(RenderFailureCode.DEPENDENCY_BINDING_INVALID, "/video_edl/event")
            rows.append({name: event[name] for name in required})
            payload = event["payload"]
            source = payload.get("source")
            if source is None:
                continue
            # Phase 3 deliberately does not own an artifact catalog. Preserve that
            # null matrix and bind only its opaque source_ref against this fixture.
            if payload.get("source_artifact_id") is not None or payload.get("source_artifact_hash") is not None:
                _fail(RenderFailureCode.DEPENDENCY_BINDING_INVALID, f"/video_edl/events/{event['event_id']}")
            try:
                asset = resolver.resolve_source_ref(source["source_ref"])
            except FixtureAssetResolverError as exc:
                _fail(RenderFailureCode(exc.code), f"/video_edl/events/{event['event_id']}")
            if event["event_id"] in seen_events:
                _fail(RenderFailureCode.DEPENDENCY_BINDING_INVALID, "/asset_bindings")
            seen_events.add(event["event_id"])
            bindings.append({"event_id": event["event_id"], "edl_source_ref": source["source_ref"], "fixture_asset_id": asset.fixture_asset_id,
                             "content_sha256": asset.content_sha256, "media_type": asset.media_type,
                             "width": asset.width, "height": asset.height})
        video_tracks.append({"track": track["track"], "kind": track["kind"], "priority": track["priority"], "events": rows})
    if len(video_tracks) != 7:
        _fail(RenderFailureCode.DEPENDENCY_BINDING_INVALID, "/video_edl/tracks")
    audio_tracks: list[dict[str, Any]] = []
    a_fields = ("schema_version", "hash_scope_version", "event_id", "event_hash", "track", "kind", "ordinal", "intent_id", "source_id", "source_media_hash", "normalized_pcm_evidence_hash", "start_sample", "end_exclusive_sample", "source_in_sample", "source_out_exclusive_sample", "gain_millibels", "cue_start_word_id", "cue_end_word_id", "cue_start_sample", "cue_end_exclusive_sample")
    for index, track in enumerate(audio["tracks"]):
        if track["track"] != f"A{index + 1}":
            _fail(RenderFailureCode.DEPENDENCY_BINDING_INVALID, "/audio_edl/tracks")
        audio_tracks.append({"track": track["track"], "priority": track["priority"], "events": [{name: event[name] for name in a_fields} for event in track["events"]]})
    if len(audio_tracks) != 5:
        _fail(RenderFailureCode.DEPENDENCY_BINDING_INVALID, "/audio_edl/tracks")
    d_fields = ("position", "left_event_id", "right_event_id", "track", "policy", "transition", "left_trim_samples", "right_trim_samples", "fade_in_samples", "fade_out_samples", "overlap_samples", "protected_silence_samples")
    decisions = tuple({name: row[name] for name in d_fields} for row in audio["boundary_decisions"])
    directive_events = {
        track["track"]: {event["event_id"]: event for event in track["events"]}
        for track in video_tracks if track["track"] in {"V3", "V4"}
    }
    directives: list[dict[str, Any]] = []
    directive_event_keys: set[tuple[str, str]] = set()
    for directive in resolver.manifest.visual_directives:
        event = directive_events.get(directive.track, {}).get(directive.event_id)
        if event is None or event["event_hash"] != directive.event_hash or event["payload"].get("source") is None:
            _fail(RenderFailureCode.VISUAL_DIRECTIVE_INVALID, "/visual_directives")
        directive_event_keys.add((directive.track, directive.event_id))
        directives.append(directive.as_row())
    expected_directive_event_keys = {
        (track, event_id)
        for track, events in directive_events.items()
        for event_id, event in events.items()
        if event["payload"].get("source") is not None
    }
    if directive_event_keys != expected_directive_event_keys:
        _fail(RenderFailureCode.VISUAL_DIRECTIVE_INVALID, "/visual_directives")
    return tuple(video_tracks), tuple(audio_tracks), decisions, tuple(sorted(bindings, key=lambda item: item["event_id"])), tuple(directives)


def build_render_props(*, video_edl: VideoEdlArtifact, audio_edl: AudioEdlArtifact,
                       fixture_assets: FixtureAssetResolver, renderer_version_value: str,
                       mode: RenderMode = RenderMode.PREVIEW,
                       composition_id: str = COMPOSITION_ID) -> RenderProps:
    # Phase 4A owns exactly one preview composition. FULL is deliberately
    # reserved for the separately-authorized Phase 4B contract.
    if mode is not RenderMode.PREVIEW:
        _fail(RenderFailureCode.MODE_NOT_AUTHORIZED, "/mode")
    if type(composition_id) is not str or composition_id != COMPOSITION_ID:
        _fail(RenderFailureCode.UNSUPPORTED_COMPOSITION, "/composition_id")
    if type(video_edl) is not VideoEdlArtifact or type(audio_edl) is not AudioEdlArtifact or type(fixture_assets) is not FixtureAssetResolver:
        _fail(RenderFailureCode.DEPENDENCY_BINDING_INVALID, "/upstream")
    if type(renderer_version_value) is not str or renderer_version_value != _trusted_renderer_version():
        _fail(RenderFailureCode.REMOTION_UNAVAILABLE, "/renderer_version")
    try:
        video_bytes = serialize_video_edl(video_edl); audio_bytes = serialize_audio_edl(audio_edl)
    except Exception:
        _fail(RenderFailureCode.UPSTREAM_NOT_MATERIALIZED, "/upstream")
    video = _strict_json(video_bytes, RenderFailureCode.UPSTREAM_NOT_MATERIALIZED, "/video_edl")
    # Audio's canonical representation contains binary32 evidence tokens but no
    # JSON float: exact byte parsing still rejects duplicate/noncanonical input.
    audio = _strict_json(audio_bytes, RenderFailureCode.UPSTREAM_NOT_MATERIALIZED, "/audio_edl")
    if (audio["video_edl_id"], audio["video_edl_hash"]) != (video["video_edl_id"], video["video_edl_hash"]):
        _fail(RenderFailureCode.DEPENDENCY_BINDING_INVALID, "/audio_edl/video_edl")
    for name in ("project_id", "document_id", "narration_revision_id", "sequence_id", "word_to_frame_id", "word_to_frame_hash"):
        if audio[name] != video[name]:
            _fail(RenderFailureCode.DEPENDENCY_BINDING_INVALID, "/lineage")
    expected_samples = video["duration_frames"] * 48000 * video["fps_denominator"] // video["fps_numerator"]
    if audio["sample_rate_hz"] != 48000 or audio["duration_samples"] != expected_samples:
        _fail(RenderFailureCode.DEPENDENCY_BINDING_INVALID, "/audio_edl/duration_samples")
    tracks, audio_tracks, decisions, bindings, directives = _project_tracks(video, audio, fixture_assets)
    base = dict(schema_version=RENDER_PROPS_V1, hash_scope_version=RENDER_PROPS_HASH_V1,
                render_props_id="", render_props_hash="", render_request_id="", mode=RenderMode.PREVIEW,
                renderer_version=renderer_version_value, project_id=video["project_id"], document_id=video["document_id"], narration_revision_id=video["narration_revision_id"], sequence_id=video["sequence_id"], video_edl_id=video["video_edl_id"], video_edl_hash=video["video_edl_hash"], audio_edl_id=audio["audio_edl_id"], audio_edl_hash=audio["audio_edl_hash"], word_to_frame_id=video["word_to_frame_id"], word_to_frame_hash=video["word_to_frame_hash"], fps_numerator=video["fps_numerator"], fps_denominator=video["fps_denominator"], duration_frames=video["duration_frames"], duration_samples=audio["duration_samples"], width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT, pixel_format=PIXEL_FORMAT, composition_id=COMPOSITION_ID, design_system_version=DESIGN_SYSTEM_VERSION, fixture_manifest_id=fixture_assets.manifest.fixture_manifest_id, fixture_manifest_hash=fixture_assets.manifest.fixture_manifest_hash, video_tracks=tracks, audio_tracks=audio_tracks, audio_boundary_decisions=decisions, asset_bindings=bindings, visual_directives=directives)
    draft = RenderProps(**base)
    props_hash = _sha(encode_canonical_json_bytes(_props_data(draft, identity=True)))
    return RenderProps(**(base | {"render_props_hash": props_hash, "render_props_id": "rprops_" + props_hash[7:39], "render_request_id": _request_id(props_hash, COMPOSITION_ID, renderer_version_value, fixture_assets.manifest.fixture_manifest_hash)}))


def serialize_render_props(value: RenderProps) -> bytes:
    _validate_props(value)
    return encode_canonical_json_bytes(_props_data(value))


def _validate_props(value: RenderProps) -> None:
    if type(value) is not RenderProps or value.schema_version != RENDER_PROPS_V1 or value.hash_scope_version != RENDER_PROPS_HASH_V1 or value.mode is not RenderMode.PREVIEW or value.composition_id != COMPOSITION_ID or value.width != PREVIEW_WIDTH or value.height != PREVIEW_HEIGHT or value.pixel_format != PIXEL_FORMAT:
        _fail(RenderFailureCode.NON_CANONICAL_PROPS, "/")
    if value.renderer_version != _trusted_renderer_version():
        _fail(RenderFailureCode.NON_CANONICAL_PROPS, "/renderer_version")
    _validate_projected_shapes(value)
    digest = _sha(encode_canonical_json_bytes(_props_data(value, identity=True)))
    if value.render_props_hash != digest or value.render_props_id != "rprops_" + digest[7:39] or value.render_request_id != _request_id(digest, value.composition_id, value.renderer_version, value.fixture_manifest_hash):
        _fail(RenderFailureCode.NON_CANONICAL_PROPS, "/identity")


def _validate_projected_shapes(value: RenderProps) -> None:
    """Reject a re-hashed but structurally forged projection before Node sees it."""
    identity = re.compile(r"^[a-z][a-z0-9_]*$")
    digest = re.compile(r"^sha256:[0-9a-f]{64}$")
    bare_digest = re.compile(r"^[0-9a-f]{64}$")
    if (not all(type(getattr(value, name)) is str and identity.fullmatch(getattr(value, name))
                for name in ("project_id", "document_id", "narration_revision_id", "sequence_id", "video_edl_id", "audio_edl_id", "word_to_frame_id", "fixture_manifest_id"))
            or not all(bare_digest.fullmatch(getattr(value, name))
                       for name in ("video_edl_hash", "audio_edl_hash", "word_to_frame_hash"))
            or not digest.fullmatch(value.fixture_manifest_hash)
            or any(type(getattr(value, name)) is not int or getattr(value, name) <= 0
                   for name in ("fps_numerator", "fps_denominator", "duration_frames", "duration_samples"))):
        _fail(RenderFailureCode.NON_CANONICAL_PROPS, "/lineage")
    if len(value.video_tracks) != 7 or len(value.audio_tracks) != 5:
        _fail(RenderFailureCode.NON_CANONICAL_PROPS, "/tracks")
    video_event_fields = {"schema_version", "hash_scope_version", "event_id", "event_hash", "track", "ordinal", "intent_id", "editorial_role", "start_frame", "end_exclusive_frame", "start_word_id", "end_word_id", "payload"}
    source_events: dict[str, dict[str, Any]] = {}
    directive_events: dict[str, dict[str, dict[str, Any]]] = {"V3": {}, "V4": {}}
    for number, track in enumerate(value.video_tracks, 1):
        if type(track) is not dict or set(track) != {"track", "kind", "priority", "events"} or track["track"] != f"V{number}" or type(track["kind"]) is not str or type(track["priority"]) is not int or type(track["events"]) is not list:
            _fail(RenderFailureCode.NON_CANONICAL_PROPS, "/video_tracks")
        for event in track["events"]:
            if type(event) is not dict or set(event) != video_event_fields or event["track"] != track["track"] or type(event["payload"]) is not dict or type(event["event_id"]) is not str or re.fullmatch(r"[0-9a-f]{64}", event["event_hash"]) is None:
                _fail(RenderFailureCode.NON_CANONICAL_PROPS, "/video_tracks/events")
            source = event["payload"].get("source")
            if source is not None:
                if type(source) is not dict or type(source.get("source_ref")) is not str:
                    _fail(RenderFailureCode.NON_CANONICAL_PROPS, "/video_tracks/events/payload/source")
                source_events[event["event_id"]] = source
            if track["track"] in directive_events:
                directive_events[track["track"]][event["event_id"]] = event
    audio_event_fields = {"schema_version", "hash_scope_version", "event_id", "event_hash", "track", "kind", "ordinal", "intent_id", "source_id", "source_media_hash", "normalized_pcm_evidence_hash", "start_sample", "end_exclusive_sample", "source_in_sample", "source_out_exclusive_sample", "gain_millibels", "cue_start_word_id", "cue_end_word_id", "cue_start_sample", "cue_end_exclusive_sample"}
    for number, track in enumerate(value.audio_tracks, 1):
        if type(track) is not dict or set(track) != {"track", "priority", "events"} or track["track"] != f"A{number}" or type(track["priority"]) is not int or type(track["events"]) is not list:
            _fail(RenderFailureCode.NON_CANONICAL_PROPS, "/audio_tracks")
        for event in track["events"]:
            if type(event) is not dict or set(event) != audio_event_fields or event["track"] != track["track"] or type(event["event_id"]) is not str or re.fullmatch(r"[0-9a-f]{64}", event["event_hash"]) is None:
                _fail(RenderFailureCode.NON_CANONICAL_PROPS, "/audio_tracks/events")
    binding_fields = {"event_id", "edl_source_ref", "fixture_asset_id", "content_sha256", "media_type", "width", "height"}
    if (any(type(row) is not dict or set(row) != binding_fields or not digest.fullmatch(row["content_sha256"])
            for row in value.asset_bindings)
            or [row["event_id"] for row in value.asset_bindings] != sorted(row["event_id"] for row in value.asset_bindings)
            or len({row["event_id"] for row in value.asset_bindings}) != len(value.asset_bindings)
            or {row["event_id"] for row in value.asset_bindings} != set(source_events)
            or any(source_events[row["event_id"]]["source_ref"] != row["edl_source_ref"] for row in value.asset_bindings)):
        _fail(RenderFailureCode.NON_CANONICAL_PROPS, "/asset_bindings")
    v3_directive_fields = {"schema_version", "directive_id", "directive_hash", "event_id", "event_hash", "track", "kind", "zoom_start_millionths", "zoom_end_millionths", "highlight_left_millionths", "highlight_top_millionths", "highlight_right_millionths", "highlight_bottom_millionths"}
    v4_directive_fields = {"schema_version", "directive_id", "directive_hash", "event_id", "event_hash", "track", "kind", "reveal_start_millionths", "reveal_end_millionths"}
    def directive_is_bound(row: Any) -> bool:
        if type(row) is not dict or re.fullmatch(r"[0-9a-f]{64}", row.get("event_hash", "")) is None or not digest.fullmatch(row.get("directive_hash", "")):
            return False
        expected_fields = v3_directive_fields if (row.get("track"), row.get("kind")) == ("V3", "SOURCE_ZOOM_HIGHLIGHT") else v4_directive_fields if (row.get("track"), row.get("kind")) == ("V4", "CHART_REVEAL") else None
        event = directive_events.get(row.get("track"), {}).get(row.get("event_id"))
        return set(row) == expected_fields and event is not None and event["event_hash"] == row["event_hash"] and event["payload"].get("source") is not None
    if (any(not directive_is_bound(row) for row in value.visual_directives)
            or [row["directive_id"] for row in value.visual_directives] != sorted(row["directive_id"] for row in value.visual_directives)
            or len({row["directive_id"] for row in value.visual_directives}) != len(value.visual_directives)
            or len({row["event_id"] for row in value.visual_directives}) != len(value.visual_directives)
            or {(row["track"], row["event_id"]) for row in value.visual_directives} != {
                (track, event_id)
                for track, events in directive_events.items()
                for event_id, event in events.items()
                if event["payload"].get("source") is not None
            }):
        _fail(RenderFailureCode.NON_CANONICAL_PROPS, "/visual_directives")


def load_render_props(source: bytes) -> RenderProps:
    value = _strict_json(source, RenderFailureCode.NON_CANONICAL_PROPS, "/")
    if set(value) != set(RenderProps.__dataclass_fields__):
        _fail(RenderFailureCode.NON_CANONICAL_PROPS, "/")
    try:
        props = RenderProps(**(value | {"mode": RenderMode(value["mode"]), "video_tracks": tuple(value["video_tracks"]), "audio_tracks": tuple(value["audio_tracks"]), "audio_boundary_decisions": tuple(value["audio_boundary_decisions"]), "asset_bindings": tuple(value["asset_bindings"]), "visual_directives": tuple(value["visual_directives"])}))
    except Exception:
        _fail(RenderFailureCode.NON_CANONICAL_PROPS, "/")
    _validate_props(props)
    if serialize_render_props(props) != source:
        _fail(RenderFailureCode.NON_CANONICAL_PROPS, "/")
    return props
