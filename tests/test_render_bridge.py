"""Phase 4A REPLAY bridge ingress/fixture acceptance scaffolding.

The behavioural bridge tests are intentionally added only after the bounded
``engine.contracts.render_bridge`` production surface lands.  These checks are
already useful: they prove that the checked-in fixture is a canonical,
network-free trusted-root input and that the accepted Phase 3 public
materializers provide a coherent video/audio byte pair without a renderer.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
import re
import shutil
from subprocess import TimeoutExpired

import pytest

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.audio_edl import compile_audio_edl, load_audio_edl, serialize_audio_edl
from engine.contracts.edl import SourcePlaybackMode, TimelineTrack, serialize_video_edl
from engine.contracts.word_to_frame import TemporalFrameRate
from engine.rendering.artifact_hook import build_artifact_batch
from engine.rendering.bridge import RenderBridgeError, RenderFailureCode, build_render_props, load_render_props, renderer_version, serialize_render_props
from engine.rendering.fixture_assets import FixtureAssetResolver
from engine.rendering.preview_runner import _decode_png_rgba, _preview_manifest, run_headless_preview
from engine.rendering.receipt import RenderStatus, build_render_receipt, serialize_render_receipt
from tests.test_audio_edl_replay import _all_track_kwargs
from tests.test_edl import _compile as _compile_video_edl
from tests.test_edl import _fixture_intents


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "phase4a"
MANIFEST_PATH = FIXTURE_ROOT / "fixture_asset_manifest.json"


def _fixture_manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _fixture_identity_projection(value: dict[str, object]) -> dict[str, object]:
    return {
        key: item
        for key, item in value.items()
        if key not in {"fixture_manifest_id", "fixture_manifest_hash"}
    }


def build_phase4a_rich_replay_inputs(*, sequence_id: str = "sequence_replay") -> dict[str, object]:
    """Build the accepted, Phase-4-owned multi-track REPLAY ingress pair.

    This deliberately uses only public Phase 3 materializers.  The V3 source
    gets a non-full declarative crop and FIT playback; spatial zoom/highlight
    are not invented here because they are absent from the accepted EDL and
    await the separately hash-bound Phase 4 fixture-directive contract.
    """
    intents = []
    for intent in _fixture_intents():
        if intent.track is TimelineTrack.V3:
            source = dataclasses.replace(
                intent.source,
                playback_mode=SourcePlaybackMode.FIT,
                crop_left_millionths=150_000,
                crop_top_millionths=100_000,
                crop_right_millionths=850_000,
                crop_bottom_millionths=900_000,
            )
            intent = dataclasses.replace(intent, source=source)
        intents.append(intent)
    video_edl = _compile_video_edl(intents=tuple(intents), sequence_id=sequence_id)
    audio_kwargs = _all_track_kwargs(rate=TemporalFrameRate(30, 1))
    audio_kwargs["video_edl"] = video_edl
    audio_edl = compile_audio_edl(**audio_kwargs)
    return {
        "video_edl": video_edl,
        "audio_edl": audio_edl,
        "audio_load_kwargs": audio_kwargs,
    }


def test_phase4a_fixture_manifest_is_canonical_hashed_and_trusted_root_relative() -> None:
    """Fixture assets are explicit allowlist rows, never an asset discovery API."""
    manifest = _fixture_manifest()
    assert tuple(manifest) == (
        "schema_version", "fixture_manifest_id", "fixture_manifest_hash", "assets",
        "visual_directives",
    )
    assert manifest["schema_version"] == "FIXTURE-ASSET-MANIFEST-V1"
    projection = _fixture_identity_projection(manifest)
    digest = hashlib.sha256(encode_canonical_json_bytes(projection)).hexdigest()
    assert manifest["fixture_manifest_hash"] == "sha256:" + digest
    assert manifest["fixture_manifest_id"] == "fixman_" + digest[:32]

    assets = manifest["assets"]
    assert isinstance(assets, list) and len(assets) == 5
    assert [row["fixture_asset_id"] for row in assets] == sorted(
        row["fixture_asset_id"] for row in assets
    )
    assert {row["media_type"] for row in assets} == {"image/svg+xml"}
    for row in assets:
        assert tuple(row) == (
            "fixture_asset_id", "edl_source_ref", "relative_posix_path",
            "content_sha256", "media_type", "width", "height",
        )
        assert row["edl_source_ref"].startswith("asset_fixture_")
        relative = row["relative_posix_path"]
        assert isinstance(relative, str)
        assert not Path(relative).is_absolute()
        assert ".." not in Path(relative).parts
        assert "\\" not in relative and ":" not in relative
        assert row["width"] == 1280 and row["height"] == 720
        payload = FIXTURE_ROOT.joinpath(*relative.split("/")).read_bytes()
        assert row["content_sha256"] == "sha256:" + hashlib.sha256(payload).hexdigest()


def test_fixture_svg_assets_are_font_free_geometry() -> None:
    """Trusted fixture pixels never depend on browser or host font fallback."""
    for row in _fixture_manifest()["assets"]:
        relative = row["relative_posix_path"]
        svg = FIXTURE_ROOT.joinpath(*relative.split("/")).read_text(encoding="utf-8")
        assert "<text" not in svg.lower()
        assert "font" not in svg.lower()


def _write_manifest_with_recomputed_identity(root: Path, manifest: dict[str, object]) -> None:
    projection = _fixture_identity_projection(manifest)
    digest = hashlib.sha256(encode_canonical_json_bytes(projection)).hexdigest()
    manifest["fixture_manifest_hash"] = "sha256:" + digest
    manifest["fixture_manifest_id"] = "fixman_" + digest[:32]
    (root / "fixture_asset_manifest.json").write_text(
        json.dumps(manifest, separators=(",", ":")), encoding="utf-8"
    )


def test_fixture_visual_directives_are_hash_bound_and_cannot_override_schedule() -> None:
    """V3/V4 motion is allowlisted projection, never a scheduler input."""
    manifest = _fixture_manifest()
    directives = manifest["visual_directives"]
    assert isinstance(directives, list) and len(directives) == 2
    directive = next(row for row in directives if row["track"] == "V3")
    assert tuple(directive) == (
        "schema_version", "directive_id", "directive_hash", "event_id", "event_hash",
        "track", "kind", "zoom_start_millionths", "zoom_end_millionths",
        "highlight_left_millionths", "highlight_top_millionths",
        "highlight_right_millionths", "highlight_bottom_millionths",
    )
    projection = {
        key: value for key, value in directive.items()
        if key not in {"directive_id", "directive_hash"}
    }
    digest = hashlib.sha256(encode_canonical_json_bytes(projection)).hexdigest()
    assert directive["directive_hash"] == "sha256:" + digest
    assert directive["directive_id"] == "vdir_" + digest[:32]
    assert directive["schema_version"] == "FIXTURE-VISUAL-DIRECTIVE-V1"
    assert (directive["track"], directive["kind"]) == ("V3", "SOURCE_ZOOM_HIGHLIGHT")
    # Phase 3 video-event hashes are bare hex digests, not ``sha256:`` values.
    assert re.fullmatch(r"[0-9a-f]{64}", directive["event_hash"])
    assert 1_000_000 <= directive["zoom_start_millionths"] <= directive["zoom_end_millionths"] <= 2_000_000
    assert directive["highlight_left_millionths"] < directive["highlight_right_millionths"] <= 1_000_000
    assert directive["highlight_top_millionths"] < directive["highlight_bottom_millionths"] <= 1_000_000
    assert not {
        "start_frame", "end_exclusive_frame", "start_word_id", "end_word_id",
        "source_ref", "crop_left_millionths", "priority",
    }.intersection(directive)

    video_edl = build_phase4a_rich_replay_inputs()["video_edl"]
    event = next(track.events[0] for track in video_edl.tracks if track.track is TimelineTrack.V3)
    assert (directive["event_id"], directive["event_hash"]) == (event.event_id, event.event_hash)
    assert event.payload.source is not None

    chart = next(row for row in directives if row["track"] == "V4")
    assert tuple(chart) == (
        "schema_version", "directive_id", "directive_hash", "event_id", "event_hash",
        "track", "kind", "reveal_start_millionths", "reveal_end_millionths",
    )
    chart_projection = {key: value for key, value in chart.items() if key not in {"directive_id", "directive_hash"}}
    chart_digest = hashlib.sha256(encode_canonical_json_bytes(chart_projection)).hexdigest()
    assert (chart["directive_hash"], chart["directive_id"]) == (
        "sha256:" + chart_digest, "vdir_" + chart_digest[:32],
    )
    assert (chart["schema_version"], chart["track"], chart["kind"]) == (
        "FIXTURE-VISUAL-DIRECTIVE-V1", "V4", "CHART_REVEAL",
    )
    assert re.fullmatch(r"[0-9a-f]{64}", chart["event_hash"])
    assert 0 <= chart["reveal_start_millionths"] < chart["reveal_end_millionths"] <= 1_000_000
    v4_event = next(track.events[0] for track in video_edl.tracks if track.track is TimelineTrack.V4)
    assert (chart["event_id"], chart["event_hash"]) == (v4_event.event_id, v4_event.event_hash)
    assert v4_event.payload.source is not None


def test_chart_reveal_uses_existing_v4_event_interval_and_integer_endpoints() -> None:
    """V4 reveal has no independent clock, cue, or schedule in the directive."""
    chart = next(row for row in _fixture_manifest()["visual_directives"] if row["track"] == "V4")
    replay = build_phase4a_rich_replay_inputs()
    v4_event = next(track.events[0] for track in replay["video_edl"].tracks if track.track is TimelineTrack.V4)
    assert v4_event.start_frame < v4_event.end_exclusive_frame
    assert not {"start_frame", "end_exclusive_frame", "start_word_id", "end_word_id", "source_ref", "priority"}.intersection(chart)

    def reveal_at(frame: int) -> int:
        span = v4_event.end_exclusive_frame - v4_event.start_frame
        if span == 1:
            return chart["reveal_end_millionths"]
        offset = min(max(frame - v4_event.start_frame, 0), span - 1)
        ratio = offset * 1_000_000 // (span - 1)
        return chart["reveal_start_millionths"] + (
            (chart["reveal_end_millionths"] - chart["reveal_start_millionths"])
            * ratio // 1_000_000
        )

    assert reveal_at(v4_event.start_frame) == chart["reveal_start_millionths"]
    assert reveal_at(v4_event.end_exclusive_frame - 1) == chart["reveal_end_millionths"]
    assert reveal_at(v4_event.start_frame) < reveal_at(v4_event.end_exclusive_frame - 1)


def test_fixture_source_refs_exactly_match_compact_phase3_replay_sources() -> None:
    """The repair maps only existing, opaque Phase 3 source references."""
    expected = tuple(intent.source.source_ref for intent in _fixture_intents())
    assert expected == tuple(f"asset_fixture_{ordinal}" for ordinal in range(5))
    manifest_refs = tuple(row["edl_source_ref"] for row in _fixture_manifest()["assets"])
    assert set(manifest_refs) == set(expected)
    assert len(manifest_refs) == len(set(manifest_refs))

    artifact = _compile_video_edl(intents=_fixture_intents())
    actual = tuple(
        event.payload.source.source_ref
        for track in artifact.tracks
        for event in track.events
        if event.payload.source is not None
    )
    assert set(actual) == set(expected)


def test_phase3_public_materializers_provide_a_coherent_replay_ingress_pair() -> None:
    """Phase 4 consumes materialized bytes and validates audio duration exactly."""
    kwargs = _all_track_kwargs(rate=TemporalFrameRate(30, 1))
    video_edl = kwargs["video_edl"]
    audio_artifact = compile_audio_edl(**kwargs)
    video_bytes = serialize_video_edl(video_edl)
    audio_bytes = serialize_audio_edl(audio_artifact)

    assert video_bytes == serialize_video_edl(video_edl)
    assert audio_bytes == serialize_audio_edl(audio_artifact)
    assert audio_artifact.video_edl_id == video_edl.video_edl_id
    assert audio_artifact.video_edl_hash == video_edl.video_edl_hash
    assert audio_artifact.duration_samples == (
        video_edl.duration_frames * 48_000 * video_edl.fps_denominator
        // video_edl.fps_numerator
    )
    loaded = load_audio_edl(audio_bytes, **kwargs)
    assert serialize_audio_edl(loaded) == audio_bytes


def test_rich_phase4_replay_materializer_has_all_video_and_audio_tracks() -> None:
    """Fixture covers five visible layers without changing Phase 3 scheduling."""
    replay = build_phase4a_rich_replay_inputs()
    video_edl = replay["video_edl"]
    audio_edl = replay["audio_edl"]
    assert [(track.track.value, len(track.events)) for track in video_edl.tracks] == [
        ("V1", 1), ("V2", 1), ("V3", 1), ("V4", 1), ("V5", 1),
        ("V6", 2), ("V7", 1), ("A1", 0), ("A2", 0), ("A3", 0),
        ("A4", 0), ("A5", 0),
    ]
    assert [(track.track.value, len(track.events)) for track in audio_edl.tracks] == [
        ("A1", 1), ("A2", 2), ("A3", 2), ("A4", 1), ("A5", 2),
    ]
    v3 = next(track for track in video_edl.tracks if track.track is TimelineTrack.V3)
    v4 = next(track for track in video_edl.tracks if track.track is TimelineTrack.V4)
    source = v3.events[0].payload.source
    assert source is not None
    assert source.playback_mode is SourcePlaybackMode.FIT
    assert (
        source.crop_left_millionths, source.crop_top_millionths,
        source.crop_right_millionths, source.crop_bottom_millionths,
    ) == (150_000, 100_000, 850_000, 900_000)
    assert v4.events[0].editorial_role == "metric_chart"
    assert audio_edl.video_edl_id == video_edl.video_edl_id
    assert audio_edl.video_edl_hash == video_edl.video_edl_hash


def test_renderer_bridge_projects_rich_replay_without_rescheduling() -> None:
    """Props carry accepted event fields plus the hash-bound V3 directive verbatim."""
    replay = build_phase4a_rich_replay_inputs()
    video_edl = replay["video_edl"]
    audio_edl = replay["audio_edl"]
    resolver = FixtureAssetResolver.load(FIXTURE_ROOT)
    lock = (ROOT / "renderer-remotion" / "package-lock.json").read_bytes()
    props = build_render_props(
        video_edl=video_edl, audio_edl=audio_edl,
        fixture_assets=resolver, renderer_version_value=renderer_version(lock),
    )
    assert [row["track"] for row in props.video_tracks] == [f"V{index}" for index in range(1, 8)]
    assert [row["track"] for row in props.audio_tracks] == [f"A{index}" for index in range(1, 6)]
    raw_video = json.loads(serialize_video_edl(video_edl))
    raw_audio = json.loads(serialize_audio_edl(audio_edl))
    assert props.video_tracks == tuple(
        {
            "track": track["track"], "kind": track["kind"],
            "priority": track["priority"], "events": track["events"],
        }
        for track in raw_video["tracks"][:7]
    )
    audio_event_fields = (
        "schema_version", "hash_scope_version", "event_id", "event_hash", "track",
        "kind", "ordinal", "intent_id", "source_id", "source_media_hash",
        "normalized_pcm_evidence_hash", "start_sample", "end_exclusive_sample",
        "source_in_sample", "source_out_exclusive_sample", "gain_millibels",
        "cue_start_word_id", "cue_end_word_id", "cue_start_sample",
        "cue_end_exclusive_sample",
    )
    assert props.audio_tracks == tuple(
        {
            "track": track["track"], "priority": track["priority"],
            "events": [{name: event[name] for name in audio_event_fields} for event in track["events"]],
        }
        for track in raw_audio["tracks"]
    )
    boundary_fields = (
        "position", "left_event_id", "right_event_id", "track", "policy",
        "transition", "left_trim_samples", "right_trim_samples", "fade_in_samples",
        "fade_out_samples", "overlap_samples", "protected_silence_samples",
    )
    assert props.audio_boundary_decisions == tuple(
        {name: decision[name] for name in boundary_fields}
        for decision in raw_audio["boundary_decisions"]
    )
    assert props.visual_directives == tuple(_fixture_manifest()["visual_directives"])
    assert [row["event_id"] for row in props.asset_bindings] == sorted(
        row["event_id"] for row in props.asset_bindings
    )
    assert {row["edl_source_ref"] for row in props.asset_bindings} == {
        f"asset_fixture_{ordinal}" for ordinal in range(5)
    }
    data = serialize_render_props(props)
    assert serialize_render_props(load_render_props(data)) == data


def test_bridge_rejects_missing_or_forged_v4_chart_directive(tmp_path: Path) -> None:
    """The chart can move only through its exact V4 event/hash-bound directive."""
    fixture_root = tmp_path / "fixture"
    shutil.copytree(FIXTURE_ROOT, fixture_root)
    missing = json.loads((fixture_root / "fixture_asset_manifest.json").read_text(encoding="utf-8"))
    missing["visual_directives"] = [row for row in missing["visual_directives"] if row["track"] != "V4"]
    _write_manifest_with_recomputed_identity(fixture_root, missing)
    replay = build_phase4a_rich_replay_inputs()
    # The Python contract allows a manifest without V4 only until a chart event
    # is projected; the bridge must reject that attempted static-chart path.
    with pytest.raises(RenderBridgeError) as rejected:
        build_render_props(
            video_edl=replay["video_edl"], audio_edl=replay["audio_edl"],
            fixture_assets=FixtureAssetResolver.load(fixture_root),
            renderer_version_value=renderer_version((ROOT / "renderer-remotion" / "package-lock.json").read_bytes()),
        )
    assert rejected.value.code is RenderFailureCode.VISUAL_DIRECTIVE_INVALID

    forged = _fixture_manifest()
    chart = next(row for row in forged["visual_directives"] if row["track"] == "V4")
    chart["event_hash"] = "0" * 64
    chart_projection = {key: value for key, value in chart.items() if key not in {"directive_id", "directive_hash"}}
    digest = hashlib.sha256(encode_canonical_json_bytes(chart_projection)).hexdigest()
    chart["directive_hash"] = "sha256:" + digest
    chart["directive_id"] = "vdir_" + digest[:32]
    _write_manifest_with_recomputed_identity(fixture_root, forged)
    with pytest.raises(RenderBridgeError) as rejected:
        build_render_props(
            video_edl=replay["video_edl"], audio_edl=replay["audio_edl"],
            fixture_assets=FixtureAssetResolver.load(fixture_root),
            renderer_version_value=renderer_version((ROOT / "renderer-remotion" / "package-lock.json").read_bytes()),
        )
    assert rejected.value.code is RenderFailureCode.VISUAL_DIRECTIVE_INVALID


def test_bridge_rejects_rehashed_renderer_version_or_forged_projected_shape() -> None:
    """The checked-in lock, not a caller supplied version-looking string, is trusted."""
    replay = build_phase4a_rich_replay_inputs()
    resolver = FixtureAssetResolver.load(FIXTURE_ROOT)
    trusted = renderer_version((ROOT / "renderer-remotion" / "package-lock.json").read_bytes())
    with pytest.raises(RenderBridgeError) as rejected:
        build_render_props(video_edl=replay["video_edl"], audio_edl=replay["audio_edl"], fixture_assets=resolver, renderer_version_value=trusted + "+forged")
    assert rejected.value.code is RenderFailureCode.REMOTION_UNAVAILABLE
    props = build_render_props(video_edl=replay["video_edl"], audio_edl=replay["audio_edl"], fixture_assets=resolver, renderer_version_value=trusted)
    forged = dataclasses.replace(props, renderer_version="RRV1|bridge=999.0.0|package_lock_sha256=" + "0" * 64)
    with pytest.raises(RenderBridgeError) as rejected:
        serialize_render_props(forged)
    assert rejected.value.code is RenderFailureCode.NON_CANONICAL_PROPS


def test_phase4a_error_oracles_reject_ingress_and_selector_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every bridge ingress/selector failure is typed before a renderer attempt."""
    import engine.rendering.bridge as bridge_module

    replay = build_phase4a_rich_replay_inputs()
    resolver = FixtureAssetResolver.load(FIXTURE_ROOT)
    version = renderer_version((ROOT / "renderer-remotion" / "package-lock.json").read_bytes())

    monkeypatch.setattr(bridge_module, "serialize_video_edl", lambda _: (_ for _ in ()).throw(RuntimeError("fixture")))
    with pytest.raises(RenderBridgeError) as rejected:
        build_render_props(video_edl=replay["video_edl"], audio_edl=replay["audio_edl"], fixture_assets=resolver, renderer_version_value=version)
    assert rejected.value.code is RenderFailureCode.UPSTREAM_NOT_MATERIALIZED

    with pytest.raises(RenderBridgeError) as rejected:
        build_render_props(video_edl=object(), audio_edl=replay["audio_edl"], fixture_assets=resolver, renderer_version_value=version)  # type: ignore[arg-type]
    assert rejected.value.code is RenderFailureCode.DEPENDENCY_BINDING_INVALID

    with pytest.raises(RenderBridgeError) as rejected:
        build_render_props(video_edl=replay["video_edl"], audio_edl=replay["audio_edl"], fixture_assets=resolver, renderer_version_value=version, composition_id="full-film-v1")
    assert rejected.value.code is RenderFailureCode.UNSUPPORTED_COMPOSITION

    with pytest.raises(RenderBridgeError) as rejected:
        build_render_props(video_edl=replay["video_edl"], audio_edl=replay["audio_edl"], fixture_assets=resolver, renderer_version_value=version, mode=bridge_module.RenderMode.FULL)
    assert rejected.value.code is RenderFailureCode.MODE_NOT_AUTHORIZED


