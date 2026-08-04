"""Deterministic Phase 2 V5/V6 preview collision report contract."""

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
from .caption_preview import (
    CaptionPreviewArtifact,
    CaptionPreviewContractError,
    PreviewRect,
    PreviewTrack,
    serialize_caption_preview,
)

V5_V6_COLLISION_REPORT_V1 = "V5-V6-COLLISION-REPORT-V1"
V5_V6_COLLISION_REPORT_HASH_V1 = "V5-V6-COLLISION-REPORT-HASH-V1"
V5_V6_COLLISION_FINDING_V1 = "V5-V6-COLLISION-FINDING-V1"
V5_V6_COLLISION_FINDING_HASH_V1 = "V5-V6-COLLISION-FINDING-HASH-V1"

__all__ = [
    "V5_V6_COLLISION_REPORT_V1", "V5_V6_COLLISION_REPORT_HASH_V1",
    "V5_V6_COLLISION_FINDING_V1", "V5_V6_COLLISION_FINDING_HASH_V1",
    "V5V6CollisionFindingKind", "V5V6CollisionSeverity",
    "V5V6CollisionRejectionReason", "V5V6CollisionFinding",
    "V5V6CollisionReport", "V5V6CollisionContractError",
    "compile_v5_v6_collision_report", "load_v5_v6_collision_report",
    "serialize_v5_v6_collision_report", "render_v5_v6_collision_diagnostic_svg",
]


class V5V6CollisionFindingKind(str, Enum):
    CROSS_TRACK_OCCLUSION = "CROSS_TRACK_OCCLUSION"
    SAFE_AREA_VIOLATION = "SAFE_AREA_VIOLATION"


class V5V6CollisionSeverity(str, Enum):
    BLOCKER = "BLOCKER"


class V5V6CollisionRejectionReason(str, Enum):
    STRUCTURE_INVALID = "STRUCTURE_INVALID"
    UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
    DEPENDENCY_CONTENT_DRIFT = "DEPENDENCY_CONTENT_DRIFT"
    DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
    FINDING_INVALID = "FINDING_INVALID"
    NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    CONTENT_DRIFT = "CONTENT_DRIFT"
    NOT_MATERIALIZED = "NOT_MATERIALIZED"


@dataclass(frozen=True)
class V5V6CollisionFinding:
    schema_version: str
    hash_scope_version: str
    v5_v6_collision_finding_id: str
    v5_v6_collision_finding_hash: str
    ordinal: int
    kind: V5V6CollisionFindingKind
    severity: V5V6CollisionSeverity
    primary_preview_scene_id: str
    secondary_preview_scene_id: str | None
    overlap_start_frame: int
    overlap_end_exclusive_frame: int
    overlap_rect: PreviewRect | None


@dataclass(frozen=True)
class V5V6CollisionReport:
    schema_version: str
    hash_scope_version: str
    v5_v6_collision_report_id: str
    v5_v6_collision_report_hash: str
    caption_preview_id: str
    caption_preview_hash: str
    finding_count: int
    blocker_count: int
    findings: tuple[V5V6CollisionFinding, ...]


_FIXED_POINTERS = frozenset({"/", "/caption_preview", "/findings"})
_INDEXED = re.compile(r"/findings/(?:0|[1-9][0-9]*)")
_FINDING_FIELDS = (
    "schema_version", "hash_scope_version", "v5_v6_collision_finding_id",
    "v5_v6_collision_finding_hash", "ordinal", "kind", "severity",
    "primary_preview_scene_id", "secondary_preview_scene_id", "overlap_start_frame",
    "overlap_end_exclusive_frame", "overlap_rect",
)
_ROOT_FIELDS = (
    "schema_version", "hash_scope_version", "v5_v6_collision_report_id",
    "v5_v6_collision_report_hash", "caption_preview_id", "caption_preview_hash",
    "finding_count", "blocker_count", "findings",
)
_REGISTRY: dict[int, tuple[weakref.ReferenceType[V5V6CollisionReport], bytes, tuple[Any, ...]]] = {}
_OWNERS: dict[int, weakref.ReferenceType[V5V6CollisionReport]] = {}


