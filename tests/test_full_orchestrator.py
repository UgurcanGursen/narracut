"""Focused replay-only integration evidence for the Phase 4B orchestrator."""
from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

from engine.rendering import FullRenderError, OutputTargetHead, provision_output_target
from engine.rendering.full_orchestrator import (
    RemotionFullRuntime, make_remotion_full_producer, run_full_render,
)
from engine.rendering.bridge import build_render_props, renderer_version
from engine.rendering.fixture_assets import FixtureAssetResolver
from tests.test_audio_render_plan import _inputs
from tests.test_render_bridge import FIXTURE_ROOT, ROOT, build_phase4a_rich_replay_inputs

PROFILE_ID = "frp_phase4b_replay_win32_x64"
PROFILE_HASH = "sha256:d0934f098430334ec1f15be78083635bebb7402ac08fa2ed5fda8fec810461b2"


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


def _runtime() -> RemotionFullRuntime:
    node = Path(shutil.which("node") or "")
    if not node.is_file():
        pytest.skip("paired Node/Remotion fixture runtime unavailable")
    return RemotionFullRuntime(node_executable=node, renderer_root=ROOT / "renderer-remotion")


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

    runtime = _runtime()
    render_video = make_remotion_full_producer(
        runtime=runtime,
        fixture_assets=FixtureAssetResolver.load(FIXTURE_ROOT), fixture_root=FIXTURE_ROOT,
    )

    outcome = run_full_render(project_root=tmp_path, props=props, audio_edl=audio,
        pcm_manifest=manifest, pcm_materialization_report=report, pcm_sources=sources,
        output_target_id="outt_" + "9" * 32, profile_id=PROFILE_ID,
        profile_hash=PROFILE_HASH, cancellation_ingress_id="cancel_1",
        attempt_id="attempt_replay_1", video_producer=render_video, ffmpeg=ffmpeg, ffprobe=ffprobe,
        remotion_runtime=runtime)
    assert outcome.status == "SUCCEEDED" and outcome.output_path is not None
    assert outcome.output_path.is_file() and outcome.receipt is not None
    assert outcome.receipt["status"] == "SUCCEEDED"
    from engine.rendering.lifecycle_registry import resolve_target_head
    head = resolve_target_head(project_root=tmp_path, output_target_id="outt_" + "9" * 32)
    assert outcome.receipt["committed_output_target_record_id"] == head["output_target_record_id"]
    assert outcome.receipt["committed_output_target_record_hash"] == head["output_target_record_hash"]
    assert outcome.receipt["committed_output_target_revision"] == head["revision"]
    registry = (tmp_path / "artifacts" / "registry.jsonl").read_text(encoding="utf-8")
    assert outcome.receipt["pre_cleanup_manifest_id"] in registry
    assert outcome.receipt["post_cleanup_manifest_id"] in registry
    assert head["current_output_artifact_id"] in registry
    for kind in ("full_render_request", "render_props", "pcm_input_manifest",
                 "pcm_materialization_report", "renderer_video", "audio_render_plan",
                 "audio_filter_script", "normalized_audio", "final_output", "full_render_toolchain_preflight"):
        assert f'"kind":"{kind}"' in registry
    assert outcome.receipt["payload"]["toolchain_preflight_id"] in registry
    assert not list((tmp_path / "renders" / "attempts" / "attempt_replay_1").rglob("*"))


def test_pre_admission_cancel_creates_no_attempt_or_receipt(tmp_path: Path) -> None:
    props = _props()
    provision_output_target(project_root=tmp_path, head=OutputTargetHead(
        "outt_" + "8" * 32, props.project_id, props.sequence_id, "renders/final/cancel.mp4"))
    audio, manifest, report = _inputs()
    outcome = run_full_render(project_root=tmp_path, props=props, audio_edl=audio,
        pcm_manifest=manifest, pcm_materialization_report=report, pcm_sources={},
        output_target_id="outt_" + "8" * 32, profile_id=PROFILE_ID,
        profile_hash=PROFILE_HASH, cancellation_ingress_id="cancel_2",
        attempt_id="attempt_cancel_1", video_producer=lambda *_: None,
        ffmpeg=Path("ffmpeg"), ffprobe=Path("ffprobe"), cancel_before_admission=True)
    assert not outcome.admitted and outcome.status == "CANCELLED_BEFORE_ADMISSION"
    assert outcome.receipt is None and not (tmp_path / "renders" / "attempts").exists()