def test_phase4a_error_oracles_reject_missing_and_tampered_fixture_assets(tmp_path: Path) -> None:
    """Resolver failures reach the bridge as public typed failures, never a fallback."""
    replay = build_phase4a_rich_replay_inputs()
    version = renderer_version((ROOT / "renderer-remotion" / "package-lock.json").read_bytes())

    missing_root = tmp_path / "missing"
    shutil.copytree(FIXTURE_ROOT, missing_root)
    missing = json.loads((missing_root / "fixture_asset_manifest.json").read_text(encoding="utf-8"))
    missing["assets"] = missing["assets"][1:]
    _write_manifest_with_recomputed_identity(missing_root, missing)
    with pytest.raises(RenderBridgeError) as rejected:
        build_render_props(video_edl=replay["video_edl"], audio_edl=replay["audio_edl"], fixture_assets=FixtureAssetResolver.load(missing_root), renderer_version_value=version)
    assert rejected.value.code is RenderFailureCode.ASSET_RESOLUTION_FAILED

    tampered_root = tmp_path / "tampered"
    shutil.copytree(FIXTURE_ROOT, tampered_root)
    tampered_resolver = FixtureAssetResolver.load(tampered_root)
    asset = tampered_resolver.manifest.assets[0]
    target = tampered_root.joinpath(*asset.relative_posix_path.split("/"))
    target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(RenderBridgeError) as rejected:
        build_render_props(video_edl=replay["video_edl"], audio_edl=replay["audio_edl"], fixture_assets=tampered_resolver, renderer_version_value=version)
    assert rejected.value.code is RenderFailureCode.ASSET_HASH_MISMATCH


