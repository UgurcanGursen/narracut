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
                          restore_replacement_publish, run_profile_media_pipeline,
                          resolve_output_target)
from .full_profile import default_profile_paths, load_full_render_profile
from .lifecycle_registry import (append_recovery_compensation, cleanup_attempt,
                                 commit_transaction, next_target_revision,
                                 resolve_target_head, snapshot_attempt)


VideoProducer = Callable[[Path, Path, Path], None]


@dataclass(frozen=True)
class ToolchainRuntimeBindingV1:
    """The sole host-specific input for a paired offline REPLAY toolchain.

    The roots are deliberately *not* identity material.  They are checked
    against the checked-in provenance fixture before any child or attempt is
    created, and are never persisted in a receipt or artifact.
    """

    provenance_fixture_id: str
    provenance_fixture_hash: str
    platform: str
    node_root: Path
    remotion_root: Path
    ffmpeg_root: Path
    ffprobe_root: Path


_MAX_REMOTION_OUTPUT = 1_048_576
_PREFLIGHT_V1 = "FULL-RENDER-TOOLCHAIN-PREFLIGHT-V1"


def _toolchain_failure(kind: str) -> FullRenderError:
    return FullRenderError("REMOTION_TOOLCHAIN_UNAVAILABLE" if kind in {"node", "remotion"}
                           else "FFMPEG_UNAVAILABLE")


def _is_reparse(path: Path) -> bool:
    """Reject symlinks and Windows reparse points without resolving through them."""
    try:
        stat = path.lstat()
    except OSError:
        return True
    attributes = getattr(stat, "st_file_attributes", 0)
    reparse = getattr(__import__("stat"), "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_symlink() or bool(attributes & reparse)


def _checked_root(path: Path, kind: str) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        raise _toolchain_failure(kind)
    # Check every supplied element lexically before resolve() can hide a link.
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if _is_reparse(current) or not current.is_dir():
            raise _toolchain_failure(kind)
    return path.resolve(strict=True)


def _closed_child(*, root: Path, relative: str, kind: str) -> Path:
    if (type(relative) is not str or not relative or "/" in relative or "\\" in relative
            or ":" in relative or relative in {".", ".."}):
        raise _toolchain_failure(kind)
    candidate = root / relative
    if _is_reparse(candidate) or not candidate.is_file():
        raise _toolchain_failure(kind)
    resolved = candidate.resolve(strict=True)
    if resolved.parent != root:
        raise _toolchain_failure(kind)
    return resolved


def _checked_file_hash(path: Path, expected: str, kind: str) -> str:
    try:
        if not path.is_file() or _sha(path.read_bytes()) != expected:
            raise _toolchain_failure(kind)
    except OSError as exc:
        raise _toolchain_failure(kind) from exc
    return _sha(path.read_bytes())


def _version_line(*, command: list[str], timeout_seconds: int, kind: str) -> str:
    try:
        completed = subprocess.run(command, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   timeout=timeout_seconds, check=False)
        raw = completed.stdout or completed.stderr
        line = raw.decode("utf-8", "strict").splitlines()[0]
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError, IndexError) as exc:
        raise _toolchain_failure(kind) from exc
    if completed.returncode != 0 or not line:
        raise _toolchain_failure(kind)
    return line


