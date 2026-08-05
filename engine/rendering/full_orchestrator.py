"""Minimal REPLAY-only Phase 4B sequence-local full-render orchestration.

The module deliberately connects already accepted boundaries; it is not a
second timeline compiler or a renderer.  The injected video producer must
write one attempt-local video from the canonical 4A props file.  PCM sources
are addressed exclusively by their manifest artifact IDs and copied into the
attempt before FFmpeg sees them.
"""
from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Any

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.audio_edl import AudioEdlArtifact

from .audio_plan import compile_audio_render_plan
from .bridge import RenderProps, serialize_render_props
from .full_render import (FullRenderError, atomic_publish, build_full_render_request,
                          normalize_mux_probe, resolve_output_target)
from .lifecycle_registry import (cleanup_attempt, commit_transaction,
                                 next_target_revision, snapshot_attempt)


VideoProducer = Callable[[Path, Path, Path], None]


@dataclass(frozen=True)
class FullRenderOutcome:
    """Terminal result; pre-admission cancellation intentionally has no receipt."""

    admitted: bool
    status: str
    request: dict[str, Any] | None
    receipt: dict[str, Any] | None
    output_path: Path | None


def _sha(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _attempt_id(value: str) -> None:
    if (type(value) is not str or not value.startswith("attempt_")
            or not value[8:].replace("_", "").isalnum()):
        raise FullRenderError("FULL_REQUEST_INVALID")


def _artifact_row(*, artifact_id: str, path: Path, kind: str,
                  props: RenderProps) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "artifact_id": artifact_id, "kind": kind, "content_sha256": _sha(raw),
        "byte_length": len(raw), "project_id": props.project_id,
        "sequence_id": props.sequence_id, "producer": "phase4b-replay-v1",
    }


def _materialize_pcm(*, attempt_root: Path, pcm_manifest: dict[str, Any],
                     pcm_report: dict[str, Any], sources: Mapping[str, Path]) -> list[Path]:
    entries = pcm_manifest.get("entries")
    report_entries = pcm_report.get("entries")
    if type(entries) is not list or type(report_entries) is not list or len(entries) != len(report_entries):
        raise FullRenderError("PCM_INPUT_INVALID")
    result: list[Path] = []
    for entry, report in zip(entries, report_entries, strict=True):
        if type(entry) is not dict or type(report) is not dict:
            raise FullRenderError("PCM_INPUT_INVALID")
        source = sources.get(entry.get("pcm_artifact_id"))
        relative = report.get("materialized_pcm_relative_path")
        if (not isinstance(source, Path) or not source.is_file() or type(relative) is not str
                or not relative.startswith("pcm/") or "\\" in relative or ".." in relative.split("/")):
            raise FullRenderError("PCM_INPUT_INVALID")
        target = attempt_root.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        raw = target.read_bytes()
        if _sha(raw) != entry.get("pcm_content_sha256") or len(raw) != entry.get("byte_length"):
            raise FullRenderError("PCM_INPUT_INVALID")
        result.append(target)
    return result


