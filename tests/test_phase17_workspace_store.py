from __future__ import annotations

import pytest

from engine.workspace_store import WorkspaceJobJournal, WorkspaceRevisionStore


PROJECT = "prj_phase17"


def test_revision_reopens_and_preserves_prior_active_revision(tmp_path):
    store = WorkspaceRevisionStore(tmp_path)
    first = store.publish(project_id=PROJECT, created_at="2026-08-06T00:00:00Z", files={"workspace.json": b'{"version":1}'})
    second = store.publish(project_id=PROJECT, created_at="2026-08-06T00:01:00Z", files={"workspace.json": b'{"version":2}', "timing/words.json": b"[]"})
    assert store.load_active(project_id=PROJECT) == second
    assert first.revision_id != second.revision_id


def test_recovery_quarantines_staging_and_restores_verified_revision(tmp_path):
    store = WorkspaceRevisionStore(tmp_path)
    expected = store.publish(project_id=PROJECT, created_at="2026-08-06T00:00:00Z", files={"workspace.json": b"{}"})
    project = tmp_path / "projects" / PROJECT
    bad = project / ".staging" / "stage_interrupted"
    bad.mkdir(parents=True)
    (bad / "partial.bin").write_bytes(b"partial")
    (project / "active.json").write_bytes(b"not-json")
    assert store.recover(project_id=PROJECT) == expected
    assert (project / ".recovery/staging/stage_interrupted/partial.bin").read_bytes() == b"partial"


def test_tampered_revision_and_unsafe_paths_fail_closed(tmp_path):
    store = WorkspaceRevisionStore(tmp_path)
    revision = store.publish(project_id=PROJECT, created_at="2026-08-06T00:00:00Z", files={"workspace.json": b"{}"})
    revision_path = tmp_path / "projects" / PROJECT / "revisions" / revision.revision_id / "workspace.json"
    revision_path.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="WORKSPACE_REVISION_INVALID"):
        store.load_active(project_id=PROJECT)
    with pytest.raises(ValueError, match="PATH_INVALID"):
        store.publish(project_id=PROJECT, created_at="2026-08-06T00:02:00Z", files={"workspace.json": b"{}", "../escape": b"x"})


def test_job_journal_recovers_interrupted_work_as_visible_terminal_state(tmp_path):
    journal = WorkspaceJobJournal(tmp_path)
    journal.append(project_id=PROJECT, job_id="job_preview", state="queued", created_at="2026-08-06T00:00:00Z", attempt=1)
    journal.append(project_id=PROJECT, job_id="job_preview", state="running", created_at="2026-08-06T00:01:00Z", attempt=1)
    recovered = journal.recover_interrupted(project_id=PROJECT, created_at="2026-08-06T00:02:00Z")
    assert recovered[0]["state"] == "recovery_required"
    assert journal.events(project_id=PROJECT)[-1]["state"] == "recovery_required"