def preflight_full_render_toolchain(*, profile: dict[str, Any], request: dict[str, Any],
                                    runtime: ToolchainRuntimeBindingV1) -> dict[str, Any]:
    """Authenticate paired runtime bytes/versions before attempt admission."""
    if type(runtime) is not ToolchainRuntimeBindingV1:
        raise _toolchain_failure("node")
    try:
        _, provenance_path = default_profile_paths()
        provenance = json.loads(provenance_path.read_bytes())
        expected_platform = provenance["supported_platform"]
        if (runtime.provenance_fixture_id != provenance["provenance_fixture_id"]
                or runtime.provenance_fixture_hash != provenance["provenance_fixture_hash"]
                or runtime.platform != expected_platform):
            raise ValueError
        expected_roots = {row["kind"]: row["toolchain_root_relative_posix_path"]
                          for row in provenance["runtime_trees"]}
        if expected_roots != {"node": profile["node_identity"]["toolchain_root_relative_posix_path"],
                              "remotion": profile["remotion_identity"]["toolchain_root_relative_posix_path"],
                              "ffmpeg": profile["ffmpeg_identity"]["toolchain_root_relative_posix_path"],
                              "ffprobe": profile["ffprobe_identity"]["toolchain_root_relative_posix_path"]}:
            raise ValueError
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise _toolchain_failure("node") from exc
    node_root = _checked_root(runtime.node_root, "node")
    remotion_root = _checked_root(runtime.remotion_root, "remotion")
    ffmpeg_root = _checked_root(runtime.ffmpeg_root, "ffmpeg")
    ffprobe_root = _checked_root(runtime.ffprobe_root, "ffprobe")
    node = _closed_child(root=node_root, relative=profile["node_identity"]["executable_relative_posix_path"], kind="node")
    cli = _closed_child(root=remotion_root, relative=profile["remotion_identity"]["cli_entry_relative_posix_path"], kind="remotion")
    ffmpeg = _closed_child(root=ffmpeg_root, relative=profile["ffmpeg_identity"]["executable_relative_posix_path"], kind="ffmpeg")
    ffprobe = _closed_child(root=ffprobe_root, relative=profile["ffprobe_identity"]["executable_relative_posix_path"], kind="ffprobe")
    identities = (("node", profile["node_identity"], node, [str(node), "--version"]),
                  ("ffmpeg", profile["ffmpeg_identity"], ffmpeg, [str(ffmpeg), "-version"]),
                  ("ffprobe", profile["ffprobe_identity"], ffprobe, [str(ffprobe), "-version"]))
    rows: list[dict[str, str]] = []
    for kind, identity, executable, command in identities:
        observed_file_hash = _checked_file_hash(executable, identity["executable_sha256"], kind)
        line = _version_line(command=command, timeout_seconds=profile["stage_timeout_seconds"]["toolchain_preflight"], kind=kind)
        if line != identity["normalized_first_version_line"] or _sha(line.encode("utf-8")) != identity["version_output_sha256"]:
            raise _toolchain_failure(kind)
        rows.append({"kind": kind, "observed_executable_sha256": observed_file_hash,
                     "observed_version_output_sha256": _sha(line.encode("utf-8")),
                     "observed_normalized_version_line": line})
    identity = profile["remotion_identity"]
    observed_cli_hash = _checked_file_hash(cli, identity["cli_entry_sha256"], "remotion")
    try:
        # This CLI release prints its version then intentionally exits 1 when
        # called without a command, so its checked package metadata is the
        # stable version projection; the CLI entry bytes are independently
        # hash-bound above.  No package manager is invoked or discovered.
        package = json.loads((remotion_root / "package.json").read_bytes())
        remotion_line = "@remotion/cli " + package["version"]
        checked_in_renderer_root = Path(__file__).resolve().parents[2] / "renderer-remotion"
        lock_hash = _sha((checked_in_renderer_root / "package-lock.json").read_bytes())
        _, provenance_path = default_profile_paths()
        trusted_lock_hash = json.loads(provenance_path.read_bytes())["package_lock_sha256"]
    except (OSError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise _toolchain_failure("remotion") from exc
    if (lock_hash != trusted_lock_hash
            or remotion_line != identity["normalized_version_line"]
            or _sha(remotion_line.encode("utf-8")) != identity["version_output_sha256"]):
        raise _toolchain_failure("remotion")
    rows.insert(1, {"kind": "remotion", "observed_cli_entry_sha256": observed_cli_hash,
                    "observed_version_output_sha256": _sha(remotion_line.encode("utf-8")),
                    "observed_normalized_version_line": remotion_line})
    base: dict[str, Any] = {
        "schema_version": _PREFLIGHT_V1, "toolchain_preflight_id": "", "toolchain_preflight_hash": "",
        "full_render_request_id": request["full_render_request_id"],
        "full_render_request_hash": request["full_render_request_hash"],
        "full_render_profile_id": request["full_render_profile_id"],
        "full_render_profile_hash": request["full_render_profile_hash"],
        "provenance_fixture_id": provenance["provenance_fixture_id"],
        "provenance_fixture_hash": provenance["provenance_fixture_hash"],
        "profile_catalog_sha256": provenance["profile_catalog_sha256"],
        "package_lock_sha256": provenance["package_lock_sha256"], "runtime_rows": rows,
    }
    digest = _sha(encode_canonical_json_bytes({
        key: value for key, value in base.items()
        if key not in {"toolchain_preflight_id", "toolchain_preflight_hash"}
    }))
    return base | {"toolchain_preflight_id": "tpf_" + digest[7:39], "toolchain_preflight_hash": digest}


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


def make_remotion_full_producer(*, runtime: ToolchainRuntimeBindingV1,
                                fixture_assets: FixtureAssetResolver,
                                fixture_root: Path) -> VideoProducer:
    """Return the only supported real REPLAY visual producer for Phase 4B.

    ``runtime`` is supplied by the composition root, rather than discovered
    from PATH. The child gets canonical props and attempt-local asset copies.
    """
    node_root = _checked_root(runtime.node_root, "node")
    node = _closed_child(root=node_root, relative="node.exe", kind="node")
    renderer_root = Path(__file__).resolve().parents[2] / "renderer-remotion"
    runner = renderer_root / "scripts" / "render-full.mjs"
    if not node.is_file() or not runner.is_file():
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
                timeout=300, check=False,
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
                    ffmpeg: Path, ffprobe: Path, remotion_runtime: ToolchainRuntimeBindingV1 | None = None,
                    cancel_before_admission: bool = False,
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
    if remotion_runtime is None:
        raise _toolchain_failure("node")
    preflight = preflight_full_render_toolchain(profile=profile, request=request,
                                                runtime=remotion_runtime)
    # A caller may pass these legacy parameters only when they are the exact
    # preflight-bound binaries.  They never select a toolchain.
    verified_ffmpeg = _closed_child(root=_checked_root(remotion_runtime.ffmpeg_root, "ffmpeg"),
                                    relative=profile["ffmpeg_identity"]["executable_relative_posix_path"], kind="ffmpeg")
    verified_ffprobe = _closed_child(root=_checked_root(remotion_runtime.ffprobe_root, "ffprobe"),
                                     relative=profile["ffprobe_identity"]["executable_relative_posix_path"], kind="ffprobe")
    if ffmpeg.resolve() != verified_ffmpeg or ffprobe.resolve() != verified_ffprobe:
        raise _toolchain_failure("ffmpeg")
    attempt_root = project_root / "renders" / "attempts" / attempt_id
    try:
        attempt_root.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        raise FullRenderError("ARTIFACT_PERSIST_FAILED") from exc
    base_target = target
    output: Path | None = None
    replacement_backup: Path | None = None
    provisional_target: dict[str, Any] | None = None
    transaction_id = "txn_" + hashlib.sha256(
        (request["full_render_request_id"] + attempt_id).encode("ascii")).hexdigest()[:32]
    artifact_rows: list[dict[str, Any]] = []
    try:
        request_path = attempt_root / "request" / "full-render-request.json"
        request_path.parent.mkdir(parents=True)
        request_path.write_bytes(encode_canonical_json_bytes(request))
        artifact_rows.append(_artifact_row(artifact_id="art_request_" + request["full_render_request_hash"][7:39],
                                           path=request_path, kind="full_render_request", props=props))
        preflight_path = attempt_root / "toolchain" / "full-render-toolchain-preflight.json"
        preflight_path.parent.mkdir(parents=True)
        preflight_path.write_bytes(encode_canonical_json_bytes(preflight))
        artifact_rows.append(_artifact_row(
            artifact_id="art_toolchain_preflight_" + preflight["toolchain_preflight_hash"][7:39],
            path=preflight_path, kind="full_render_toolchain_preflight", props=props))
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
                                           staged_output=staged, ffmpeg=verified_ffmpeg, ffprobe=verified_ffprobe)
        artifact_rows.append(_artifact_row(artifact_id="art_normalized_audio_" + _sha(normalized_audio.read_bytes())[7:39],
                                           path=normalized_audio, kind="normalized_audio", props=props))
        replacement_policy = (
            "REPLACE_UNAPPROVED_V1"
            if base_target["current_output_artifact_id"] is not None else None
        )
        if base_target["current_output_artifact_id"] is not None:
            replacement_backup = (
                project_root / "renders" / "replacement-backups" / f"{attempt_id}.mp4"
            )
        output = atomic_publish(staged_output=staged, project_root=project_root, target=target,
                                replacement_backup=replacement_backup,
                                replacement_policy=replacement_policy)
        pre = snapshot_attempt(attempt_root=attempt_root, attempt_id=attempt_id,
                               cleanup_state="PRE_CLEANUP")
        post = cleanup_attempt(attempt_root=attempt_root, pre_cleanup=pre)
        final_id = "art_final_" + probe["output_sha256"][7:39]
        revision = next_target_revision(base=base_target, output_artifact_id=final_id,
                                        output_content_sha256=probe["output_sha256"],
                                        replacement_policy=replacement_policy)
        provisional_target = revision
        receipt = commit_transaction(
            project_root=project_root, transaction_id=transaction_id,
            base_target=base_target, target_revision=revision,
            artifact_rows=tuple([*artifact_rows, _artifact_row(artifact_id=final_id, path=output,
                                         kind="final_output", props=props)]),
            terminal_status="SUCCEEDED",
            receipt_payload={"full_render_request_id": request["full_render_request_id"],
                             "audio_render_plan_id": plan["audio_render_plan_id"],
                             "audio_filter_script_id": script_artifact["audio_filter_script_id"],
                             # Bind the entire closed, root-free projection;
                             # an ID/hash pair alone cannot prove which runtime
                             # observations were accepted for this terminal
                             # render.
                             "toolchain_preflight": preflight,
                             "output_sha256": probe["output_sha256"],
                             "replacement": {
                                 "policy": replacement_policy,
                                 "previous_output_artifact_id": base_target["current_output_artifact_id"],
                                 "previous_output_content_sha256": base_target["current_output_content_sha256"],
                                 "new_output_artifact_id": final_id,
                                 "new_output_content_sha256": probe["output_sha256"],
                             },
                             # The durable target relation itself is recorded
                             # by the registry receipt; this payload carries
                             # only the output-byte lineage.
                             },
            pre_cleanup=pre, post_cleanup=post)
        if replacement_backup is not None:
            replacement_backup.unlink()
            try:
                replacement_backup.parent.rmdir()
            except OSError:
                pass
        return FullRenderOutcome(True, "SUCCEEDED", request, receipt, output)
    except FullRenderError as failure:
        compensation: dict[str, Any] | None = None
        if replacement_backup is not None and replacement_backup.is_file() and output is not None:
            restore_replacement_publish(project_root=project_root, target=base_target,
                                        replacement_backup=replacement_backup)
            if provisional_target is not None:
                current = resolve_target_head(project_root=project_root,
                                              output_target_id=base_target["output_target_id"])
                if (current["output_target_record_id"], current["output_target_record_hash"]) == (
                    provisional_target["output_target_record_id"], provisional_target["output_target_record_hash"]
                ):
                    compensation = append_recovery_compensation(
                        project_root=project_root, transaction_id=transaction_id,
                        base_target=base_target, provisional_target=provisional_target,
                    )
        # An admitted failure still produces the same exact cleanup proof and
        # a terminal journal, but never a target revision.
        pre = snapshot_attempt(attempt_root=attempt_root, attempt_id=attempt_id,
                               cleanup_state="PRE_CLEANUP")
        post = cleanup_attempt(attempt_root=attempt_root, pre_cleanup=pre)
        status = "CANCELLED" if failure.code == "CANCELLED_BY_PARENT" else "FAILED"
        failure_base = (resolve_target_head(project_root=project_root,
                                            output_target_id=base_target["output_target_id"])
                        if compensation is not None else base_target)
        receipt = commit_transaction(
            project_root=project_root, transaction_id=transaction_id + "_terminal",
            base_target=failure_base, target_revision=None, artifact_rows=tuple(artifact_rows), terminal_status=status,
            receipt_payload={"full_render_request_id": request["full_render_request_id"],
                             "toolchain_preflight": preflight,
                             "failure_code": failure.code,
                             "replacement_compensation": (
                                 {"restored_output_artifact_id": base_target["current_output_artifact_id"],
                                  "restored_output_content_sha256": base_target["current_output_content_sha256"],
                                  "compensation_target_record_id": compensation["output_target_record_id"],
                                  "compensation_target_record_hash": compensation["output_target_record_hash"]}
                                 if compensation is not None else None)}, pre_cleanup=pre, post_cleanup=post)
        return FullRenderOutcome(True, status, request, receipt, None)
