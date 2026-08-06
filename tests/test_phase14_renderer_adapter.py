import hashlib
import pytest
from engine.contracts.models import ArtifactRecord
from engine.rendering.artifact_hook import RenderArtifactBatch
from engine.rendering.lifecycle_adapter import run_phase4_preview_cached
from engine.rendering.preview_runner import PreviewRun
from engine.rendering.receipt import RenderStatus
from engine.rendering.bridge import build_render_props, renderer_version
from engine.rendering.fixture_assets import FixtureAssetResolver
from engine.rendering.preview_runner import run_headless_preview
from engine.contracts.audio_edl import serialize_audio_edl
from engine.contracts.edl import serialize_video_edl
from tests.test_render_bridge import FIXTURE_ROOT, ROOT, build_phase4a_rich_replay_inputs
from engine.lifecycle import load_registry


def _run(payload=b"manifest"):
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    # The lifecycle adapter uses only fields that the Phase 4 artifact hook
    # already makes immutable.  A minimal typed batch keeps this test focused.
    record = ArtifactRecord("3.0.0", "art_x", "render_manifest", "prj_fx34", None,
        "now", "now", digest, len(payload), "review", (), False, False, False,
        False, "phase4a-renderer", "0.1.0", None, "ready", 1)
    class Receipt:
        status = RenderStatus.SUCCEEDED
        output_sha256 = digest
    return PreviewRun(receipt=Receipt(), artifacts=RenderArtifactBatch((record,)), preview_manifest_bytes=payload)


def test_adapter_reuses_verified_input_cache_and_registry(tmp_path):
    kwargs = dict(cache_root=tmp_path / "cache", managed_storage_root=tmp_path,
        registry_path=tmp_path / "registry.jsonl", profile="preview", inputs={"x": 1}, estimated_bytes=1,
        hard_limit_bytes=2, lifecycle_timestamp_utc="2026-08-06T00:00:00Z")
    first = run_phase4_preview_cached(**kwargs, runner=lambda: _run())
    second = run_phase4_preview_cached(**kwargs, runner=lambda: _run(b"bad"))
    assert first.disposition == "RENDERED" and second.disposition == "CACHE_HIT"
    assert second.preview_manifest_bytes == b"manifest" and (tmp_path / "registry.jsonl").is_file()


def test_adapter_blocks_before_invoking_renderer_at_hard_quota(tmp_path):
    (tmp_path / "occupied").write_bytes(b"xx")
    with pytest.raises(ValueError, match="HARD_QUOTA"):
        run_phase4_preview_cached(cache_root=tmp_path / "cache", managed_storage_root=tmp_path,
            registry_path=tmp_path / "r.jsonl", profile="preview", inputs={"x": 2}, estimated_bytes=1,
            hard_limit_bytes=2, lifecycle_timestamp_utc="2026-08-06T00:00:00Z", runner=lambda: _run())


def test_adapter_wraps_one_real_phase4_preview_and_reuses_its_manifest(tmp_path):
    replay = build_phase4a_rich_replay_inputs()
    props = build_render_props(video_edl=replay["video_edl"], audio_edl=replay["audio_edl"],
        fixture_assets=FixtureAssetResolver.load(FIXTURE_ROOT),
        renderer_version_value=renderer_version((ROOT / "renderer-remotion" / "package-lock.json").read_bytes()))
    runs: list[PreviewRun] = []
    def invoke() -> PreviewRun:
        run = run_headless_preview(props=props, video_edl_bytes=serialize_video_edl(replay["video_edl"]),
            audio_edl_bytes=serialize_audio_edl(replay["audio_edl"]), fixture_root=FIXTURE_ROOT,
            output_root=tmp_path / "renderer-output", work_root=tmp_path,
            timestamp_utc="2026-08-06T00:00:00Z")
        runs.append(run)
        return run
    kwargs = dict(cache_root=tmp_path / "cache", managed_storage_root=tmp_path,
        registry_path=tmp_path / "registry.jsonl", profile="preview", inputs={"render_props_hash": props.render_props_hash},
        estimated_bytes=10_000, hard_limit_bytes=20_000, lifecycle_timestamp_utc="2026-08-06T00:00:00Z")
    rendered = run_phase4_preview_cached(**kwargs, runner=invoke)
    reused = run_phase4_preview_cached(**kwargs, runner=lambda: pytest.fail("renderer must not run on cache hit"))
    assert rendered.disposition == "RENDERED" and reused.disposition == "CACHE_HIT"
    assert reused.output_sha256 == rendered.output_sha256
    assert {record.artifact_id for record in load_registry(registry_path=tmp_path / "registry.jsonl")} == {record.artifact_id for record in runs[0].artifacts.records}