class V5V6CollisionContractError(ValueError):
    def __init__(self, pointer: str, reason: V5V6CollisionRejectionReason, issue_code: str | None = None) -> None:
        if type(pointer) is not str or (pointer not in _FIXED_POINTERS and _INDEXED.fullmatch(pointer) is None) or type(reason) is not V5V6CollisionRejectionReason:
            raise TypeError("invalid V5/V6 collision error construction")
        if issue_code is not None and type(issue_code) is not str:
            raise TypeError("invalid V5/V6 collision issue code")
        super().__init__(f"V5/V6 collision report rejected: {reason.value}")
        self.pointer, self.reason, self.issue_code = pointer, reason, issue_code


def _reject(pointer: str, reason: V5V6CollisionRejectionReason, issue_code: str | None = None) -> None:
    raise V5V6CollisionContractError(pointer, reason, issue_code)


def _digest(value: Any) -> str:
    return hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _rect(value: PreviewRect) -> dict[str, int]:
    return {"left": value.left, "top": value.top, "right": value.right, "bottom": value.bottom}


def _finding_dict(value: V5V6CollisionFinding) -> dict[str, Any]:
    result = {field: getattr(value, field) for field in _FINDING_FIELDS}
    result["kind"] = value.kind.value
    result["severity"] = value.severity.value
    result["overlap_rect"] = None if value.overlap_rect is None else _rect(value.overlap_rect)
    return result


def _report_dict(value: V5V6CollisionReport) -> dict[str, Any]:
    result = {field: getattr(value, field) for field in _ROOT_FIELDS}
    result["findings"] = [_finding_dict(item) for item in value.findings]
    return result


def _signature(value: V5V6CollisionReport) -> tuple[Any, ...]:
    return (id(value), tuple((field, id(getattr(value, field)), repr(getattr(value, field))) for field in _ROOT_FIELDS))


def _register(value: V5V6CollisionReport, data: bytes) -> None:
    key = id(value)
    if key in _REGISTRY:
        raise RuntimeError("duplicate live collision report registration")
    def cleanup(reference: weakref.ReferenceType[V5V6CollisionReport], *, key: int = key) -> None:
        entry = _REGISTRY.get(key)
        if entry is not None and entry[0] is reference:
            _REGISTRY.pop(key, None)
            _OWNERS.pop(key, None)
    reference = weakref.ref(value, cleanup)
    _REGISTRY[key] = (reference, data, _signature(value))
    _OWNERS[key] = reference


def _contained(rect: PreviewRect, safe: PreviewRect) -> bool:
    return safe.left <= rect.left and safe.top <= rect.top and rect.right <= safe.right and rect.bottom <= safe.bottom


def _intersection(a: Any, b: Any) -> tuple[int, int, PreviewRect] | None:
    left, right = max(a.rect.left, b.rect.left), min(a.rect.right, b.rect.right)
    top, bottom = max(a.rect.top, b.rect.top), min(a.rect.bottom, b.rect.bottom)
    start, end = max(a.start_frame, b.start_frame), min(a.end_exclusive_frame, b.end_exclusive_frame)
    if left >= right or top >= bottom or start >= end:
        return None
    return start, end, PreviewRect(left, top, right, bottom)


def _spatially_overlaps(a: PreviewRect, b: PreviewRect) -> bool:
    return max(a.left, b.left) < min(a.right, b.right) and max(a.top, b.top) < min(a.bottom, b.bottom)


def _finding(*, ordinal: int, kind: V5V6CollisionFindingKind, primary: Any, secondary: Any | None, start: int, end: int, rect: PreviewRect | None) -> V5V6CollisionFinding:
    projection = {
        "schema_version": V5_V6_COLLISION_FINDING_V1, "hash_scope_version": V5_V6_COLLISION_FINDING_HASH_V1,
        "ordinal": ordinal, "kind": kind.value, "severity": "BLOCKER", "primary_preview_scene_id": primary.preview_scene_id,
        "secondary_preview_scene_id": None if secondary is None else secondary.preview_scene_id,
        "overlap_start_frame": start, "overlap_end_exclusive_frame": end, "overlap_rect": None if rect is None else _rect(rect),
    }
    digest = _digest(projection)
    return V5V6CollisionFinding(V5_V6_COLLISION_FINDING_V1, V5_V6_COLLISION_FINDING_HASH_V1, "v5v6f_" + digest[:32], digest, ordinal, kind, V5V6CollisionSeverity.BLOCKER, primary.preview_scene_id, None if secondary is None else secondary.preview_scene_id, start, end, rect)