def test_phase4a_error_oracle_reports_mocked_renderer_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The process timeout is fast and produces a terminal failed receipt."""
    import engine.rendering.preview_runner as preview_runner

    replay = build_phase4a_rich_replay_inputs()
    props = build_render_props(video_edl=replay["video_edl"], audio_edl=replay["audio_edl"], fixture_assets=FixtureAssetResolver.load(FIXTURE_ROOT), renderer_version_value=renderer_version((ROOT / "renderer-remotion" / "package-lock.json").read_bytes()))
    monkeypatch.setattr(preview_runner, "which", lambda _: "node")
    monkeypatch.setattr(preview_runner, "_node_version", lambda _: "v0.0.0")

    def timed_out(command, **kwargs):
        raise TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(preview_runner, "_bounded_run", timed_out)
    timed_out_run = run_headless_preview(
        props=props, video_edl_bytes=serialize_video_edl(replay["video_edl"]),
        audio_edl_bytes=serialize_audio_edl(replay["audio_edl"]), fixture_root=FIXTURE_ROOT,
        output_root=tmp_path / "timeout", work_root=tmp_path,
        timestamp_utc="2026-08-05T00:00:00Z", timeout_seconds=1,
    )
    assert timed_out_run.receipt.status is RenderStatus.FAILED
    assert timed_out_run.receipt.failure_code == RenderFailureCode.RENDER_TIMEOUT.value
    assert timed_out_run.preview_manifest_bytes is None


def test_phase4a_error_oracle_maps_nonzero_renderer_exit_to_terminal_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A real adapter nonzero path produces the public terminal failure receipt."""
    import engine.rendering.preview_runner as preview_runner

    replay = build_phase4a_rich_replay_inputs()
    props = build_render_props(
        video_edl=replay["video_edl"], audio_edl=replay["audio_edl"],
        fixture_assets=FixtureAssetResolver.load(FIXTURE_ROOT),
        renderer_version_value=renderer_version((ROOT / "renderer-remotion" / "package-lock.json").read_bytes()),
    )
    monkeypatch.setattr(preview_runner, "which", lambda _: "node")
    monkeypatch.setattr(preview_runner, "_node_version", lambda _: "v0.0.0")
    monkeypatch.setattr(
        preview_runner,
        "_bounded_run",
        lambda *args, **kwargs: (1, b"", b"RENDER_EXIT_NONZERO: forced test failure", False),
    )

    failed = run_headless_preview(
        props=props, video_edl_bytes=serialize_video_edl(replay["video_edl"]),
        audio_edl_bytes=serialize_audio_edl(replay["audio_edl"]), fixture_root=FIXTURE_ROOT,
        output_root=tmp_path / "nonzero", work_root=tmp_path,
        timestamp_utc="2026-08-05T00:00:00Z",
    )
    assert failed.receipt.status is RenderStatus.FAILED
    assert failed.receipt.failure_code == RenderFailureCode.RENDER_EXIT_NONZERO.value
    assert failed.preview_manifest_bytes is None


