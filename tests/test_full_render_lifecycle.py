"""Focused REPLAY-only Phase 4B admission and FFmpeg terminality gates."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from engine.rendering import (
    FullRenderError, OutputTargetHead, atomic_publish, build_full_render_request,
    provision_output_target, resolve_output_target,
)
from engine.rendering.bridge import build_render_props, renderer_version
from engine.rendering.fixture_assets import FixtureAssetResolver
from tests.test_render_bridge import FIXTURE_ROOT, ROOT, build_phase4a_rich_replay_inputs


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
        props=props, profile_id="profile_replay", profile_hash="sha256:" + "2" * 64,
        output_target_id="outt_" + "1" * 32, pcm_manifest=manifest,
        cancellation_ingress_id="cancel_fixture_1",
    )
    assert request["schema_version"] == "FULL-RENDER-REQUEST-V1"
    assert request["render_props"]["mode"] == "PREVIEW"
    assert request["render_props_canonical_sha256"] == "sha256:" + hashlib.sha256(
        __import__("engine.rendering.bridge", fromlist=["serialize_render_props"]).serialize_render_props(props)
    ).hexdigest()
    with pytest.raises(FullRenderError) as rejected:
        build_full_render_request(props=props, profile_id="", profile_hash="sha256:" + "2" * 64, output_target_id="outt_" + "1" * 32, pcm_manifest=manifest, cancellation_ingress_id="x")
    assert rejected.value.code == "FULL_REQUEST_INVALID"


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
