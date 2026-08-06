"""Small SQLite-backed local queue for Phase 17 single-machine workers."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from engine.contracts._canonical_json import encode_canonical_json_bytes


def _hash(value: object) -> str:
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


@dataclass(frozen=True)
class QueuedJob:
    job_id: str
    job_hash: str
    kind: str
    payload: dict[str, object]
    max_attempts: int
    attempt: int
    state: str


class DurableLocalQueue:
    """Durable admission, leasing and crash recovery; it never starts a thread."""

    def __init__(self, database_path: Path) -> None:
        self.connection = sqlite3.connect(Path(database_path), isolation_level=None)
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS durable_jobs (
            job_id TEXT PRIMARY KEY, job_hash TEXT UNIQUE NOT NULL, kind TEXT NOT NULL,
            payload_json BLOB NOT NULL, max_attempts INTEGER NOT NULL, attempt INTEGER NOT NULL,
            state TEXT NOT NULL
        )""")

    def close(self) -> None:
        self.connection.close()

    def enqueue(self, *, kind: str, payload: dict[str, object], max_attempts: int = 2) -> QueuedJob:
        if type(kind) is not str or not kind or type(payload) is not dict or type(max_attempts) is not int or not 1 <= max_attempts <= 5:
            raise ValueError("DURABLE_QUEUE_INPUT_INVALID")
        body = {"kind": kind, "payload": payload, "max_attempts": max_attempts}
        digest = _hash(body)
        job = QueuedJob("dqjob_" + digest[7:31], digest, kind, payload, max_attempts, 0, "queued")
        try:
            self.connection.execute("INSERT INTO durable_jobs(job_id,job_hash,kind,payload_json,max_attempts,attempt,state) VALUES(?,?,?,?,?,?,?)", (job.job_id, job.job_hash, kind, encode_canonical_json_bytes(payload), max_attempts, 0, "queued"))
        except sqlite3.IntegrityError:
            existing = self.get(job.job_id)
            if existing is None or existing.job_hash != digest:
                raise ValueError("DURABLE_QUEUE_IDENTITY_CONFLICT")
            return existing
        return job

    def lease_next(self) -> QueuedJob | None:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            row = self.connection.execute("SELECT job_id FROM durable_jobs WHERE state='queued' ORDER BY job_id LIMIT 1").fetchone()
            if row is None:
                self.connection.execute("COMMIT"); return None
            self.connection.execute("UPDATE durable_jobs SET state='running',attempt=attempt+1 WHERE job_id=? AND state='queued'", (row[0],))
            job = self.get(row[0])
            self.connection.execute("COMMIT")
            return job
        except BaseException:
            self.connection.execute("ROLLBACK"); raise

    def complete(self, *, job_id: str, succeeded: bool) -> QueuedJob:
        job = self.get(job_id)
        if job is None or job.state != "running":
            raise ValueError("DURABLE_QUEUE_TRANSITION_INVALID")
        state = "succeeded" if succeeded else ("queued" if job.attempt < job.max_attempts else "failed")
        self.connection.execute("UPDATE durable_jobs SET state=? WHERE job_id=?", (state, job_id))
        return self.get(job_id)  # type: ignore[return-value]

    def recover_interrupted(self) -> tuple[QueuedJob, ...]:
        self.connection.execute("UPDATE durable_jobs SET state=CASE WHEN attempt < max_attempts THEN 'queued' ELSE 'failed' END WHERE state='running'")
        rows = self.connection.execute("SELECT job_id FROM durable_jobs WHERE state IN ('queued','failed') ORDER BY job_id").fetchall()
        return tuple(self.get(row[0]) for row in rows)  # type: ignore[arg-type]

    def get(self, job_id: str) -> QueuedJob | None:
        row = self.connection.execute("SELECT job_id,job_hash,kind,payload_json,max_attempts,attempt,state FROM durable_jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            return None
        payload = json.loads(row[3].decode("utf-8"))
        body = {"kind": row[2], "payload": payload, "max_attempts": row[4]}
        if row[1] != _hash(body) or row[0] != "dqjob_" + row[1][7:31]:
            raise ValueError("DURABLE_QUEUE_RECORD_INVALID")
        return QueuedJob(row[0], row[1], row[2], payload, row[4], row[5], row[6])
