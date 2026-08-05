"""Fail-closed Phase 7 visualization core.

No network, asset catalog, scheduler mutation, or Phase 4 props mutation lives
here.  The renderer output is a deterministic diagnostic SVG and a hash-bound
receipt so numeric/evidence assertions precede later media integration.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, fields, is_dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping

from engine.acquisition import EvidenceTreatmentPlanner, SourceCapturePlan
from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.domain import policy_snapshot_hash
from engine.contracts.edl import VideoEdlArtifact, serialize_video_edl
from engine.contracts.models import DomainPolicySnapshot
from engine.contracts.word_to_frame import WordToFrameArtifact, serialize_word_to_frame
from engine.rendering.bridge import RenderProps, serialize_render_props
from engine.rendering.visual_directives import validate_directive

VISUALIZATION_ARTIFACT_V1 = "VISUALIZATION-ARTIFACT-V1"
VISUALIZATION_RENDER_PLAN_V1 = "VISUALIZATION-RENDER-PLAN-V1"
VISUALIZATION_METADATA_V1 = "RENDERED-VISUALIZATION-METADATA-V1"
VISUALIZATION_RECEIPT_V1 = "VISUALIZATION-RENDER-RECEIPT-V1"
VISUALIZATION_POLICY_V1 = "VISUALIZATION-POLICY-V1"
_ID = re.compile(r"^[a-z][a-z0-9_]{0,127}$")
_LEXEME = re.compile(r"^-?(0|[1-9][0-9]*)(?:\.[0-9]{1,12})?$")
_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")


class VisualizationKind(str, Enum):
    CHART = "chart"; METRIC = "metric"; TIMELINE = "timeline"
    RELATIONSHIP_GRAPH = "relationship_graph"; EVIDENCE_CHAIN = "evidence_chain"; MAP = "map"


class VisualizationUnitKind(str, Enum):
    CURRENCY = "currency"; PERCENT = "percent"; COUNT = "count"; RATIO = "ratio"; CUSTOM = "custom"


class VisualizationStageKind(str, Enum):
    AXIS_REVEAL = "axis_reveal"; LABEL_REVEAL = "label_reveal"; LINE_DRAW = "line_draw"; BAR_GROW = "bar_grow"
    VALUE_CALLOUT = "value_callout"; BEFORE_AFTER = "before_after"; SERIES_FOCUS = "series_focus"
    METRIC_COUNT = "metric_count"; EQUATION_MORPH = "equation_morph"


CHART_KINDS = frozenset({"line", "bar", "area", "stacked", "comparison", "waterfall", "timeline"})
RECEIPT_FAILURE_CODES = frozenset({"UPSTREAM_BINDING_INVALID", "RENDER_PLAN_INVALID", "REPLAY_FRAME_INVALID", "SOURCE_CAPTION_CAPTURE_MISSING", "SOURCE_CAPTION_CAPTURE_FORGED"})
_FIXED_EDGES = {
    VisualizationKind.TIMELINE: frozenset({"chronological"}),
    VisualizationKind.EVIDENCE_CHAIN: frozenset({"supports", "qualifies", "contradicts"}),
    VisualizationKind.MAP: frozenset({"adjacent", "contains", "flows_to"}),
}


class VisualizationContractError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code); self.code = code


def _fail(code: str) -> None: raise VisualizationContractError(code)
def _hash(value: Any) -> str: return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()
def _id(value: Any) -> bool: return type(value) is str and _ID.fullmatch(value) is not None
def _text(value: Any) -> bool: return type(value) is str and bool(value) and value == value.strip()


@dataclass(frozen=True)
class ExactDecimalV1:
    coefficient: int
    scale: int

    @classmethod
    def from_lexeme(cls, value: str) -> "ExactDecimalV1":
        if type(value) is not str or _LEXEME.fullmatch(value) is None: _fail("NUMERIC_LEXEME_INVALID")
        sign = -1 if value.startswith("-") else 1; raw = value.removeprefix("-")
        whole, dot, fraction = raw.partition(".")
        coefficient = sign * int(whole + fraction); scale = len(fraction) if dot else 0
        while coefficient and scale > 0 and coefficient % 10 == 0: coefficient //= 10; scale -= 1
        return cls(coefficient, scale)

    def validate(self) -> None:
        if type(self.coefficient) is not int or type(self.scale) is not int or not 0 <= self.scale <= 12: _fail("EXACT_DECIMAL_INVALID")
        if (self.coefficient == 0 and self.scale != 0) or (self.coefficient != 0 and self.scale > 0 and self.coefficient % 10 == 0): _fail("EXACT_DECIMAL_NONCANONICAL")

    def text(self) -> str:
        self.validate(); sign = "-" if self.coefficient < 0 else ""; digits = str(abs(self.coefficient))
        if self.scale == 0: return sign + digits
        return sign + ("0." + "0" * (self.scale - len(digits)) + digits if len(digits) <= self.scale else digits[:-self.scale] + "." + digits[-self.scale:])


@dataclass(frozen=True)
class PeriodV1:
    period_id: str; ordinal: int; label: str; kind: str = "instant"; start_label: str | None = None; end_label: str | None = None

    def validate(self) -> None:
        if not _id(self.period_id) or type(self.ordinal) is not int or self.ordinal < 1 or not _text(self.label) or self.kind not in {"instant", "interval"}: _fail("PERIOD_INVALID")
        if self.kind == "instant" and (self.start_label is not None or self.end_label is not None): _fail("PERIOD_INVALID")
        if self.kind == "interval" and (not _text(self.start_label) or not _text(self.end_label)): _fail("PERIOD_INVALID")


@dataclass(frozen=True)
class SourceCaptureEvidenceBindingV1:
    source_capture_plan_id: str; source_capture_plan_hash: str; source_package_hash: str
    region_dom_path: str; evidence_text: str; numeric_lexeme: str; unit_lexeme: str; period_lexeme: str


@dataclass(frozen=True)
class SourceCaptionV1:
    source_caption_id: str; source_caption_hash: str; item_id: str
    source_capture_plan_id: str; source_capture_plan_hash: str; source_package_hash: str
    source_label: str; publication_date: str; region_dom_path: str


@dataclass(frozen=True)
class SourceCaptionCollectionV1:
    source_caption_collection_id: str; source_caption_collection_hash: str
    captions: tuple[SourceCaptionV1, ...]


@dataclass(frozen=True)
class VisualizationItemV1:
    item_id: str; kind: VisualizationKind; label: str; payload: Mapping[str, Any]
    source_caption_id: str | None = None


@dataclass(frozen=True)
class VisualizationPolicyV1:
    allowed_kinds: tuple[VisualizationKind, ...]; allowed_chart_kinds: tuple[str, ...]
    banned_chart_kinds: tuple[str, ...]; preferred_chart_kinds: tuple[str, ...]
    count_unit_labels: tuple[str, ...]; custom_unit_labels: tuple[str, ...]
    allowed_relationship_edge_kinds: tuple[str, ...]; theme_id: str
    policy_snapshot_id: str; policy_snapshot_hash: str


@dataclass(frozen=True)
class VisualizationArtifactV1:
    schema_version: str; visualization_id: str; visualization_hash: str; title: str; editorial_role: str
    policy: VisualizationPolicyV1; source_captions: SourceCaptionCollectionV1; items: tuple[VisualizationItemV1, ...]


@dataclass(frozen=True)
class VisualizationEdlBindingV1:
    video_edl_id: str; video_edl_hash: str; v4_event_id: str; v4_event_hash: str
    v4_directive_id: str; v4_directive_hash: str; local_start_frame: int; local_end_exclusive_frame: int


@dataclass(frozen=True)
class VisualizationFrameBindingV1:
    word_to_frame_id: str; word_to_frame_hash: str; sequence_start_frame: int
    start_word_id: str; end_word_id: str; global_start_frame: int; global_end_exclusive_frame: int; local_start_frame: int; local_end_exclusive_frame: int


@dataclass(frozen=True)
class VisualizationStageV1:
    stage_id: str; kind: VisualizationStageKind; target_ids: tuple[str, ...]; frame_binding: VisualizationFrameBindingV1; ordinal: int


@dataclass(frozen=True)
class VisualizationRenderPlanV1:
    schema_version: str; render_plan_id: str; render_plan_hash: str; visualization_id: str; visualization_hash: str
    render_props_id: str; render_props_hash: str; edl_binding: VisualizationEdlBindingV1; stages: tuple[VisualizationStageV1, ...]


@dataclass(frozen=True)
class RenderedVisualizationMetadataV1:
    metadata_id: str; metadata_hash: str; visualization_id: str; visualization_hash: str; render_plan_id: str; render_plan_hash: str
    rendered_elements: tuple[tuple[str, str, str], ...]; rendered_stage_ids: tuple[str, ...]
    source_caption_collection_id: str; source_caption_collection_hash: str; source_caption_ids: tuple[str, ...]
    rendered_values_hash: str; rendered_svg_hash: str; rendered_output_media_type: str
    width: int; height: int; local_start_frame: int; local_end_exclusive_frame: int


@dataclass(frozen=True)
class VisualizationRenderReceiptV1:
    receipt_id: str; receipt_hash: str; artifact_type: str; dependencies: tuple[tuple[str, str], ...]
    status: str; metadata_hash: str | None; svg_hash: str | None; rejection_code: str | None


def _policy_data(value: VisualizationPolicyV1) -> dict[str, Any]:
    return {"allowed_kinds": [item.value for item in value.allowed_kinds], "allowed_chart_kinds": list(value.allowed_chart_kinds), "banned_chart_kinds": list(value.banned_chart_kinds), "preferred_chart_kinds": list(value.preferred_chart_kinds), "count_unit_labels": list(value.count_unit_labels), "custom_unit_labels": list(value.custom_unit_labels), "allowed_relationship_edge_kinds": list(value.allowed_relationship_edge_kinds), "theme_id": value.theme_id, "policy_snapshot_id": value.policy_snapshot_id, "policy_snapshot_hash": value.policy_snapshot_hash}


def visualization_policy_from_snapshot(snapshot: DomainPolicySnapshot) -> VisualizationPolicyV1:
    if type(snapshot) is not DomainPolicySnapshot: _fail("POLICY_SNAPSHOT_INVALID")
    raw_snapshot = {field: getattr(snapshot, field) for field in snapshot.__dataclass_fields__}
    if not snapshot.immutable or snapshot.canonical_hash != policy_snapshot_hash(raw_snapshot): _fail("POLICY_SNAPSHOT_INVALID")
    matches = []
    resolved = snapshot.resolved_policy
    for bundle in resolved.get("policy_bundles", []) if type(resolved) is dict else []:
        policy = bundle.get("policy") if type(bundle) is dict else None; visual = policy.get("visual") if type(policy) is dict else None
        if type(visual) is dict and "visualization_policy" in visual: matches.append(visual["visualization_policy"])
    if len(matches) != 1 or type(matches[0]) is not dict: _fail("VISUALIZATION_POLICY_MISSING")
    data = matches[0]; required = {"policy_version", "allowed_kinds", "allowed_chart_kinds", "banned_chart_kinds", "preferred_chart_kinds", "required_evidence_binding_kinds", "count_unit_labels", "custom_unit_labels", "allowed_relationship_edge_kinds", "theme_id"}
    if set(data) != required or data["policy_version"] != VISUALIZATION_POLICY_V1 or data["required_evidence_binding_kinds"] != ["source_capture_region"]: _fail("VISUALIZATION_POLICY_INVALID")
    try:
        kinds = tuple(VisualizationKind(item) for item in data["allowed_kinds"])
    except (TypeError, ValueError): _fail("VISUALIZATION_POLICY_INVALID")
    lists = (data["allowed_chart_kinds"], data["banned_chart_kinds"], data["preferred_chart_kinds"], data["count_unit_labels"], data["custom_unit_labels"], data["allowed_relationship_edge_kinds"])
    if not kinds or len(set(kinds)) != len(kinds) or any(type(rows) is not list or len(rows) != len(set(rows)) or any(not _text(x) for x in rows) for rows in lists) or not set(data["allowed_chart_kinds"]).issubset(CHART_KINDS) or not set(data["banned_chart_kinds"]).issubset(CHART_KINDS) or set(data["allowed_chart_kinds"]) & set(data["banned_chart_kinds"]) or not set(data["preferred_chart_kinds"]).issubset(data["allowed_chart_kinds"]) or not _text(data["theme_id"]): _fail("VISUALIZATION_POLICY_INVALID")
    return VisualizationPolicyV1(kinds, tuple(data["allowed_chart_kinds"]), tuple(data["banned_chart_kinds"]), tuple(data["preferred_chart_kinds"]), tuple(data["count_unit_labels"]), tuple(data["custom_unit_labels"]), tuple(data["allowed_relationship_edge_kinds"]), data["theme_id"], snapshot.snapshot_id, snapshot.canonical_hash)


def _period_data(value: PeriodV1) -> dict[str, Any]: return {field: getattr(value, field) for field in value.__dataclass_fields__}
def _decimal_data(value: ExactDecimalV1) -> dict[str, int]: value.validate(); return {"coefficient": value.coefficient, "scale": value.scale}
def _evidence_data(value: SourceCaptureEvidenceBindingV1) -> dict[str, str]: return {field: getattr(value, field) for field in value.__dataclass_fields__}
def _caption_data(value: SourceCaptionV1, *, identity: bool) -> dict[str, str]:
    result = {field: getattr(value, field) for field in value.__dataclass_fields__}
    if identity: result.pop("source_caption_id"); result.pop("source_caption_hash")
    return result
def _caption_collection_data(value: SourceCaptionCollectionV1, *, identity: bool) -> dict[str, Any]:
    result = {"source_caption_collection_id": value.source_caption_collection_id, "source_caption_collection_hash": value.source_caption_collection_hash, "captions": [_caption_data(item, identity=False) for item in value.captions]}
    if identity: result.pop("source_caption_collection_id"); result.pop("source_caption_collection_hash")
    return result
def _plain(value: Any) -> Any:
    if isinstance(value, Enum): return value.value
    if is_dataclass(value): return {field.name: _plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping): return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)): return [_plain(item) for item in value]
    return value
def _item_data(value: VisualizationItemV1) -> dict[str, Any]: return {"item_id": value.item_id, "kind": value.kind.value, "label": value.label, "payload": _plain(value.payload), "source_caption_id": value.source_caption_id}
def _artifact_data(value: VisualizationArtifactV1, *, identity: bool) -> dict[str, Any]:
    result = {"schema_version": value.schema_version, "visualization_id": value.visualization_id, "visualization_hash": value.visualization_hash, "title": value.title, "editorial_role": value.editorial_role, "policy": _policy_data(value.policy), "source_captions": _caption_collection_data(value.source_captions, identity=False), "items": [_item_data(item) for item in value.items]}
    if identity: result.pop("visualization_id"); result.pop("visualization_hash")
    return result


def _validate_evidence(value: Any, *, capture_plans: Mapping[str, SourceCapturePlan], decimal: ExactDecimalV1, unit: VisualizationUnitKind, currency: str | None, period: PeriodV1, policy: VisualizationPolicyV1) -> None:
    if type(value) is not SourceCaptureEvidenceBindingV1 or not all(_text(getattr(value, name)) for name in value.__dataclass_fields__): _fail("EVIDENCE_BINDING_INVALID")
    try: capture = capture_plans[value.source_capture_plan_id]
    except KeyError: _fail("EVIDENCE_CAPTURE_MISSING")
    if type(capture) is not SourceCapturePlan or (capture.source_capture_plan_id, capture.source_capture_plan_hash, capture.source_package_hash) != (value.source_capture_plan_id, value.source_capture_plan_hash, value.source_package_hash): _fail("EVIDENCE_CAPTURE_FORGED")
    try: EvidenceTreatmentPlanner().plan(capture)
    except Exception: _fail("EVIDENCE_CAPTURE_UNUSABLE")
    regions = {region.dom_path: region.text for region in capture.crop_regions}
    if regions.get(value.region_dom_path) != value.evidence_text or value.evidence_text.count(value.numeric_lexeme) != 1 or ExactDecimalV1.from_lexeme(value.numeric_lexeme) != decimal: _fail("EVIDENCE_NUMERIC_MISMATCH")
    expected_unit = currency if unit is VisualizationUnitKind.CURRENCY else "%" if unit is VisualizationUnitKind.PERCENT else "ratio" if unit is VisualizationUnitKind.RATIO else None
    if expected_unit is None: allowed = policy.count_unit_labels if unit is VisualizationUnitKind.COUNT else policy.custom_unit_labels; expected_unit = value.unit_lexeme if value.unit_lexeme in allowed else None
    if expected_unit != value.unit_lexeme or value.evidence_text.count(value.unit_lexeme) != 1: _fail("EVIDENCE_UNIT_MISMATCH")
    valid_periods = {period.label} | ({period.start_label, period.end_label} if period.kind == "interval" else set())
    if value.period_lexeme not in valid_periods or value.evidence_text.count(value.period_lexeme) != 1: _fail("EVIDENCE_PERIOD_MISMATCH")


def _validate_point(row: Any, *, policy: VisualizationPolicyV1, capture_plans: Mapping[str, SourceCapturePlan], unit: VisualizationUnitKind, currency: str | None, ordinal: int) -> None:
    if type(row) is not dict or set(row) != {"point_id", "value", "period", "evidence"} or not _id(row["point_id"]) or type(row["value"]) is not ExactDecimalV1 or type(row["period"]) is not PeriodV1 or type(row["evidence"]) is not tuple or not row["evidence"]: _fail("DATAPOINT_INVALID")
    row["period"].validate()
    row["value"].validate()
    if row["period"].ordinal != ordinal: _fail("PERIOD_ORDER_INVALID")
    for evidence in row["evidence"]: _validate_evidence(evidence, capture_plans=capture_plans, decimal=row["value"], unit=unit, currency=currency, period=row["period"], policy=policy)


def _validate_unit(unit: Any, currency: Any) -> None:
    if type(unit) is not VisualizationUnitKind or (unit is VisualizationUnitKind.CURRENCY and not (type(currency) is str and re.fullmatch(r"[A-Z]{3}", currency) is not None)) or (unit is not VisualizationUnitKind.CURRENCY and currency is not None): _fail("UNIT_INVALID")


def _validate_item(item: VisualizationItemV1, *, all_items: tuple[VisualizationItemV1, ...], policy: VisualizationPolicyV1, capture_plans: Mapping[str, SourceCapturePlan]) -> None:
    if type(item) is not VisualizationItemV1 or not _id(item.item_id) or not _text(item.label) or item.kind not in policy.allowed_kinds or type(item.payload) is not dict: _fail("VISUALIZATION_ITEM_INVALID")
    if item.kind is VisualizationKind.CHART:
        if set(item.payload) != {"chart_kind", "series"} or item.payload["chart_kind"] not in policy.allowed_chart_kinds or item.payload["chart_kind"] in policy.banned_chart_kinds or type(item.payload["series"]) is not tuple or not item.payload["series"]: _fail("CHART_INVALID")
        series_ids: set[str] = set()
        for series in item.payload["series"]:
            if type(series) is not dict or set(series) != {"series_id", "label", "unit", "currency", "datapoints"} or not _id(series["series_id"]) or series["series_id"] in series_ids or not _text(series["label"]) or type(series["datapoints"]) is not tuple or not series["datapoints"]: _fail("SERIES_INVALID")
            _validate_unit(series["unit"], series["currency"])
            series_ids.add(series["series_id"]); seen_points: set[str] = set()
            for ordinal, point in enumerate(series["datapoints"], 1): _validate_point(point, policy=policy, capture_plans=capture_plans, unit=series["unit"], currency=series["currency"], ordinal=ordinal); seen_points.add(point["point_id"])
            if len(seen_points) != len(series["datapoints"]): _fail("DATAPOINT_DUPLICATE")
    elif item.kind is VisualizationKind.METRIC:
        required = {"metric_id", "chart_context_id", "value", "unit", "currency", "period", "evidence"}
        if set(item.payload) != required or not _id(item.payload["metric_id"]) or not _id(item.payload["chart_context_id"]) or not any(row.item_id == item.payload["chart_context_id"] and row.kind is VisualizationKind.CHART for row in all_items): _fail("METRIC_CONTEXT_INVALID")
        _validate_unit(item.payload["unit"], item.payload["currency"])
        _validate_point({"point_id": item.payload["metric_id"], "value": item.payload["value"], "period": item.payload["period"], "evidence": item.payload["evidence"]}, policy=policy, capture_plans=capture_plans, unit=item.payload["unit"], currency=item.payload["currency"], ordinal=item.payload["period"].ordinal)
    else:
        if set(item.payload) != {"nodes", "edges"} or type(item.payload["nodes"]) is not tuple or type(item.payload["edges"]) is not tuple or not item.payload["nodes"]: _fail("TOPOLOGY_INVALID")
        nodes = item.payload["nodes"]; ids = []
        for ordinal, node in enumerate(nodes, 1):
            if type(node) is not dict or set(node) != {"node_id", "label", "value", "unit", "currency", "period", "evidence"} or not _id(node["node_id"]) or not _text(node["label"]): _fail("TOPOLOGY_NODE_INVALID")
            _validate_unit(node["unit"], node["currency"])
            _validate_point({"point_id": node["node_id"], "value": node["value"], "period": node["period"], "evidence": node["evidence"]}, policy=policy, capture_plans=capture_plans, unit=node["unit"], currency=node["currency"], ordinal=ordinal)
            ids.append(node["node_id"])
        if ids != sorted(ids) or len(set(ids)) != len(ids): _fail("TOPOLOGY_NODE_INVALID")
        allowed_edges = _FIXED_EDGES.get(item.kind, frozenset(policy.allowed_relationship_edge_kinds))
        edge_ids: set[str] = set(); adjacency: dict[str, set[str]] = {node_id: set() for node_id in ids}
        for ordinal, edge in enumerate(item.payload["edges"], 1):
            if type(edge) is not dict or set(edge) != {"edge_id", "edge_kind", "from_node_id", "to_node_id", "ordinal", "label"} or not _id(edge["edge_id"]) or edge["edge_kind"] not in allowed_edges or edge["from_node_id"] not in ids or edge["to_node_id"] not in ids or edge["from_node_id"] == edge["to_node_id"] or edge["ordinal"] != ordinal or (edge["label"] is not None and not _text(edge["label"])): _fail("TOPOLOGY_EDGE_INVALID")
            if edge["edge_id"] in edge_ids: _fail("TOPOLOGY_EDGE_INVALID")
            edge_ids.add(edge["edge_id"]); adjacency[edge["from_node_id"]].add(edge["to_node_id"])
        def cyclic(node_id: str, path: set[str], seen: set[str]) -> bool:
            if node_id in path: return True
            if node_id in seen: return False
            return any(cyclic(child, path | {node_id}, seen | {node_id}) for child in adjacency[node_id])
        if any(cyclic(node_id, set(), set()) for node_id in ids): _fail("TOPOLOGY_CYCLE_INVALID")


def _compile_source_caption(*, item: VisualizationItemV1, capture_plans: Mapping[str, SourceCapturePlan]) -> SourceCaptionV1:
    bindings = _find_bindings(item.payload)
    if not bindings: _fail("SOURCE_CAPTION_MISSING")
    binding = bindings[0]
    try: capture = capture_plans[binding.source_capture_plan_id]
    except KeyError: _fail("SOURCE_CAPTION_CAPTURE_MISSING")
    if type(capture) is not SourceCapturePlan or (capture.source_capture_plan_id, capture.source_capture_plan_hash, capture.source_package_hash) != (binding.source_capture_plan_id, binding.source_capture_plan_hash, binding.source_package_hash): _fail("SOURCE_CAPTION_CAPTURE_FORGED")
    base = SourceCaptionV1("", "", item.item_id, binding.source_capture_plan_id, binding.source_capture_plan_hash, binding.source_package_hash, capture.source_label, capture.publication_date, binding.region_dom_path)
    digest = _hash(_caption_data(base, identity=True))
    return replace(base, source_caption_id="cap_" + digest[7:39], source_caption_hash=digest)


def _compile_source_caption_collection(captions: tuple[SourceCaptionV1, ...]) -> SourceCaptionCollectionV1:
    if not captions or tuple(item.source_caption_id for item in captions) != tuple(sorted(item.source_caption_id for item in captions)) or len({item.source_caption_id for item in captions}) != len(captions): _fail("SOURCE_CAPTION_COLLECTION_INVALID")
    for item in captions:
        if item.source_caption_hash != _hash(_caption_data(item, identity=True)) or item.source_caption_id != "cap_" + item.source_caption_hash[7:39]: _fail("SOURCE_CAPTION_IDENTITY_INVALID")
    base = SourceCaptionCollectionV1("", "", captions); digest = _hash(_caption_collection_data(base, identity=True))
    return replace(base, source_caption_collection_id="capcol_" + digest[7:39], source_caption_collection_hash=digest)


def _validate_source_caption_collection(value: SourceCaptionCollectionV1, items: tuple[VisualizationItemV1, ...]) -> None:
    if type(value) is not SourceCaptionCollectionV1 or value.source_caption_collection_hash != _hash(_caption_collection_data(value, identity=True)) or value.source_caption_collection_id != "capcol_" + value.source_caption_collection_hash[7:39]: _fail("SOURCE_CAPTION_COLLECTION_INVALID")
    caption_ids = {item.source_caption_id for item in value.captions}
    if len(caption_ids) != len(value.captions) or any(item.source_caption_id not in caption_ids for item in items): _fail("SOURCE_CAPTION_COLLECTION_INVALID")


def compile_visualization_artifact(*, title: str, editorial_role: str, policy: VisualizationPolicyV1, items: tuple[VisualizationItemV1, ...], capture_plans: Mapping[str, SourceCapturePlan]) -> VisualizationArtifactV1:
    if not _text(title) or not _id(editorial_role) or type(policy) is not VisualizationPolicyV1 or type(items) is not tuple or not items: _fail("VISUALIZATION_ARTIFACT_INVALID")
    if len({item.item_id for item in items if type(item) is VisualizationItemV1}) != len(items): _fail("VISUALIZATION_ITEM_DUPLICATE")
    for item in items: _validate_item(item, all_items=items, policy=policy, capture_plans=capture_plans)
    captions_by_item = {item.item_id: _compile_source_caption(item=item, capture_plans=capture_plans) for item in items}
    compiled_items = tuple(replace(item, source_caption_id=captions_by_item[item.item_id].source_caption_id) if item.source_caption_id is None else item for item in items)
    if any(item.source_caption_id != captions_by_item[item.item_id].source_caption_id for item in compiled_items): _fail("SOURCE_CAPTION_REFERENCE_INVALID")
    captions = _compile_source_caption_collection(tuple(sorted(captions_by_item.values(), key=lambda item: item.source_caption_id)))
    _validate_source_caption_collection(captions, compiled_items)
    base = VisualizationArtifactV1(VISUALIZATION_ARTIFACT_V1, "", "", title, editorial_role, policy, captions, compiled_items); digest = _hash(_artifact_data(base, identity=True))
    return VisualizationArtifactV1(**(base.__dict__ | {"visualization_id": "viz_" + digest[7:39], "visualization_hash": digest}))


def serialize_visualization_artifact(value: VisualizationArtifactV1) -> bytes:
    if type(value) is not VisualizationArtifactV1 or value.schema_version != VISUALIZATION_ARTIFACT_V1 or value.visualization_hash != _hash(_artifact_data(value, identity=True)) or value.visualization_id != "viz_" + value.visualization_hash[7:39]: _fail("VISUALIZATION_IDENTITY_INVALID")
    _validate_source_caption_collection(value.source_captions, value.items)
    return encode_canonical_json_bytes(_artifact_data(value, identity=False))


def serialize_rendered_visualization_metadata(value: RenderedVisualizationMetadataV1) -> bytes:
    if type(value) is not RenderedVisualizationMetadataV1 or value.metadata_hash != _hash(_metadata_data(value, identity=True)) or value.metadata_id != "vizmeta_" + value.metadata_hash[7:39] or not _id(value.visualization_id) or not _HASH.fullmatch(value.visualization_hash) or not _id(value.render_plan_id) or not _HASH.fullmatch(value.render_plan_hash) or not _id(value.source_caption_collection_id) or not _HASH.fullmatch(value.source_caption_collection_hash) or not _HASH.fullmatch(value.rendered_values_hash) or not _HASH.fullmatch(value.rendered_svg_hash) or value.rendered_output_media_type not in {"image/svg+xml", "image/png"} or not (0 <= value.local_start_frame < value.local_end_exclusive_frame) or len(set(value.rendered_stage_ids)) != len(value.rendered_stage_ids) or len(set(value.source_caption_ids)) != len(value.source_caption_ids): _fail("RENDERED_METADATA_INVALID")
    return encode_canonical_json_bytes(_metadata_data(value, identity=False))


def validate_visualization_render_receipt(value: VisualizationRenderReceiptV1) -> None:
    prefixes = ("viz_", "vizplan_", "w2f_", "vedl_", "rprops_", "capcol_", "vizmeta_", "vizsvg_")
    if type(value) is not VisualizationRenderReceiptV1 or value.artifact_type != "visualization_render_receipt" or value.status not in {"SUCCESS", "FAILURE"} or len(value.dependencies) != 8 or len({item[0] for item in value.dependencies}) != 8 or any(type(item) is not tuple or len(item) != 2 or not _id(item[0]) or not _HASH.fullmatch(item[1]) for item in value.dependencies) or tuple(item[0].split("_", 1)[0] + "_" for item in value.dependencies) != prefixes or any(item[0] == value.receipt_id for item in value.dependencies): _fail("VISUALIZATION_RECEIPT_INVALID")
    if value.status == "SUCCESS":
        if value.metadata_hash is None or value.svg_hash is None or value.rejection_code is not None or not _HASH.fullmatch(value.metadata_hash) or not _HASH.fullmatch(value.svg_hash): _fail("VISUALIZATION_RECEIPT_INVALID")
    elif value.metadata_hash is not None or value.svg_hash is not None or value.rejection_code not in RECEIPT_FAILURE_CODES: _fail("VISUALIZATION_RECEIPT_INVALID")
    base = {"artifact_type": value.artifact_type, "dependencies": [list(dep) for dep in value.dependencies], "status": value.status, "metadata_hash": value.metadata_hash, "svg_hash": value.svg_hash, "rejection_code": value.rejection_code}
    if value.receipt_hash != _hash(base) or value.receipt_id != "vizrcpt_" + value.receipt_hash[7:39]: _fail("VISUALIZATION_RECEIPT_INVALID")


def _frame_data(value: VisualizationFrameBindingV1) -> dict[str, Any]: return {field: getattr(value, field) for field in value.__dataclass_fields__}
def _edl_data(value: VisualizationEdlBindingV1) -> dict[str, Any]: return {field: getattr(value, field) for field in value.__dataclass_fields__}
def _plan_data(value: VisualizationRenderPlanV1, *, identity: bool) -> dict[str, Any]:
    row = {field: getattr(value, field) for field in value.__dataclass_fields__}; row["edl_binding"] = _edl_data(value.edl_binding); row["stages"] = [{"stage_id": x.stage_id, "kind": x.kind.value, "target_ids": list(x.target_ids), "frame_binding": _frame_data(x.frame_binding), "ordinal": x.ordinal} for x in value.stages]
    if identity: row.pop("render_plan_id"); row.pop("render_plan_hash")
    return row


def _stage_targets(artifact: VisualizationArtifactV1) -> dict[str, VisualizationKind]:
    targets: dict[str, VisualizationKind] = {}
    for item in artifact.items:
        targets[item.item_id] = item.kind
        if item.kind is VisualizationKind.CHART:
            for series in item.payload["series"]:
                targets[series["series_id"]] = item.kind
                for point in series["datapoints"]: targets[point["point_id"]] = item.kind
        elif item.kind is VisualizationKind.METRIC: targets[item.payload["metric_id"]] = item.kind
        else:
            for node in item.payload["nodes"]: targets[node["node_id"]] = item.kind
            for edge in item.payload["edges"]: targets[edge["edge_id"]] = item.kind
    return targets


def _verified_edl_binding(*, video_edl: VideoEdlArtifact, word_to_frame: WordToFrameArtifact, render_props: RenderProps, v4_event_id: str) -> VisualizationEdlBindingV1:
    if type(video_edl) is not VideoEdlArtifact or type(word_to_frame) is not WordToFrameArtifact or type(render_props) is not RenderProps or not _id(v4_event_id): _fail("UPSTREAM_BINDING_INVALID")
    try: serialize_video_edl(video_edl); serialize_word_to_frame(word_to_frame); serialize_render_props(render_props)
    except Exception: _fail("UPSTREAM_NOT_MATERIALIZED")
    if (video_edl.word_to_frame_id, video_edl.word_to_frame_hash) != (word_to_frame.word_to_frame_id, word_to_frame.word_to_frame_hash) or (render_props.video_edl_id, render_props.video_edl_hash, render_props.word_to_frame_id, render_props.word_to_frame_hash) != (video_edl.video_edl_id, video_edl.video_edl_hash, word_to_frame.word_to_frame_id, word_to_frame.word_to_frame_hash): _fail("UPSTREAM_BINDING_INVALID")
    events = [event for track in video_edl.tracks if track.track.value == "V4" for event in track.events if event.event_id == v4_event_id]
    directives = [validate_directive(row) for row in render_props.visual_directives if type(row) is dict and row.get("track") == "V4" and row.get("kind") == "CHART_REVEAL" and row.get("event_id") == v4_event_id]
    if len(events) != 1 or len(directives) != 1 or (events[0].event_hash, events[0].track.value) != (directives[0].event_hash, "V4"): _fail("V4_DIRECTIVE_BINDING_INVALID")
    event, directive = events[0], directives[0]
    return VisualizationEdlBindingV1(video_edl.video_edl_id, video_edl.video_edl_hash, event.event_id, event.event_hash, directive.directive_id, directive.directive_hash, event.start_frame, event.end_exclusive_frame)


def compile_visualization_render_plan(*, artifact: VisualizationArtifactV1, render_props: RenderProps, video_edl: VideoEdlArtifact, word_to_frame: WordToFrameArtifact, v4_event_id: str, stages: tuple[VisualizationStageV1, ...]) -> VisualizationRenderPlanV1:
    serialize_visualization_artifact(artifact)
    edl_binding = _verified_edl_binding(video_edl=video_edl, word_to_frame=word_to_frame, render_props=render_props, v4_event_id=v4_event_id)
    if type(stages) is not tuple or not stages: _fail("VISUALIZATION_STAGE_INVALID")
    targets = _stage_targets(artifact); stage_ids: set[str] = set(); previous: list[VisualizationStageV1] = []
    for ordinal, stage in enumerate(stages, 1):
        if type(stage) is not VisualizationStageV1 or not _id(stage.stage_id) or stage.stage_id in stage_ids or stage.ordinal != ordinal or type(stage.kind) is not VisualizationStageKind or not stage.target_ids or len(set(stage.target_ids)) != len(stage.target_ids) or not set(stage.target_ids).issubset(targets) or (stage.kind is VisualizationStageKind.SERIES_FOCUS and not all(targets[target] is VisualizationKind.CHART and target not in {item.item_id for item in artifact.items} for target in stage.target_ids)): _fail("VISUALIZATION_STAGE_INVALID")
        frame = stage.frame_binding
        if type(frame) is not VisualizationFrameBindingV1: _fail("FRAME_BINDING_INVALID")
        start = next((row for row in word_to_frame.word_frames if row.start_word_id == frame.start_word_id), None); end = next((row for row in word_to_frame.word_frames if row.end_word_id == frame.end_word_id), None)
        if not _id(frame.word_to_frame_id) or not _id(frame.start_word_id) or not _id(frame.end_word_id) or not re.fullmatch(r"[0-9a-f]{64}", frame.word_to_frame_hash) or start is None or end is None or (frame.word_to_frame_id, frame.word_to_frame_hash, frame.sequence_start_frame, frame.global_start_frame, frame.global_end_exclusive_frame, frame.local_start_frame, frame.local_end_exclusive_frame) != (word_to_frame.word_to_frame_id, word_to_frame.word_to_frame_hash, video_edl.sequence_start_frame, start.start_frame, end.end_exclusive_frame, start.start_frame - video_edl.sequence_start_frame, end.end_exclusive_frame - video_edl.sequence_start_frame) or not (edl_binding.local_start_frame <= frame.local_start_frame < frame.local_end_exclusive_frame <= edl_binding.local_end_exclusive_frame): _fail("FRAME_BINDING_INVALID")
        if previous and (frame.word_to_frame_id, frame.word_to_frame_hash, frame.sequence_start_frame) != (previous[0].frame_binding.word_to_frame_id, previous[0].frame_binding.word_to_frame_hash, previous[0].frame_binding.sequence_start_frame): _fail("FRAME_BINDING_INVALID")
        if any(set(stage.target_ids) & set(other.target_ids) and max(frame.local_start_frame, other.frame_binding.local_start_frame) < min(frame.local_end_exclusive_frame, other.frame_binding.local_end_exclusive_frame) for other in previous): _fail("VISUALIZATION_STAGE_OVERLAP")
        stage_ids.add(stage.stage_id)
        previous.append(stage)
    base = VisualizationRenderPlanV1(VISUALIZATION_RENDER_PLAN_V1, "", "", artifact.visualization_id, artifact.visualization_hash, render_props.render_props_id, render_props.render_props_hash, edl_binding, stages); digest = _hash(_plan_data(base, identity=True))
    return VisualizationRenderPlanV1(**(base.__dict__ | {"render_plan_id": "vizplan_" + digest[7:39], "render_plan_hash": digest}))


def _find_bindings(value: Any) -> tuple[SourceCaptureEvidenceBindingV1, ...]:
    if type(value) is SourceCaptureEvidenceBindingV1: return (value,)
    if isinstance(value, Mapping): return tuple(item for child in value.values() for item in _find_bindings(child))
    if isinstance(value, (tuple, list)): return tuple(item for child in value for item in _find_bindings(child))
    return ()


def _metadata_data(value: RenderedVisualizationMetadataV1, *, identity: bool) -> dict[str, Any]:
    result = {field: getattr(value, field) for field in value.__dataclass_fields__}
    result["rendered_elements"] = [list(item) for item in value.rendered_elements]
    result["rendered_stage_ids"] = list(value.rendered_stage_ids)
    result["source_caption_ids"] = list(value.source_caption_ids)
    if identity: result.pop("metadata_id"); result.pop("metadata_hash")
    return result


def _render_remotion_replay_frame(props: Mapping[str, Any], frame: int) -> bytes:
    renderer_root = Path(__file__).resolve().parents[2] / "renderer-remotion"
    runner = renderer_root / "scripts" / "render-visualization-replay.mjs"
    if not runner.is_file(): _fail("REMOTION_REPLAY_UNAVAILABLE")
    with tempfile.TemporaryDirectory(prefix="kurgu_phase7_") as temporary:
        root = Path(temporary); props_path = root / "props.json"; output_path = root / "frame.png"
        props_path.write_bytes(encode_canonical_json_bytes(dict(props)))
        try: result = subprocess.run(["node", str(runner), "--props", str(props_path), "--output", str(output_path), "--frame", str(frame)], cwd=renderer_root, capture_output=True, timeout=120, check=False)
        except (OSError, subprocess.TimeoutExpired): _fail("REMOTION_REPLAY_FAILED")
        if result.returncode != 0 or not output_path.is_file(): _fail("REMOTION_REPLAY_FAILED")
        return output_path.read_bytes()


def render_replay_visualization(*, artifact: VisualizationArtifactV1, plan: VisualizationRenderPlanV1, capture_plans: Mapping[str, SourceCapturePlan], local_frame: int | None = None) -> tuple[bytes, RenderedVisualizationMetadataV1, VisualizationRenderReceiptV1]:
    serialize_visualization_artifact(artifact)
    if plan.visualization_id != artifact.visualization_id or plan.visualization_hash != artifact.visualization_hash or plan.render_plan_hash != _hash(_plan_data(plan, identity=True)): _fail("RENDER_PLAN_INVALID")
    frame = plan.edl_binding.local_start_frame if local_frame is None else local_frame
    if type(frame) is not int or not (plan.edl_binding.local_start_frame <= frame < plan.edl_binding.local_end_exclusive_frame): _fail("REPLAY_FRAME_INVALID")
    elements: list[tuple[str, str, str]] = []; captions: list[tuple[str, str]] = []
    captions_by_id = {item.source_caption_id: item for item in artifact.source_captions.captions}
    for item in artifact.items:
        caption = captions_by_id.get(item.source_caption_id)
        if caption is None: _fail("SOURCE_CAPTION_REFERENCE_INVALID")
        try: capture = capture_plans[caption.source_capture_plan_id]
        except KeyError: _fail("SOURCE_CAPTION_CAPTURE_MISSING")
        if type(capture) is not SourceCapturePlan or (capture.source_capture_plan_id, capture.source_capture_plan_hash, capture.source_package_hash, capture.source_label, capture.publication_date) != (caption.source_capture_plan_id, caption.source_capture_plan_hash, caption.source_package_hash, caption.source_label, caption.publication_date): _fail("SOURCE_CAPTION_CAPTURE_FORGED")
        caption_text = f"{capture.source_label} — {capture.publication_date}"
        captions.append((caption.source_caption_id, caption_text))
        if item.kind is VisualizationKind.CHART:
            for series in item.payload["series"]:
                for point in series["datapoints"]: elements.append((point["point_id"], point["value"].text(), point["period"].label))
        elif item.kind is VisualizationKind.METRIC: elements.append((item.payload["metric_id"], item.payload["value"].text(), item.payload["period"].label))
        else:
            for node in item.payload["nodes"]: elements.append((node["node_id"], node["label"], "topology"))
    form_rows = [(item.item_id, item.kind.value, item.payload["chart_kind"] if item.kind is VisualizationKind.CHART else item.kind.value) for item in artifact.items]
    visible_rows = form_rows + elements + [(caption_id, caption_text, "source") for caption_id, caption_text in captions]
    active_stage_ids = tuple(stage.stage_id for stage in plan.stages if stage.frame_binding.local_start_frame <= frame < stage.frame_binding.local_end_exclusive_frame)
    stage_row = ("stage", ",".join(f"{stage.stage_id}:{frame - stage.frame_binding.local_start_frame}" for stage in plan.stages if stage.stage_id in active_stage_ids) if active_stage_ids else "idle", str(frame))
    body = "".join(f'<text x="24" y="{50 + index * 28}">{html.escape(" | ".join(row))}</text>' for index, row in enumerate(visible_rows + [stage_row]))
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720">{body}</svg>'.encode("utf-8")
    diagnostic_hash = "sha256:" + hashlib.sha256(svg).hexdigest(); values_hash = _hash({"elements": [list(row) for row in elements]})
    base_metadata = RenderedVisualizationMetadataV1("", "", artifact.visualization_id, artifact.visualization_hash, plan.render_plan_id, plan.render_plan_hash, tuple(elements), tuple(stage.stage_id for stage in plan.stages), artifact.source_captions.source_caption_collection_id, artifact.source_captions.source_caption_collection_hash, tuple(caption_id for caption_id, _ in captions), values_hash, diagnostic_hash, "image/svg+xml", 1280, 720, plan.edl_binding.local_start_frame, plan.edl_binding.local_end_exclusive_frame)
    preliminary_hash = _hash(_metadata_data(base_metadata, identity=True)); preliminary = replace(base_metadata, metadata_id="vizmeta_" + preliminary_hash[7:39], metadata_hash=preliminary_hash)
    remotion_png = _render_remotion_replay_frame(build_visualization_replay_props(artifact=artifact, plan=plan, metadata=preliminary), frame)
    svg_hash = "sha256:" + hashlib.sha256(remotion_png).hexdigest()
    base_metadata = replace(base_metadata, rendered_svg_hash=svg_hash, rendered_output_media_type="image/png")
    metadata_hash = _hash(_metadata_data(base_metadata, identity=True)); metadata = replace(base_metadata, metadata_id="vizmeta_" + metadata_hash[7:39], metadata_hash=metadata_hash)
    svg_id = "vizsvg_" + svg_hash[7:39]
    deps = ((artifact.visualization_id, artifact.visualization_hash), (plan.render_plan_id, plan.render_plan_hash), (plan.stages[0].frame_binding.word_to_frame_id, "sha256:" + plan.stages[0].frame_binding.word_to_frame_hash), (plan.edl_binding.video_edl_id, "sha256:" + plan.edl_binding.video_edl_hash), (plan.render_props_id, plan.render_props_hash), (artifact.source_captions.source_caption_collection_id, artifact.source_captions.source_caption_collection_hash), (metadata.metadata_id, metadata.metadata_hash), (svg_id, svg_hash))
    base = {"artifact_type": "visualization_render_receipt", "dependencies": [list(dep) for dep in deps], "status": "SUCCESS", "metadata_hash": metadata.metadata_hash, "svg_hash": svg_hash, "rejection_code": None}; receipt_hash = _hash(base)
    receipt = VisualizationRenderReceiptV1("vizrcpt_" + receipt_hash[7:39], receipt_hash, "visualization_render_receipt", deps, "SUCCESS", metadata.metadata_hash, svg_hash, None)
    serialize_rendered_visualization_metadata(metadata); validate_visualization_render_receipt(receipt)
    return remotion_png, metadata, receipt


def build_visualization_replay_props(*, artifact: VisualizationArtifactV1, plan: VisualizationRenderPlanV1, metadata: RenderedVisualizationMetadataV1) -> dict[str, Any]:
    """Produce the only Node ingress projection from Python-verified artifacts."""
    serialize_visualization_artifact(artifact); serialize_rendered_visualization_metadata(metadata)
    if (metadata.visualization_id, metadata.visualization_hash, metadata.render_plan_id, metadata.render_plan_hash) != (artifact.visualization_id, artifact.visualization_hash, plan.render_plan_id, plan.render_plan_hash): _fail("NODE_PROPS_BINDING_INVALID")
    forms = [{"item_id": item.item_id, "kind": item.kind.value, "form": item.payload["chart_kind"] if item.kind is VisualizationKind.CHART else item.kind.value} for item in artifact.items]
    return {"schema_version": "VISUALIZATION-REPLAY-PROPS-V1", "visualization_id": artifact.visualization_id, "visualization_hash": artifact.visualization_hash, "render_plan_id": plan.render_plan_id, "render_plan_hash": plan.render_plan_hash, "width": metadata.width, "height": metadata.height, "duration_in_frames": plan.edl_binding.local_end_exclusive_frame, "forms": forms, "rows": [{"element_id": item_id, "value": value, "label": label} for item_id, value, label in metadata.rendered_elements], "source_captions": [{"source_caption_id": caption.source_caption_id, "text": f"{caption.source_label} â€” {caption.publication_date}"} for caption in artifact.source_captions.captions], "stages": [{"stage_id": stage.stage_id, "target_ids": list(stage.target_ids), "start_frame": stage.frame_binding.local_start_frame, "end_exclusive_frame": stage.frame_binding.local_end_exclusive_frame} for stage in plan.stages]}