def test_artifact_batch_rejects_canonical_but_wrong_edl_bytes() -> None:
    """A named EDL cannot be substituted after props lineage has been created."""
    replay = build_phase4a_rich_replay_inputs()
    props = build_render_props(video_edl=replay["video_edl"], audio_edl=replay["audio_edl"], fixture_assets=FixtureAssetResolver.load(FIXTURE_ROOT), renderer_version_value=renderer_version((ROOT / "renderer-remotion" / "package-lock.json").read_bytes()))
    receipt = build_render_receipt(props=props, status=RenderStatus.FAILED, failure_code=RenderFailureCode.RENDER_EXIT_NONZERO.value, node_version=None, preview_manifest_id=None, preview_manifest_hash=None, output_artifact_id=None, output_sha256=None, output_size_bytes=None, artifact_ids=("art_vedl_" + props.video_edl_hash[:32], "art_aedl_" + props.audio_edl_hash[:32], "art_fixman_" + props.fixture_manifest_hash[7:39], "art_rprops_" + props.render_props_hash[7:39]), stdout_bytes=b"", stderr_bytes=b"failed")
    with pytest.raises(RenderBridgeError) as rejected:
        build_artifact_batch(props=props, video_edl_bytes=serialize_audio_edl(replay["audio_edl"]), audio_edl_bytes=serialize_audio_edl(replay["audio_edl"]), fixture_manifest_bytes=MANIFEST_PATH.read_bytes(), receipt=receipt, timestamp_utc="2026-08-05T00:00:00Z")
    assert rejected.value.code is RenderFailureCode.ARTIFACT_REGISTRATION_FAILED