def run_full_render(*, project_root: Path, props: RenderProps,
                    audio_edl: AudioEdlArtifact, pcm_manifest: dict[str, Any],
                    pcm_materialization_report: dict[str, Any], pcm_sources: Mapping[str, Path],
                    output_target_id: str, profile_id: str, profile_hash: str,
                    cancellation_ingress_id: str, attempt_id: str, video_producer: VideoProducer,
                    ffmpeg: Path, ffprobe: Path, cancel_before_admission: bool = False,
                    cancel_after_admission: bool = False) -> FullRenderOutcome:
    """Run one isolated render attempt and append exactly one terminal journal.

    The producer is an intentionally narrow adapter seam for the checked-in
    Remotion full renderer.  It receives no source paths, profile argv or
    output target; only canonical props and an attempt-local output path.
    """
    _attempt_id(attempt_id)
    request = build_full_render_request(
        props=props, profile_id=profile_id, profile_hash=profile_hash,
        output_target_id=output_target_id, pcm_manifest=pcm_manifest,
        cancellation_ingress_id=cancellation_ingress_id,
    )
    # Admission checks must precede attempt-directory/process creation.
    target = resolve_output_target(project_root=project_root,
                                   output_target_id=output_target_id, props=props)
    if cancel_before_admission:
        return FullRenderOutcome(False, "CANCELLED_BEFORE_ADMISSION", request, None, None)
    attempt_root = project_root / "renders" / "attempts" / attempt_id
    try:
        attempt_root.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        raise FullRenderError("ARTIFACT_PERSIST_FAILED") from exc
    base_target = target
    output: Path | None = None
    try:
        props_path = attempt_root / "remotion" / "render-props.json"
        props_path.parent.mkdir(parents=True)
        props_path.write_bytes(serialize_render_props(props))
        video = attempt_root / "remotion" / "video.mp4"
        if cancel_after_admission:
            raise FullRenderError("CANCELLED_BY_PARENT")
        try:
            video_producer(props_path, video, attempt_root)
        except FullRenderError:
            raise
        except Exception as exc:
            raise FullRenderError("REMOTION_FULL_RENDER_FAILED") from exc
        if not video.is_file() or not video.stat().st_size:
            raise FullRenderError("REMOTION_FULL_RENDER_FAILED")
        pcm_paths = _materialize_pcm(attempt_root=attempt_root, pcm_manifest=pcm_manifest,
                                     pcm_report=pcm_materialization_report, sources=pcm_sources)
        plan, script_artifact, script = compile_audio_render_plan(
            audio_edl=audio_edl, pcm_manifest=pcm_manifest,
            pcm_materialization_report=pcm_materialization_report)
        plan_path = attempt_root / "audio" / "audio-render-plan.json"
        script_path = attempt_root / "audio" / "filter-script.ffscript"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_bytes(encode_canonical_json_bytes(plan))
        script_path.write_bytes(script)
        staged = attempt_root / "staged" / "output.mp4"
        probe = normalize_mux_probe(video_path=video, pcm_paths=pcm_paths,
                                   staged_output=staged, ffmpeg=ffmpeg, ffprobe=ffprobe)
        output = atomic_publish(staged_output=staged, project_root=project_root, target=target)
        pre = snapshot_attempt(attempt_root=attempt_root, attempt_id=attempt_id,
                               cleanup_state="PRE_CLEANUP")
        post = cleanup_attempt(attempt_root=attempt_root, pre_cleanup=pre)
        final_id = "art_final_" + probe["output_sha256"][7:39]
        revision = next_target_revision(base=base_target, output_artifact_id=final_id,
                                        output_content_sha256=probe["output_sha256"],
                                        replacement_policy=None)
        receipt = commit_transaction(
            project_root=project_root, transaction_id="txn_" + hashlib.sha256(
                (request["full_render_request_id"] + attempt_id).encode("ascii")).hexdigest()[:32],
            base_target=base_target, target_revision=revision,
            artifact_rows=(_artifact_row(artifact_id=final_id, path=output,
                                         kind="final_output", props=props),),
            terminal_status="SUCCEEDED",
            receipt_payload={"full_render_request_id": request["full_render_request_id"],
                             "audio_render_plan_id": plan["audio_render_plan_id"],
                             "audio_filter_script_id": script_artifact["audio_filter_script_id"],
                             "output_sha256": probe["output_sha256"]},
            pre_cleanup=pre, post_cleanup=post)
        return FullRenderOutcome(True, "SUCCEEDED", request, receipt, output)
    except FullRenderError as failure:
        # An admitted failure still produces the same exact cleanup proof and
        # a terminal journal, but never a target revision.
        pre = snapshot_attempt(attempt_root=attempt_root, attempt_id=attempt_id,
                               cleanup_state="PRE_CLEANUP")
        post = cleanup_attempt(attempt_root=attempt_root, pre_cleanup=pre)
        status = "CANCELLED" if failure.code == "CANCELLED_BY_PARENT" else "FAILED"
        receipt = commit_transaction(
            project_root=project_root, transaction_id="txn_" + hashlib.sha256(
                (request["full_render_request_id"] + attempt_id).encode("ascii")).hexdigest()[:32],
            base_target=base_target, target_revision=None, artifact_rows=(), terminal_status=status,
            receipt_payload={"full_render_request_id": request["full_render_request_id"],
                             "failure_code": failure.code}, pre_cleanup=pre, post_cleanup=post)
        return FullRenderOutcome(True, status, request, receipt, None)
