"""Focused replay-only integration evidence for the Phase 4B orchestrator."""
from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

from engine.rendering import OutputTargetHead, provision_output_target
from engine.rendering.full_orchestrator import run_full_render
from engine.rendering.bridge import build_render_props, renderer_version
from engine.rendering.fixture_assets import FixtureAssetResolver
from tests.test_audio_render_plan import _inputs
from tests.test_render_bridge import FIXTURE_ROOT, ROOT, build_phase4a_rich_replay_inputs


def _sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _props():
    replay = build_phase4a_rich_replay_inputs()
    return build_render_props(video_edl=replay["video_edl"], audio_edl=replay["audio_edl"],
        fixture_assets=FixtureAssetResolver.load(FIXTURE_ROOT),
        renderer_version_value=renderer_version((ROOT / "renderer-remotion" / "package-lock.json").read_bytes()))


def _tools() -> tuple[Path, Path]:
    ffmpeg, ffprobe = Path(shutil.which("ffmpeg") or ""), Path(shutil.which("ffprobe") or "")
    if not ffmpeg.is_file() or not ffprobe.is_file():
        pytest.skip("paired FFmpeg fixture runtime unavailable")
    return ffmpeg, ffprobe


def test_replay_orchestrator_mixes_and_publishes_one_sequence(tmp_path: Path) -> None:
    ffmpeg, ffprobe = _tools()
    props = _props()
    provision_output_target(project_root=tmp_path, head=OutputTargetHead(
        "outt_" + "9" * 32, props.project_id, props.sequence_id, "renders/final/sequence.mp4"))
    audio, manifest, report = _inputs()
    pcm = tmp_path / "source.wav"
    made = subprocess.run([str(ffmpeg), "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", "1", "-c:a", "pcm_f32le", str(pcm)], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    assert made.returncode == 0
    sources: dict[str, Path] = {}
    for entry in manifest["entries"]:
        entry["pcm_content_sha256"], entry["byte_length"] = _sha(pcm), pcm.stat().st_size
        sources[entry["pcm_artifact_id"]] = pcm
    for entry in report["entries"]:
        entry["materialized_pcm_content_sha256"], entry["byte_length"] = _sha(pcm), pcm.stat().st_size

    def render_video(props_path: Path, video_path: Path, _attempt: Path) -> None:
        assert props_path.is_file()
        video_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run([str(ffmpeg), "-y", "-f", "lavfi", "-i", "color=c=black:s=64x64:r=30",
            "-t", "1", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video_path)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        assert result.returncode == 0

    outcome = run_full_render(project_root=tmp_path, props=props, audio_edl=audio,
        pcm_manifest=manifest, pcm_materialization_report=report, pcm_sources=sources,
        output_target_id="outt_" + "9" * 32, profile_id="replay-profile",
        profile_hash="sha256:" + "2" * 64, cancellation_ingress_id="cancel_1",
        attempt_id="attempt_replay_1", video_producer=render_video, ffmpeg=ffmpeg, ffprobe=ffprobe)
    assert outcome.status == "SUCCEEDED" and outcome.output_path is not None
    assert outcome.output_path.is_file() and outcome.receipt is not None
    assert outcome.receipt["status"] == "SUCCEEDED"
    assert not list((tmp_path / "renders" / "attempts" / "attempt_replay_1").rglob("*"))


def test_pre_admission_cancel_creates_no_attempt_or_receipt(tmp_path: Path) -> None:
    props = _props()
    provision_output_target(project_root=tmp_path, head=OutputTargetHead(
        "outt_" + "8" * 32, props.project_id, props.sequence_id, "renders/final/cancel.mp4"))
    audio, manifest, report = _inputs()
    outcome = run_full_render(project_root=tmp_path, props=props, audio_edl=audio,
        pcm_manifest=manifest, pcm_materialization_report=report, pcm_sources={},
        output_target_id="outt_" + "8" * 32, profile_id="replay-profile",
        profile_hash="sha256:" + "2" * 64, cancellation_ingress_id="cancel_2",
        attempt_id="attempt_cancel_1", video_producer=lambda *_: None,
        ffmpeg=Path("ffmpeg"), ffprobe=Path("ffprobe"), cancel_before_admission=True)
    assert not outcome.admitted and outcome.status == "CANCELLED_BEFORE_ADMISSION"
    assert outcome.receipt is None and not (tmp_path / "renders" / "attempts").exists()