def test_phase4a_headless_preview_adapter_is_deterministic_and_registers_dag(tmp_path: Path) -> None:
    """Python writes canonical props once per isolated run; Node renders no fake path."""
    replay = build_phase4a_rich_replay_inputs()
    video_edl = replay["video_edl"]
    audio_edl = replay["audio_edl"]
    video_bytes = serialize_video_edl(video_edl)
    audio_bytes = serialize_audio_edl(audio_edl)
    props = build_render_props(
        video_edl=video_edl, audio_edl=audio_edl,
        fixture_assets=FixtureAssetResolver.load(FIXTURE_ROOT),
        renderer_version_value=renderer_version((ROOT / "renderer-remotion" / "package-lock.json").read_bytes()),
    )
    first = run_headless_preview(
        props=props, video_edl_bytes=video_bytes, audio_edl_bytes=audio_bytes,
        fixture_root=FIXTURE_ROOT, output_root=tmp_path / "preview-one",
        work_root=tmp_path, timestamp_utc="2026-08-05T00:00:00Z",
    )
    second = run_headless_preview(
        props=props, video_edl_bytes=video_bytes, audio_edl_bytes=audio_bytes,
        fixture_root=FIXTURE_ROOT, output_root=tmp_path / "preview-two",
        work_root=tmp_path, timestamp_utc="2026-08-05T00:00:00Z",
    )
    assert first.receipt.status is RenderStatus.SUCCEEDED
    assert second.receipt.status is RenderStatus.SUCCEEDED
    assert first.preview_manifest_bytes == second.preview_manifest_bytes
    assert serialize_render_receipt(first.receipt) == serialize_render_receipt(second.receipt)
    assert first.receipt.artifact_ids == second.receipt.artifact_ids
    assert first.receipt.output_sha256 == "sha256:" + hashlib.sha256(first.preview_manifest_bytes).hexdigest()
    assert first.receipt.preview_manifest_hash == first.receipt.output_sha256
    assert first.receipt.preview_manifest_id == first.receipt.output_artifact_id
    for forged in (
        dataclasses.replace(first.receipt, output_size_bytes=True),
        dataclasses.replace(first.receipt, output_size_bytes=1 << 64),
        dataclasses.replace(first.receipt, preview_manifest_hash="sha256:" + "0" * 64),
    ):
        with pytest.raises(RenderBridgeError) as rejected:
            serialize_render_receipt(forged)
        assert rejected.value.code is RenderFailureCode.RECEIPT_INVALID
    # V4 chart-reveal evidence is not accepted merely because both endpoint
    # files exist: the actual decoded frame pixels must prove visual change.
    rgba_33 = _decode_png_rgba((tmp_path / "preview-one" / "preview" / "frames" / "33.png").read_bytes())[2]
    rgba_65 = _decode_png_rgba((tmp_path / "preview-one" / "preview" / "frames" / "65.png").read_bytes())[2]
    assert hashlib.sha256(rgba_33).hexdigest() != hashlib.sha256(rgba_65).hexdigest()
    assert rgba_33 != rgba_65
    # V3 has independent evidence at its EDL-bound endpoints.  This crop lies
    # inside the V3 source panel and outside V4, captions and the brand mark,
    # so a changed decoded region proves the hash-bound zoom/crop projection
    # rather than a chart reveal or a scheduler-side timing rewrite.
    rgba_12 = _decode_png_rgba((tmp_path / "preview-one" / "preview" / "frames" / "12.png").read_bytes())[2]
    rgba_47 = _decode_png_rgba((tmp_path / "preview-one" / "preview" / "frames" / "47.png").read_bytes())[2]
    def v3_source_region(rgba: bytes) -> bytes:
        return b"".join(
            rgba[(row * 1280 + 260) * 4:(row * 1280 + 620) * 4]
            for row in range(300, 490)
        )
    assert hashlib.sha256(v3_source_region(rgba_12)).hexdigest() != hashlib.sha256(v3_source_region(rgba_47)).hexdigest()
    assert not (tmp_path / "preview-one" / "trusted-public").exists()
    assert not (tmp_path / "preview-two" / "trusted-public").exists()
    assert [record.artifact_id for record in first.artifacts.records] == list(first.receipt.artifact_ids) + [
        "art_rreceipt_" + first.receipt.receipt_hash[7:39]
    ]
    assert {record.artifact_type for record in first.artifacts.records} >= {
        "renderer_input", "fixture_manifest", "render_props", "render_frame",
        "render_manifest", "render_receipt",
    }
    assert not list(tmp_path.glob("phase4a_preview_*"))


