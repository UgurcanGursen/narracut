"""Canonical terminal receipt values for the Phase 4A preview adapter."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from engine.contracts._canonical_json import encode_canonical_json_bytes

from .bridge import COMPOSITION_ID, RenderBridgeError, RenderFailureCode, RenderProps, _trusted_renderer_version, serialize_render_props

RENDER_RECEIPT_V1 = "RENDER-RECEIPT-V1"
RENDER_RECEIPT_HASH_V1 = "RENDER-RECEIPT-HASH-V1"


class RenderStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class RenderReceipt:
    schema_version: str
    receipt_id: str
    receipt_hash: str
    render_request_id: str
    status: RenderStatus
    failure_code: str | None
    render_props_id: str
    render_props_hash: str
    video_edl_id: str
    video_edl_hash: str
    audio_edl_id: str
    audio_edl_hash: str
    composition_id: str
    renderer_version: str
    node_version: str | None
    preview_manifest_id: str | None
    preview_manifest_hash: str | None
    output_artifact_id: str | None
    output_sha256: str | None
    output_size_bytes: int | None
    artifact_ids: tuple[str, ...]
    stdout_sha256: str
    stderr_sha256: str


_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_BARE_HASH = re.compile(r"^[0-9a-f]{64}$")
_NODE = re.compile(r"^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_ART = re.compile(r"^art_[a-z0-9_]+$")
_REQUEST = re.compile(r"^rrq_[0-9a-f]{32}$")
_PROPS_ID = re.compile(r"^rprops_[0-9a-f]{32}$")
_RECEIPT_ID = re.compile(r"^rrc_[0-9a-f]{32}$")
_MANIFEST_ARTIFACT = re.compile(r"^art_rmanifest_[0-9a-f]{32}$")
_UINT64_MAX = (1 << 64) - 1


def _fail(pointer: str) -> None:
    raise RenderBridgeError(RenderFailureCode.RECEIPT_INVALID, pointer)


def _sha(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _data(value: RenderReceipt, *, identity: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name in RenderReceipt.__dataclass_fields__:
        item = getattr(value, name)
        result[name] = item.value if isinstance(item, Enum) else list(item) if isinstance(item, tuple) else item
    if identity:
        result.pop("receipt_id"); result.pop("receipt_hash")
    return result


def _validate(value: RenderReceipt) -> None:
    if type(value) is not RenderReceipt or value.schema_version != RENDER_RECEIPT_V1 or value.composition_id != COMPOSITION_ID:
        _fail("/")
    if value.renderer_version != _trusted_renderer_version():
        _fail("/renderer_version")
    if not all(type(getattr(value, name)) is str and getattr(value, name) for name in ("render_request_id", "render_props_id", "render_props_hash", "video_edl_id", "video_edl_hash", "audio_edl_id", "audio_edl_hash", "renderer_version", "stdout_sha256", "stderr_sha256", "receipt_id", "receipt_hash")) or not (_REQUEST.fullmatch(value.render_request_id) and _PROPS_ID.fullmatch(value.render_props_id) and _RECEIPT_ID.fullmatch(value.receipt_id) and _HASH.fullmatch(value.receipt_hash) and _HASH.fullmatch(value.render_props_hash) and _BARE_HASH.fullmatch(value.video_edl_hash) and _BARE_HASH.fullmatch(value.audio_edl_hash) and _HASH.fullmatch(value.stdout_sha256) and _HASH.fullmatch(value.stderr_sha256)):
        _fail("/lineage")
    if value.status is RenderStatus.SUCCEEDED:
        if value.failure_code is not None or any(item is None for item in (value.node_version, value.preview_manifest_id, value.preview_manifest_hash, value.output_artifact_id, value.output_sha256, value.output_size_bytes)):
            _fail("/status")
        if (value.preview_manifest_id != value.output_artifact_id
                or _MANIFEST_ARTIFACT.fullmatch(value.preview_manifest_id) is None
                or not _HASH.fullmatch(value.preview_manifest_hash)
                or value.preview_manifest_hash != value.output_sha256
                or not _HASH.fullmatch(value.output_sha256)
                or type(value.output_size_bytes) is not int or value.output_size_bytes < 0
                or value.output_size_bytes > _UINT64_MAX):
            _fail("/output")
    elif value.status is RenderStatus.CANCELLED:
        if value.failure_code != RenderFailureCode.CANCELLED_BY_PARENT.value:
            _fail("/failure_code")
    elif value.status is RenderStatus.FAILED:
        if value.failure_code not in {item.value for item in RenderFailureCode if item is not RenderFailureCode.CANCELLED_BY_PARENT}:
            _fail("/failure_code")
    else:
        _fail("/status")
    if value.status is not RenderStatus.SUCCEEDED and any(item is not None for item in (value.preview_manifest_id, value.preview_manifest_hash, value.output_artifact_id, value.output_sha256, value.output_size_bytes)):
        _fail("/output")
    if value.node_version is not None and _NODE.fullmatch(value.node_version) is None:
        _fail("/node_version")
    if type(value.failure_code) is not str and value.failure_code is not None:
        _fail("/failure_code")
    if type(value.artifact_ids) is not tuple or len(value.artifact_ids) != len(set(value.artifact_ids)) or any(_ART.fullmatch(item) is None for item in value.artifact_ids):
        _fail("/artifact_ids")
    digest = _sha(encode_canonical_json_bytes(_data(value, identity=True)))
    if value.receipt_hash != digest or value.receipt_id != "rrc_" + digest[7:39]:
        _fail("/identity")


def build_render_receipt(*, props: RenderProps, status: RenderStatus, failure_code: str | None,
                         node_version: str | None, preview_manifest_id: str | None,
                         preview_manifest_hash: str | None, output_artifact_id: str | None,
                         output_sha256: str | None, output_size_bytes: int | None,
                         artifact_ids: tuple[str, ...], stdout_bytes: bytes, stderr_bytes: bytes) -> RenderReceipt:
    if type(props) is not RenderProps or type(status) is not RenderStatus or type(stdout_bytes) is not bytes or type(stderr_bytes) is not bytes:
        _fail("/")
    # This validates the trusted renderer lock, request identity, and every
    # projected EDL shape before a receipt can make it durable lineage.
    try:
        serialize_render_props(props)
    except RenderBridgeError:
        _fail("/props")
    base = dict(schema_version=RENDER_RECEIPT_V1, receipt_id="", receipt_hash="", render_request_id=props.render_request_id, status=status, failure_code=failure_code, render_props_id=props.render_props_id, render_props_hash=props.render_props_hash, video_edl_id=props.video_edl_id, video_edl_hash=props.video_edl_hash, audio_edl_id=props.audio_edl_id, audio_edl_hash=props.audio_edl_hash, composition_id=props.composition_id, renderer_version=props.renderer_version, node_version=node_version, preview_manifest_id=preview_manifest_id, preview_manifest_hash=preview_manifest_hash, output_artifact_id=output_artifact_id, output_sha256=output_sha256, output_size_bytes=output_size_bytes, artifact_ids=artifact_ids, stdout_sha256=_sha(stdout_bytes), stderr_sha256=_sha(stderr_bytes))
    draft = RenderReceipt(**base)
    digest = _sha(encode_canonical_json_bytes(_data(draft, identity=True)))
    result = RenderReceipt(**(base | {"receipt_id": "rrc_" + digest[7:39], "receipt_hash": digest}))
    _validate(result)
    return result


def serialize_render_receipt(value: RenderReceipt) -> bytes:
    _validate(value)
    return encode_canonical_json_bytes(_data(value))


def load_render_receipt(source: bytes) -> RenderReceipt:
    from .bridge import _strict_json  # keep the JSON ingress oracle in one place
    value = _strict_json(source, RenderFailureCode.RECEIPT_INVALID, "/")
    if set(value) != set(RenderReceipt.__dataclass_fields__):
        _fail("/")
    try:
        result = RenderReceipt(**(value | {"status": RenderStatus(value["status"]), "artifact_ids": tuple(value["artifact_ids"])}))
    except Exception:
        _fail("/")
    _validate(result)
    if serialize_render_receipt(result) != source:
        _fail("/")
    return result
