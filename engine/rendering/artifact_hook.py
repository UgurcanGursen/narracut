"""In-memory, append-only Phase 4A adapter graph construction."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.artifacts import validate_artifact_graph
from engine.contracts.models import ArtifactRecord

from .bridge import RenderBridgeError, RenderFailureCode, RenderProps, _strict_json, serialize_render_props
from .receipt import RenderReceipt, RenderStatus, serialize_render_receipt


@dataclass(frozen=True)
class RenderArtifactBatch:
    records: tuple[ArtifactRecord, ...]


def _record(*, artifact_id: str, artifact_type: str, content_hash: str, size_bytes: int,
            dependencies: tuple[str, ...], props: RenderProps, timestamp: str) -> ArtifactRecord:
    return ArtifactRecord("3.0.0", artifact_id, artifact_type, props.project_id, props.sequence_id,
                          timestamp, timestamp, content_hash, size_bytes, "review", dependencies,
                          False, False, False, False, "phase4a-renderer", "0.1.0", None, "ready", 1)


def build_artifact_batch(*, props: RenderProps, video_edl_bytes: bytes, audio_edl_bytes: bytes,
                         fixture_manifest_bytes: bytes, receipt: RenderReceipt,
                         timestamp_utc: str, preview_manifest_bytes: bytes | None = None,
                         frame_bytes: tuple[tuple[int, bytes], ...] = ()) -> RenderArtifactBatch:
    """Validate a complete typed graph without persisting or mutating a registry."""
    if type(props) is not RenderProps or type(receipt) is not RenderReceipt or type(timestamp_utc) is not str:
        raise RenderBridgeError(RenderFailureCode.ARTIFACT_REGISTRATION_FAILED, "/")
    # Canonical bytes are the artifact evidence.  Do not register a graph from
    # merely named inputs: every supplied byte stream must match the lineage
    # hash already admitted into RenderProps/RenderReceipt.
    try:
        serialize_render_props(props)
        _strict_json(video_edl_bytes, RenderFailureCode.ARTIFACT_REGISTRATION_FAILED, "/video_edl")
        _strict_json(audio_edl_bytes, RenderFailureCode.ARTIFACT_REGISTRATION_FAILED, "/audio_edl")
        # The checked-in fixture manifest intentionally remains human-readable;
        # its identity is nevertheless canonical over the documented projection.
        manifest = json.loads(fixture_manifest_bytes.decode("utf-8"))
        if type(manifest) is not dict or type(manifest.get("fixture_manifest_id")) is not str or type(manifest.get("fixture_manifest_hash")) is not str:
            raise ValueError("invalid fixture manifest")
    except (RenderBridgeError, TypeError):
        raise RenderBridgeError(RenderFailureCode.ARTIFACT_REGISTRATION_FAILED, "/inputs") from None
    manifest_projection = {key: item for key, item in manifest.items()
                           if key not in {"fixture_manifest_id", "fixture_manifest_hash"}}
    video_projection = {key: item for key, item in _strict_json(video_edl_bytes, RenderFailureCode.ARTIFACT_REGISTRATION_FAILED, "/video_edl").items()
                        if key not in {"video_edl_id", "video_edl_hash"}}
    audio_projection = {key: item for key, item in _strict_json(audio_edl_bytes, RenderFailureCode.ARTIFACT_REGISTRATION_FAILED, "/audio_edl").items()
                        if key not in {"audio_edl_id", "audio_edl_hash"}}
    if (hashlib.sha256(encode_canonical_json_bytes(video_projection)).hexdigest() != props.video_edl_hash
            or hashlib.sha256(encode_canonical_json_bytes(audio_projection)).hexdigest() != props.audio_edl_hash
            or manifest.get("fixture_manifest_hash") != props.fixture_manifest_hash
            or manifest.get("fixture_manifest_id") != props.fixture_manifest_id
            or "sha256:" + hashlib.sha256(encode_canonical_json_bytes(manifest_projection)).hexdigest() != props.fixture_manifest_hash):
        raise RenderBridgeError(RenderFailureCode.ARTIFACT_REGISTRATION_FAILED, "/inputs/hash")
    if (receipt.render_props_hash != props.render_props_hash
            or receipt.render_props_id != props.render_props_id
            or receipt.render_request_id != props.render_request_id
            or receipt.video_edl_id != props.video_edl_id
            or receipt.video_edl_hash != props.video_edl_hash
            or receipt.audio_edl_id != props.audio_edl_id
            or receipt.audio_edl_hash != props.audio_edl_hash
            or receipt.renderer_version != props.renderer_version):
        raise RenderBridgeError(RenderFailureCode.ARTIFACT_REGISTRATION_FAILED, "/receipt")
    vedl = "art_vedl_" + props.video_edl_hash[:32]
    aedl = "art_aedl_" + props.audio_edl_hash[:32]
    fixman = "art_fixman_" + props.fixture_manifest_hash[7:39]
    rprops = "art_rprops_" + props.render_props_hash[7:39]
    rows = [
        _record(artifact_id=vedl, artifact_type="renderer_input", content_hash="sha256:" + props.video_edl_hash, size_bytes=len(video_edl_bytes), dependencies=(), props=props, timestamp=timestamp_utc),
        _record(artifact_id=aedl, artifact_type="renderer_input", content_hash="sha256:" + props.audio_edl_hash, size_bytes=len(audio_edl_bytes), dependencies=(), props=props, timestamp=timestamp_utc),
        _record(artifact_id=fixman, artifact_type="fixture_manifest", content_hash=props.fixture_manifest_hash, size_bytes=len(fixture_manifest_bytes), dependencies=(), props=props, timestamp=timestamp_utc),
        _record(artifact_id=rprops, artifact_type="render_props", content_hash=props.render_props_hash, size_bytes=len(serialize_render_props(props)), dependencies=(vedl, aedl, fixman), props=props, timestamp=timestamp_utc),
    ]
    if receipt.status is RenderStatus.SUCCEEDED:
        if type(preview_manifest_bytes) is not bytes or receipt.output_sha256 != "sha256:" + hashlib.sha256(preview_manifest_bytes).hexdigest() or receipt.output_size_bytes != len(preview_manifest_bytes):
            raise RenderBridgeError(RenderFailureCode.ARTIFACT_REGISTRATION_FAILED, "/receipt/output")
        frame_ids: list[str] = []
        seen_frame_indices: set[int] = set()
        for index, raw in frame_bytes:
            if type(index) is not int or type(index) is bool or index < 0 or type(raw) is not bytes or index in seen_frame_indices:
                raise RenderBridgeError(RenderFailureCode.ARTIFACT_REGISTRATION_FAILED, "/frames")
            seen_frame_indices.add(index)
            digest = "sha256:" + hashlib.sha256(raw).hexdigest()
            artifact_id = f"art_rframe_{index}_{digest[7:39]}"
            frame_ids.append(artifact_id)
            rows.append(_record(artifact_id=artifact_id, artifact_type="render_frame", content_hash=digest, size_bytes=len(raw), dependencies=(rprops, fixman), props=props, timestamp=timestamp_utc))
        manifest_id = "art_rmanifest_" + receipt.output_sha256[7:39]
        if receipt.output_artifact_id != manifest_id or receipt.preview_manifest_id != manifest_id:
            raise RenderBridgeError(RenderFailureCode.ARTIFACT_REGISTRATION_FAILED, "/receipt/output")
        rows.append(_record(artifact_id=manifest_id, artifact_type="render_manifest", content_hash=receipt.output_sha256, size_bytes=len(preview_manifest_bytes), dependencies=(rprops, *frame_ids), props=props, timestamp=timestamp_utc))
        expected_ids = tuple(item.artifact_id for item in rows)
        receipt_dependencies = (rprops, manifest_id)
    else:
        expected_ids = tuple(item.artifact_id for item in rows)
        receipt_dependencies = (rprops,)
    if receipt.artifact_ids != expected_ids:
        raise RenderBridgeError(RenderFailureCode.ARTIFACT_REGISTRATION_FAILED, "/receipt/artifact_ids")
    receipt_id = "art_rreceipt_" + receipt.receipt_hash[7:39]
    rows.append(_record(artifact_id=receipt_id, artifact_type="render_receipt", content_hash=receipt.receipt_hash, size_bytes=len(serialize_render_receipt(receipt)), dependencies=receipt_dependencies, props=props, timestamp=timestamp_utc))
    result = validate_artifact_graph(rows, project_ids={props.project_id}, sequence_ids={props.sequence_id})
    if not result.is_valid:
        raise RenderBridgeError(RenderFailureCode.ARTIFACT_REGISTRATION_FAILED, "/artifacts")
    return RenderArtifactBatch(tuple(rows))
