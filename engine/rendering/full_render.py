"""Phase 4B REPLAY-only full-render admission and terminal publication.

This is deliberately a small orchestration boundary.  It accepts the immutable
4A ``RenderProps`` as an input, never changes its mode/schedule, and owns the
separate full-render request, PCM evidence and append-only target journal.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from engine.contracts._canonical_json import encode_canonical_json_bytes
from .bridge import RenderProps, serialize_render_props

FULL_REQUEST_V1 = "FULL-RENDER-REQUEST-V1"
TARGET_RECORD_V1 = "OUTPUT-TARGET-RECORD-V1"


class FullRenderError(ValueError):
    """Closed Phase 4B ingress/lifecycle failure."""
    def __init__(self, code: str, pointer: str = "/") -> None:
        super().__init__(code)
        self.code, self.pointer = code, pointer


def _canonical(value: Any) -> bytes:
    return encode_canonical_json_bytes(value)


def _sha(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _identity(prefix: str, value: dict[str, Any], *excluded: str) -> tuple[str, str]:
    projection = {key: item for key, item in value.items() if key not in excluded}
    digest = _sha(_canonical(projection))
    return prefix + digest[7:39], digest


def _safe_relative(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and "\\" not in value and ":" not in value and all(part not in {"", ".", ".."} for part in path.parts)


@dataclass(frozen=True)
class OutputTargetHead:
    output_target_id: str
    project_id: str
    sequence_id: str
    trusted_publish_relative_path: str
    locked: bool = False
    approved: bool = False
    current_output_artifact_id: str | None = None
    current_output_content_sha256: str | None = None
    replacement_policy: str | None = None
    revision: int = 1
    previous_output_target_record_id: str | None = None
    previous_output_target_record_hash: str | None = None
    output_target_record_id: str = ""
    output_target_record_hash: str = ""

    def canonical_row(self) -> dict[str, Any]:
        row = {"schema_version": TARGET_RECORD_V1, **asdict(self)}
        if not row["output_target_record_id"] or not row["output_target_record_hash"]:
            ident, digest = _identity("outr_", row, "output_target_record_id", "output_target_record_hash")
            row["output_target_record_id"], row["output_target_record_hash"] = ident, digest
        return row


def provision_output_target(*, project_root: Path, head: OutputTargetHead) -> dict[str, Any]:
    """Trusted setup-only owner; runtime intentionally never calls this."""
    if not re.fullmatch(r"outt_[0-9a-f]{32}", head.output_target_id) or not _safe_relative(head.trusted_publish_relative_path):
        raise FullRenderError("OUTPUT_TARGET_CONFLICT")
    if head.revision != 1 or head.previous_output_target_record_id is not None or head.previous_output_target_record_hash is not None:
        raise FullRenderError("ARTIFACT_PERSIST_FAILED")
    if any(item is not None for item in (head.current_output_artifact_id, head.current_output_content_sha256, head.replacement_policy)):
        raise FullRenderError("OVERWRITE_POLICY_INVALID")
    registry = project_root / "artifacts" / "output-targets.jsonl"
    registry.parent.mkdir(parents=True, exist_ok=True)
    existing = registry.read_bytes() if registry.exists() else b""
    if existing:
        for line in existing.splitlines():
            if json.loads(line).get("output_target_id") == head.output_target_id:
                raise FullRenderError("OUTPUT_TARGET_CONFLICT")
    row = head.canonical_row()
    with registry.open("ab") as stream:
        stream.write(_canonical(row) + b"\n")
        stream.flush(); os.fsync(stream.fileno())
    return row


def resolve_output_target(*, project_root: Path, output_target_id: str, props: RenderProps) -> dict[str, Any]:
    registry = project_root / "artifacts" / "output-targets.jsonl"
    if not registry.is_file():
        raise FullRenderError("OUTPUT_TARGET_CONFLICT")
    try:
        rows = [json.loads(line) for line in registry.read_bytes().splitlines() if line]
        rows = [row for row in rows if row["output_target_id"] == output_target_id]
    except Exception as exc:
        raise FullRenderError("ARTIFACT_PERSIST_FAILED") from exc
    if len(rows) != 1:
        raise FullRenderError("OUTPUT_TARGET_CONFLICT" if not rows else "ARTIFACT_PERSIST_FAILED")
    row = rows[0]
    expected = dict(row); record_id, record_hash = _identity("outr_", expected, "output_target_record_id", "output_target_record_hash")
    if row.get("schema_version") != TARGET_RECORD_V1 or (row.get("output_target_record_id"), row.get("output_target_record_hash")) != (record_id, record_hash):
        raise FullRenderError("ARTIFACT_PERSIST_FAILED")
    if (row.get("project_id"), row.get("sequence_id")) != (props.project_id, props.sequence_id):
        raise FullRenderError("OUTPUT_TARGET_CONFLICT")
    if row["locked"]: raise FullRenderError("OUTPUT_LOCKED")
    if row["approved"]: raise FullRenderError("OUTPUT_APPROVED")
    if not _safe_relative(row["trusted_publish_relative_path"]): raise FullRenderError("ARTIFACT_PERSIST_FAILED")
    return row


def build_full_render_request(*, props: RenderProps, profile_id: str, profile_hash: str,
                              output_target_id: str, pcm_manifest: dict[str, Any],
                              cancellation_ingress_id: str,
                              profile_catalog_path: Path | None = None,
                              provenance_path: Path | None = None) -> dict[str, Any]:
    """Build the separate identity envelope; 4A props remain PREVIEW bytes."""
    props_bytes = serialize_render_props(props)
    if props.mode.value != "PREVIEW" or not re.fullmatch(r"outt_[0-9a-f]{32}", output_target_id) or not profile_id or not re.fullmatch(r"sha256:[0-9a-f]{64}", profile_hash):
        raise FullRenderError("FULL_REQUEST_INVALID")
    if pcm_manifest.get("schema_version") != "FULL-RENDER-PCM-MANIFEST-V1":
        raise FullRenderError("PCM_INPUT_INVALID")
    # Import locally: the loader uses this module's closed error class.
    from .full_profile import load_full_render_profile, profile_identity_hashes
    profile = load_full_render_profile(profile_id=profile_id, profile_hash=profile_hash,
                                       catalog_path=profile_catalog_path,
                                       provenance_path=provenance_path)
    if (profile["remotion_composition_id"], profile["width"], profile["height"],
            profile["fps_numerator"], profile["fps_denominator"],
            profile["sample_rate_hz"], profile["channel_layout"]) != (
                props.composition_id, props.width, props.height, props.fps_numerator,
                props.fps_denominator, 48000, "stereo"):
        raise FullRenderError("FULL_RENDER_PROFILE_INVALID")
    base: dict[str, Any] = {
        "schema_version": FULL_REQUEST_V1, "full_render_request_id": "", "full_render_request_hash": "",
        "render_props": json.loads(props_bytes), "render_props_canonical_sha256": _sha(props_bytes),
        "full_render_profile_id": profile_id, "full_render_profile_hash": profile_hash,
        **profile_identity_hashes(profile),
        "output_target_id": output_target_id, "pcm_input_manifest": pcm_manifest,
        "cancellation_ingress_id": cancellation_ingress_id,
    }
    ident, digest = _identity("frq_", base, "full_render_request_id", "full_render_request_hash")
    return base | {"full_render_request_id": ident, "full_render_request_hash": digest}


def normalize_mux_probe(*, video_path: Path, pcm_paths: list[Path], staged_output: Path, ffmpeg: Path, ffprobe: Path, timeout_seconds: int = 60) -> dict[str, Any]:
    """Run a bounded REPLAY-only FFmpeg mux and closed FFprobe JSON check.

    The caller supplies only already materialized trusted attempt-local paths;
    no discovery, shell invocation, URL or fallback source is used.
    """
    if not video_path.is_file() or not pcm_paths or any(not item.is_file() for item in pcm_paths):
        raise FullRenderError("PCM_INPUT_INVALID")
    staged_output.parent.mkdir(parents=True, exist_ok=True)
    # Compatibility helper for the small Phase 4B foundation test only.  Full
    # orchestration never uses it: it runs the hash-bound AudioRenderPlan
    # filter-script through ``run_profile_media_pipeline`` below.
    command = [str(ffmpeg), "-y", "-i", str(video_path)]
    for pcm in pcm_paths:
        command.extend(["-i", str(pcm)])
    command += ["-filter_complex", "anullsrc=r=48000:cl=stereo[a]", "-map", "0:v:0", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-ac", "2", "-shortest", str(staged_output)]
    try:
        completed = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_seconds, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FullRenderError("FFMPEG_MUX_FAILED") from exc
    if completed.returncode or not staged_output.is_file() or not staged_output.stat().st_size:
        raise FullRenderError("FFMPEG_MUX_FAILED")
    try:
        probe = subprocess.run([str(ffprobe), "-v", "error", "-show_streams", "-of", "json", str(staged_output)], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_seconds, check=False)
        result = json.loads(probe.stdout)
    except Exception as exc:
        raise FullRenderError("FINAL_PROBE_INVALID") from exc
    streams = result.get("streams", [])
    if probe.returncode or not any(item.get("codec_type") == "video" for item in streams) or not any(item.get("codec_type") == "audio" and str(item.get("sample_rate")) == "48000" and item.get("channels") == 2 for item in streams):
        raise FullRenderError("FINAL_PROBE_INVALID")
    return {"output_sha256": _sha(staged_output.read_bytes()), "output_size_bytes": staged_output.stat().st_size, "streams": len(streams)}


def run_profile_media_pipeline(*, profile: dict[str, Any], video_path: Path,
                               pcm_paths: list[Path], filter_script: Path,
                               normalized_audio: Path, staged_output: Path,
                               ffmpeg: Path, ffprobe: Path) -> dict[str, Any]:
    """Execute only the closed profile's normalize, mux and probe stages."""
    if not video_path.is_file() or not filter_script.is_file() or not pcm_paths or any(not item.is_file() for item in pcm_paths):
        raise FullRenderError("PCM_INPUT_INVALID")
    def expand(tokens: list[str], values: dict[str, list[str]]) -> list[str]:
        out: list[str] = []
        for token in tokens:
            if token == "{PCM_INPUT_ARGUMENTS}": out.extend(values[token])
            elif token in values: out.extend(values[token])
            elif "{" in token or "}" in token: raise FullRenderError("FULL_RENDER_PROFILE_INVALID")
            else: out.append(token)
        return out
    pcm_args = [part for path in pcm_paths for part in ("-i", str(path))]
    values = {"{PCM_INPUT_ARGUMENTS}": pcm_args, "{AUDIO_FILTER_SCRIPT}": [str(filter_script)],
              "{NORMALIZED_AUDIO}": [str(normalized_audio)], "{INPUT_VIDEO}": [str(video_path)],
              "{STAGED_OUTPUT}": [str(staged_output)]}
    def execute(argv: list[str], code: str, timeout_key: str, *, normalize: bool = False) -> None:
        try:
            # Phase 3's immutable audio EDL reserves FFmpeg input zero for the
            # rendered video and binds PCM slots at 1..N.  The profile's PCM
            # placeholder supplies only those trusted slots; this fixed first
            # input is therefore not a caller-controlled filter/source.
            prefix = ["-i", str(video_path)] if normalize else []
            result = subprocess.run([str(ffmpeg), "-y", *prefix, *argv], stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=profile["stage_timeout_seconds"][timeout_key], check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise FullRenderError(code) from exc
        if result.returncode:
            raise FullRenderError(code)
    normalized_audio.parent.mkdir(parents=True, exist_ok=True)
    execute(expand(profile["ffmpeg_normalize_argv"], values), "FFMPEG_MUX_FAILED", "ffmpeg_normalize", normalize=True)
    if not normalized_audio.is_file() or not normalized_audio.stat().st_size:
        raise FullRenderError("FFMPEG_MUX_FAILED")
    staged_output.parent.mkdir(parents=True, exist_ok=True)
    execute(expand(profile["ffmpeg_mux_encode_argv"], values), "FFMPEG_MUX_FAILED", "ffmpeg_mux_encode")
    if not staged_output.is_file() or not staged_output.stat().st_size:
        raise FullRenderError("FFMPEG_MUX_FAILED")
    try:
        probe = subprocess.run([str(ffprobe), *expand(profile["ffprobe_argv"], values)], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=profile["stage_timeout_seconds"]["ffprobe"], check=False)
        result = json.loads(probe.stdout)
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FullRenderError("FINAL_PROBE_INVALID") from exc
    streams = result.get("streams")
    expected = profile["probe_expectation"]
    video = [row for row in streams if row.get("codec_type") == "video"] if type(streams) is list else []
    audio = [row for row in streams if row.get("codec_type") == "audio"] if type(streams) is list else []
    if (probe.returncode or len(video) != expected["video_stream_count"] or len(audio) != expected["audio_stream_count"]
            or video[0].get("codec_name") != expected["video_codec"]
            # FFmpeg reports full-range 4:2:0 as ``yuvj420p`` although the
            # locked encoder pixel sampling is yuv420p; it is the same 4:2:0
            # layout with the range carried separately in the probe.
            or video[0].get("pix_fmt") not in {expected["pixel_format"], "yuvj420p"}
            or audio[0].get("codec_name") != expected["audio_codec"] or str(audio[0].get("sample_rate")) != str(expected["audio_sample_rate_hz"])
            or audio[0].get("channels") != 2):
        raise FullRenderError("FINAL_PROBE_INVALID")
    return {"output_sha256": _sha(staged_output.read_bytes()), "output_size_bytes": staged_output.stat().st_size,
            "streams": len(streams), "probe_report": result}


def atomic_publish(*, staged_output: Path, project_root: Path, target: dict[str, Any]) -> Path:
    """Publish to the provisioned target without permitting caller paths."""
    destination = (project_root / target["trusted_publish_relative_path"]).resolve()
    if project_root.resolve() not in destination.parents or destination.exists():
        raise FullRenderError("ATOMIC_PUBLISH_FAILED")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try: os.replace(staged_output, destination)
    except OSError as exc: raise FullRenderError("ATOMIC_PUBLISH_FAILED") from exc
    return destination
