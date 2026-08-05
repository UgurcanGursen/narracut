"""Append-only local storage for canonical Phase 10 planner artifacts."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Mapping

from engine.contracts._canonical_json import encode_canonical_json_bytes

from .contracts import ChapterBriefV1, GlobalOutlineV1, NarrativeBeatV1, PlannerAssetBriefV1, PlannerContractError, SequencePlanV1, validate_record, validate_snapshot_record
from .policy import PlannerPolicyV1


class PlannerStore:
    """Immutable artifact store; only canonical bytes may cross this boundary."""

    def __init__(self, path: Path, *, policy: PlannerPolicyV1 | None = None) -> None:
        self.connection = sqlite3.connect(Path(path))
        self.policy = policy
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("CREATE TABLE IF NOT EXISTS phase10_records(kind TEXT NOT NULL, record_id TEXT NOT NULL, record_hash TEXT NOT NULL, project_id TEXT NOT NULL, payload BLOB NOT NULL, PRIMARY KEY(kind,record_id), UNIQUE(kind,record_hash))")
        self.connection.execute("CREATE TABLE IF NOT EXISTS phase10_snapshots(kind TEXT NOT NULL, snapshot_id TEXT NOT NULL, snapshot_hash TEXT NOT NULL, project_id TEXT NOT NULL, payload BLOB NOT NULL, PRIMARY KEY(kind,snapshot_id), UNIQUE(kind,snapshot_hash))")
        self.connection.execute("CREATE TABLE IF NOT EXISTS phase10_continuity(state_id TEXT PRIMARY KEY, state_hash TEXT NOT NULL UNIQUE, project_id TEXT NOT NULL, policy_snapshot_id TEXT NOT NULL, policy_snapshot_hash TEXT NOT NULL, payload BLOB NOT NULL)")

    def close(self) -> None:
        self.connection.close()

    def put(self, *, kind: str, record: Mapping[str, object]) -> None:
        record_id, record_hash, value = validate_record(kind, record)
        self._validate_policy(kind, value)
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

    def _validate_policy(self, kind: str, value: Mapping[str, object]) -> None:
        if self.policy is None: raise PlannerContractError("PLANNER_STORE_POLICY_REQUIRED")
        policy = self.policy
        if value["policy_snapshot_id"] != policy.policy_snapshot_id or value["policy_snapshot_hash"] != policy.policy_snapshot_hash:
            raise PlannerContractError("PLANNER_STORE_POLICY_INVALID")
        if kind == "chapter_brief" and any(token not in policy.allowed_visual_role_tokens for token in value["visual_opportunity_tokens"]):
            raise PlannerContractError("PLANNER_STORE_POLICY_INVALID")
        if kind == "narrative_beat" and (value["core_kind"] not in policy.allowed_core_beat_kinds or value["editorial_role"] not in policy.allowed_editorial_roles or (value["domain_subtype"] is not None and value["domain_subtype"] not in policy.allowed_domain_beat_subtypes) or any(token not in policy.allowed_safe_wording_tokens for token in value["safe_wording_tokens"])):
            raise PlannerContractError("PLANNER_STORE_POLICY_INVALID")
        if kind == "planner_asset_brief" and (value["visual_role"] not in policy.allowed_visual_role_tokens or any(token not in policy.allowed_visual_role_tokens for token in value["preferred_type_tokens"]) or (value["visual_role"] == "show_evidence" and not value["evidence_id_hash_pairs"]) or value["fallback_mode"] not in {"fail_closed", "require_review"}):
            raise PlannerContractError("PLANNER_STORE_POLICY_INVALID")
        if kind == "sequence_plan" and (type(value["duration_ms"]) is not int or not policy.min_sequence_duration_ms <= value["duration_ms"] <= policy.max_sequence_duration_ms or not value["claim_id_hash_pairs"] or len(value["claim_id_hash_pairs"]) > policy.max_claims_per_sequence or len(value["planner_asset_brief_id_hash_pairs"]) > policy.max_asset_briefs_per_sequence or not policy.min_edit_events_per_sequence <= len(value["edit_event_intents"]) <= policy.max_edit_events_per_sequence):
            raise PlannerContractError("PLANNER_STORE_POLICY_INVALID")
        self._semantic_record(kind, value)

    def _semantic_record(self, kind: str, value: Mapping[str, object]) -> None:
        p=self.policy; common=(value["status"],value["version"],value["created_at"],value["supersedes_id"],value["supersedes_hash"])
        try:
            if kind=="outline": rebuilt=GlobalOutlineV1(value["project_id"],value["policy_snapshot_id"],value["policy_snapshot_hash"],value["central_question"],value["hook"],tuple(value["chapter_order"]),tuple(value["major_reveals"]),tuple(value["counterarguments"]),value["payoff"],value["final_question"],*common).data()
            elif kind=="chapter_brief": rebuilt=ChapterBriefV1(value["project_id"],p,value["outline_id"],value["outline_hash"],value["order"],value["goal"],value["entry_state"],value["exit_state"],tuple(map(tuple,value["claim_id_hash_pairs"])),tuple(map(tuple,value["required_evidence_id_hash_pairs"])),value["main_reveal"],value["counterpoint"],tuple(value["visual_opportunity_tokens"]),value["continuity_handoff"],value["estimated_duration_ms"],*common).data()
            elif kind=="narrative_beat": rebuilt=NarrativeBeatV1(value["project_id"],p,value["chapter_brief_id"],value["chapter_brief_hash"],value["order"],value["core_kind"],value["domain_subtype"],value["editorial_role"],tuple(map(tuple,value["claim_id_hash_pairs"])),value["narration_intent"],tuple(value["safe_wording_tokens"]),value["estimated_duration_ms"],*common).data()
            elif kind=="planner_asset_brief": rebuilt=PlannerAssetBriefV1(value["project_id"],p,value["narrative_beat_id"],value["narrative_beat_hash"],value["order"],value["visual_role"],tuple(map(tuple,value["evidence_id_hash_pairs"])),value["purpose"],tuple(value["preferred_type_tokens"]),tuple(map(tuple,value["avoid_family_id_hash_pairs"])),value["fallback_mode"],*common).data()
            else: rebuilt=SequencePlanV1(value["project_id"],p,value["narrative_beat_id"],value["narrative_beat_hash"],value["order"],value["narration_intent"],value["duration_ms"],tuple(map(tuple,value["claim_id_hash_pairs"])),tuple(map(tuple,value["evidence_id_hash_pairs"])),tuple(map(tuple,value["template_capability_id_hash_pairs"])),tuple(map(tuple,value["planner_asset_brief_id_hash_pairs"])),tuple(value["edit_event_intents"]),tuple(value["text_emphasis_intents"]),tuple(value["audio_direction_tokens"]),None if value["incoming_continuity_state_id_hash"] is None else tuple(value["incoming_continuity_state_id_hash"]),None if value["outgoing_continuity_state_id_hash"] is None else tuple(value["outgoing_continuity_state_id_hash"]),*common).data()
        except (KeyError,TypeError,ValueError): raise PlannerContractError("PLANNER_STORE_SEMANTIC_INVALID")
        if rebuilt != value: raise PlannerContractError("PLANNER_STORE_SEMANTIC_INVALID")

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
        self._validate_policy(kind,value)
        if calculated_hash != row[0]:
            raise PlannerContractError("PLANNER_STORE_CANONICAL_INVALID")
        return value

    def _put_produced_snapshot(self, *, snapshot: object) -> tuple[str, str]:
        if type(snapshot).__module__ != "engine.planner.snapshots" or type(snapshot).__name__ != "ProducedPlannerSnapshot":
            raise PlannerContractError("PLANNER_SNAPSHOT_PRODUCER_REQUIRED")
        kind, snapshot = snapshot.kind, snapshot.payload
        snapshot_id, snapshot_hash, _ = validate_snapshot_record(kind, snapshot)
        if self.policy is None or snapshot["policy_snapshot_id"] != self.policy.policy_snapshot_id or snapshot["policy_snapshot_hash"] != self.policy.policy_snapshot_hash:
            raise PlannerContractError("PLANNER_SNAPSHOT_POLICY_INVALID")
        payload = encode_canonical_json_bytes(snapshot)
        old = self.connection.execute("SELECT payload,snapshot_hash FROM phase10_snapshots WHERE kind=? AND snapshot_id=?", (kind,snapshot_id)).fetchone()
        if old is not None:
            if old != (payload,snapshot_hash): raise PlannerContractError("PLANNER_SNAPSHOT_IMMUTABILITY")
            return snapshot_id,snapshot_hash
        self.connection.execute("INSERT INTO phase10_snapshots(kind,snapshot_id,snapshot_hash,project_id,payload) VALUES(?,?,?,?,?)", (kind,snapshot_id,snapshot_hash,snapshot["project_id"],payload)); self.connection.commit()
        return snapshot_id,snapshot_hash

    def snapshot(self, *, kind: str, snapshot_id: str, expected_hash: str, project_id: str) -> dict[str, object]:
        row=self.connection.execute("SELECT snapshot_hash,project_id,payload FROM phase10_snapshots WHERE kind=? AND snapshot_id=?",(kind,snapshot_id)).fetchone()
        if row is None or row[0] != expected_hash or row[1] != project_id: raise PlannerContractError("PLANNER_SNAPSHOT_REFERENCE_INVALID")
        raw=json.loads(row[2].decode("utf-8"))
        if encode_canonical_json_bytes(raw)!=row[2]: raise PlannerContractError("PLANNER_SNAPSHOT_CANONICAL_INVALID")
        validate_snapshot_record(kind,raw); return raw

    def put_continuity(self, *, state_id: str, state_hash: str, project_id: str, payload: Mapping[str, object]) -> None:
        if self.policy is None or not state_id.startswith("cont_") or not state_hash.startswith("sha256:") or payload.get("project_id") != project_id or payload.get("policy_snapshot_id") != self.policy.policy_snapshot_id or payload.get("policy_snapshot_hash") != self.policy.policy_snapshot_hash or payload.get("status") != "accepted" or encode_canonical_json_bytes(payload) != encode_canonical_json_bytes(dict(payload)):
            raise PlannerContractError("PLANNER_CONTINUITY_INVALID")
        raw=encode_canonical_json_bytes(dict(payload)); old=self.connection.execute("SELECT payload,state_hash FROM phase10_continuity WHERE state_id=?",(state_id,)).fetchone()
        if old is not None:
            if old != (raw,state_hash): raise PlannerContractError("PLANNER_CONTINUITY_IMMUTABILITY")
            return
        self.connection.execute("INSERT INTO phase10_continuity(state_id,state_hash,project_id,policy_snapshot_id,policy_snapshot_hash,payload) VALUES(?,?,?,?,?,?)",(state_id,state_hash,project_id,self.policy.policy_snapshot_id,self.policy.policy_snapshot_hash,raw)); self.connection.commit()

    def continuity_pairs(self, *, project_id: str) -> tuple[tuple[str,str], ...]:
        rows=self.connection.execute("SELECT state_id,state_hash FROM phase10_continuity WHERE project_id=? ORDER BY state_id DESC LIMIT 2",(project_id,)).fetchall()
        return tuple(rows)

    def accepted(self, *, kind: str, project_id: str) -> tuple[dict[str, object], ...]:
        rows = self.connection.execute("SELECT record_id,record_hash FROM phase10_records WHERE kind=? AND project_id=? ORDER BY record_id", (kind, project_id)).fetchall()
        return tuple(self.get(kind=kind, record_id=row[0], expected_hash=row[1], project_id=project_id) for row in rows)

    def export_jsonl(self, destination: Path) -> Path:
        rows = self.connection.execute("SELECT payload FROM phase10_records ORDER BY kind,record_id").fetchall()
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(b"".join(row[0]+b"\n" for row in rows))
        return destination