def _derive(preview: CaptionPreviewArtifact) -> V5V6CollisionReport:
    findings: list[V5V6CollisionFinding] = []
    for scene in preview.scenes:
        if not _contained(scene.rect, preview.safe_rect):
            findings.append(_finding(ordinal=len(findings), kind=V5V6CollisionFindingKind.SAFE_AREA_VIOLATION, primary=scene, secondary=None, start=scene.start_frame, end=scene.end_exclusive_frame, rect=scene.rect))
    v5 = [item for item in preview.scenes if item.track is PreviewTrack.V5]
    v6 = [item for item in preview.scenes if item.track is PreviewTrack.V6]
    # Caption groups and emphasis events are canonical, ordinal-ordered,
    # non-overlapping source spans.  Preserve that invariant explicitly so a
    # linear two-pointer walk is both complete and in required V5/V6 ordinal
    # order; a mutated/noncanonical preview is rejected before derivation.
    for track in (v5, v6):
        if any(item.ordinal != track[0].ordinal + index or (index and track[index - 1].end_exclusive_frame > item.start_frame) for index, item in enumerate(track)):
            _reject("/caption_preview", V5V6CollisionRejectionReason.DEPENDENCY_CONTENT_DRIFT)
    cursor = 0
    for primary in v5:
        while cursor < len(v6) and v6[cursor].end_exclusive_frame <= primary.start_frame:
            cursor += 1
        candidate = cursor
        while candidate < len(v6) and v6[candidate].start_frame < primary.end_exclusive_frame:
            secondary = v6[candidate]
            hit = _intersection(primary, secondary)
            if hit is not None:
                start, end, rect = hit
                findings.append(_finding(ordinal=len(findings), kind=V5V6CollisionFindingKind.CROSS_TRACK_OCCLUSION, primary=primary, secondary=secondary, start=start, end=end, rect=rect))
            candidate += 1
    body = {"schema_version": V5_V6_COLLISION_REPORT_V1, "hash_scope_version": V5_V6_COLLISION_REPORT_HASH_V1,
            "caption_preview_id": preview.caption_preview_id, "caption_preview_hash": preview.caption_preview_hash,
            "finding_count": len(findings), "blocker_count": len(findings), "findings": [_finding_dict(item) for item in findings]}
    digest = _digest(body)
    return V5V6CollisionReport(V5_V6_COLLISION_REPORT_V1, V5_V6_COLLISION_REPORT_HASH_V1, "v5v6r_" + digest[:32], digest, preview.caption_preview_id, preview.caption_preview_hash, len(findings), len(findings), tuple(findings))


def _preflight(caption_preview: Any) -> None:
    if type(caption_preview) is not CaptionPreviewArtifact:
        raise TypeError("caption_preview must be a genuine caption preview artifact")
    try:
        serialize_caption_preview(caption_preview)
    except CaptionPreviewContractError as error:
        if error.reason.value == "NOT_MATERIALIZED":
            raise TypeError("caption_preview must be a genuine caption preview artifact") from None
        _reject("/caption_preview", V5V6CollisionRejectionReason.DEPENDENCY_CONTENT_DRIFT)


def compile_v5_v6_collision_report(*, caption_preview: CaptionPreviewArtifact) -> V5V6CollisionReport:
    _preflight(caption_preview)
    value = _derive(caption_preview)
    data = encode_canonical_json_bytes(_report_dict(value))
    _register(value, data)
    return value


