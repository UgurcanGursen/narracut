"""Canonical Phase 14 sequence dependency decisions; no renderer scheduling."""
from __future__ import annotations
import hashlib
from collections.abc import Callable
from typing import Mapping
from engine.contracts._canonical_json import encode_canonical_json_bytes


def sequence_dependency_snapshot(*, project_id: str, sequence_input_hashes: Mapping[str, str]) -> dict[str, object]:
    if not project_id or any(not isinstance(key, str) or not key or not isinstance(value, str) or not value.startswith("sha256:") for key, value in sequence_input_hashes.items()):
        raise ValueError("SEQUENCE_SNAPSHOT_INVALID")
    body = {"schema_version": "SEQUENCE-DEPENDENCY-SNAPSHOT-V1", "project_id": project_id,
            "sequences": [{"sequence_id": key, "input_hash": sequence_input_hashes[key]} for key in sorted(sequence_input_hashes)]}
    digest = "sha256:" + hashlib.sha256(encode_canonical_json_bytes(body)).hexdigest()
    return {"snapshot_id": "sds_" + digest[7:39], "snapshot_hash": digest, **body}


def plan_incremental_sequences(*, previous: Mapping[str, object] | None, current: Mapping[str, object]) -> tuple[dict[str, str], ...]:
    if current.get("schema_version") != "SEQUENCE-DEPENDENCY-SNAPSHOT-V1" or not isinstance(current.get("sequences"), list):
        raise ValueError("SEQUENCE_SNAPSHOT_INVALID")
    if previous is not None and previous.get("project_id") != current.get("project_id"):
        raise ValueError("SEQUENCE_SNAPSHOT_PROJECT_DRIFT")
    before = {item["sequence_id"]: item["input_hash"] for item in previous.get("sequences", [])} if previous else {}
    after = {item["sequence_id"]: item["input_hash"] for item in current["sequences"]}
    rows = [{"sequence_id": key, "action": "REUSE" if before.get(key) == value else "REBUILD"} for key, value in sorted(after.items())]
    rows.extend({"sequence_id": key, "action": "ORPHANED"} for key in sorted(set(before) - set(after)))
    return tuple(rows)


def run_incremental_sequences(*, previous: Mapping[str, object] | None,
                              current: Mapping[str, object],
                              rebuilders: Mapping[str, Callable[[], object]]) -> tuple[dict[str, object], ...]:
    """Invoke only changed sequence rebuilders; unchanged IDs are untouched."""
    results = []
    for decision in plan_incremental_sequences(previous=previous, current=current):
        if decision["action"] == "REBUILD":
            runner = rebuilders.get(decision["sequence_id"])
            if runner is None: raise ValueError("SEQUENCE_REBUILDER_MISSING")
            results.append({**decision, "result": runner()})
        else: results.append(dict(decision))
    return tuple(results)