@pytest.mark.parametrize(
    ("cancel", "producer_code", "expected_status"),
    ((True, None, "CANCELLED"), (False, "REMOTION_FULL_RENDER_FAILED", "FAILED")),
)
def test_admitted_terminal_failure_and_cancellation_persist_cleanup_receipts(
    tmp_path: Path, cancel: bool, producer_code: str | None, expected_status: str,
) -> None:
    """Admitted non-success paths never publish a target revision, but do journal cleanup."""
    props = _props()
    ffmpeg, ffprobe = _tools()
    runtime = _runtime()
    target_id = "outt_" + ("6" if cancel else "7") * 32
    provision_output_target(project_root=tmp_path, head=OutputTargetHead(
        target_id, props.project_id, props.sequence_id, "renders/final/terminal.mp4"))
    audio, manifest, report = _inputs()

    def producer(*_args: Path) -> None:
        assert producer_code is not None
        raise FullRenderError(producer_code)

    outcome = run_full_render(
        project_root=tmp_path, props=props, audio_edl=audio,
        pcm_manifest=manifest, pcm_materialization_report=report, pcm_sources={},
        output_target_id=target_id, profile_id=PROFILE_ID,
        profile_hash=PROFILE_HASH, cancellation_ingress_id="cancel_terminal",
        attempt_id="attempt_terminal_" + ("cancel" if cancel else "failure"),
        video_producer=producer, ffmpeg=ffmpeg, ffprobe=ffprobe, remotion_runtime=runtime,
        cancel_after_admission=cancel,
    )
    assert outcome.admitted and outcome.status == expected_status and outcome.output_path is None
    assert outcome.receipt is not None and outcome.receipt["status"] == expected_status
    assert outcome.receipt["committed_output_target_record_id"] is None
    assert outcome.receipt["committed_output_target_record_hash"] is None
    assert outcome.receipt["committed_output_target_revision"] is None
    assert outcome.receipt["pre_cleanup_manifest_id"]
    assert outcome.receipt["post_cleanup_manifest_id"]
    from engine.rendering.lifecycle_registry import resolve_target_head
    assert resolve_target_head(project_root=tmp_path, output_target_id=target_id)["revision"] == 1
    registry = (tmp_path / "artifacts" / "registry.jsonl").read_text(encoding="utf-8")
    assert outcome.receipt["receipt_id"] in registry
    assert outcome.receipt["pre_cleanup_manifest_id"] in registry
    assert outcome.receipt["post_cleanup_manifest_id"] in registry


def test_toolchain_preflight_rejects_untrusted_runtime_before_attempt(tmp_path: Path) -> None:
    ffmpeg, ffprobe = _tools()
    props = _props()
    target_id = "outt_" + "5" * 32
    provision_output_target(project_root=tmp_path, head=OutputTargetHead(
        target_id, props.project_id, props.sequence_id, "renders/final/preflight.mp4"))
    audio, manifest, report = _inputs()
    with pytest.raises(FullRenderError, match="FULL_RENDER_TOOLCHAIN_PREFLIGHT_FAILED"):
        run_full_render(project_root=tmp_path, props=props, audio_edl=audio,
            pcm_manifest=manifest, pcm_materialization_report=report, pcm_sources={},
            output_target_id=target_id, profile_id=PROFILE_ID, profile_hash=PROFILE_HASH,
            cancellation_ingress_id="cancel_preflight", attempt_id="attempt_preflight_1",
            video_producer=lambda *_: None, ffmpeg=ffmpeg, ffprobe=ffprobe,
            remotion_runtime=RemotionFullRuntime(node_executable=tmp_path / "untrusted-node.exe",
                                                 renderer_root=ROOT / "renderer-remotion"))
    assert not (tmp_path / "renders" / "attempts").exists()