def _parse(source: bytes) -> Any:
    if type(source) is not bytes:
        raise TypeError("source must be bytes")
    if source.startswith(b"\xef\xbb\xbf"):
        _reject("/", V5V6CollisionRejectionReason.NON_CANONICAL_SERIALIZATION)
    def duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError
            result[key] = value
        return result
    try:
        return json.loads(source.decode("utf-8"), object_pairs_hook=duplicates, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except Exception:
        _reject("/", V5V6CollisionRejectionReason.NON_CANONICAL_SERIALIZATION)


def _root_has_exact_types(value: dict[str, Any]) -> bool:
    return (
        all(type(value[field]) is str for field in _ROOT_FIELDS[:6])
        and type(value["finding_count"]) is int and type(value["blocker_count"]) is int
        and 0 <= value["finding_count"] <= 2**32 - 1 and 0 <= value["blocker_count"] <= 2**32 - 1
        and type(value["findings"]) is list
    )


def _finding_has_exact_types(value: dict[str, Any]) -> bool:
    return (
        all(type(value[field]) is str for field in ("schema_version", "hash_scope_version", "v5_v6_collision_finding_id", "v5_v6_collision_finding_hash", "kind", "severity", "primary_preview_scene_id"))
        and (value["secondary_preview_scene_id"] is None or type(value["secondary_preview_scene_id"]) is str)
        and all(type(value[field]) is int and 0 <= value[field] <= 2**32 - 1 for field in ("ordinal", "overlap_start_frame", "overlap_end_exclusive_frame"))
        and (value["overlap_rect"] is None or (type(value["overlap_rect"]) is dict and set(value["overlap_rect"]) == {"left", "top", "right", "bottom"} and all(type(value["overlap_rect"][field]) is int for field in ("left", "top", "right", "bottom"))))
    )


def load_v5_v6_collision_report(source: bytes, *, caption_preview: CaptionPreviewArtifact) -> V5V6CollisionReport:
    _preflight(caption_preview)
    expected = _derive(caption_preview)
    value = _parse(source)
    try:
        canonical = encode_canonical_json_bytes(value)
    except Exception:
        _reject("/", V5V6CollisionRejectionReason.NON_CANONICAL_SERIALIZATION)
    if source != canonical:
        _reject("/", V5V6CollisionRejectionReason.NON_CANONICAL_SERIALIZATION)
    if type(value) is not dict or set(value) != set(_ROOT_FIELDS) or not _root_has_exact_types(value):
        _reject("/", V5V6CollisionRejectionReason.STRUCTURE_INVALID)
    if value["schema_version"] != V5_V6_COLLISION_REPORT_V1 or value["hash_scope_version"] != V5_V6_COLLISION_REPORT_HASH_V1:
        _reject("/", V5V6CollisionRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
    if value["caption_preview_id"] != expected.caption_preview_id or value["caption_preview_hash"] != expected.caption_preview_hash:
        _reject("/caption_preview", V5V6CollisionRejectionReason.DEPENDENCY_BINDING_INVALID)
    wanted = _report_dict(expected)
    if len(value["findings"]) != len(wanted["findings"]):
        _reject("/findings", V5V6CollisionRejectionReason.FINDING_INVALID)
    for index, (actual, expected_finding) in enumerate(zip(value["findings"], wanted["findings"])):
        pointer = f"/findings/{index}"
        if type(actual) is not dict or set(actual) != set(_FINDING_FIELDS):
            _reject(pointer, V5V6CollisionRejectionReason.FINDING_INVALID)
        if not _finding_has_exact_types(actual):
            _reject(pointer, V5V6CollisionRejectionReason.STRUCTURE_INVALID)
        if actual["schema_version"] != V5_V6_COLLISION_FINDING_V1 or actual["hash_scope_version"] != V5_V6_COLLISION_FINDING_HASH_V1 or actual["kind"] not in {x.value for x in V5V6CollisionFindingKind}:
            _reject(pointer, V5V6CollisionRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
        if actual["severity"] != V5V6CollisionSeverity.BLOCKER.value:
            _reject(pointer, V5V6CollisionRejectionReason.FINDING_INVALID)
        for field in _FINDING_FIELDS[4:]:
            if actual[field] != expected_finding[field]:
                _reject(pointer, V5V6CollisionRejectionReason.FINDING_INVALID)
        projection = dict(actual); projection.pop("v5_v6_collision_finding_id"); projection.pop("v5_v6_collision_finding_hash")
        digest = _digest(projection)
        if actual["v5_v6_collision_finding_hash"] != digest or actual["v5_v6_collision_finding_id"] != "v5v6f_" + digest[:32]:
            _reject(pointer, V5V6CollisionRejectionReason.IDENTITY_MISMATCH)
    projection = dict(value); projection.pop("v5_v6_collision_report_id"); projection.pop("v5_v6_collision_report_hash")
    digest = _digest(projection)
    if value["v5_v6_collision_report_hash"] != digest or value["v5_v6_collision_report_id"] != "v5v6r_" + digest[:32]:
        _reject("/", V5V6CollisionRejectionReason.IDENTITY_MISMATCH)
    if source != encode_canonical_json_bytes(wanted):
        _reject("/", V5V6CollisionRejectionReason.NON_CANONICAL_SERIALIZATION)
    _register(expected, source)
    return expected


def serialize_v5_v6_collision_report(report: V5V6CollisionReport) -> bytes:
    entry = _REGISTRY.get(id(report)); owner = _OWNERS.get(id(report))
    if type(report) is not V5V6CollisionReport or owner is None or owner() is not report:
        _reject("/", V5V6CollisionRejectionReason.NOT_MATERIALIZED)
    if entry is None or entry[0] is not owner or entry[0]() is not report or entry[2] != _signature(report):
        _reject("/", V5V6CollisionRejectionReason.CONTENT_DRIFT)
    try:
        if encode_canonical_json_bytes(_report_dict(report)) != entry[1]:
            raise ValueError
    except Exception:
        _reject("/", V5V6CollisionRejectionReason.CONTENT_DRIFT)
    return entry[1]


def _escape(label: str) -> str:
    if unicodedata.normalize("NFC", label) != label or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in label):
        _reject("/", V5V6CollisionRejectionReason.CONTENT_DRIFT)
    return label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")


def render_v5_v6_collision_diagnostic_svg(report: V5V6CollisionReport, *, caption_preview: CaptionPreviewArtifact) -> str:
    if report.caption_preview_id != getattr(caption_preview, "caption_preview_id", None) or report.caption_preview_hash != getattr(caption_preview, "caption_preview_hash", None):
        _reject("/caption_preview", V5V6CollisionRejectionReason.DEPENDENCY_BINDING_INVALID)
    serialize_v5_v6_collision_report(report); _preflight(caption_preview)
    safe = caption_preview.safe_rect
    bits = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" width="1000" height="1000">', f'<rect data-kind="safe-area" x="{safe.left//1000}" y="{safe.top//1000}" width="{(safe.right-safe.left)//1000}" height="{(safe.bottom-safe.top)//1000}" fill="none" stroke="#111111"/>']
    for scene in caption_preview.scenes:
        rect = scene.rect; color = "#E8A317" if scene.track is PreviewTrack.V5 else "#2C7BE5"
        bits.append(f'<rect data-track="{scene.track.value}" data-scene-id="{scene.preview_scene_id}" x="{rect.left//1000}" y="{rect.top//1000}" width="{(rect.right-rect.left)//1000}" height="{(rect.bottom-rect.top)//1000}" fill="{color}"/>')
        bits.append(f'<text data-scene-id="{scene.preview_scene_id}" x="{rect.left//1000}" y="{rect.top//1000}">{_escape(scene.semantic_proxy_label)}</text>')
    for finding in report.findings:
        if finding.overlap_rect is not None:
            rect = finding.overlap_rect
            bits.append(f'<rect data-kind="{finding.kind.value}" x="{rect.left//1000}" y="{rect.top//1000}" width="{(rect.right-rect.left)//1000}" height="{(rect.bottom-rect.top)//1000}" fill="#D7263D"/>')
    return "".join(bits) + "</svg>"
