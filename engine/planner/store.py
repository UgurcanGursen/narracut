"""Append-only local storage for canonical Phase 10 planner artifacts."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Mapping

from engine.contracts._canonical_json import encode_canonical_json_bytes

from .contracts import PlannerContractError, validate_record


class PlannerStore:
    """Immutable artifact store; only canonical bytes may cross this boundary."""

    def __init__(self, path: Path) -> None:
        self.connection = sqlite3.connect(Path(path))
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("CREATE TABLE IF NOT EXISTS phase10_records(kind TEXT NOT NULL, record_id TEXT NOT NULL, record_hash TEXT NOT NULL, project_id TEXT NOT NULL, payload BLOB NOT NULL, PRIMARY KEY(kind,record_id), UNIQUE(kind,record_hash))")

    def close(self) -> None:
        self.connection.close()

    def put(self, *, kind: str, record: Mapping[str, object]) -> None:
        record_id, record_hash, value = validate_record(kind, record)
        payload = encode_canonical_json_bytes(value)
        if value["status"] != "accepted":
            raise PlannerContractError("PLANNER_STORE_STATUS_INVALID")
        parent_id, parent_hash = value["parent_id"], value["parent_hash"]
        if parent_id is not None:
            parent = self.connection.execute("SELECT record_hash,project_id FROM phase10_records WHERE record_id=?", (parent_id,)).fetchone()
            if parent is None or parent[0] != parent_hash or parent[1] != value["project_id"]:
                raise PlannerContractError("PLANNER_STORE_PARENT_INVALID")
        supersedes_id, supersedes_hash = value["supersedes_id"], value["supersedes_hash"]
        if supersedes_id is not None:
            prior = self.connection.execute("SELECT record_hash,project_id,payload FROM phase10_records WHERE kind=? AND record_id=?", (kind, supersedes_id)).fetchone()
            if prior is None or prior[0] != supersedes_hash or prior[1] != value["project_id"]:
                raise PlannerContractError("PLANNER_STORE_SUCCESSOR_INVALID")
            prior_raw = json.loads(prior[2].decode("utf-8"))
            if value["version"] != prior_raw["version"] + 1:
                raise PlannerContractError("PLANNER_STORE_SUCCESSOR_INVALID")
        elif value["version"] != 1:
            raise PlannerContractError("PLANNER_STORE_INITIAL_VERSION_INVALID")
        old = self.connection.execute("SELECT payload,record_hash FROM phase10_records WHERE kind=? AND record_id=?", (kind, record_id)).fetchone()
        if old is not None:
            if old != (payload, record_hash):
                raise PlannerContractError("PLANNER_STORE_IMMUTABILITY")
            return
        self.connection.execute("INSERT INTO phase10_records(kind,record_id,record_hash,project_id,payload) VALUES(?,?,?,?,?)", (kind, record_id,record_hash,value["project_id"],payload))
        self.connection.commit()

    def get(self, *, kind: str, record_id: str, expected_hash: str, project_id: str) -> dict[str, object]:
        row = self.connection.execute("SELECT record_hash,project_id,payload FROM phase10_records WHERE kind=? AND record_id=?", (kind,record_id)).fetchone()
        if row is None or row[0] != expected_hash or row[1] != project_id:
            raise PlannerContractError("PLANNER_STORE_REFERENCE_INVALID")
        try:
            raw = json.loads(row[2].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise PlannerContractError("PLANNER_STORE_CANONICAL_INVALID")
        if encode_canonical_json_bytes(raw) != row[2]:
            raise PlannerContractError("PLANNER_STORE_CANONICAL_INVALID")
        _, calculated_hash, value = validate_record(kind, raw)
        if calculated_hash != row[0]:
            raise PlannerContractError("PLANNER_STORE_CANONICAL_INVALID")
        return value

    def accepted(self, *, kind: str, project_id: str) -> tuple[dict[str, object], ...]:
        rows = self.connection.execute("SELECT record_id,record_hash FROM phase10_records WHERE kind=? AND project_id=? ORDER BY record_id", (kind, project_id)).fetchall()
        return tuple(self.get(kind=kind, record_id=row[0], expected_hash=row[1], project_id=project_id) for row in rows)

    def export_jsonl(self, destination: Path) -> Path:
        rows = self.connection.execute("SELECT payload FROM phase10_records ORDER BY kind,record_id").fetchall()
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(b"".join(row[0]+b"\n" for row in rows))
        return destination