def test_headless_preview_cancellation_is_terminal_before_renderer_side_effects(tmp_path: Path) -> None:
    """The parent-owned cancellation double cannot leave a partial preview DAG."""
    replay = build_phase4a_rich_replay_inputs()
    props = build_render_props(
        video_edl=replay["video_edl"], audio_edl=replay["audio_edl"],
        fixture_assets=FixtureAssetResolver.load(FIXTURE_ROOT),
        renderer_version_value=renderer_version((ROOT / "renderer-remotion" / "package-lock.json").read_bytes()),
    )
    output_root = tmp_path / "must-not-exist"
    cancelled = run_headless_preview(
        props=props, video_edl_bytes=serialize_video_edl(replay["video_edl"]),
        audio_edl_bytes=serialize_audio_edl(replay["audio_edl"]), fixture_root=FIXTURE_ROOT,
        output_root=output_root, work_root=tmp_path, timestamp_utc="2026-08-05T00:00:00Z",
        cancel_requested=True,
    )
    assert cancelled.receipt.status is RenderStatus.CANCELLED
    assert cancelled.receipt.failure_code == RenderFailureCode.CANCELLED_BY_PARENT.value
    assert cancelled.preview_manifest_bytes is None
    assert not output_root.exists()
    assert [record.artifact_type for record in cancelled.artifacts.records] == [
        "renderer_input", "renderer_input", "fixture_manifest", "render_props", "render_receipt",
    ]
    assert all(record.artifact_type not in {"render_frame", "render_manifest"} for record in cancelled.artifacts.records)


