import json
from pathlib import Path

import pytest

from engine.rendering import OutputTargetHead, provision_output_target
from engine.rendering.full_render import FullRenderError
from engine.rendering.lifecycle_registry import (
    append_recovery_compensation, build_compensation_revision, cleanup_attempt,
    commit_transaction, next_target_revision, resolve_target_head, snapshot_attempt,
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


def test_cleanup_retains_only_explicit_non_ephemeral_inventory_entries(tmp_path: Path) -> None:
    attempt = tmp_path / "attempt"; attempt.mkdir()
    (attempt / "keep.bin").write_bytes(b"keep")
    (attempt / "remove.bin").write_bytes(b"remove")
    pre = snapshot_attempt(
        attempt_root=attempt, attempt_id="attempt_3", cleanup_state="PRE_CLEANUP",
        retention_by_relative_path={"keep.bin": "review"},
    )
    post = cleanup_attempt(attempt_root=attempt, pre_cleanup=pre)
    assert [row["relative_path"] for row in post.files] == ["keep.bin"]
    assert post.files[0]["retention_class"] == "review"


@pytest.mark.parametrize("locked,approved,expected", [(True, False, "OUTPUT_LOCKED"), (False, True, "OUTPUT_APPROVED")])
def test_locked_or_approved_head_cannot_create_a_revision(
    tmp_path: Path, locked: bool, approved: bool, expected: str,
) -> None:
    head = OutputTargetHead(
        _head().output_target_id, "project_replay", "sequence_replay",
        "renders/final/output.mp4", locked=locked, approved=approved,
    )
    provision_output_target(project_root=tmp_path, head=head)
    base = resolve_target_head(project_root=tmp_path, output_target_id=head.output_target_id)
    with pytest.raises(FullRenderError) as rejected:
        next_target_revision(
            base=base, output_artifact_id="art_final_locked",
            output_content_sha256="sha256:" + "d" * 64, replacement_policy=None,
        )
    assert rejected.value.code == expected


def test_recovery_compensation_appends_new_head_and_restores_first_publish_null_state(tmp_path: Path) -> None:
    provision_output_target(project_root=tmp_path, head=_head())
    base = resolve_target_head(project_root=tmp_path, output_target_id=_head().output_target_id)
    provisional = next_target_revision(
        base=base, output_artifact_id="art_final_rollback",
        output_content_sha256="sha256:" + "e" * 64, replacement_policy=None,
    )
    targets = tmp_path / "artifacts" / "output-targets.jsonl"
    with targets.open("ab") as stream:
        stream.write(json.dumps(provisional, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n")
    journal = tmp_path / "artifacts" / "transactions" / "txn_recovery_1.json"
    journal.parent.mkdir(parents=True)
    journal.write_text(json.dumps({
        "schema_version": "FULL-RENDER-TRANSACTION-V1", "transaction_id": "txn_recovery_1",
        "base_target_record_id": base["output_target_record_id"],
        "base_target_record_hash": base["output_target_record_hash"],
        "target_revision": provisional,
    }, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    expected = build_compensation_revision(base_target=base, provisional_target=provisional)
    actual = append_recovery_compensation(
        project_root=tmp_path, transaction_id="txn_recovery_1",
        base_target=base, provisional_target=provisional,
    )
    assert actual == expected
    head = resolve_target_head(project_root=tmp_path, output_target_id=_head().output_target_id)
    assert head["revision"] == 3
    assert head["current_output_artifact_id"] is None
    assert head["replacement_policy"] is None
    markers = (tmp_path / "artifacts" / "registry.jsonl").read_text(encoding="utf-8")
    assert "RECOVERY_COMPENSATION_RECORDED" in markers
