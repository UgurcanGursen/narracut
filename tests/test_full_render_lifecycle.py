"""Focused REPLAY-only Phase 4B admission and FFmpeg terminality gates."""
from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

from engine.rendering import (
    FullRenderError, OutputTargetHead, atomic_publish, build_full_render_request,
    provision_output_target, resolve_output_target,
    normalize_mux_probe,
)
from engine.rendering.bridge import build_render_props, renderer_version
from engine.rendering.fixture_assets import FixtureAssetResolver
from engine.rendering.full_profile import load_full_render_profile
from tests.test_render_bridge import FIXTURE_ROOT, ROOT, build_phase4a_rich_replay_inputs

PROFILE_ID = "frp_phase4b_replay_win32_x64"
PROFILE_HASH = "sha256:d0934f098430334ec1f15be78083635bebb7402ac08fa2ed5fda8fec810461b2"


def _props():
    replay = build_phase4a_rich_replay_inputs()
    return build_render_props(
        video_edl=replay["video_edl"], audio_edl=replay["audio_edl"],
        fixture_assets=FixtureAssetResolver.load(FIXTURE_ROOT),
        renderer_version_value=renderer_version((ROOT / "renderer-remotion" / "package-lock.json").read_bytes()),
    )


def _target() -> OutputTargetHead:
    return OutputTargetHead(
        output_target_id="outt_" + "1" * 32, project_id="project_replay",
        sequence_id="sequence_replay", trusted_publish_relative_path="renders/final/out.mp4",
    )


def test_target_is_provisioned_before_runtime_and_resolves_its_4a_binding(tmp_path: Path) -> None:
    props = _props()
    head = OutputTargetHead(
        output_target_id="outt_" + "1" * 32, project_id=props.project_id,
        sequence_id=props.sequence_id, trusted_publish_relative_path="renders/final/out.mp4",
    )
    row = provision_output_target(project_root=tmp_path, head=head)
    assert row["revision"] == 1 and row["current_output_artifact_id"] is None
    assert resolve_output_target(project_root=tmp_path, output_target_id=head.output_target_id, props=props)["output_target_record_hash"] == row["output_target_record_hash"]
    with pytest.raises(FullRenderError) as rejected:
        provision_output_target(project_root=tmp_path, head=head)
    assert rejected.value.code == "OUTPUT_TARGET_CONFLICT"


def test_full_request_is_separate_hash_bound_envelope_and_4a_props_stay_preview(tmp_path: Path) -> None:
    props = _props()
    manifest = {"schema_version": "FULL-RENDER-PCM-MANIFEST-V1", "entries": []}
    request = build_full_render_request(
        props=props, profile_id=PROFILE_ID, profile_hash=PROFILE_HASH,
        output_target_id="outt_" + "1" * 32, pcm_manifest=manifest,
        cancellation_ingress_id="cancel_fixture_1",
    )
    assert request["schema_version"] == "FULL-RENDER-REQUEST-V1"
    assert request["render_props"]["mode"] == "PREVIEW"
    assert request["render_props_canonical_sha256"] == "sha256:" + hashlib.sha256(
        __import__("engine.rendering.bridge", fromlist=["serialize_render_props"]).serialize_render_props(props)
    ).hexdigest()
    assert set(("remotion_identity_hash", "node_identity_hash", "ffmpeg_identity_hash", "ffprobe_identity_hash")) <= set(request)
    with pytest.raises(FullRenderError) as rejected:
        build_full_render_request(props=props, profile_id="", profile_hash="sha256:" + "2" * 64, output_target_id="outt_" + "1" * 32, pcm_manifest=manifest, cancellation_ingress_id="x")
    assert rejected.value.code == "FULL_REQUEST_INVALID"


def test_unknown_or_hash_drift_profile_is_pre_admission_fail_closed() -> None:
    with pytest.raises(FullRenderError) as unknown:
        load_full_render_profile(profile_id="frp_missing", profile_hash=PROFILE_HASH)
    assert unknown.value.code == "FULL_RENDER_PROFILE_INVALID"
    with pytest.raises(FullRenderError) as drift:
        load_full_render_profile(profile_id=PROFILE_ID, profile_hash="sha256:" + "0" * 64)
    assert drift.value.code == "FULL_RENDER_PROFILE_INVALID"


def test_locked_and_approved_targets_fail_before_publish(tmp_path: Path) -> None:
    props = _props()
    for index, kwargs, code in (("3", {"locked": True}, "OUTPUT_LOCKED"), ("4", {"approved": True}, "OUTPUT_APPROVED")):
        head = OutputTargetHead(output_target_id="outt_" + index * 32, project_id=props.project_id, sequence_id=props.sequence_id, trusted_publish_relative_path=f"renders/{index}.mp4", **kwargs)
        provision_output_target(project_root=tmp_path, head=head)
        with pytest.raises(FullRenderError) as rejected:
            resolve_output_target(project_root=tmp_path, output_target_id=head.output_target_id, props=props)
        assert rejected.value.code == code


def test_atomic_publish_does_not_overwrite_existing_target(tmp_path: Path) -> None:
    staged = tmp_path / "attempt.mp4"; staged.write_bytes(b"fixture-bytes")
    target = {"trusted_publish_relative_path": "renders/final/output.mp4"}
    published = atomic_publish(staged_output=staged, project_root=tmp_path, target=target)
    assert published.read_bytes() == b"fixture-bytes" and not staged.exists()
    staged.write_bytes(b"new")
    with pytest.raises(FullRenderError) as rejected:
        atomic_publish(staged_output=staged, project_root=tmp_path, target=target)
    assert rejected.value.code == "ATOMIC_PUBLISH_FAILED"


def test_replay_ffmpeg_mux_and_ffprobe_produce_a_staged_av_output(tmp_path: Path) -> None:
    """The bounded adapter executes real local tools; no media fallback exists."""
    ffmpeg = Path(shutil.which("ffmpeg") or "")
    ffprobe = Path(shutil.which("ffprobe") or "")
    if not ffmpeg.is_file() or not ffprobe.is_file():
        pytest.skip("paired FFmpeg fixture runtime unavailable")
    video = tmp_path / "renderer-video.mp4"
    generated = subprocess.run(
        [str(ffmpeg), "-y", "-f", "lavfi", "-i", "color=c=black:s=64x64:r=30",
         "-t", "0.02", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    assert generated.returncode == 0 and video.is_file()
    pcm = tmp_path / "trusted-pcm.wav"
    pcm_generated = subprocess.run(
        [str(ffmpeg), "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-t", "0.2", "-c:a", "pcm_f32le", str(pcm)],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    assert pcm_generated.returncode == 0 and pcm.is_file()
    result = normalize_mux_probe(video_path=video, pcm_paths=[pcm], staged_output=tmp_path / "staged.mp4", ffmpeg=ffmpeg, ffprobe=ffprobe)
    assert result["output_size_bytes"] > 0 and result["streams"] >= 2
