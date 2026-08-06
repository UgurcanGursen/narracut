"""Phase 17 local workspace revision persistence and crash recovery.

This store owns only a new managed root.  It never migrates the Studio SQLite
database or reaches into legacy ``assets``, ``cache`` or ``output`` paths.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.paths import resolve_relative

_PROJECT_ID = re.compile(r"^prj_[a-z0-9][a-z0-9_-]{2,63}$")
_MANIFEST = "P17-WORKSPACE-REVISION-V1"
_POINTER = "P17-WORKSPACE-ACTIVE-POINTER-V1"


def _sha(value: bytes | object) -> str:
    raw = value if type(value) is bytes else encode_canonical_json_bytes(value)
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _write_durable(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _load_json(path: Path, code: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(code) from exc
    if type(value) is not dict:
        raise ValueError(code)
    return value


@dataclass(frozen=True)
class WorkspaceRevision:
    project_id: str
    revision_id: str
    revision_hash: str
    created_at: str
    files: tuple[dict[str, object], ...]


class WorkspaceRevisionStore:
    """Atomic revision directory publication with last-known-good recovery."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        if not self.root.is_dir():
            raise ValueError("WORKSPACE_STORE_ROOT_INVALID")

    def publish(self, *, project_id: str, files: Mapping[str, bytes], created_at: str) -> WorkspaceRevision:
        if _PROJECT_ID.fullmatch(project_id) is None or type(created_at) is not str or not created_at:
            raise ValueError("WORKSPACE_REVISION_INPUT_INVALID")
        if type(files) is not dict or not files or "workspace.json" not in files:
            raise ValueError("WORKSPACE_REVISION_INPUT_INVALID")
        normalized = self._validate_files(files)
        file_rows = tuple({"path": name, "content_hash": _sha(content), "size_bytes": len(content)} for name, content in normalized)
        body = {"schema_version": _MANIFEST, "project_id": project_id, "created_at": created_at, "files": list(file_rows)}
        revision_hash = _sha(body)
        revision = WorkspaceRevision(project_id, "wrev_" + revision_hash[7:31], revision_hash, created_at, file_rows)
        project = self._project_root(project_id)
        revisions = project / "revisions"
        target = revisions / revision.revision_id
        if target.exists():
            existing = self._load_revision(target, project_id)
            if existing != revision:
                raise ValueError("WORKSPACE_REVISION_IDENTITY_CONFLICT")
            self._publish_pointer(project, existing)
            return existing
        staging_parent = project / ".staging"
        staging_parent.mkdir(parents=True, exist_ok=True)
        stage = staging_parent / ("stage_" + uuid.uuid4().hex)
        stage.mkdir()
        try:
            for name, content in normalized:
                _write_durable(resolve_relative(stage, name), content)
            manifest = {"revision_id": revision.revision_id, "revision_hash": revision.revision_hash, **body}
            _write_durable(stage / "revision.json", encode_canonical_json_bytes(manifest))
            revisions.mkdir(parents=True, exist_ok=True)
            os.replace(stage, target)
            self._publish_pointer(project, revision)
            return revision
        except BaseException:
            # A staging directory is intentionally retained for recovery audit;
            # the active pointer still names the prior known-good revision.
            raise

    def load_active(self, *, project_id: str) -> WorkspaceRevision:
        project = self._project_root(project_id)
        pointer = _load_json(project / "active.json", "WORKSPACE_ACTIVE_POINTER_INVALID")
        if set(pointer) != {"schema_version", "project_id", "revision_id", "revision_hash", "pointer_hash"} or pointer["schema_version"] != _POINTER or pointer["project_id"] != project_id:
            raise ValueError("WORKSPACE_ACTIVE_POINTER_INVALID")
        identity = {key: pointer[key] for key in ("schema_version", "project_id", "revision_id", "revision_hash")}
        if pointer["pointer_hash"] != _sha(identity) or type(pointer["revision_id"]) is not str:
            raise ValueError("WORKSPACE_ACTIVE_POINTER_INVALID")
        revision = self._load_revision(project / "revisions" / pointer["revision_id"], project_id)
        if revision.revision_hash != pointer["revision_hash"]:
            raise ValueError("WORKSPACE_ACTIVE_POINTER_INVALID")
        return revision

    def recover(self, *, project_id: str) -> WorkspaceRevision:
        """Quarantine incomplete staging and repoint only to a verified revision."""
        project = self._project_root(project_id)
        staging = project / ".staging"
        if staging.exists():
            quarantine = project / ".recovery" / "staging"
            quarantine.mkdir(parents=True, exist_ok=True)
            for entry in sorted(staging.iterdir(), key=lambda item: item.name):
                target = quarantine / entry.name
                if target.exists():
                    raise ValueError("WORKSPACE_RECOVERY_COLLISION")
                os.replace(entry, target)
        try:
            return self.load_active(project_id=project_id)
        except ValueError:
            revisions = project / "revisions"
            valid: list[WorkspaceRevision] = []
            if revisions.exists():
                for entry in revisions.iterdir():
                    if entry.is_dir():
                        try:
                            valid.append(self._load_revision(entry, project_id))
                        except ValueError:
                            continue
            if not valid:
                raise ValueError("WORKSPACE_RECOVERY_NO_VALID_REVISION")
            recovered = max(valid, key=lambda item: (item.created_at, item.revision_id))
            self._publish_pointer(project, recovered)
            return recovered

    def _project_root(self, project_id: str) -> Path:
        if _PROJECT_ID.fullmatch(project_id) is None:
            raise ValueError("WORKSPACE_REVISION_INPUT_INVALID")
        path = self.root / "projects" / project_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _validate_files(files: Mapping[str, bytes]) -> tuple[tuple[str, bytes], ...]:
        rows: list[tuple[str, bytes]] = []
        for name, content in files.items():
            if type(name) is not str or type(content) is not bytes or not content:
                raise ValueError("WORKSPACE_REVISION_INPUT_INVALID")
            candidate = Path(name)
            if candidate.is_absolute() or candidate.drive or ".." in candidate.parts or name.replace("\\", "/").startswith("/"):
                raise ValueError("WORKSPACE_REVISION_PATH_INVALID")
            rows.append((name.replace("\\", "/"), content))
        if len({name for name, _ in rows}) != len(rows):
            raise ValueError("WORKSPACE_REVISION_PATH_INVALID")
        return tuple(sorted(rows))

    def _load_revision(self, directory: Path, project_id: str) -> WorkspaceRevision:
        manifest = _load_json(directory / "revision.json", "WORKSPACE_REVISION_INVALID")
        required = {"revision_id", "revision_hash", "schema_version", "project_id", "created_at", "files"}
        if set(manifest) != required or manifest.get("schema_version") != _MANIFEST or manifest.get("project_id") != project_id or type(manifest.get("files")) is not list:
            raise ValueError("WORKSPACE_REVISION_INVALID")
        body = {key: manifest[key] for key in ("schema_version", "project_id", "created_at", "files")}
        expected = _sha(body)
        if manifest.get("revision_hash") != expected or manifest.get("revision_id") != "wrev_" + expected[7:31]:
            raise ValueError("WORKSPACE_REVISION_INVALID")
        rows = tuple(manifest["files"])
        if not rows or any(type(row) is not dict or set(row) != {"path", "content_hash", "size_bytes"} for row in rows):
            raise ValueError("WORKSPACE_REVISION_INVALID")
        for row in rows:
            path = resolve_relative(directory, str(row["path"]))
            if not path.is_file() or type(row["size_bytes"]) is not int or path.stat().st_size != row["size_bytes"] or _sha(path.read_bytes()) != row["content_hash"]:
                raise ValueError("WORKSPACE_REVISION_INVALID")
        return WorkspaceRevision(project_id, manifest["revision_id"], expected, manifest["created_at"], rows)

    def _publish_pointer(self, project: Path, revision: WorkspaceRevision) -> None:
        body = {"schema_version": _POINTER, "project_id": revision.project_id, "revision_id": revision.revision_id, "revision_hash": revision.revision_hash}
        pointer = {**body, "pointer_hash": _sha(body)}
        temporary = project / (".active_" + uuid.uuid4().hex)
        _write_durable(temporary, encode_canonical_json_bytes(pointer))
        os.replace(temporary, project / "active.json")