def test_headless_preview_reports_existing_output_target_without_materializing_assets(tmp_path: Path) -> None:
    """A pre-existing output root is a typed terminal error, never overwrite permission."""
    replay = build_phase4a_rich_replay_inputs()
    props = build_render_props(
        video_edl=replay["video_edl"], audio_edl=replay["audio_edl"],
        fixture_assets=FixtureAssetResolver.load(FIXTURE_ROOT),
        renderer_version_value=renderer_version((ROOT / "renderer-remotion" / "package-lock.json").read_bytes()),
    )
    output_root = tmp_path / "already-registered"
    output_root.mkdir()
    failed = run_headless_preview(
        props=props, video_edl_bytes=serialize_video_edl(replay["video_edl"]),
        audio_edl_bytes=serialize_audio_edl(replay["audio_edl"]), fixture_root=FIXTURE_ROOT,
        output_root=output_root, work_root=tmp_path, timestamp_utc="2026-08-05T00:00:00Z",
    )
    assert failed.receipt.status is RenderStatus.FAILED
    assert failed.receipt.failure_code == RenderFailureCode.OUTPUT_TARGET_EXISTS.value
    assert failed.preview_manifest_bytes is None
    assert list(output_root.iterdir()) == []
    assert not list(tmp_path.glob("phase4a_preview_*"))


