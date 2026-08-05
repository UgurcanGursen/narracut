"""Minimal REPLAY-only Phase 4B sequence-local full-render orchestration.

The module deliberately connects already accepted boundaries; it is not a
second timeline compiler or a renderer.  The injected video producer must
write one attempt-local video from the canonical 4A props file.  PCM sources
are addressed exclusively by their manifest artifact IDs and copied into the
attempt before FFmpeg sees them.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Any

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.audio_edl import AudioEdlArtifact

from .audio_plan import compile_audio_render_plan
from .bridge import RenderProps, load_render_props, serialize_render_props
from .fixture_assets import FixtureAssetResolver, FixtureAssetResolverError
from .full_render import (FullRenderError, atomic_publish, build_full_render_request,
                          run_profile_media_pipeline, resolve_output_target)
from .full_profile import load_full_render_profile
from .lifecycle_registry import (cleanup_attempt, commit_transaction,
                                 next_target_revision, snapshot_attempt)


VideoProducer = Callable[[Path, Path, Path], None]


@dataclass(frozen=True)
class RemotionFullRuntime:
    """Explicit paired runtime seam; no PATH/package-manager discovery occurs."""

    node_executable: Path
    renderer_root: Path
    timeout_seconds: int = 300


_MAX_REMOTION_OUTPUT = 1_048_576


def _child_environment() -> dict[str, str]:
    result = {"PATH": os.environ.get("PATH", ""), "TZ": "UTC", "LANG": "C", "NODE_ENV": "production"}
    if os.name == "nt":
        result["SystemRoot"] = os.environ.get("SystemRoot", "")
        result["COMSPEC"] = os.environ.get("COMSPEC", "")
    return result


def _copy_remotion_assets(*, props: RenderProps, resolver: FixtureAssetResolver,
                          fixture_root: Path, public_root: Path) -> None:
    """Materialize only already authenticated props bindings under this attempt."""
    root = fixture_root.resolve(strict=True)
    asset_dir = public_root / "phase4a-assets"
    asset_dir.mkdir(parents=True, exist_ok=False)
    for binding in props.asset_bindings:
        try:
            asset = resolver.resolve_source_ref(binding["edl_source_ref"])
        except (KeyError, FixtureAssetResolverError) as exc:
            raise FullRenderError("REMOTION_FULL_RENDER_FAILED") from exc
        if asset.content_sha256 != binding["content_sha256"] or asset.media_type != "image/svg+xml":
            raise FullRenderError("REMOTION_FULL_RENDER_FAILED")
        source = (root.joinpath(*asset.relative_posix_path.split("/"))).resolve(strict=True)
        try:
            source.relative_to(root)
        except ValueError as exc:
            raise FullRenderError("REMOTION_FULL_RENDER_FAILED") from exc
        target = asset_dir / (asset.content_sha256[7:] + ".svg")
        shutil.copyfile(source, target)
        if _sha(target.read_bytes()) != asset.content_sha256:
            raise FullRenderError("REMOTION_FULL_RENDER_FAILED")


def make_remotion_full_producer(*, runtime: RemotionFullRuntime,
                                fixture_assets: FixtureAssetResolver,
                                fixture_root: Path) -> VideoProducer:
    """Return the only supported real REPLAY visual producer for Phase 4B.

    ``runtime`` is supplied by the composition root, rather than discovered
    from PATH. The child gets canonical props and attempt-local asset copies.
    """
    node, renderer_root = runtime.node_executable.resolve(), runtime.renderer_root.resolve()
    runner = renderer_root / "scripts" / "render-full.mjs"
    if (not node.is_file() or not runner.is_file() or type(runtime.timeout_seconds) is not int
            or not 1 <= runtime.timeout_seconds <= 600):
        raise FullRenderError("REMOTION_FULL_RENDER_FAILED")

    def produce(props_path: Path, video_path: Path, attempt_root: Path) -> None:
        try:
            props = load_render_props(props_path.read_bytes())
            public_root = attempt_root / "remotion" / "public"
            _copy_remotion_assets(props=props, resolver=fixture_assets,
                                  fixture_root=fixture_root, public_root=public_root)
            completed = subprocess.run(
                [str(node), str(runner), "--props", str(props_path), "--output", str(video_path),
                 "--public-dir", str(public_root)], cwd=renderer_root, env=_child_environment(),
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=runtime.timeout_seconds, check=False,
            )
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            raise FullRenderError("REMOTION_FULL_RENDER_FAILED") from exc
        if (len(completed.stdout) > _MAX_REMOTION_OUTPUT or len(completed.stderr) > _MAX_REMOTION_OUTPUT
                or completed.returncode != 0):
            raise FullRenderError("REMOTION_FULL_RENDER_FAILED")
        try:
            handoff = json.loads(completed.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FullRenderError("REMOTION_FULL_RENDER_FAILED") from exc
        expected = {"schema_version", "render_request_id", "render_props_hash", "composition_id", "width", "height", "fps_numerator", "fps_denominator", "duration_frames", "video_relative_path", "video_sha256", "video_byte_length"}
        if (type(handoff) is not dict or set(handoff) != expected
                or handoff.get("schema_version") != "REMOTION-FULL-VIDEO-V1"
                or handoff.get("render_request_id") != props.render_request_id
                or handoff.get("render_props_hash") != props.render_props_hash
                or handoff.get("composition_id") != props.composition_id
                or handoff.get("width") != props.width or handoff.get("height") != props.height
                or handoff.get("fps_numerator") != props.fps_numerator
                or handoff.get("fps_denominator") != props.fps_denominator
                or handoff.get("duration_frames") != props.duration_frames
                or handoff.get("video_relative_path") != "video.mp4"
                or handoff.get("video_sha256") != _sha(video_path.read_bytes())
                or handoff.get("video_byte_length") != video_path.stat().st_size):
            raise FullRenderError("REMOTION_FULL_RENDER_FAILED")
    return produce


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
    profile = load_full_render_profile(profile_id=profile_id, profile_hash=profile_hash)
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
    artifact_rows: list[dict[str, Any]] = []
    try:
        request_path = attempt_root / "request" / "full-render-request.json"
        request_path.parent.mkdir(parents=True)
        request_path.write_bytes(encode_canonical_json_bytes(request))
        artifact_rows.append(_artifact_row(artifact_id="art_request_" + request["full_render_request_hash"][7:39],
                                           path=request_path, kind="full_render_request", props=props))
        props_path = attempt_root / "remotion" / "render-props.json"
        props_path.parent.mkdir(parents=True)
        props_path.write_bytes(serialize_render_props(props))
        artifact_rows.append(_artifact_row(artifact_id="art_props_" + props.render_props_hash[7:39],
                                           path=props_path, kind="render_props", props=props))
        pcm_manifest_path = attempt_root / "audio" / "pcm-input-manifest.json"
        pcm_report_path = attempt_root / "audio" / "pcm-materialization-report.json"
        pcm_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        pcm_manifest_path.write_bytes(encode_canonical_json_bytes(pcm_manifest))
        pcm_report_path.write_bytes(encode_canonical_json_bytes(pcm_materialization_report))
        artifact_rows.extend((_artifact_row(artifact_id="art_pcm_manifest_" + _sha(pcm_manifest_path.read_bytes())[7:39],
                                            path=pcm_manifest_path, kind="pcm_input_manifest", props=props),
                              _artifact_row(artifact_id="art_pcm_report_" + _sha(pcm_report_path.read_bytes())[7:39],
                                            path=pcm_report_path, kind="pcm_materialization_report", props=props)))
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
        artifact_rows.append(_artifact_row(artifact_id="art_renderer_video_" + _sha(video.read_bytes())[7:39],
                                           path=video, kind="renderer_video", props=props))
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
        artifact_rows.extend((_artifact_row(artifact_id="art_audio_plan_" + plan["audio_render_plan_hash"][7:39],
                                            path=plan_path, kind="audio_render_plan", props=props),
                              _artifact_row(artifact_id="art_filter_script_" + script_artifact["audio_filter_script_hash"][7:39],
                                            path=script_path, kind="audio_filter_script", props=props)))
        staged = attempt_root / "staged" / "output.mp4"
        normalized_audio = attempt_root / "audio" / "normalized.wav"
        probe = run_profile_media_pipeline(profile=profile, video_path=video, pcm_paths=pcm_paths,
                                           filter_script=script_path, normalized_audio=normalized_audio,
                                           staged_output=staged, ffmpeg=ffmpeg, ffprobe=ffprobe)
        artifact_rows.append(_artifact_row(artifact_id="art_normalized_audio_" + _sha(normalized_audio.read_bytes())[7:39],
                                           path=normalized_audio, kind="normalized_audio", props=props))
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
            artifact_rows=tuple([*artifact_rows, _artifact_row(artifact_id=final_id, path=output,
                                         kind="final_output", props=props)]),
            terminal_status="SUCCEEDED",
            receipt_payload={"full_render_request_id": request["full_render_request_id"],
                             "audio_render_plan_id": plan["audio_render_plan_id"],
                             "audio_filter_script_id": script_artifact["audio_filter_script_id"],
                             "output_sha256": probe["output_sha256"],
                             # The durable target relation itself is recorded
                             # by the registry receipt; this payload carries
                             # only the output-byte lineage.
                             },
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
            base_target=base_target, target_revision=None, artifact_rows=tuple(artifact_rows), terminal_status=status,
            receipt_payload={"full_render_request_id": request["full_render_request_id"],
                             "failure_code": failure.code}, pre_cleanup=pre, post_cleanup=post)
        return FullRenderOutcome(True, status, request, receipt, None)
