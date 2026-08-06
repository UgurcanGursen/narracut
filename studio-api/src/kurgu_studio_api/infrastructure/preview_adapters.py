"""Narrow Phase 13 REPLAY preview adapters; no lifecycle or media store."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Mapping

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.audio_edl import AudioEdlArtifact, serialize_audio_edl
from engine.contracts.edl import VideoEdlArtifact, serialize_video_edl
from engine.rendering import FixtureAssetResolver, build_render_props, load_render_props, run_headless_preview, serialize_render_props
from engine.rendering.receipt import RenderStatus

from ..application.models import PreviewExecutionResult, RenderInputSnapshotRecord, ReviewSnapshotRecord


def _sha(raw: bytes) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _canonical_object(raw: bytes) -> dict[str, Any]:
    value = json.loads(raw.decode("utf-8"))
    if type(value) is not dict or encode_canonical_json_bytes(value) != raw:
        raise ValueError("RENDER_INPUT_NON_CANONICAL")
    return value


def _snapshot_identity(value: RenderInputSnapshotRecord) -> dict[str, Any]:
    return {
        field: getattr(value, field)
        for field in value.__dataclass_fields__
        if field not in {"snapshot_id", "snapshot_hash", "video_edl_bytes", "audio_edl_bytes", "render_props_bytes"}
    } | {
        "video_edl_bytes_sha256": _sha(value.video_edl_bytes),
        "audio_edl_bytes_sha256": _sha(value.audio_edl_bytes),
        "render_props_bytes_sha256": _sha(value.render_props_bytes),
    }


def validate_render_input_snapshot(value: RenderInputSnapshotRecord) -> None:
    """Validate the sealed replay handoff before it is persisted or executed."""
    if type(value) is not RenderInputSnapshotRecord or value.mode != "preview_replay":
        raise ValueError("RENDER_INPUT_INVALID")
    video = _canonical_object(value.video_edl_bytes)
    audio = _canonical_object(value.audio_edl_bytes)
    props = load_render_props(value.render_props_bytes)
    if (video.get("video_edl_id"), video.get("video_edl_hash"), audio.get("audio_edl_id"), audio.get("audio_edl_hash")) != (value.video_edl_id, value.video_edl_hash, value.audio_edl_id, value.audio_edl_hash):
        raise ValueError("RENDER_INPUT_LINEAGE_INVALID")
    if (audio.get("video_edl_id"), audio.get("video_edl_hash")) != (value.video_edl_id, value.video_edl_hash):
        raise ValueError("RENDER_INPUT_LINEAGE_INVALID")
    if (props.project_id, props.sequence_id, props.video_edl_id, props.video_edl_hash, props.audio_edl_id, props.audio_edl_hash, props.render_props_id, props.render_props_hash, props.fixture_manifest_id, props.fixture_manifest_hash) != (value.project_id, value.executable_sequence_id, value.video_edl_id, value.video_edl_hash, value.audio_edl_id, value.audio_edl_hash, value.render_props_id, value.render_props_hash, value.fixture_manifest_id, value.fixture_manifest_hash):
        raise ValueError("RENDER_INPUT_LINEAGE_INVALID")
    digest = _sha(encode_canonical_json_bytes(_snapshot_identity(value)))
    if value.snapshot_hash != digest or value.snapshot_id != "risnap_" + digest[7:31]:
        raise ValueError("RENDER_INPUT_IDENTITY_INVALID")


class CanonicalReplayInputFactory:
    """Trusted server-side constructor; callers never submit render bytes."""

    def build(self, *, project_id: str, executable_sequence_hash: str, domain_pack_version: str, policy_snapshot_id: str, policy_snapshot_hash: str, executable_plan_id: str, executable_plan_hash: str, final_edl_bundle_id: str, final_edl_bundle_hash: str, video_edl: VideoEdlArtifact, audio_edl: AudioEdlArtifact, fixture_assets: FixtureAssetResolver, renderer_version: str, created_at: str) -> RenderInputSnapshotRecord:
        video_bytes = serialize_video_edl(video_edl)
        audio_bytes = serialize_audio_edl(audio_edl)
        props = build_render_props(video_edl=video_edl, audio_edl=audio_edl, fixture_assets=fixture_assets, renderer_version_value=renderer_version)
        props_bytes = serialize_render_props(props)
        draft = RenderInputSnapshotRecord(snapshot_id="", snapshot_hash="", project_id=project_id, executable_sequence_id=props.sequence_id, executable_sequence_hash=executable_sequence_hash, domain_pack_version=domain_pack_version, policy_snapshot_id=policy_snapshot_id, policy_snapshot_hash=policy_snapshot_hash, executable_plan_id=executable_plan_id, executable_plan_hash=executable_plan_hash, final_edl_bundle_id=final_edl_bundle_id, final_edl_bundle_hash=final_edl_bundle_hash, video_edl_id=props.video_edl_id, video_edl_hash=props.video_edl_hash, video_edl_bytes=video_bytes, audio_edl_id=props.audio_edl_id, audio_edl_hash=props.audio_edl_hash, audio_edl_bytes=audio_bytes, render_props_bytes=props_bytes, render_props_id=props.render_props_id, render_props_hash=props.render_props_hash, fixture_manifest_id=props.fixture_manifest_id, fixture_manifest_hash=props.fixture_manifest_hash, mode="preview_replay", created_at=created_at, producer="phase13-replay-handoff", producer_version="0.1.0")
        digest = _sha(encode_canonical_json_bytes(_snapshot_identity(draft)))
        value = RenderInputSnapshotRecord(**({field: getattr(draft, field) for field in draft.__dataclass_fields__} | {"snapshot_id": "risnap_" + digest[7:31], "snapshot_hash": digest}))
        validate_render_input_snapshot(value)
        return value


class PersistedRenderInputResolver:
    """Returns only an already-verified, review-bound SQLite snapshot."""

    def __init__(self, repository) -> None:
        self._repository = repository

    def resolve(self, *, project_id: str, sequence_id: str, review_snapshot: ReviewSnapshotRecord) -> RenderInputSnapshotRecord | None:
        value = self._repository.get_render_input(project_id, sequence_id)
        if value is None:
            return None
        try:
            validate_render_input_snapshot(value)
        except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        if (value.executable_plan_id, value.executable_plan_hash, value.final_edl_bundle_id, value.final_edl_bundle_hash) != (
            review_snapshot.executable_plan["executable_editorial_plan_id"], review_snapshot.executable_plan["executable_editorial_plan_hash"], review_snapshot.final_edl_bundle["final_edl_bundle_id"], review_snapshot.final_edl_bundle["final_edl_bundle_hash"],
        ):
            return None
        return value


class ReplayPreviewExecutor:
    """Owns a single-use Phase 4 output folder and exposes only verified bytes."""

    def __init__(self, *, fixture_root: Path) -> None:
        self._fixture_root = fixture_root.resolve(strict=True)

    def execute(self, snapshot: RenderInputSnapshotRecord, *, timestamp_utc: str) -> PreviewExecutionResult:
        try:
            props = load_render_props(snapshot.render_props_bytes)
            if (props.project_id, props.sequence_id, props.render_props_id, props.render_props_hash, props.fixture_manifest_id, props.fixture_manifest_hash) != (snapshot.project_id, snapshot.executable_sequence_id, snapshot.render_props_id, snapshot.render_props_hash, snapshot.fixture_manifest_id, snapshot.fixture_manifest_hash):
                return PreviewExecutionResult("failed", None, None, {}, "RENDER_INPUT_UNAVAILABLE")
            with tempfile.TemporaryDirectory(prefix="kurgu_phase13_preview_") as root:
                work = Path(root)
                output = work / "output"
                result = run_headless_preview(props=props, video_edl_bytes=snapshot.video_edl_bytes, audio_edl_bytes=snapshot.audio_edl_bytes, fixture_root=self._fixture_root, output_root=output, work_root=work, timestamp_utc=timestamp_utc)
                if result.receipt.status is not RenderStatus.SUCCEEDED or result.preview_manifest_bytes is None:
                    return PreviewExecutionResult("failed", result.receipt.receipt_hash, None, {}, result.receipt.failure_code or "PREVIEW_EXECUTION_FAILED")
                manifest = json.loads(result.preview_manifest_bytes.decode("utf-8"))
                frames = {int(row["frame_index"]): (output / "preview" / "frames" / f"{row['frame_index']}.png").read_bytes() for row in manifest["frames"]}
                return PreviewExecutionResult("succeeded", result.receipt.receipt_hash, result.preview_manifest_bytes, frames)
        except Exception:
            return PreviewExecutionResult("failed", None, None, {}, "PREVIEW_EXECUTION_FAILED")


class InMemoryPreviewDelivery:
    """Attempt-local delivery, intentionally lost on process restart."""

    def __init__(self) -> None:
        self._items: dict[str, tuple[str, str, bytes, dict[int, bytes], frozenset[int]]] = {}

    def put(self, *, delivery_id: str, project_id: str, job_id: str, manifest: bytes, frames: Mapping[int, bytes]) -> None:
        parsed = _canonical_object(manifest)
        rows = parsed.get("frames")
        if not isinstance(rows, list):
            raise ValueError("PREVIEW_DELIVERY_MANIFEST_INVALID")
        declared = frozenset(row.get("frame_index") for row in rows if type(row) is dict and type(row.get("frame_index")) is int and row["frame_index"] >= 0)
        copied = {int(key): bytes(value) for key, value in frames.items()}
        if not declared or declared != frozenset(copied):
            raise ValueError("PREVIEW_DELIVERY_MANIFEST_INVALID")
        self._items[delivery_id] = (project_id, job_id, bytes(manifest), copied, declared)

    def manifest(self, *, delivery_id: str, project_id: str, job_id: str) -> bytes | None:
        value = self._items.get(delivery_id)
        return None if value is None or value[:2] != (project_id, job_id) else value[2]

    def frame(self, *, delivery_id: str, project_id: str, job_id: str, frame_index: int) -> bytes | None:
        value = self._items.get(delivery_id)
        return None if value is None or value[:2] != (project_id, job_id) or frame_index not in value[4] else value[3].get(frame_index)
