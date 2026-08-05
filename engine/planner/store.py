"""Append-only local storage for canonical Phase 10 planner artifacts."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Mapping

from engine.contracts._canonical_json import encode_canonical_json_bytes

from .contracts import PlannerContractError, _hash


class PlannerStore:
    def __init__(self, path: Path) -> None:
        self.connection = sqlite3.connect(Path(path))
        self.connection.execute("CREATE TABLE IF NOT EXISTS phase10_records(kind TEXT NOT NULL, record_id TEXT NOT NULL, record_hash TEXT NOT NULL, project_id TEXT NOT NULL, payload BLOB NOT NULL, PRIMARY KEY(kind,record_id), UNIQUE(kind,record_hash))")

    def close(self) -> None: self.connection.close()

    def put(self, *, kind: str, record: Mapping[str, object]) -> None:
        if type(kind) is not str or not kind or type(record) is not dict:
            raise PlannerContractError("PLANNER_STORE_INVALID")
        id_key, hash_key = {"outline": ("outline_id", "outline_hash"), "beat": ("narrative_beat_id", "narrative_beat_hash"), "sequence_plan": ("sequence_plan_id", "sequence_plan_hash")}.get(kind, (None, None))
        if id_key is None or id_key not in record or hash_key not in record or "project_id" not in record:
            raise PlannerContractError("PLANNER_STORE_INVALID")
        payload = encode_canonical_json_bytes(record)
        old = self.connection.execute("SELECT payload,record_hash FROM phase10_records WHERE kind=? AND record_id=?", (kind, record[id_key])).fetchone()
        if old is not None:
            if old != (payload, record[hash_key]): raise PlannerContractError("PLANNER_STORE_IMMUTABILITY")
            return
        self.connection.execute("INSERT INTO phase10_records(kind,record_id,record_hash,project_id,payload) VALUES(?,?,?,?,?)", (kind,record[id_key],record[hash_key],record["project_id"],payload)); self.connection.commit()

    def get(self, *, kind: str, record_id: str, expected_hash: str, project_id: str) -> dict[str, object]:
        row=self.connection.execute("SELECT record_hash,project_id,payload FROM phase10_records WHERE kind=? AND record_id=?",(kind,record_id)).fetchone()
        if row is None or row[0]!=expected_hash or row[1]!=project_id: raise PlannerContractError("PLANNER_STORE_REFERENCE_INVALID")
        raw=json.loads(row[2].decode("utf-8"))
        if encode_canonical_json_bytes(raw)!=row[2]: raise PlannerContractError("PLANNER_STORE_CANONICAL_INVALID")
        return raw

    def export_jsonl(self, destination: Path) -> Path:
        rows=self.connection.execute("SELECT payload FROM phase10_records ORDER BY kind,record_id").fetchall(); destination.parent.mkdir(parents=True,exist_ok=True); destination.write_bytes(b"".join(row[0]+b"\n" for row in rows)); return destination