def test_preview_manifest_rejects_lineage_substitution_and_decoded_rgba_mismatch(tmp_path: Path) -> None:
    """Canonical re-hashing cannot make substituted preview evidence trusted."""
    replay = build_phase4a_rich_replay_inputs()
    props = build_render_props(
        video_edl=replay["video_edl"], audio_edl=replay["audio_edl"],
        fixture_assets=FixtureAssetResolver.load(FIXTURE_ROOT),
        renderer_version_value=renderer_version((ROOT / "renderer-remotion" / "package-lock.json").read_bytes()),
    )
    output = tmp_path / "valid"
    completed = run_headless_preview(
        props=props, video_edl_bytes=serialize_video_edl(replay["video_edl"]),
        audio_edl_bytes=serialize_audio_edl(replay["audio_edl"]), fixture_root=FIXTURE_ROOT,
        output_root=output, work_root=tmp_path, timestamp_utc="2026-08-05T00:00:00Z",
    )
    assert completed.receipt.status is RenderStatus.SUCCEEDED

    extra_output = tmp_path / "unexpected-preview-output"
    shutil.copytree(output, extra_output)
    (extra_output / "preview" / "unrelated.txt").write_text("must not be accepted", encoding="utf-8")
    valid_result = {
        "status": "SUCCEEDED",
        "node_version": "v0.0.0",
        "manifest_path": "preview/render-manifest.json",
        "manifest_id": completed.receipt.preview_manifest_id,
        "manifest_hash": completed.receipt.preview_manifest_hash,
    }
    with pytest.raises(RenderBridgeError) as rejected:
        _preview_manifest(extra_output, valid_result, props=props)
    assert rejected.value.code is RenderFailureCode.PREVIEW_MANIFEST_INVALID

    def rewrite(root: Path, mutate) -> dict[str, object]:
        shutil.copytree(output, root)
        path = root / "preview" / "render-manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        mutate(manifest)
        identity = {key: item for key, item in manifest.items() if key not in {"manifest_id", "manifest_hash"}}
        digest = "sha256:" + hashlib.sha256(encode_canonical_json_bytes(identity)).hexdigest()
        manifest["manifest_hash"] = digest
        manifest["manifest_id"] = "rman_" + digest[7:39]
        path.write_bytes(encode_canonical_json_bytes(manifest))
        return {"status": "SUCCEEDED", "node_version": "v0.0.0", "manifest_path": "preview/render-manifest.json", "manifest_id": manifest["manifest_id"], "manifest_hash": manifest["manifest_hash"]}

    replaced = rewrite(tmp_path / "substituted", lambda value: value.__setitem__("render_props_hash", "sha256:" + "0" * 64))
    with pytest.raises(RenderBridgeError) as rejected:
        _preview_manifest(tmp_path / "substituted", replaced, props=props)
    assert rejected.value.code is RenderFailureCode.PREVIEW_MANIFEST_INVALID

    rgba_mismatch = rewrite(tmp_path / "rgba-mismatch", lambda value: value["frames"][0].__setitem__("decoded_rgba_sha256", "sha256:" + "0" * 64))
    with pytest.raises(RenderBridgeError) as rejected:
        _preview_manifest(tmp_path / "rgba-mismatch", rgba_mismatch, props=props)
    assert rejected.value.code is RenderFailureCode.PREVIEW_FRAME_HASH_MISMATCH


def test_phase3_video_event_contract_preserves_only_existing_scheduler_fields() -> None:
    """Guard against a test-side scheduler or asset-binding rewrite.

    The bridge must project these accepted events verbatim; this scaffold does
    not mutate source descriptors, event timing, or audio boundary decisions.
    """
    kwargs = _all_track_kwargs(rate=TemporalFrameRate(30, 1))
    video_edl = kwargs["video_edl"]
    event = next(item for track in video_edl.tracks for item in track.events)
    source = event.payload.source
    assert source is not None
    assert tuple(field.name for field in dataclasses.fields(type(event))) == (
        "schema_version", "hash_scope_version", "event_id", "event_hash", "track",
        "ordinal", "intent_id", "editorial_role", "start_frame",
        "end_exclusive_frame", "start_word_id", "end_word_id", "payload",
    )
    assert event.start_frame < event.end_exclusive_frame
    assert source.bound_start_word_id == event.start_word_id
    assert source.bound_end_word_id == event.end_word_id
