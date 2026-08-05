from pathlib import Path

import pytest

from engine.rendering import OutputTargetHead, provision_output_target
from engine.rendering.full_render import FullRenderError
from engine.rendering.lifecycle_registry import (
    cleanup_attempt, commit_transaction, next_target_revision, resolve_target_head, snapshot_attempt,
)


def _head() -> OutputTargetHead:
    return OutputTargetHead("outt_" + "a" * 32, "project_replay", "sequence_replay", "renders/final/output.mp4")


def test_append_only_target_revision_and_terminal_journal(tmp_path: Path) -> None:
    initial = provision_output_target(project_root=tmp_path, head=_head())
    base = resolve_target_head(project_root=tmp_path, output_target_id=_head().output_target_id)
    attempt = tmp_path / "attempt"; attempt.mkdir(); (attempt / "stage.bin").write_bytes(b"stage")
    pre = snapshot_attempt(attempt_root=attempt, attempt_id="attempt_1", cleanup_state="PRE_CLEANUP")
    post = cleanup_attempt(attempt_root=attempt, pre_cleanup=pre)
    revision = next_target_revision(base=base, output_artifact_id="art_final_1", output_content_sha256="sha256:" + "b" * 64, replacement_policy=None)
    receipt = commit_transaction(project_root=tmp_path, transaction_id="txn_1", base_target=base, target_revision=revision, artifact_rows=(), terminal_status="SUCCEEDED", receipt_payload={"request_id": "frq_1"}, pre_cleanup=pre, post_cleanup=post)
    assert receipt["status"] == "SUCCEEDED"
    assert resolve_target_head(project_root=tmp_path, output_target_id=_head().output_target_id)["revision"] == initial["revision"] + 1
    assert not list(attempt.rglob("*"))


def test_failed_terminal_cannot_append_target_revision_and_cleanup_detects_orphan(tmp_path: Path) -> None:
    provision_output_target(project_root=tmp_path, head=_head())
    base = resolve_target_head(project_root=tmp_path, output_target_id=_head().output_target_id)
    attempt = tmp_path / "attempt"; attempt.mkdir(); (attempt / "expected.bin").write_bytes(b"x")
    pre = snapshot_attempt(attempt_root=attempt, attempt_id="attempt_2", cleanup_state="PRE_CLEANUP")
    (attempt / "orphan.bin").write_bytes(b"y")
    with pytest.raises(FullRenderError) as orphan:
        cleanup_attempt(attempt_root=attempt, pre_cleanup=pre)
    assert orphan.value.code == "ARTIFACT_PERSIST_FAILED"
    post = snapshot_attempt(attempt_root=attempt, attempt_id="attempt_2", cleanup_state="POST_CLEANUP")
    revision = next_target_revision(base=base, output_artifact_id="art_final_2", output_content_sha256="sha256:" + "c" * 64, replacement_policy=None)
    with pytest.raises(FullRenderError) as rejected:
        commit_transaction(project_root=tmp_path, transaction_id="txn_2", base_target=base, target_revision=revision, artifact_rows=(), terminal_status="FAILED", receipt_payload={}, pre_cleanup=pre, post_cleanup=post)
    assert rejected.value.code == "ARTIFACT_PERSIST_FAILED"
