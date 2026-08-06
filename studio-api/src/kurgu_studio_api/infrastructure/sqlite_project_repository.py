"""Local durable project repository for the Studio control plane.

It persists validated project/domain metadata only. Media, artifact lifecycle
and workspace recovery remain outside this Phase 13 repository.
"""

from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any, Mapping

from ..application.models import ProjectAggregate, ResolvedDomainSelection
from ..application.models import PreviewJobEvent, PreviewJobRecord, RenderInputSnapshotRecord, ReviewSnapshotRecord, StudioTaskRecord, StudioTaskView
from ..application.ports import RepositoryCollisionError


class SQLiteProjectRepository:
    persistence_scope = "local_sqlite"

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS studio_projects (
              project_id TEXT PRIMARY KEY,
              project_json BLOB NOT NULL,
              domain_json BLOB NOT NULL,
              artifacts_json BLOB NOT NULL
            )
            """
        )
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS studio_tasks (
              task_id TEXT PRIMARY KEY,
              task_hash TEXT NOT NULL UNIQUE,
              project_id TEXT NOT NULL REFERENCES studio_projects(project_id),
              payload_json BLOB NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS studio_task_events (
              event_id INTEGER PRIMARY KEY AUTOINCREMENT,
              task_id TEXT NOT NULL REFERENCES studio_tasks(task_id),
              status TEXT NOT NULL,
              response_hash TEXT,
              validation_issues_json BLOB NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS studio_review_snapshots (
              project_id TEXT PRIMARY KEY REFERENCES studio_projects(project_id),
              snapshot_id TEXT NOT NULL UNIQUE,
              snapshot_hash TEXT NOT NULL UNIQUE,
              payload_json BLOB NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS studio_review_decisions (
              decision_id TEXT PRIMARY KEY,
              decision_hash TEXT NOT NULL UNIQUE,
              project_id TEXT NOT NULL REFERENCES studio_projects(project_id),
              sequence_id TEXT NOT NULL,
              payload_json BLOB NOT NULL,
              UNIQUE(project_id, sequence_id)
            );
            CREATE TABLE IF NOT EXISTS studio_render_inputs (
              snapshot_id TEXT PRIMARY KEY,
              snapshot_hash TEXT NOT NULL UNIQUE,
              project_id TEXT NOT NULL REFERENCES studio_projects(project_id),
              sequence_id TEXT NOT NULL,
              payload_json BLOB NOT NULL,
              video_edl_bytes BLOB NOT NULL,
              audio_edl_bytes BLOB NOT NULL,
              render_props_bytes BLOB NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(project_id, sequence_id, snapshot_hash)
            );
            CREATE TABLE IF NOT EXISTS studio_preview_jobs (
              job_id TEXT PRIMARY KEY,
              request_hash TEXT NOT NULL,
              attempt_ordinal INTEGER NOT NULL,
              project_id TEXT NOT NULL REFERENCES studio_projects(project_id),
              payload_json BLOB NOT NULL,
              active INTEGER NOT NULL,
              UNIQUE(request_hash, attempt_ordinal)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS studio_one_active_preview_request
              ON studio_preview_jobs(request_hash) WHERE active = 1;
            CREATE TABLE IF NOT EXISTS studio_preview_job_events (
              job_id TEXT NOT NULL REFERENCES studio_preview_jobs(job_id),
              ordinal INTEGER NOT NULL,
              payload_json BLOB NOT NULL,
              PRIMARY KEY(job_id, ordinal)
            );
            """
        )
        self.connection.commit()

    def close(self) -> None:
        with self._lock:
            self.connection.close()

    @staticmethod
    def _encode(value: object) -> bytes:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    @staticmethod
    def _decode(value: bytes) -> Any:
        return json.loads(value.decode("utf-8"))

    def create(self, aggregate: ProjectAggregate) -> None:
        project_id = aggregate.project["project_id"]
        domain = {
            field: getattr(aggregate.domain, field)
            for field in aggregate.domain.__dataclass_fields__
        }
        with self._lock:
            try:
                self.connection.execute(
                    """
                    INSERT INTO studio_projects(
                      project_id, project_json, domain_json, artifacts_json
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        self._encode(aggregate.project),
                        self._encode(domain),
                        self._encode(list(aggregate.artifacts)),
                    ),
                )
                self.connection.commit()
            except sqlite3.IntegrityError as exc:
                raise RepositoryCollisionError(project_id) from exc

    def get(self, project_id: str) -> ProjectAggregate | None:
        with self._lock:
            row = self.connection.execute(
                """
                SELECT project_json, domain_json, artifacts_json
                FROM studio_projects WHERE project_id = ?
                """,
                (project_id,),
            ).fetchone()
        return None if row is None else self._aggregate(row)

    def list_projects(self) -> tuple[ProjectAggregate, ...]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT project_json, domain_json, artifacts_json
                FROM studio_projects ORDER BY project_id ASC
                """
            ).fetchall()
        return tuple(self._aggregate(row) for row in rows)

    def list_artifacts(
        self,
        project_id: str,
    ) -> tuple[Mapping[str, Any], ...] | None:
        aggregate = self.get(project_id)
        return None if aggregate is None else aggregate.artifacts

    def _aggregate(self, row: tuple[bytes, bytes, bytes]) -> ProjectAggregate:
        project = self._decode(row[0])
        domain_data = self._decode(row[1])
        artifacts = self._decode(row[2])
        domain = ResolvedDomainSelection(
            **{
                **domain_data,
                "profile": deepcopy(domain_data["profile"]),
                "policy_snapshot": deepcopy(domain_data["policy_snapshot"]),
            }
        )
        return ProjectAggregate(
            project=deepcopy(project),
            domain=domain,
            artifacts=tuple(deepcopy(artifacts)),
        )

    def put_task(self, task: StudioTaskRecord) -> None:
        payload = {
            field: getattr(task, field)
            for field in task.__dataclass_fields__
        }
        with self._lock:
            try:
                self.connection.execute(
                    """
                    INSERT INTO studio_tasks(task_id, task_hash, project_id, payload_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (task.task_id, task.task_hash, task.project_id, self._encode(payload), task.created_at),
                )
                self.connection.commit()
            except sqlite3.IntegrityError as exc:
                row = self.connection.execute(
                    "SELECT payload_json FROM studio_tasks WHERE task_id = ?", (task.task_id,)
                ).fetchone()
                if row is None or row[0] != self._encode(payload):
                    raise ValueError("STUDIO_TASK_IMMUTABILITY") from exc

    def get_task(self, task_id: str) -> StudioTaskView | None:
        with self._lock:
            row = self.connection.execute(
                """
                SELECT task.payload_json, event.status, event.response_hash, event.validation_issues_json
                FROM studio_tasks AS task
                LEFT JOIN studio_task_events AS event ON event.event_id = (
                  SELECT event_id FROM studio_task_events
                  WHERE task_id = task.task_id ORDER BY event_id DESC LIMIT 1
                )
                WHERE task.task_id = ?
                """,
                (task_id,),
            ).fetchone()
        return None if row is None else self._task_view(row)

    def list_tasks(self, project_id: str) -> tuple[StudioTaskView, ...]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT task.payload_json, event.status, event.response_hash, event.validation_issues_json
                FROM studio_tasks AS task
                LEFT JOIN studio_task_events AS event ON event.event_id = (
                  SELECT event_id FROM studio_task_events
                  WHERE task_id = task.task_id ORDER BY event_id DESC LIMIT 1
                )
                WHERE task.project_id = ? ORDER BY task.created_at ASC, task.task_id ASC
                """,
                (project_id,),
            ).fetchall()
        return tuple(self._task_view(row) for row in rows)

    def record_task_result(
        self,
        *,
        task_id: str,
        status: str,
        response_hash: str | None,
        validation_issues: tuple[str, ...],
        created_at: str,
    ) -> None:
        if status not in {"waiting", "valid", "repair_required", "approved"}:
            raise ValueError("STUDIO_TASK_EVENT_INVALID")
        with self._lock:
            self.connection.execute(
                """
                INSERT INTO studio_task_events(task_id, status, response_hash, validation_issues_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (task_id, status, response_hash, self._encode(list(validation_issues)), created_at),
            )
            self.connection.commit()

    def put_review_snapshot(self, snapshot: ReviewSnapshotRecord) -> None:
        payload = {
            field: getattr(snapshot, field)
            for field in snapshot.__dataclass_fields__
        }
        with self._lock:
            existing = self.connection.execute(
                "SELECT snapshot_hash, payload_json FROM studio_review_snapshots WHERE project_id = ?",
                (snapshot.project_id,),
            ).fetchone()
            if existing is not None:
                if existing != (snapshot.snapshot_hash, self._encode(payload)):
                    raise ValueError("REVIEW_SNAPSHOT_REPLACEMENT_REQUIRES_NEW_PROJECT_REVISION")
                return
            self.connection.execute(
                """
                INSERT INTO studio_review_snapshots(project_id, snapshot_id, snapshot_hash, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (snapshot.project_id, snapshot.snapshot_id, snapshot.snapshot_hash, self._encode(payload), snapshot.created_at),
            )
            self.connection.commit()

    def get_review_snapshot(self, project_id: str) -> ReviewSnapshotRecord | None:
        with self._lock:
            row = self.connection.execute(
                "SELECT payload_json FROM studio_review_snapshots WHERE project_id = ?", (project_id,)
            ).fetchone()
        if row is None:
            return None
        value = self._decode(row[0])
        return ReviewSnapshotRecord(**value)

    def get_review_decision(
        self,
        *,
        project_id: str,
        sequence_id: str,
    ) -> Mapping[str, Any] | None:
        with self._lock:
            row = self.connection.execute(
                """
                SELECT payload_json FROM studio_review_decisions
                WHERE project_id = ? AND sequence_id = ?
                """,
                (project_id, sequence_id),
            ).fetchone()
        return None if row is None else self._decode(row[0])

    def put_review_decision(self, value: Mapping[str, Any]) -> None:
        with self._lock:
            try:
                self.connection.execute(
                    """
                    INSERT INTO studio_review_decisions(
                      decision_id, decision_hash, project_id, sequence_id, payload_json
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        value["decision_id"], value["decision_hash"], value["project_id"],
                        value["sequence_id"], self._encode(value),
                    ),
                )
                self.connection.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError("REVIEW_SEQUENCE_LOCKED") from exc

    def put_render_input(self, value: RenderInputSnapshotRecord) -> None:
        payload = {field: getattr(value, field) for field in value.__dataclass_fields__ if not field.endswith("_bytes")}
        with self._lock:
            try:
                self.connection.execute(
                    """INSERT INTO studio_render_inputs(snapshot_id, snapshot_hash, project_id, sequence_id, payload_json, video_edl_bytes, audio_edl_bytes, render_props_bytes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (value.snapshot_id, value.snapshot_hash, value.project_id, value.executable_sequence_id,
                     self._encode(payload), value.video_edl_bytes, value.audio_edl_bytes,
                     value.render_props_bytes, value.created_at),
                )
                self.connection.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError("RENDER_INPUT_IMMUTABILITY") from exc

    def get_render_input(self, project_id: str, sequence_id: str) -> RenderInputSnapshotRecord | None:
        with self._lock:
            row = self.connection.execute(
                """SELECT payload_json, video_edl_bytes, audio_edl_bytes, render_props_bytes
                FROM studio_render_inputs WHERE project_id = ? AND sequence_id = ? ORDER BY created_at DESC LIMIT 1""",
                (project_id, sequence_id),
            ).fetchone()
        if row is None:
            return None
        return RenderInputSnapshotRecord(**(self._decode(row[0]) | {
            "video_edl_bytes": row[1], "audio_edl_bytes": row[2], "render_props_bytes": row[3],
        }))

    def create_preview_job(self, job: PreviewJobRecord) -> None:
        payload = {field: getattr(job, field) for field in job.__dataclass_fields__}
        with self._lock:
            try:
                self.connection.execute(
                    "INSERT INTO studio_preview_jobs(job_id, request_hash, attempt_ordinal, project_id, payload_json, active) VALUES (?, ?, ?, ?, ?, 1)",
                    (job.job_id, job.preview_request_hash, job.attempt_ordinal, job.project_id, self._encode(payload)),
                )
                self._append_preview_event(job, ordinal=1, state="requested", created_at=job.created_at, public_code=None)
                self.connection.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError("RENDER_REQUEST_CONFLICT") from exc

    def get_preview_job(self, job_id: str) -> PreviewJobRecord | None:
        with self._lock:
            row = self.connection.execute("SELECT payload_json FROM studio_preview_jobs WHERE job_id = ?", (job_id,)).fetchone()
        return None if row is None else PreviewJobRecord(**self._decode(row[0]))

    def get_active_preview_job(self, request_hash: str) -> PreviewJobRecord | None:
        with self._lock:
            row = self.connection.execute("SELECT payload_json FROM studio_preview_jobs WHERE request_hash = ? AND active = 1", (request_hash,)).fetchone()
        return None if row is None else PreviewJobRecord(**self._decode(row[0]))

    def next_preview_attempt(self, request_hash: str) -> int:
        with self._lock:
            row = self.connection.execute("SELECT COALESCE(MAX(attempt_ordinal), 0) FROM studio_preview_jobs WHERE request_hash = ?", (request_hash,)).fetchone()
        return int(row[0]) + 1

    def transition_preview_job(self, job_id: str, *, state: str, created_at: str, public_failure_code: str | None = None, receipt_hash: str | None = None, preview_manifest_hash: str | None = None, delivery_id: str | None = None) -> PreviewJobRecord:
        allowed = {"requested": {"admitted", "rejected_pre_admission"}, "admitted": {"running", "cancelled", "failed"}, "running": {"succeeded", "failed", "cancelled"}}
        with self._lock:
            current = self.get_preview_job(job_id)
            if current is None or state not in allowed.get(current.state, set()):
                raise ValueError("PREVIEW_JOB_TRANSITION_INVALID")
            if state == "succeeded" and (not receipt_hash or not preview_manifest_hash or not delivery_id):
                raise ValueError("PREVIEW_JOB_SUCCESS_INCOMPLETE")
            terminal = state in {"succeeded", "failed", "cancelled", "rejected_pre_admission"}
            value = PreviewJobRecord(**({field: getattr(current, field) for field in current.__dataclass_fields__} | {"state": state, "updated_at": created_at, "public_failure_code": public_failure_code, "receipt_hash": receipt_hash, "preview_manifest_hash": preview_manifest_hash, "delivery_id": delivery_id}))
            self.connection.execute("UPDATE studio_preview_jobs SET payload_json = ?, active = ? WHERE job_id = ?", (self._encode({field: getattr(value, field) for field in value.__dataclass_fields__}), 0 if terminal else 1, job_id))
            ordinal = self.connection.execute("SELECT COALESCE(MAX(ordinal), 0) + 1 FROM studio_preview_job_events WHERE job_id = ?", (job_id,)).fetchone()[0]
            self._append_preview_event(value, ordinal=int(ordinal), state=state, created_at=created_at, public_code=public_failure_code)
            self.connection.commit()
        return value

    def list_preview_events(self, job_id: str, *, after: int) -> tuple[PreviewJobEvent, ...]:
        with self._lock:
            rows = self.connection.execute("SELECT payload_json FROM studio_preview_job_events WHERE job_id = ? AND ordinal > ? ORDER BY ordinal ASC", (job_id, after)).fetchall()
        return tuple(PreviewJobEvent(**self._decode(row[0])) for row in rows)

    def _append_preview_event(self, job: PreviewJobRecord, *, ordinal: int, state: str, created_at: str, public_code: str | None) -> None:
        body = {"job_id": job.job_id, "ordinal": ordinal, "state": state, "created_at": created_at, "public_code": public_code}
        digest = "sha256:" + __import__("hashlib").sha256(self._encode(body)).hexdigest()
        value = PreviewJobEvent(event_id="pevt_" + digest[7:31], **body)
        self.connection.execute("INSERT INTO studio_preview_job_events(job_id, ordinal, payload_json) VALUES (?, ?, ?)", (job.job_id, ordinal, self._encode({field: getattr(value, field) for field in value.__dataclass_fields__})))

    def _task_view(self, row: tuple[bytes, str | None, str | None, bytes | None]) -> StudioTaskView:
        task = StudioTaskRecord(**self._decode(row[0]))
        status = row[1] or "waiting"
        issues = () if row[3] is None else tuple(self._decode(row[3]))
        return StudioTaskView(
            record=task,
            status=status,
            validation_issues=issues,
            response_hash=row[2],
        )
