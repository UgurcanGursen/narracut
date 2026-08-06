from __future__ import annotations

from engine.durable_queue import DurableLocalQueue


def test_queue_is_durable_idempotent_and_retries_once(tmp_path):
    path = tmp_path / "jobs.sqlite3"
    queue = DurableLocalQueue(path)
    job = queue.enqueue(kind="preview_replay", payload={"snapshot_id": "risnap_1"}, max_attempts=2)
    assert queue.enqueue(kind="preview_replay", payload={"snapshot_id": "risnap_1"}, max_attempts=2) == job
    assert queue.lease_next().state == "running"
    assert queue.complete(job_id=job.job_id, succeeded=False).state == "queued"
    assert queue.lease_next().attempt == 2
    assert queue.complete(job_id=job.job_id, succeeded=False).state == "failed"
    queue.close()
    reopened = DurableLocalQueue(path)
    assert reopened.get(job.job_id).state == "failed"


def test_recovery_requeues_interrupted_job_until_attempt_limit(tmp_path):
    queue = DurableLocalQueue(tmp_path / "jobs.sqlite3")
    job = queue.enqueue(kind="preview_replay", payload={"snapshot_id": "risnap_1"}, max_attempts=2)
    queue.lease_next()
    assert queue.recover_interrupted()[0].state == "queued"
    queue.lease_next()
    assert queue.recover_interrupted()[0].state == "failed"
