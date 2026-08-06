"""Narrow Phase 13 REPLAY preview adapters; no lifecycle or media store."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Mapping

from engine.rendering import load_render_props, run_headless_preview
from engine.rendering.receipt import RenderStatus

from ..application.models import PreviewExecutionResult, RenderInputSnapshotRecord, ReviewSnapshotRecord


class PersistedRenderInputResolver:
    """Returns only an already-verified, review-bound SQLite snapshot."""

    def __init__(self, repository) -> None:
        self._repository = repository

    def resolve(self, *, project_id: str, sequence_id: str, review_snapshot: ReviewSnapshotRecord) -> RenderInputSnapshotRecord | None:
        value = self._repository.get_render_input(project_id, sequence_id)
        if value is None:
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
        self._items: dict[str, tuple[str, str, bytes, dict[int, bytes]]] = {}

    def put(self, *, delivery_id: str, project_id: str, job_id: str, manifest: bytes, frames: Mapping[int, bytes]) -> None:
        self._items[delivery_id] = (project_id, job_id, bytes(manifest), {int(key): bytes(value) for key, value in frames.items()})

    def manifest(self, *, delivery_id: str, project_id: str, job_id: str) -> bytes | None:
        value = self._items.get(delivery_id)
        return None if value is None or value[:2] != (project_id, job_id) else value[2]

    def frame(self, *, delivery_id: str, project_id: str, job_id: str, frame_index: int) -> bytes | None:
        value = self._items.get(delivery_id)
        return None if value is None or value[:2] != (project_id, job_id) else value[3].get(frame_index)
