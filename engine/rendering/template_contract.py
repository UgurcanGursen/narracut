"""Phase 5 deterministic core motion-template contract.

This module deliberately owns composition *intent* only.  It cannot create
events, assets, time, or a new renderer request; all of those remain bound to
the accepted Phase 2--4 artifacts passed to it.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.domain import policy_snapshot_hash
from engine.contracts.models import DomainPolicySnapshot
from engine.contracts.word_to_frame import (
    TemporalFrameRate, WordToFrameArtifact, load_word_to_frame,
    serialize_word_to_frame,
)

from .bridge import RenderProps, load_render_props, serialize_render_props


TEMPLATE_VERSION_V1 = "1.0.0"
TEMPLATE_RENDER_PLAN_V1 = "TEMPLATE-RENDER-PLAN-V1"
TEMPLATE_RENDER_INPUT_V1 = "TEMPLATE-RENDER-INPUT-V1"
SAFE_AREA_POLICY_V1 = "SAFE-AREA-V1"
PHASE5_FONT_ASSET_HASH_V1 = "sha256:bfb7bb691513f12e734dc346c03a03f784912432d7e3fa8e56efcf906fe86b3d"

CONTENT_SAFE_AREA_V1 = (64_000, 56_000, 936_000, 746_000)
SUBTITLE_SAFE_AREA_V1 = (64_000, 772_000, 936_000, 936_000)


class TemplateId(str, Enum):
    COLD_OPEN_SOURCE_MONTAGE = "cold_open_source_montage"
    CHAPTER_TITLE = "chapter_title"
    ARTICLE_FOCUS_SCAN = "article_focus_scan"
    HEADLINE_TO_PARAGRAPH_ZOOM = "headline_to_paragraph_zoom"
    HIGHLIGHT_WIPE = "highlight_wipe"
    EXPERT_QUOTE_CARD = "expert_quote_card"
    METRIC_REVEAL = "metric_reveal"
    METRIC_COMPARISON = "metric_comparison"
    PROCESS_DIAGRAM = "process_diagram"
    SPLIT_SCREEN_COMPARISON = "split_screen_comparison"
    TIMELINE_PROGRESSION = "timeline_progression"
    NEWS_CLIP_CONTEXT = "news_clip_context"
    FINAL_THESIS_CARD = "final_thesis_card"
    KINETIC_KEYWORD = "kinetic_keyword"
    CAPTION_PHRASE = "caption_phrase"


class TemplateKind(str, Enum):
    SOURCE = "SOURCE"
    TEXT = "TEXT"
    METRIC = "METRIC"
    DIAGRAM = "DIAGRAM"
    COMPARISON = "COMPARISON"
    KINETIC = "KINETIC"


class PayloadKind(str, Enum):
    SOURCE_TEXT = "SOURCE_TEXT"
    TITLE_BODY = "TITLE_BODY"
    QUOTE = "QUOTE"
    METRIC_SINGLE = "METRIC_SINGLE"
    METRIC_PAIR = "METRIC_PAIR"
    DIAGRAM = "DIAGRAM"
    TIMELINE = "TIMELINE"
    COMPARISON = "COMPARISON"
    KINETIC = "KINETIC"


class TemplateContractRejectionReason(str, Enum):
    STRUCTURE_INVALID = "STRUCTURE_INVALID"
    UNSUPPORTED_TEMPLATE = "UNSUPPORTED_TEMPLATE"
    DEFINITION_MISMATCH = "DEFINITION_MISMATCH"
    PAYLOAD_INVALID = "PAYLOAD_INVALID"
    SAFE_AREA_INVALID = "SAFE_AREA_INVALID"
    SOURCE_BINDING_INVALID = "SOURCE_BINDING_INVALID"
    WORD_BINDING_INVALID = "WORD_BINDING_INVALID"
    DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
    POLICY_INVALID = "POLICY_INVALID"
    CONSECUTIVE_TEMPLATE_LIMIT = "CONSECUTIVE_TEMPLATE_LIMIT"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"


class TemplateContractError(ValueError):
    def __init__(self, pointer: str, reason: TemplateContractRejectionReason) -> None:
        super().__init__(f"Template contract rejected: {reason.value}")
        self.pointer = pointer
        self.reason = reason


def _reject(pointer: str, reason: TemplateContractRejectionReason) -> None:
    raise TemplateContractError(pointer, reason)


@dataclass(frozen=True)
class TemplateDefinition:
    template_id: TemplateId
    template_version: str
    kind: TemplateKind
    supported_editorial_roles: tuple[str, ...]
    requires_source_asset: bool
    supports_target_region: bool
    supports_caption: bool
    supports_source_label: bool
    supports_word_binding: bool
    safe_area_policy: str
    payload_kind: PayloadKind


@dataclass(frozen=True)
class TemplateRectV1:
    left_millionths: int
    top_millionths: int
    right_millionths: int
    bottom_millionths: int


@dataclass(frozen=True)
class TemplateStylePresetV1:
    preset_id: str
    color_theme_id: str
    typography_id: str
    font_asset_hash: str
    tone_id: str
    preset_hash: str
    policy_snapshot_id: str | None
    policy_snapshot_hash: str | None


@dataclass(frozen=True)
class TemplatePolicyV1:
    preferred_template_ids: tuple[TemplateId, ...]
    banned_template_ids: tuple[TemplateId, ...]
    required_template_ids: tuple[TemplateId, ...]
    style_preset: TemplateStylePresetV1


@dataclass(frozen=True)
class WordBindingV1:
    narration_revision_id: str
    word_to_frame_id: str
    word_to_frame_hash: str
    start_word_id: str
    end_word_id: str
    start_frame: int
    end_exclusive_frame: int


@dataclass(frozen=True)
class TemplateInvocationV1:
    template_id: TemplateId
    template_version: str
    editorial_role: str
    start_frame: int
    end_exclusive_frame: int
    layout: TemplateRectV1
    source_event_id: str | None
    target_region: TemplateRectV1 | None
    entry_animation: str
    exit_animation: str
    camera_motion: str
    caption: str | None
    source_label: str | None
    style_preset_id: str
    payload: Mapping[str, Any]
    word_binding: WordBindingV1 | None
    safe_area_policy: str


@dataclass(frozen=True)
class TemplateRenderPlanV1:
    schema_version: str
    template_plan_id: str
    template_plan_hash: str
    render_request_id: str
    render_props_hash: str
    word_to_frame_id: str
    word_to_frame_hash: str
    style_preset: TemplateStylePresetV1
    invocations: tuple[TemplateInvocationV1, ...]


@dataclass(frozen=True)
class TemplateCompilationInputV1:
    """Canonical ingress material for a template compiler invocation.

    The dependency artifacts are kept opaque here so this renderer-owned
    contract does not duplicate Phase 2 model definitions.
    """
    render_props_bytes: bytes
    word_to_frame_bytes: bytes
    alignment_result: Any
    caption_groups: Any
    emphasis_events: Any
    frame_rate: TemporalFrameRate
    invocations: tuple[TemplateInvocationV1, ...]
    style_preset: TemplateStylePresetV1 | None = None


@dataclass(frozen=True)
class TemplateRenderInputV1:
    schema_version: str
    render_props: RenderProps
    template_render_plan: TemplateRenderPlanV1
    word_to_frame_artifact: WordToFrameArtifact
    template_input_id: str
    template_input_hash: str


_ROWS = (
    ("cold_open_source_montage", "SOURCE", ("introduce", "context"), 1, 0, 0, 1, 0, "SOURCE_TEXT"),
    ("chapter_title", "TEXT", ("chapter", "introduce"), 0, 0, 1, 0, 0, "TITLE_BODY"),
    ("article_focus_scan", "SOURCE", ("prove_claim", "context"), 1, 1, 0, 1, 0, "SOURCE_TEXT"),
    ("headline_to_paragraph_zoom", "SOURCE", ("prove_claim", "context"), 1, 1, 0, 1, 0, "SOURCE_TEXT"),
    ("highlight_wipe", "SOURCE", ("prove_claim", "emphasize"), 1, 1, 0, 1, 0, "SOURCE_TEXT"),
    ("expert_quote_card", "TEXT", ("quote", "context"), 0, 0, 1, 1, 0, "QUOTE"),
    ("metric_reveal", "METRIC", ("quantify", "prove_claim"), 0, 0, 1, 1, 0, "METRIC_SINGLE"),
    ("metric_comparison", "METRIC", ("compare", "quantify"), 0, 0, 1, 1, 0, "METRIC_PAIR"),
    ("process_diagram", "DIAGRAM", ("explain_mechanism", "context"), 0, 0, 1, 0, 0, "DIAGRAM"),
    ("split_screen_comparison", "COMPARISON", ("compare", "context"), 1, 0, 1, 1, 0, "COMPARISON"),
    ("timeline_progression", "DIAGRAM", ("chronology", "context"), 0, 0, 1, 0, 0, "TIMELINE"),
    ("news_clip_context", "SOURCE", ("context", "prove_claim"), 1, 0, 1, 1, 0, "SOURCE_TEXT"),
    ("final_thesis_card", "TEXT", ("conclude", "emphasize"), 0, 0, 1, 0, 0, "TITLE_BODY"),
    ("kinetic_keyword", "KINETIC", ("emphasize",), 0, 0, 1, 0, 1, "KINETIC"),
    ("caption_phrase", "KINETIC", ("caption",), 0, 0, 1, 0, 1, "KINETIC"),
)

CORE_TEMPLATE_DEFINITIONS = tuple(sorted((
    TemplateDefinition(
        TemplateId(row[0]), TEMPLATE_VERSION_V1, TemplateKind(row[1]), row[2],
        *(bool(value) for value in row[3:8]), SAFE_AREA_POLICY_V1, PayloadKind(row[8]),
    )
    for row in _ROWS
), key=lambda definition: definition.template_id.value))
_DEFINITION_BY_ID = {definition.template_id: definition for definition in CORE_TEMPLATE_DEFINITIONS}


def _plain_string(value: Any) -> bool:
    return type(value) is str and bool(value) and unicodedata.normalize("NFC", value) == value


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _rect_data(rect: TemplateRectV1) -> dict[str, int]:
    return {field: getattr(rect, field) for field in TemplateRectV1.__dataclass_fields__}


def _rect_inside(rect: TemplateRectV1, bounds: tuple[int, int, int, int]) -> bool:
    if type(rect) is not TemplateRectV1 or any(type(getattr(rect, field)) is not int for field in TemplateRectV1.__dataclass_fields__):
        return False
    left, top, right, bottom = _rect_data(rect).values()
    return 0 <= left < right <= 1_000_000 and 0 <= top < bottom <= 1_000_000 and left >= bounds[0] and top >= bounds[1] and right <= bounds[2] and bottom <= bounds[3]


def _validate_payload(kind: PayloadKind, value: Mapping[str, Any], pointer: str) -> None:
    if type(value) is not dict:
        _reject(pointer, TemplateContractRejectionReason.PAYLOAD_INVALID)
    fields: dict[PayloadKind, tuple[str, ...]] = {
        PayloadKind.SOURCE_TEXT: ("headline", "body"), PayloadKind.TITLE_BODY: ("title", "body"),
        PayloadKind.QUOTE: ("quote", "attribution"), PayloadKind.METRIC_SINGLE: ("label", "value", "qualifier"),
        PayloadKind.METRIC_PAIR: ("left_label", "left_value", "right_label", "right_value", "qualifier"),
        PayloadKind.COMPARISON: ("left_label", "right_label", "conclusion"), PayloadKind.KINETIC: ("display_text",),
    }
    if kind in fields:
        if set(value) != set(fields[kind]) or not all(_plain_string(value[name]) for name in fields[kind]):
            _reject(pointer, TemplateContractRejectionReason.PAYLOAD_INVALID)
        return
    if kind is PayloadKind.DIAGRAM:
        if set(value) != {"nodes", "edges"} or type(value["nodes"]) is not list or type(value["edges"]) is not list or not value["nodes"]:
            _reject(pointer, TemplateContractRejectionReason.PAYLOAD_INVALID)
        ids: list[str] = []
        for node in value["nodes"]:
            if type(node) is not dict or set(node) != {"node_id", "label"} or not all(_plain_string(node[key]) for key in ("node_id", "label")):
                _reject(pointer, TemplateContractRejectionReason.PAYLOAD_INVALID)
            ids.append(node["node_id"])
        if ids != sorted(ids) or len(set(ids)) != len(ids):
            _reject(pointer, TemplateContractRejectionReason.PAYLOAD_INVALID)
        for edge in value["edges"]:
            if type(edge) is not dict or set(edge) != {"from_node_id", "to_node_id"} or edge["from_node_id"] not in ids or edge["to_node_id"] not in ids:
                _reject(pointer, TemplateContractRejectionReason.PAYLOAD_INVALID)
        return
    if kind is PayloadKind.TIMELINE:
        if set(value) != {"points"} or type(value["points"]) is not list or not value["points"]:
            _reject(pointer, TemplateContractRejectionReason.PAYLOAD_INVALID)
        for index, point in enumerate(value["points"], 1):
            if type(point) is not dict or set(point) != {"point_id", "label", "ordinal"} or not _plain_string(point["point_id"]) or not _plain_string(point["label"]) or type(point["ordinal"]) is not int or point["ordinal"] != index:
                _reject(pointer, TemplateContractRejectionReason.PAYLOAD_INVALID)
        return
    _reject(pointer, TemplateContractRejectionReason.PAYLOAD_INVALID)


def _preset_data(value: TemplateStylePresetV1) -> dict[str, Any]:
    return {field: getattr(value, field) for field in TemplateStylePresetV1.__dataclass_fields__}


def _validate_preset(value: TemplateStylePresetV1) -> None:
    if type(value) is not TemplateStylePresetV1 or not all(_plain_string(getattr(value, name)) for name in ("preset_id", "color_theme_id", "typography_id", "tone_id")) or value.typography_id != "phase5-noto-sans-v1" or value.font_asset_hash != PHASE5_FONT_ASSET_HASH_V1:
        _reject("/style_preset", TemplateContractRejectionReason.POLICY_INVALID)
    if (value.policy_snapshot_id is None) != (value.policy_snapshot_hash is None):
        _reject("/style_preset", TemplateContractRejectionReason.POLICY_INVALID)
    if value.policy_snapshot_id is not None and (not _plain_string(value.policy_snapshot_id) or type(value.policy_snapshot_hash) is not str or not value.policy_snapshot_hash.startswith("sha256:")):
        _reject("/style_preset", TemplateContractRejectionReason.POLICY_INVALID)
    projection = _preset_data(value); projection.pop("preset_hash")
    if value.preset_hash != _hash(projection):
        _reject("/style_preset", TemplateContractRejectionReason.IDENTITY_MISMATCH)


def core_neutral_style_preset() -> TemplateStylePresetV1:
    projection = {"preset_id": "core-neutral-v1", "color_theme_id": "core-neutral", "typography_id": "phase5-noto-sans-v1", "font_asset_hash": PHASE5_FONT_ASSET_HASH_V1, "tone_id": "editorial-neutral", "policy_snapshot_id": None, "policy_snapshot_hash": None}
    return TemplateStylePresetV1(**(projection | {"preset_hash": _hash(projection)}))


def _invocation_data(value: TemplateInvocationV1) -> dict[str, Any]:
    return {
        "template_id": value.template_id.value, "template_version": value.template_version,
        "editorial_role": value.editorial_role, "start_frame": value.start_frame,
        "end_exclusive_frame": value.end_exclusive_frame, "layout": _rect_data(value.layout),
        "source_event_id": value.source_event_id, "target_region": None if value.target_region is None else _rect_data(value.target_region),
        "entry_animation": value.entry_animation, "exit_animation": value.exit_animation,
        "camera_motion": value.camera_motion, "caption": value.caption, "source_label": value.source_label,
        "style_preset_id": value.style_preset_id, "payload": dict(value.payload),
        "word_binding": None if value.word_binding is None else {field: getattr(value.word_binding, field) for field in WordBindingV1.__dataclass_fields__},
        "safe_area_policy": value.safe_area_policy,
    }


def _validate_invocation(value: TemplateInvocationV1, props: RenderProps, word_to_frame: WordToFrameArtifact, preset: TemplateStylePresetV1, index: int) -> None:
    pointer = f"/invocations/{index}"
    if type(value) is not TemplateInvocationV1 or value.template_id not in _DEFINITION_BY_ID or value.template_version != TEMPLATE_VERSION_V1 or not _plain_string(value.editorial_role):
        _reject(pointer, TemplateContractRejectionReason.STRUCTURE_INVALID)
    definition = _DEFINITION_BY_ID[value.template_id]
    if value.editorial_role not in definition.supported_editorial_roles or value.safe_area_policy != SAFE_AREA_POLICY_V1 or value.style_preset_id != preset.preset_id:
        _reject(pointer, TemplateContractRejectionReason.DEFINITION_MISMATCH)
    if type(value.start_frame) is not int or type(value.end_exclusive_frame) is not int or not 0 <= value.start_frame < value.end_exclusive_frame <= props.duration_frames:
        _reject(pointer, TemplateContractRejectionReason.DEPENDENCY_BINDING_INVALID)
    if not _rect_inside(value.layout, SUBTITLE_SAFE_AREA_V1 if definition.kind is TemplateKind.KINETIC else CONTENT_SAFE_AREA_V1):
        _reject(pointer + "/layout", TemplateContractRejectionReason.SAFE_AREA_INVALID)
    if value.target_region is not None:
        if not definition.supports_target_region or not _rect_inside(value.target_region, CONTENT_SAFE_AREA_V1):
            _reject(pointer + "/target_region", TemplateContractRejectionReason.SAFE_AREA_INVALID)
    binding_events = {row["event_id"] for row in props.asset_bindings}
    if definition.requires_source_asset:
        if value.source_event_id not in binding_events:
            _reject(pointer + "/source_event_id", TemplateContractRejectionReason.SOURCE_BINDING_INVALID)
    elif value.source_event_id is not None:
        _reject(pointer + "/source_event_id", TemplateContractRejectionReason.SOURCE_BINDING_INVALID)
    if (value.caption is not None and not definition.supports_caption) or (value.source_label is not None and not definition.supports_source_label):
        _reject(pointer, TemplateContractRejectionReason.DEFINITION_MISMATCH)
    if any(item is not None and not _plain_string(item) for item in (value.caption, value.source_label)) or not all(_plain_string(item) for item in (value.entry_animation, value.exit_animation, value.camera_motion)):
        _reject(pointer, TemplateContractRejectionReason.STRUCTURE_INVALID)
    _validate_payload(definition.payload_kind, value.payload, pointer + "/payload")
    if definition.supports_word_binding:
        binding = value.word_binding
        if type(binding) is not WordBindingV1:
            _reject(pointer + "/word_binding", TemplateContractRejectionReason.WORD_BINDING_INVALID)
        if (binding.narration_revision_id, binding.word_to_frame_id, binding.word_to_frame_hash) != (props.narration_revision_id, word_to_frame.word_to_frame_id, word_to_frame.word_to_frame_hash):
            _reject(pointer + "/word_binding", TemplateContractRejectionReason.WORD_BINDING_INVALID)
        start_matches = [span for span in word_to_frame.word_frames if span.start_word_id == binding.start_word_id]
        end_matches = [span for span in word_to_frame.word_frames if span.end_word_id == binding.end_word_id]
        if len(start_matches) != 1 or len(end_matches) != 1 or (binding.start_frame, binding.end_exclusive_frame) != (start_matches[0].start_frame, end_matches[0].end_exclusive_frame) or start_matches[0].ordinal > end_matches[0].ordinal or not binding.start_frame < binding.end_exclusive_frame:
            _reject(pointer + "/word_binding", TemplateContractRejectionReason.WORD_BINDING_INVALID)
    elif value.word_binding is not None:
        _reject(pointer + "/word_binding", TemplateContractRejectionReason.WORD_BINDING_INVALID)


def _plan_data(value: TemplateRenderPlanV1, *, identity: bool) -> dict[str, Any]:
    result = {"schema_version": value.schema_version, "template_plan_id": value.template_plan_id, "template_plan_hash": value.template_plan_hash, "render_request_id": value.render_request_id, "render_props_hash": value.render_props_hash, "word_to_frame_id": value.word_to_frame_id, "word_to_frame_hash": value.word_to_frame_hash, "style_preset": _preset_data(value.style_preset), "invocations": [_invocation_data(item) for item in value.invocations]}
    if identity:
        result.pop("template_plan_id"); result.pop("template_plan_hash")
    return result


def compile_template_render_plan(*, render_props: RenderProps, word_to_frame_artifact: WordToFrameArtifact, invocations: tuple[TemplateInvocationV1, ...], style_preset: TemplateStylePresetV1 | None = None) -> TemplateRenderPlanV1:
    props = load_render_props(serialize_render_props(render_props))
    # serialize is a canonical-materialization revalidation boundary; callers
    # cannot substitute a merely similar WordToFrame dataclass.
    word_bytes = serialize_word_to_frame(word_to_frame_artifact)
    if not word_bytes:
        _reject("/word_to_frame_artifact", TemplateContractRejectionReason.DEPENDENCY_BINDING_INVALID)
    word = word_to_frame_artifact
    if (props.word_to_frame_id, props.word_to_frame_hash, props.narration_revision_id, props.fps_numerator, props.fps_denominator) != (word.word_to_frame_id, word.word_to_frame_hash, word.narration_revision_id, word.frame_rate.numerator, word.frame_rate.denominator):
        _reject("/word_to_frame_artifact", TemplateContractRejectionReason.DEPENDENCY_BINDING_INVALID)
    preset = core_neutral_style_preset() if style_preset is None else style_preset
    _validate_preset(preset)
    if type(invocations) is not tuple or not invocations:
        _reject("/invocations", TemplateContractRejectionReason.STRUCTURE_INVALID)
    for index, invocation in enumerate(invocations):
        _validate_invocation(invocation, props, word, preset, index)
        if index >= 2 and invocations[index - 2].template_id is invocation.template_id and invocations[index - 1].template_id is invocation.template_id:
            _reject(f"/invocations/{index}", TemplateContractRejectionReason.CONSECUTIVE_TEMPLATE_LIMIT)
    base = TemplateRenderPlanV1(TEMPLATE_RENDER_PLAN_V1, "", "", props.render_request_id, props.render_props_hash, word.word_to_frame_id, word.word_to_frame_hash, preset, invocations)
    digest = _hash(_plan_data(base, identity=True))
    return TemplateRenderPlanV1(**(base.__dict__ | {"template_plan_hash": digest, "template_plan_id": "tmplplan_" + digest[7:39]}))


def compile_template_render_plan_from_canonical(
    value: TemplateCompilationInputV1,
) -> TemplateRenderPlanV1:
    """Compile only after both upstream byte envelopes pass their loaders."""
    if type(value) is not TemplateCompilationInputV1:
        raise TypeError("value must be exact TemplateCompilationInputV1")
    props = load_render_props(value.render_props_bytes)
    word = load_word_to_frame(
        value.word_to_frame_bytes,
        alignment_result=value.alignment_result,
        caption_groups=value.caption_groups,
        emphasis_events=value.emphasis_events,
        frame_rate=value.frame_rate,
    )
    return compile_template_render_plan(
        render_props=props,
        word_to_frame_artifact=word,
        invocations=value.invocations,
        style_preset=value.style_preset,
    )


def serialize_template_render_plan(value: TemplateRenderPlanV1, *, render_props: RenderProps, word_to_frame_artifact: WordToFrameArtifact) -> bytes:
    expected = compile_template_render_plan(render_props=render_props, word_to_frame_artifact=word_to_frame_artifact, invocations=value.invocations, style_preset=value.style_preset)
    if value != expected:
        _reject("/", TemplateContractRejectionReason.IDENTITY_MISMATCH)
    return encode_canonical_json_bytes(_plan_data(expected, identity=False))


def load_template_render_plan(source: bytes, *, render_props: RenderProps, word_to_frame_artifact: WordToFrameArtifact) -> TemplateRenderPlanV1:
    if type(source) is not bytes or source.startswith(b"\xef\xbb\xbf"):
        _reject("/", TemplateContractRejectionReason.NON_CANONICAL_SERIALIZATION)
    try:
        data = json.loads(source.decode("utf-8"))
    except Exception:
        _reject("/", TemplateContractRejectionReason.NON_CANONICAL_SERIALIZATION)
    if type(data) is not dict or set(data) != set(TemplateRenderPlanV1.__dataclass_fields__):
        _reject("/", TemplateContractRejectionReason.STRUCTURE_INVALID)
    # This parser intentionally accepts only bytes emitted by this module; it
    # avoids a loose dict-to-plan ingress at the renderer boundary.
    expected = compile_template_render_plan(render_props=render_props, word_to_frame_artifact=word_to_frame_artifact, invocations=tuple(_invocation_from_data(item) for item in data.get("invocations", [])), style_preset=_preset_from_data(data.get("style_preset")))
    if data != _plan_data(expected, identity=False) or encode_canonical_json_bytes(data) != source:
        _reject("/", TemplateContractRejectionReason.NON_CANONICAL_SERIALIZATION)
    return expected


def _rect_from_data(value: Any) -> TemplateRectV1:
    if type(value) is not dict or set(value) != set(TemplateRectV1.__dataclass_fields__):
        _reject("/", TemplateContractRejectionReason.STRUCTURE_INVALID)
    return TemplateRectV1(**value)


def _preset_from_data(value: Any) -> TemplateStylePresetV1:
    if type(value) is not dict or set(value) != set(TemplateStylePresetV1.__dataclass_fields__):
        _reject("/style_preset", TemplateContractRejectionReason.STRUCTURE_INVALID)
    return TemplateStylePresetV1(**value)


def _invocation_from_data(value: Any) -> TemplateInvocationV1:
    if type(value) is not dict or set(value) != set(TemplateInvocationV1.__dataclass_fields__):
        _reject("/invocations", TemplateContractRejectionReason.STRUCTURE_INVALID)
    try:
        binding_data = value["word_binding"]
        return TemplateInvocationV1(**(value | {"template_id": TemplateId(value["template_id"]), "layout": _rect_from_data(value["layout"]), "target_region": None if value["target_region"] is None else _rect_from_data(value["target_region"]), "word_binding": None if binding_data is None else WordBindingV1(**binding_data)}))
    except (TypeError, ValueError):
        _reject("/invocations", TemplateContractRejectionReason.STRUCTURE_INVALID)


def build_template_render_input(*, render_props: RenderProps, template_render_plan: TemplateRenderPlanV1, word_to_frame_artifact: WordToFrameArtifact) -> TemplateRenderInputV1:
    plan_bytes = serialize_template_render_plan(template_render_plan, render_props=render_props, word_to_frame_artifact=word_to_frame_artifact)
    plan = load_template_render_plan(plan_bytes, render_props=render_props, word_to_frame_artifact=word_to_frame_artifact)
    props = load_render_props(serialize_render_props(render_props))
    serialize_word_to_frame(word_to_frame_artifact)
    base = {"schema_version": TEMPLATE_RENDER_INPUT_V1, "render_props": json.loads(serialize_render_props(props)), "template_render_plan": json.loads(plan_bytes), "word_to_frame_artifact": json.loads(serialize_word_to_frame(word_to_frame_artifact)), "template_input_id": "", "template_input_hash": ""}
    digest = _hash({key: value for key, value in base.items() if key not in {"template_input_id", "template_input_hash"}})
    return TemplateRenderInputV1(TEMPLATE_RENDER_INPUT_V1, props, plan, word_to_frame_artifact, "tmplinput_" + digest[7:39], digest)


def serialize_template_render_input(value: TemplateRenderInputV1) -> bytes:
    if type(value) is not TemplateRenderInputV1:
        raise TypeError("value must be exact TemplateRenderInputV1")
    expected = build_template_render_input(render_props=value.render_props, template_render_plan=value.template_render_plan, word_to_frame_artifact=value.word_to_frame_artifact)
    if value != expected:
        _reject("/", TemplateContractRejectionReason.IDENTITY_MISMATCH)
    return encode_canonical_json_bytes({"schema_version": value.schema_version, "render_props": json.loads(serialize_render_props(value.render_props)), "template_render_plan": json.loads(serialize_template_render_plan(value.template_render_plan, render_props=value.render_props, word_to_frame_artifact=value.word_to_frame_artifact)), "word_to_frame_artifact": json.loads(serialize_word_to_frame(value.word_to_frame_artifact)), "template_input_id": value.template_input_id, "template_input_hash": value.template_input_hash})


def template_policy_from_policy_snapshot(snapshot: DomainPolicySnapshot) -> TemplatePolicyV1:
    """Extract only the manifest-resolved visual template policy bundle."""
    if type(snapshot) is not DomainPolicySnapshot:
        raise TypeError("snapshot must be exact DomainPolicySnapshot")
    snapshot_data = {field: getattr(snapshot, field) for field in DomainPolicySnapshot.__dataclass_fields__}
    if not snapshot.immutable or snapshot.canonical_hash != policy_snapshot_hash(snapshot_data):
        _reject("/policy_snapshot", TemplateContractRejectionReason.POLICY_INVALID)
    resolved = snapshot.resolved_policy
    if type(resolved) is not dict or set(resolved) != {"policy_bundles", "extensions", "enabled_extensions", "overrides"} or type(resolved["policy_bundles"]) is not list:
        _reject("/policy_snapshot", TemplateContractRejectionReason.POLICY_INVALID)
    policies = []
    for bundle in resolved["policy_bundles"]:
        if type(bundle) is not dict or set(bundle) != {"ref", "policy"} or type(bundle["ref"]) is not str or type(bundle["policy"]) is not dict:
            _reject("/policy_snapshot", TemplateContractRejectionReason.POLICY_INVALID)
        visual = bundle["policy"].get("visual")
        if type(visual) is dict and "template_policy" in visual:
            policies.append(visual["template_policy"])
    if len(policies) != 1 or type(policies[0]) is not dict:
        _reject("/policy_snapshot", TemplateContractRejectionReason.POLICY_INVALID)
    policy = policies[0]
    required = {"preferred_template_ids", "banned_template_ids", "required_template_ids", "style_preset"}
    if set(policy) != required or type(policy["style_preset"]) is not dict:
        _reject("/policy_snapshot", TemplateContractRejectionReason.POLICY_INVALID)
    for key in ("preferred_template_ids", "banned_template_ids", "required_template_ids"):
        values = policy[key]
        if type(values) is not list or len(values) != len(set(values)) or any(type(item) is not str or item not in {member.value for member in TemplateId} for item in values):
            _reject("/policy_snapshot", TemplateContractRejectionReason.POLICY_INVALID)
    if set(policy["preferred_template_ids"]) & set(policy["banned_template_ids"]):
        _reject("/policy_snapshot", TemplateContractRejectionReason.POLICY_INVALID)
    raw = policy["style_preset"]
    if set(raw) != {"preset_id", "color_theme_id", "typography_id", "font_asset_hash", "tone_id"} or not all(_plain_string(raw[key]) for key in ("preset_id", "color_theme_id", "typography_id", "tone_id")) or raw["font_asset_hash"] != PHASE5_FONT_ASSET_HASH_V1:
        _reject("/policy_snapshot", TemplateContractRejectionReason.POLICY_INVALID)
    projection = raw | {"policy_snapshot_id": snapshot.snapshot_id, "policy_snapshot_hash": snapshot.canonical_hash}
    preset = TemplateStylePresetV1(**(projection | {"preset_hash": _hash(projection)}))
    _validate_preset(preset)
    return TemplatePolicyV1(
        preferred_template_ids=tuple(TemplateId(item) for item in policy["preferred_template_ids"]),
        banned_template_ids=tuple(TemplateId(item) for item in policy["banned_template_ids"]),
        required_template_ids=tuple(TemplateId(item) for item in policy["required_template_ids"]),
        style_preset=preset,
    )


def style_preset_from_policy_snapshot(snapshot: DomainPolicySnapshot) -> TemplateStylePresetV1:
    return template_policy_from_policy_snapshot(snapshot).style_preset