class WorkspaceJobJournal:
    """Append-only local journal; no worker/provider execution is implied."""

    _terminal = frozenset({"succeeded", "failed", "cancelled", "recovery_required"})
    _states = frozenset({"queued", "running", * _terminal})

    def __init__(self, root: Path) -> None:
        self.store = WorkspaceRevisionStore(root)

    def append(self, *, project_id: str, job_id: str, state: str, created_at: str, attempt: int) -> dict[str, object]:
        if _PROJECT_ID.fullmatch(project_id) is None or not re.fullmatch(r"job_[a-z0-9][a-z0-9_-]{2,63}", job_id) or state not in self._states or type(created_at) is not str or not created_at or type(attempt) is not int or attempt < 1:
            raise ValueError("WORKSPACE_JOB_EVENT_INVALID")
        events = self.events(project_id=project_id)
        prior = [event for event in events if event["job_id"] == job_id]
        if prior and (prior[-1]["state"] in self._terminal or attempt < prior[-1]["attempt"]):
            raise ValueError("WORKSPACE_JOB_TRANSITION_INVALID")
        body = {"schema_version": "P17-WORKSPACE-JOB-EVENT-V1", "project_id": project_id, "job_id": job_id, "state": state, "created_at": created_at, "attempt": attempt}
        event = {"event_hash": _sha(body), **body}
        path = self.store._project_root(project_id) / "jobs.jsonl"
        with path.open("ab") as stream:
            stream.write(encode_canonical_json_bytes(event) + b"\n")
            stream.flush(); os.fsync(stream.fileno())
        return event

    def events(self, *, project_id: str) -> tuple[dict[str, object], ...]:
        path = self.store._project_root(project_id) / "jobs.jsonl"
        if not path.exists():
            return ()
        values: list[dict[str, object]] = []
        try:
            for line in path.read_bytes().splitlines():
                value = json.loads(line.decode("utf-8"))
                body = {key: value[key] for key in ("schema_version", "project_id", "job_id", "state", "created_at", "attempt")}
                if set(value) != {*body, "event_hash"} or value["event_hash"] != _sha(body) or body["project_id"] != project_id or body["state"] not in self._states:
                    raise ValueError
                values.append(value)
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError("WORKSPACE_JOB_JOURNAL_INVALID") from exc
        return tuple(values)

    def recover_interrupted(self, *, project_id: str, created_at: str) -> tuple[dict[str, object], ...]:
        latest: dict[str, dict[str, object]] = {}
        for event in self.events(project_id=project_id):
            latest[event["job_id"]] = event
        return tuple(
            self.append(project_id=project_id, job_id=event["job_id"], state="recovery_required", created_at=created_at, attempt=event["attempt"])
            for event in sorted(latest.values(), key=lambda value: str(value["job_id"]))
            if event["state"] == "running"
        )
