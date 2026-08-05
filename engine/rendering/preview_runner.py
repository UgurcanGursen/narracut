"""Bounded Phase 4A Python -> Node headless preview adapter.

This module deliberately owns process invocation only.  It never derives a
timeline or replaces the accepted EDL/props contracts with a Python renderer.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import struct
import threading
import zlib
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from subprocess import PIPE, Popen, TimeoutExpired, run
from tempfile import TemporaryDirectory
from typing import Any

from engine.contracts._canonical_json import encode_canonical_json_bytes

from .artifact_hook import RenderArtifactBatch, build_artifact_batch
from .bridge import RenderBridgeError, RenderFailureCode, RenderProps, serialize_render_props
from .receipt import RenderReceipt, RenderStatus, build_render_receipt


@dataclass(frozen=True)
class PreviewRun:
    """Terminal result for one already-materialized Phase 4A PREVIEW attempt."""

    receipt: RenderReceipt
    artifacts: RenderArtifactBatch
    preview_manifest_bytes: bytes | None


_RESULT_FIELDS = frozenset(
    {"status", "node_version", "manifest_path", "manifest_id", "manifest_hash"}
)
_MAX_PROCESS_OUTPUT_BYTES = 1_048_576


def _sha(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _failure_code(stderr: bytes, *, timed_out: bool) -> str:
    if timed_out:
        return RenderFailureCode.RENDER_TIMEOUT.value
    line = stderr.decode("utf-8", errors="replace").split("\n", 1)[0].split(":", 1)[0]
    allowed = {item.value for item in RenderFailureCode}
    return line if line in allowed else RenderFailureCode.RENDER_EXIT_NONZERO.value


def _node_environment() -> dict[str, str]:
    """Pass a minimal, credential-free environment to the Node adapter."""
    result = {
        "PATH": os.environ.get("PATH", ""),
        "TZ": "UTC",
        "LANG": "C",
        "NODE_ENV": "production",
    }
    if os.name == "nt":
        result["SystemRoot"] = os.environ.get("SystemRoot", "")
        result["COMSPEC"] = os.environ.get("COMSPEC", "")
    return result


def _node_version(node: str) -> str | None:
    try:
        probe = run([node, "--version"], cwd=None, env=_node_environment(),
                    stdin=PIPE, stdout=PIPE, stderr=PIPE, timeout=10, check=False)
    except (OSError, TimeoutExpired):
        return None
    value = probe.stdout.decode("ascii", errors="ignore").strip()
    return value if probe.returncode == 0 else None


def _decode_png_rgba(png: bytes) -> tuple[int, int, bytes]:
    """Decode the deliberately narrow Phase 4A PNG contract without Pillow.

    The Node adapter emits 8-bit RGB/RGBA PNGs.  Recomputing its decoded RGBA
    hash here makes the preview manifest evidence independent of Node's claim.
    """
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("signature")
    offset = 8
    width = height = bit_depth = color_type = 0
    compressed: list[bytes] = []
    while offset < len(png):
        if len(png) - offset < 12:
            raise ValueError("chunk")
        length = struct.unpack(">I", png[offset:offset + 4])[0]
        end = offset + 12 + length
        if end > len(png):
            raise ValueError("chunk")
        kind = png[offset + 4:offset + 8]
        body = png[offset + 8:offset + 8 + length]
        if (zlib.crc32(kind + body) & 0xffffffff) != struct.unpack(">I", png[offset + 8 + length:end])[0]:
            raise ValueError("crc")
        offset = end
        if kind == b"IHDR":
            if length != 13:
                raise ValueError("ihdr")
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", body)
            if not width or not height or bit_depth != 8 or color_type not in (2, 6) or (compression, filtering, interlace) != (0, 0, 0):
                raise ValueError("ihdr")
        elif kind == b"IDAT":
            compressed.append(body)
        elif kind == b"IEND":
            if length != 0 or offset != len(png):
                raise ValueError("iend")
            break
    else:
        raise ValueError("iend")
    channels = 4 if color_type == 6 else 3
    row_length = width * channels
    try:
        decoded = zlib.decompress(b"".join(compressed))
    except zlib.error as exc:
        raise ValueError("deflate") from exc
    if len(decoded) != height * (row_length + 1):
        raise ValueError("length")
    scan = bytearray(height * row_length)
    source = 0
    for row in range(height):
        filter_type = decoded[source]; source += 1
        if filter_type not in range(5):
            raise ValueError("filter")
        start = row * row_length
        for column in range(row_length):
            left = scan[start + column - channels] if column >= channels else 0
            up = scan[start - row_length + column] if row else 0
            up_left = scan[start - row_length + column - channels] if row and column >= channels else 0
            value = decoded[source]; source += 1
            if filter_type == 1:
                value += left
            elif filter_type == 2:
                value += up
            elif filter_type == 3:
                value += (left + up) // 2
            elif filter_type == 4:
                p = left + up - up_left
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - up_left)
                value += left if pa <= pb and pa <= pc else up if pb <= pc else up_left
            scan[start + column] = value & 0xff
    rgba = bytearray(width * height * 4)
    for source_index in range(0, len(scan), channels):
        destination = source_index // channels * 4
        rgba[destination:destination + 3] = scan[source_index:source_index + 3]
        rgba[destination + 3] = scan[source_index + 3] if channels == 4 else 255
    return width, height, bytes(rgba)


def _expected_preview_frames(props: RenderProps) -> list[int]:
    """Derive preview evidence points from already accepted props only."""
    event_by_id = {
        event["event_id"]: event
        for track in props.video_tracks
        for event in track["events"]
    }
    directive_points: list[int] = []
    for directive in props.visual_directives:
        if ((directive["track"] == "V4" and directive["kind"] == "CHART_REVEAL")
                or (directive["track"] == "V3" and directive["kind"] == "SOURCE_ZOOM_HIGHLIGHT")):
            event = event_by_id[directive["event_id"]]
            # Directive interpolation is constrained to this already accepted
            # EDL interval.  Capturing both endpoints proves spatial motion
            # without granting the directive an independent schedule.
            directive_points.extend((event["start_frame"], event["end_exclusive_frame"] - 1))
    return sorted({0, props.duration_frames // 2, props.duration_frames - 1, *directive_points})


def _validate_preview_output_tree(output_root: Path, *, expected_files: set[str]) -> None:
    """Require the preview directory to contain exactly its declared evidence.

    The Node process is not trusted to leave benign extra files behind.  A
    directory traversal is deliberately avoided here: directory entries are
    enumerated without following links, and every accepted entry must be a
    regular file or one of the two expected directories.
    """
    preview_root = output_root / "preview"
    expected_directories = {"preview", "preview/frames"}
    actual_files: set[str] = set()
    actual_directories: set[str] = set()

    def visit(directory: Path) -> None:
        try:
            directory_mode = directory.stat(follow_symlinks=False).st_mode
            if not stat.S_ISDIR(directory_mode):
                raise OSError("not a directory")
            relative_directory = directory.relative_to(output_root).as_posix()
            actual_directories.add(relative_directory)
            with os.scandir(directory) as entries:
                for entry in entries:
                    entry_path = Path(entry.path)
                    mode = entry.stat(follow_symlinks=False).st_mode
                    if stat.S_ISLNK(mode):
                        raise OSError("symbolic link")
                    if stat.S_ISDIR(mode):
                        visit(entry_path)
                    elif stat.S_ISREG(mode):
                        actual_files.add(entry_path.relative_to(output_root).as_posix())
                    else:
                        raise OSError("non-regular output entry")
        except (OSError, ValueError) as exc:
            raise RenderBridgeError(
                RenderFailureCode.PREVIEW_MANIFEST_INVALID, "/preview_manifest/output_tree"
            ) from exc

    visit(preview_root)
    if actual_directories != expected_directories or actual_files != expected_files:
        raise RenderBridgeError(
            RenderFailureCode.PREVIEW_MANIFEST_INVALID, "/preview_manifest/output_tree"
        )


def _preview_manifest(output_root: Path, result: dict[str, Any], *, props: RenderProps) -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    if set(result) != _RESULT_FIELDS or result.get("status") != "SUCCEEDED":
        raise RenderBridgeError(RenderFailureCode.PREVIEW_MANIFEST_INVALID, "/runner/stdout")
    relative = result.get("manifest_path")
    if relative != "preview/render-manifest.json":
        raise RenderBridgeError(RenderFailureCode.PREVIEW_MANIFEST_INVALID, "/runner/manifest_path")
    manifest_path = output_root / "preview" / "render-manifest.json"
    try:
        raw = manifest_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RenderBridgeError(RenderFailureCode.PREVIEW_MANIFEST_INVALID, "/preview_manifest") from exc
    if encode_canonical_json_bytes(parsed) != raw:
        raise RenderBridgeError(RenderFailureCode.PREVIEW_MANIFEST_INVALID, "/preview_manifest")
    required = {
        "schema_version", "manifest_id", "manifest_hash", "render_request_id",
        "render_props_hash", "composition_id", "renderer_version", "width",
        "height", "fps_numerator", "fps_denominator", "duration_frames",
        "pixel_format", "frames",
    }
    if set(parsed) != required or parsed.get("schema_version") != "RENDER-MANIFEST-V1" or not isinstance(parsed.get("frames"), list):
        raise RenderBridgeError(RenderFailureCode.PREVIEW_MANIFEST_INVALID, "/preview_manifest")
    expected_lineage = {
        "render_request_id": props.render_request_id,
        "render_props_hash": props.render_props_hash,
        "composition_id": props.composition_id,
        "renderer_version": props.renderer_version,
        "width": props.width,
        "height": props.height,
        "fps_numerator": props.fps_numerator,
        "fps_denominator": props.fps_denominator,
        "duration_frames": props.duration_frames,
        "pixel_format": props.pixel_format,
    }
    if any(parsed.get(key) != expected for key, expected in expected_lineage.items()):
        raise RenderBridgeError(RenderFailureCode.PREVIEW_MANIFEST_INVALID, "/preview_manifest/lineage")
    projection = dict(parsed); projection.pop("manifest_id"); projection.pop("manifest_hash")
    digest = _sha(encode_canonical_json_bytes(projection))
    if parsed["manifest_hash"] != digest or parsed["manifest_id"] != "rman_" + digest[7:39]:
        raise RenderBridgeError(RenderFailureCode.PREVIEW_MANIFEST_INVALID, "/preview_manifest/identity")
    if result["manifest_id"] != parsed["manifest_id"] or result["manifest_hash"] != parsed["manifest_hash"]:
        raise RenderBridgeError(RenderFailureCode.PREVIEW_MANIFEST_INVALID, "/runner/stdout")
    expected_frames = _expected_preview_frames(props)
    expected_files = {"preview/render-manifest.json"}
    for frame in parsed["frames"]:
        if type(frame) is not dict or type(frame.get("frame_index")) is not int or frame["frame_index"] < 0:
            raise RenderBridgeError(RenderFailureCode.PREVIEW_MANIFEST_INVALID, "/preview_manifest/frames")
        expected_files.add(f"preview/frames/{frame['frame_index']}.png")
    _validate_preview_output_tree(output_root, expected_files=expected_files)
    frames: list[tuple[int, bytes]] = []
    for frame in parsed["frames"]:
        if type(frame) is not dict or set(frame) != {"frame_index", "relative_path", "png_sha256", "decoded_rgba_sha256", "width", "height"} or type(frame["frame_index"]) is not int or frame["frame_index"] < 0 or frame["relative_path"] != f"preview/frames/{frame['frame_index']}.png":
            raise RenderBridgeError(RenderFailureCode.PREVIEW_MANIFEST_INVALID, "/preview_manifest/frames")
        path = output_root / "preview" / "frames" / f"{frame['frame_index']}.png"
        try:
            png = path.read_bytes()
        except OSError as exc:
            raise RenderBridgeError(RenderFailureCode.PREVIEW_FRAME_HASH_MISMATCH, "/preview_frames") from exc
        if (frame["png_sha256"] != _sha(png) or type(frame["width"]) is not int
                or type(frame["height"]) is not int):
            raise RenderBridgeError(RenderFailureCode.PREVIEW_FRAME_HASH_MISMATCH, "/preview_frames")
        try:
            width, height, rgba = _decode_png_rgba(png)
        except ValueError as exc:
            raise RenderBridgeError(RenderFailureCode.PREVIEW_FRAME_HASH_MISMATCH, "/preview_frames") from exc
        if (width, height) != (props.width, props.height) or (frame["width"], frame["height"]) != (width, height) or frame["decoded_rgba_sha256"] != _sha(rgba):
            raise RenderBridgeError(RenderFailureCode.PREVIEW_FRAME_HASH_MISMATCH, "/preview_frames")
        frames.append((frame["frame_index"], png))
    if [index for index, _ in frames] != expected_frames:
        raise RenderBridgeError(RenderFailureCode.PREVIEW_MANIFEST_INVALID, "/preview_manifest/frames")
    return raw, tuple(frames)


def _bounded_run(command: list[str], *, cwd: Path, env: dict[str, str], timeout: int) -> tuple[int, bytes, bytes, bool]:
    """Run Node while bounding untrusted stdout/stderr in memory and time."""
    process = Popen(command, cwd=cwd, env=env, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    captured: dict[str, bytearray] = {"stdout": bytearray(), "stderr": bytearray()}
    exceeded = threading.Event()

    def read(name: str, stream: Any) -> None:
        while chunk := stream.read(65_536):
            remaining = _MAX_PROCESS_OUTPUT_BYTES - len(captured[name])
            if remaining > 0:
                captured[name].extend(chunk[:remaining])
            if len(chunk) > remaining:
                exceeded.set()
                process.kill()

    readers = [threading.Thread(target=read, args=(name, stream), daemon=True)
               for name, stream in (("stdout", process.stdout), ("stderr", process.stderr))]
    for reader in readers:
        reader.start()
    try:
        code = process.wait(timeout=timeout)
    except TimeoutExpired:
        process.kill()
        process.wait()
        raise
    finally:
        for reader in readers:
            reader.join()
    return code, bytes(captured["stdout"]), bytes(captured["stderr"]), exceeded.is_set()


def _matches_edl_identity(raw: bytes, *, field: str, expected: str) -> bool:
    """Check that adapter bookkeeping bytes are canonical and lineage-bound.

    Phase 3 EDL identity hashes are their own accepted identity projections;
    they are intentionally not the SHA-256 of the whole serialized envelope.
    """
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    return type(value) is dict and encode_canonical_json_bytes(value) == raw and value.get(field) == expected


def run_headless_preview(*, props: RenderProps, video_edl_bytes: bytes,
                         audio_edl_bytes: bytes, fixture_root: Path, output_root: Path,
                         work_root: Path, timestamp_utc: str,
                         timeout_seconds: int = 130, cancel_requested: bool = False) -> PreviewRun:
    """Run the checked-in Node adapter and return a validated terminal result.

    ``output_root`` is single-use and must not exist. ``work_root`` is an
    existing caller-owned temporary parent; canonical props are written inside
    a fresh private child and removed after process completion.
    """
    props_bytes = serialize_render_props(props)  # validates before an attempt
    if type(video_edl_bytes) is not bytes or type(audio_edl_bytes) is not bytes:
        raise RenderBridgeError(RenderFailureCode.DEPENDENCY_BINDING_INVALID, "/edl_bytes")
    if not _matches_edl_identity(video_edl_bytes, field="video_edl_hash", expected=props.video_edl_hash) or not _matches_edl_identity(audio_edl_bytes, field="audio_edl_hash", expected=props.audio_edl_hash):
        raise RenderBridgeError(RenderFailureCode.DEPENDENCY_BINDING_INVALID, "/edl_bytes")
    if not isinstance(fixture_root, Path) or not isinstance(output_root, Path) or not isinstance(work_root, Path):
        raise RenderBridgeError(RenderFailureCode.DEPENDENCY_BINDING_INVALID, "/paths")
    if (type(timestamp_utc) is not str or type(timeout_seconds) is not int
            or timeout_seconds < 1 or type(cancel_requested) is not bool):
        raise RenderBridgeError(RenderFailureCode.DEPENDENCY_BINDING_INVALID, "/attempt")
    fixture_root = fixture_root.resolve(strict=True)
    work_root = work_root.resolve(strict=True)
    output_root = output_root.resolve()
    manifest_bytes = (fixture_root / "fixture_asset_manifest.json").read_bytes()
    base_ids = (
        "art_vedl_" + props.video_edl_hash[:32], "art_aedl_" + props.audio_edl_hash[:32],
        "art_fixman_" + props.fixture_manifest_hash[7:39], "art_rprops_" + props.render_props_hash[7:39],
    )
    # Deliberately testable at the orchestration boundary: cancellation is
    # terminal before node probing, output-directory creation, or renderer I/O.
    if cancel_requested:
        receipt = build_render_receipt(
            props=props, status=RenderStatus.CANCELLED,
            failure_code=RenderFailureCode.CANCELLED_BY_PARENT.value,
            node_version=None, preview_manifest_id=None, preview_manifest_hash=None,
            output_artifact_id=None, output_sha256=None, output_size_bytes=None,
            artifact_ids=base_ids, stdout_bytes=b"", stderr_bytes=b"",
        )
        artifacts = build_artifact_batch(
            props=props, video_edl_bytes=video_edl_bytes, audio_edl_bytes=audio_edl_bytes,
            fixture_manifest_bytes=manifest_bytes, receipt=receipt, timestamp_utc=timestamp_utc,
        )
        return PreviewRun(receipt=receipt, artifacts=artifacts, preview_manifest_bytes=None)
    node = which("node")
    node_version = _node_version(node) if node else None
    stdout = b""; stderr = b""; manifest: bytes | None = None; frames: tuple[tuple[int, bytes], ...] = ()
    status = RenderStatus.FAILED
    failure_code: str | None = RenderFailureCode.REMOTION_UNAVAILABLE.value if node_version is None else RenderFailureCode.RENDER_EXIT_NONZERO.value
    if node is not None and node_version is not None:
        renderer_root = Path(__file__).resolve().parents[2] / "renderer-remotion"
        script = renderer_root / "scripts" / "render-fixture.mjs"
        try:
            with TemporaryDirectory(prefix="phase4a_preview_", dir=work_root) as attempt:
                props_path = Path(attempt) / "render-props.json"
                props_path.write_bytes(props_bytes)
                return_code, stdout, stderr, output_exceeded = _bounded_run(
                    [node, str(script), "--props", str(props_path), "--output", str(output_root),
                     "--fixture-root", str(fixture_root), "--work-root", str(attempt)],
                    cwd=renderer_root, env=_node_environment(), timeout=timeout_seconds,
                )
                if return_code == 0 and not output_exceeded:
                    try:
                        runner_result = json.loads(stdout.decode("utf-8"))
                        manifest, frames = _preview_manifest(output_root, runner_result, props=props)
                        status = RenderStatus.SUCCEEDED; failure_code = None
                    except (UnicodeDecodeError, json.JSONDecodeError, RenderBridgeError):
                        status = RenderStatus.FAILED; failure_code = RenderFailureCode.PREVIEW_MANIFEST_INVALID.value
                else:
                    failure_code = _failure_code(stderr, timed_out=False)
        except TimeoutExpired as exc:
            stdout = exc.stdout if type(exc.stdout) is bytes else b""
            stderr = exc.stderr if type(exc.stderr) is bytes else b""
            failure_code = _failure_code(stderr, timed_out=True)
        except OSError:
            failure_code = RenderFailureCode.REMOTION_UNAVAILABLE.value
    if status is RenderStatus.SUCCEEDED and manifest is not None:
        frame_ids = tuple(f"art_rframe_{index}_{_sha(raw)[7:39]}" for index, raw in frames)
        output_hash = _sha(manifest)
        artifact_ids = base_ids + frame_ids + ("art_rmanifest_" + output_hash[7:39],)
        receipt = build_render_receipt(props=props, status=status, failure_code=None,
            node_version=node_version, preview_manifest_id=artifact_ids[-1], preview_manifest_hash=output_hash,
            output_artifact_id=artifact_ids[-1], output_sha256=output_hash, output_size_bytes=len(manifest),
            artifact_ids=artifact_ids, stdout_bytes=stdout, stderr_bytes=stderr)
    else:
        receipt = build_render_receipt(props=props, status=RenderStatus.FAILED, failure_code=failure_code,
            node_version=node_version, preview_manifest_id=None, preview_manifest_hash=None,
            output_artifact_id=None, output_sha256=None, output_size_bytes=None,
            artifact_ids=base_ids, stdout_bytes=stdout, stderr_bytes=stderr)
    artifacts = build_artifact_batch(props=props, video_edl_bytes=video_edl_bytes, audio_edl_bytes=audio_edl_bytes,
        fixture_manifest_bytes=manifest_bytes, receipt=receipt, timestamp_utc=timestamp_utc,
        preview_manifest_bytes=manifest, frame_bytes=frames)
    return PreviewRun(receipt=receipt, artifacts=artifacts, preview_manifest_bytes=manifest)
