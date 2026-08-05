"""Phase 9 immutable SQLite research records and deterministic importers."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from engine.acquisition.source_engine import (
    AccessStatus, ReplaySourcePackage, SourceAdapterRegistry, SourceCapturePlan,
    SourcePriorityPolicy, SourceType, rank_source_packages,
)
from engine.contracts._canonical_json import encode_canonical_json_bytes

from .gateway import (
    BackendMode, ClaimResearchPolicyV1, LLMTaskService, LLMTaskV1, PHASE9_RESPONSE_V1,
    ResearchError, TaskType, _bytes_hash, _canonical_json_load, _fail, _hash,
    _hash_ok, _id, _iso_date, _token, _tokens, TaskStatus, canonical_url, validate_task,
)


@dataclass(frozen=True)
class CandidateSourceV1:
    candidate_id: str
    candidate_hash: str
    canonical_url: str
    source_type: SourceType
    source_label: str
    publication_date: str
    authority_tokens: tuple[str, ...]
    rationale_tokens: tuple[str, ...]


@dataclass(frozen=True)
class SourceRecordV1:
    source_id: str; source_hash: str; project_id: str; policy_snapshot_id: str
    policy_snapshot_hash: str; candidate_id: str; source_capture_plan_id: str
    source_capture_plan_hash: str; source_package_hash: str; canonical_url: str
    source_type: SourceType; source_label: str; publication_date: str
    content_hash: str; captured_text: str


@dataclass(frozen=True)
class FactRecordV1:
    fact_id: str; fact_hash: str; project_id: str; policy_snapshot_id: str
    policy_snapshot_hash: str; source_id: str; source_hash: str; task_id: str
    task_hash: str; kind: str; text: str; span_start: int; span_end: int
    number_value: str | None; number_unit: str | None; speaker: str | None
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class ClaimRecordV1:
    claim_id: str; claim_hash: str; project_id: str; policy_snapshot_id: str
    policy_snapshot_hash: str; task_id: str; task_hash: str; canonical_text: str
    claim_type: str; status: str; confidence_millionths: int; fact_ids: tuple[str, ...]
    contradicting_fact_ids: tuple[str, ...]; time_start: str | None; time_end: str | None
    visual_potential_tokens: tuple[str, ...]; safe_wording_tokens: tuple[str, ...]


@dataclass(frozen=True)
class ClaimSourceEdgeV1:
    edge_id: str; edge_hash: str; project_id: str; policy_snapshot_id: str
    policy_snapshot_hash: str; claim_id: str; claim_hash: str; source_id: str
    source_hash: str; fact_id: str; fact_hash: str; relation: str


@dataclass(frozen=True)
class ContradictionRecordV1:
    contradiction_id: str; contradiction_hash: str; project_id: str
    policy_snapshot_id: str; policy_snapshot_hash: str; claim_id: str
    claim_hash: str; contradicting_claim_id: str; contradicting_claim_hash: str
    kind: str; visible_wording_tokens: tuple[str, ...]


@dataclass(frozen=True)
class ChronologyRecordV1:
    chronology_id: str; chronology_hash: str; project_id: str
    policy_snapshot_id: str; policy_snapshot_hash: str; claim_id: str
    claim_hash: str; date_value: str | None; date_precision: str | None
    ordinal: int; unknown_date: bool


def _candidate_projection(value: CandidateSourceV1) -> dict[str, object]:
    return {"canonical_url": value.canonical_url, "source_type": value.source_type.value,
            "source_label": value.source_label, "publication_date": value.publication_date,
            "authority_tokens": list(value.authority_tokens), "rationale_tokens": list(value.rationale_tokens)}


def _source_projection(value: SourceRecordV1) -> dict[str, object]:
    return {key: (getattr(value, key).value if key == "source_type" else getattr(value, key))
            for key in value.__dataclass_fields__ if key not in {"source_id", "source_hash"}}


def _fact_projection(value: FactRecordV1) -> dict[str, object]:
    return {key: (list(getattr(value, key)) if key == "tokens" else getattr(value, key))
            for key in value.__dataclass_fields__ if key not in {"fact_id", "fact_hash"}}


def _claim_projection(value: ClaimRecordV1) -> dict[str, object]:
    return {key: (list(getattr(value, key)) if key in {"fact_ids", "contradicting_fact_ids", "visual_potential_tokens", "safe_wording_tokens"} else getattr(value, key))
            for key in value.__dataclass_fields__ if key not in {"claim_id", "claim_hash"}}


def _edge_projection(value: ClaimSourceEdgeV1) -> dict[str, object]:
    return {key: getattr(value, key) for key in value.__dataclass_fields__ if key not in {"edge_id", "edge_hash"}}


def _contradiction_projection(value: ContradictionRecordV1) -> dict[str, object]:
    return {key: (list(value.visible_wording_tokens) if key == "visible_wording_tokens" else getattr(value, key))
            for key in value.__dataclass_fields__ if key not in {"contradiction_id", "contradiction_hash"}}


def _chronology_projection(value: ChronologyRecordV1) -> dict[str, object]:
    return {key: getattr(value, key) for key in value.__dataclass_fields__ if key not in {"chronology_id", "chronology_hash"}}


def _canonical_dataclass(value: object) -> bytes:
    if type(value) is CandidateSourceV1:
        data = {"candidate_id": value.candidate_id, "candidate_hash": value.candidate_hash, **_candidate_projection(value)}
    elif type(value) is SourceRecordV1:
        data = {"source_id": value.source_id, "source_hash": value.source_hash, **_source_projection(value)}
    elif type(value) is FactRecordV1:
        data = {"fact_id": value.fact_id, "fact_hash": value.fact_hash, **_fact_projection(value)}
    elif type(value) is ClaimRecordV1:
        data = {"claim_id": value.claim_id, "claim_hash": value.claim_hash, **_claim_projection(value)}
    elif type(value) is ClaimSourceEdgeV1:
        data = {"edge_id": value.edge_id, "edge_hash": value.edge_hash, **_edge_projection(value)}
    elif type(value) is ContradictionRecordV1:
        data = {"contradiction_id": value.contradiction_id, "contradiction_hash": value.contradiction_hash, **_contradiction_projection(value)}
    elif type(value) is ChronologyRecordV1:
        data = {"chronology_id": value.chronology_id, "chronology_hash": value.chronology_hash, **_chronology_projection(value)}
    else:
        _fail("RECORD_TYPE_INVALID")
    return encode_canonical_json_bytes(data)


def _candidate_from_raw(raw: object, policy: ClaimResearchPolicyV1) -> CandidateSourceV1:
    fields = {"candidate_id", "candidate_hash", "canonical_url", "source_type", "source_label", "publication_date", "authority_tokens", "rationale_tokens"}
    if type(raw) is not dict or set(raw) != fields:
        _fail("DISCOVERY_RESULT_INVALID")
    try:
        value = CandidateSourceV1(raw["candidate_id"], raw["candidate_hash"], canonical_url(raw["canonical_url"]), SourceType(raw["source_type"]), raw["source_label"], _iso_date(raw["publication_date"]), _tokens(raw["authority_tokens"]), _tokens(raw["rationale_tokens"]))
    except (KeyError, ValueError):
        _fail("DISCOVERY_RESULT_INVALID")
    if not _id(value.candidate_id, "cand_") or not _hash_ok(value.candidate_hash) or type(value.source_label) is not str or not value.source_label.strip() or not value.rationale_tokens or any(token not in policy.allowed_authority_tokens for token in value.authority_tokens):
        _fail("DISCOVERY_RESULT_INVALID")
    if value.candidate_hash != _hash(_candidate_projection(value)) or value.candidate_id != "cand_" + value.candidate_hash[7:27]:
        _fail("DISCOVERY_IDENTITY_INVALID")
    return value


class LLMResultValidator:
    def response(self, *, task: LLMTaskV1, payload: bytes) -> dict[str, object]:
        validate_task(task)
        raw = _canonical_json_load(payload)
        fields = {"schema_version", "task_id", "task_hash", "task_type", "policy_snapshot_id", "policy_snapshot_hash", "result"}
        if type(raw) is not dict or set(raw) != fields or raw["schema_version"] != PHASE9_RESPONSE_V1 or (raw["task_id"], raw["task_hash"], raw["task_type"], raw["policy_snapshot_id"], raw["policy_snapshot_hash"]) != (task.task_id, task.task_hash, task.task_type.value, task.input_manifest["policy_snapshot_id"], task.input_manifest["policy_snapshot_hash"]) or type(raw["result"]) is not dict:
            _fail("RESPONSE_BINDING_INVALID")
        return raw

    def discovery(self, *, task: LLMTaskV1, payload: bytes, policy: ClaimResearchPolicyV1) -> tuple[CandidateSourceV1, ...]:
        response = self.response(task=task, payload=payload)
        if task.task_type is not TaskType.SOURCE_DISCOVERY or set(response["result"]) != {"candidates"} or type(response["result"]["candidates"]) is not list:
            _fail("DISCOVERY_RESULT_INVALID")
        values = tuple(_candidate_from_raw(value, policy) for value in response["result"]["candidates"])
        if tuple(sorted(values, key=lambda item: (item.canonical_url, item.candidate_id))) != values or len({item.canonical_url for item in values}) != len(values):
            _fail("DISCOVERY_RESULT_INVALID")
        return values


class ClaimStore:
    """Small append-only SQLite store; JSON payload is canonical and immutable."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS phase9_records (
              record_kind TEXT NOT NULL, record_id TEXT NOT NULL, record_hash TEXT NOT NULL,
              project_id TEXT NOT NULL, payload BLOB NOT NULL,
              PRIMARY KEY (record_kind, record_id), UNIQUE (record_kind, record_hash)
            );
            CREATE TABLE IF NOT EXISTS phase9_responses (
              task_id TEXT NOT NULL, task_hash TEXT NOT NULL, response_hash TEXT NOT NULL,
              payload BLOB NOT NULL, accepted INTEGER NOT NULL, PRIMARY KEY(task_id, response_hash)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS phase9_one_accepted_response
              ON phase9_responses(task_id) WHERE accepted=1;
        """)

    def close(self) -> None:
        self.connection.close()

    def _put(self, *, kind: str, record_id: str, record_hash: str, project_id: str, payload: bytes) -> None:
        existing = self.connection.execute("SELECT payload, record_hash FROM phase9_records WHERE record_kind=? AND record_id=?", (kind, record_id)).fetchone()
        if existing is not None:
            if existing != (payload, record_hash):
                _fail("STORE_IMMUTABILITY_VIOLATION")
            return
        self.connection.execute("INSERT INTO phase9_records(record_kind,record_id,record_hash,project_id,payload) VALUES(?,?,?,?,?)", (kind, record_id, record_hash, project_id, payload))
        self.connection.commit()

    def put_task(self, task: LLMTaskV1) -> None:
        validate_task(task)
        if task.supersedes_task_id is not None:
            previous = self.task(task.supersedes_task_id)
            allowed = {
                TaskStatus.CREATED: {TaskStatus.PACKAGE_READY, TaskStatus.SUPERSEDED},
                TaskStatus.PACKAGE_READY: {TaskStatus.RESPONSE_SUBMITTED, TaskStatus.SUPERSEDED},
                TaskStatus.RESPONSE_SUBMITTED: {TaskStatus.ACCEPTED, TaskStatus.REJECTED, TaskStatus.SUPERSEDED},
                TaskStatus.REJECTED: {TaskStatus.PACKAGE_READY, TaskStatus.SUPERSEDED},
            }
            if (task.status not in allowed.get(previous.status, set())
                    or task.logical_task_id != previous.logical_task_id
                    or task.project_id != previous.project_id
                    or task.task_type is not previous.task_type
                    or task.input_manifest["policy_snapshot_id"] != previous.input_manifest["policy_snapshot_id"]
                    or task.input_manifest["policy_snapshot_hash"] != previous.input_manifest["policy_snapshot_hash"]
                    or task.input_manifest["prompt_hash"] != previous.input_manifest["prompt_hash"]):
                _fail("TASK_TRANSITION_INVALID")
        elif task.parent_task_id is not None:
            parent = self.task(task.parent_task_id)
            if (task.task_type is not TaskType.REPAIR or parent.status is not TaskStatus.REJECTED
                    or task.project_id != parent.project_id
                    or task.attempt != parent.attempt + 1
                    or task.input_manifest["policy_snapshot_id"] != parent.input_manifest["policy_snapshot_id"]
                    or task.input_manifest["policy_snapshot_hash"] != parent.input_manifest["policy_snapshot_hash"]):
                _fail("REPAIR_PARENT_INVALID")
        elif task.status is not TaskStatus.CREATED or task.attempt != 0:
            _fail("TASK_INITIAL_STATE_INVALID")
        payload = {"task_id": task.task_id, "task_hash": task.task_hash, "logical_task_id": task.logical_task_id, "supersedes_task_id": task.supersedes_task_id, "task_type": task.task_type.value, "project_id": task.project_id, "input_manifest": task.input_manifest, "prompt_template_ref": task.prompt_template_ref, "context_artifacts": list(task.context_artifacts), "expected_output_schema": task.expected_output_schema, "backend_mode": task.backend_mode.value, "status": task.status.value, "attempt": task.attempt, "parent_task_id": task.parent_task_id, "created_at": task.created_at, "completed_at": task.completed_at}
        self._put(kind="task", record_id=task.task_id, record_hash=task.task_hash, project_id=task.project_id, payload=encode_canonical_json_bytes(payload))

    def task(self, task_id: str) -> LLMTaskV1:
        row = self.connection.execute("SELECT payload FROM phase9_records WHERE record_kind='task' AND record_id=?", (task_id,)).fetchone()
        if row is None:
            _fail("TASK_UNKNOWN")
        raw = _canonical_json_load(row[0])
        try:
            task = LLMTaskV1(**{**raw, "task_type": TaskType(raw["task_type"]), "backend_mode": BackendMode(raw["backend_mode"]), "status": TaskStatus(raw["status"]), "context_artifacts": tuple(raw["context_artifacts"])})
        except (KeyError, TypeError, ValueError):
            _fail("TASK_RECORD_INVALID")
        return validate_task(task)

    def _stored_task(self, task: LLMTaskV1, policy: ClaimResearchPolicyV1) -> LLMTaskV1:
        stored = self.task(task.task_id)
        if (stored != task or stored.task_hash != task.task_hash
                or policy.policy_snapshot_id != task.input_manifest["policy_snapshot_id"]
                or policy.policy_snapshot_hash != task.input_manifest["policy_snapshot_hash"]
                or stored.status is not TaskStatus.RESPONSE_SUBMITTED):
            _fail("TASK_RESPONSE_BINDING_INVALID")
        return stored

    def put_candidates(self, *, task: LLMTaskV1, response: bytes, policy: ClaimResearchPolicyV1) -> tuple[CandidateSourceV1, ...]:
        self._stored_task(task, policy)
        candidates = LLMResultValidator().discovery(task=task, payload=response, policy=policy)
        self._put_response(task, response, True)
        for item in candidates:
            self._put(kind="candidate", record_id=item.candidate_id, record_hash=item.candidate_hash, project_id=task.project_id, payload=_canonical_dataclass(item))
        return candidates

    def _put_response(self, task: LLMTaskV1, payload: bytes, accepted: bool) -> None:
        if accepted:
            prior = self.connection.execute("SELECT response_hash FROM phase9_responses WHERE task_id=? AND accepted=1", (task.task_id,)).fetchone()
            if prior is not None and prior[0] != _bytes_hash(payload):
                _fail("RESPONSE_ALREADY_ACCEPTED")
        self.connection.execute("INSERT OR IGNORE INTO phase9_responses(task_id,task_hash,response_hash,payload,accepted) VALUES(?,?,?,?,?)", (task.task_id, task.task_hash, _bytes_hash(payload), payload, int(accepted)))
        self.connection.commit()
        terminal = LLMTaskService().transition(
            previous=task,
            status=TaskStatus.ACCEPTED if accepted else TaskStatus.REJECTED,
            completed_at=task.created_at,
        )
        self.put_task(terminal)

    def candidate(self, candidate_id: str, policy: ClaimResearchPolicyV1) -> CandidateSourceV1:
        row = self.connection.execute("SELECT payload FROM phase9_records WHERE record_kind='candidate' AND record_id=?", (candidate_id,)).fetchone()
        if row is None:
            _fail("CANDIDATE_UNKNOWN")
        raw = _canonical_json_load(row[0]); value = _candidate_from_raw(raw, policy)
        if value.candidate_id != candidate_id:
            _fail("CANDIDATE_RECORD_INVALID")
        return value

    def bind_capture(self, *, candidate: CandidateSourceV1, package: ReplaySourcePackage, adapters: SourceAdapterRegistry, project_id: str, policy: ClaimResearchPolicyV1) -> SourceRecordV1:
        stored_candidate = self.candidate(candidate.candidate_id, policy)
        candidate_project = self.connection.execute("SELECT project_id FROM phase9_records WHERE record_kind='candidate' AND record_id=?", (candidate.candidate_id,)).fetchone()
        if (stored_candidate != candidate or candidate.candidate_hash != stored_candidate.candidate_hash
                or candidate_project is None or candidate_project[0] != project_id
                or not _id(project_id, "prj_") or policy.policy_snapshot_id == ""
                or type(package) is not ReplaySourcePackage
                or candidate.canonical_url != canonical_url(package.url)
                or candidate.source_type is not package.source_type
                or candidate.source_label != package.source_label
                or candidate.publication_date != package.publication_date):
            _fail("SOURCE_CAPTURE_BINDING_INVALID")
        plan = adapters.acquire(package)
        if plan.access_status not in {AccessStatus.ACCESSIBLE, AccessStatus.TEXT_FOUND, AccessStatus.SNAPSHOT_AVAILABLE} or type(package.document_text) is not str or not package.document_text:
            _fail("SOURCE_CAPTURE_UNUSABLE")
        content_hash = _bytes_hash(package.document_text.encode("utf-8"))
        capture_payload = encode_canonical_json_bytes({"source_capture_plan_id": plan.source_capture_plan_id, "source_capture_plan_hash": plan.source_capture_plan_hash, "source_package_hash": plan.source_package_hash, "canonical_url": candidate.canonical_url, "source_type": package.source_type.value})
        self._put(kind="source_capture_plan", record_id=plan.source_capture_plan_id, record_hash=plan.source_capture_plan_hash, project_id=project_id, payload=capture_payload)
        projection = {"project_id": project_id, "policy_snapshot_id": policy.policy_snapshot_id, "policy_snapshot_hash": policy.policy_snapshot_hash, "candidate_id": candidate.candidate_id, "source_capture_plan_id": plan.source_capture_plan_id, "source_capture_plan_hash": plan.source_capture_plan_hash, "source_package_hash": plan.source_package_hash, "canonical_url": candidate.canonical_url, "source_type": package.source_type.value, "source_label": package.source_label, "publication_date": package.publication_date, "content_hash": content_hash, "captured_text": package.document_text}
        digest = _hash(projection)
        source = SourceRecordV1("src_" + digest[7:27], digest, **{**projection, "source_type": package.source_type})
        self._put(kind="source", record_id=source.source_id, record_hash=source.source_hash, project_id=project_id, payload=_canonical_dataclass(source))
        return source

    def source(self, source_id: str, *, project_id: str | None = None, policy: ClaimResearchPolicyV1 | None = None) -> SourceRecordV1:
        row = self.connection.execute("SELECT payload FROM phase9_records WHERE record_kind='source' AND record_id=?", (source_id,)).fetchone()
        if row is None:
            _fail("SOURCE_UNKNOWN")
        raw = _canonical_json_load(row[0])
        try:
            value = SourceRecordV1(**{**raw, "source_type": SourceType(raw["source_type"])})
        except (KeyError, TypeError, ValueError):
            _fail("SOURCE_RECORD_INVALID")
        if value.source_hash != _hash(_source_projection(value)) or value.source_id != "src_" + value.source_hash[7:27] or value.content_hash != _bytes_hash(value.captured_text.encode("utf-8")):
            _fail("SOURCE_RECORD_INVALID")
        capture = self.connection.execute("SELECT record_hash,payload FROM phase9_records WHERE record_kind='source_capture_plan' AND record_id=?", (value.source_capture_plan_id,)).fetchone()
        if capture is None or capture[0] != value.source_capture_plan_hash:
            _fail("SOURCE_CAPTURE_PLAN_UNKNOWN")
        capture_raw = _canonical_json_load(capture[1])
        if capture_raw.get("source_package_hash") != value.source_package_hash or capture_raw.get("canonical_url") != value.canonical_url or capture_raw.get("source_type") != value.source_type.value:
            _fail("SOURCE_CAPTURE_PLAN_INVALID")
        if ((project_id is not None and value.project_id != project_id)
                or (policy is not None and (value.policy_snapshot_id != policy.policy_snapshot_id or value.policy_snapshot_hash != policy.policy_snapshot_hash))):
            _fail("SOURCE_LINEAGE_INVALID")
        return value

    def fact(self, fact_id: str, *, project_id: str | None = None, policy: ClaimResearchPolicyV1 | None = None) -> FactRecordV1:
        row = self.connection.execute("SELECT payload FROM phase9_records WHERE record_kind='fact' AND record_id=?", (fact_id,)).fetchone()
        if row is None:
            _fail("FACT_UNKNOWN")
        raw = _canonical_json_load(row[0])
        try:
            value = FactRecordV1(**{**raw, "tokens": tuple(raw["tokens"])})
        except (KeyError, TypeError):
            _fail("FACT_RECORD_INVALID")
        if value.fact_hash != _hash(_fact_projection(value)) or value.fact_id != "fact_" + value.fact_hash[7:27]:
            _fail("FACT_RECORD_INVALID")
        source = self.source(value.source_id, project_id=project_id, policy=policy)
        if (source.source_hash != value.source_hash
                or (project_id is not None and value.project_id != project_id)
                or (policy is not None and (value.policy_snapshot_id != policy.policy_snapshot_id or value.policy_snapshot_hash != policy.policy_snapshot_hash))):
            _fail("FACT_RECORD_INVALID")
        return value

    def claim(self, claim_id: str, *, project_id: str | None = None, policy: ClaimResearchPolicyV1 | None = None) -> ClaimRecordV1:
        row = self.connection.execute("SELECT payload FROM phase9_records WHERE record_kind='claim' AND record_id=?", (claim_id,)).fetchone()
        if row is None:
            _fail("CLAIM_UNKNOWN")
        raw = _canonical_json_load(row[0])
        try:
            value = ClaimRecordV1(**{**raw, "fact_ids": tuple(raw["fact_ids"]), "contradicting_fact_ids": tuple(raw["contradicting_fact_ids"]), "visual_potential_tokens": tuple(raw["visual_potential_tokens"]), "safe_wording_tokens": tuple(raw["safe_wording_tokens"])})
        except (KeyError, TypeError):
            _fail("CLAIM_RECORD_INVALID")
        if value.claim_hash != _hash(_claim_projection(value)) or value.claim_id != "clm_" + value.claim_hash[7:27]:
            _fail("CLAIM_RECORD_INVALID")
        if ((project_id is not None and value.project_id != project_id)
                or (policy is not None and (value.policy_snapshot_id != policy.policy_snapshot_id or value.policy_snapshot_hash != policy.policy_snapshot_hash))):
            _fail("CLAIM_RECORD_INVALID")
        for fact_id in value.fact_ids + value.contradicting_fact_ids:
            self.fact(fact_id, project_id=value.project_id, policy=policy)
        return value

    def import_extraction(self, *, task: LLMTaskV1, payload: bytes, policy: ClaimResearchPolicyV1) -> tuple[FactRecordV1, ...]:
        self._stored_task(task, policy)
        response = LLMResultValidator().response(task=task, payload=payload)
        result = response["result"]
        groups = ("facts", "quotes", "numbers", "uncertainties")
        if task.task_type is not TaskType.SOURCE_EXTRACTION or set(result) != set(groups) or any(type(result[group]) is not list for group in groups):
            _fail("EXTRACTION_RESULT_INVALID")
        records: list[FactRecordV1] = []
        local_ids: set[str] = set()
        for group in groups:
            for raw in result[group]:
                required = {"local_id", "source_id", "source_content_hash", "source_span", "text", "kind", "tokens"}
                extra = {"value", "unit"} if group == "numbers" else ({"speaker"} if group == "quotes" else set())
                if type(raw) is not dict or set(raw) != required | extra or not _id(raw["local_id"], "loc_") or raw["local_id"] in local_ids or not _token(raw["kind"]) or type(raw["text"]) is not str or not raw["text"]:
                    _fail("EXTRACTION_RESULT_INVALID")
                local_ids.add(raw["local_id"])
                source = self.source(raw["source_id"], project_id=task.project_id, policy=policy)
                span = raw["source_span"]
                if type(span) is not dict or set(span) != {"start", "end"} or any(type(span[key]) is not int for key in span) or span["start"] < 0 or span["end"] <= span["start"] or span["end"] > len(source.captured_text) or raw["source_content_hash"] != source.content_hash or source.captured_text[span["start"]:span["end"]] != raw["text"]:
                    _fail("SOURCE_SPAN_INVALID")
                value = raw.get("value"); unit = raw.get("unit"); speaker = raw.get("speaker")
                if group == "numbers" and (type(value) is not str or not value or type(unit) is not str or not unit.strip()):
                    _fail("NUMBER_INVALID")
                if group == "quotes" and (type(speaker) is not str or not speaker.strip()):
                    _fail("QUOTE_INVALID")
                projection = {"project_id": task.project_id, "policy_snapshot_id": policy.policy_snapshot_id, "policy_snapshot_hash": policy.policy_snapshot_hash, "source_id": source.source_id, "source_hash": source.source_hash, "task_id": task.task_id, "task_hash": task.task_hash, "kind": raw["kind"], "text": raw["text"], "span_start": span["start"], "span_end": span["end"], "number_value": value, "number_unit": unit, "speaker": speaker, "tokens": list(_tokens(raw["tokens"]))}
                digest = _hash(projection)
                record = FactRecordV1("fact_" + digest[7:27], digest, **{**projection, "tokens": tuple(projection["tokens"])})
                self._put(kind="fact", record_id=record.fact_id, record_hash=record.fact_hash, project_id=task.project_id, payload=_canonical_dataclass(record))
                records.append(record)
        self._put_response(task, payload, True)
        return tuple(records)

    def import_claims(self, *, task: LLMTaskV1, payload: bytes, policy: ClaimResearchPolicyV1, facts_by_local_id: dict[str, FactRecordV1]) -> tuple[ClaimRecordV1, ...]:
        self._stored_task(task, policy)
        response = LLMResultValidator().response(task=task, payload=payload)
        result = response["result"]
        if task.task_type is not TaskType.CLAIM_NORMALIZATION or set(result) != {"claims"} or type(result["claims"]) is not list:
            _fail("CLAIM_RESULT_INVALID")
        values: list[ClaimRecordV1] = []
        for raw in result["claims"]:
            required = {"canonical_text", "claim_type", "status", "confidence_millionths", "fact_local_ids", "contradicting_fact_local_ids", "time_start", "time_end", "visual_potential_tokens", "safe_wording_tokens"}
            if type(raw) is not dict or set(raw) != required or type(raw["canonical_text"]) is not str or not raw["canonical_text"].strip() or raw["claim_type"] not in policy.allowed_claim_types or raw["status"] not in policy.allowed_claim_statuses or type(raw["confidence_millionths"]) is not int or not 0 <= raw["confidence_millionths"] <= 1_000_000:
                _fail("CLAIM_RESULT_INVALID")
            local_ids = _tokens(raw["fact_local_ids"]); contradictory = _tokens(raw["contradicting_fact_local_ids"])
            if not local_ids or set(local_ids).intersection(contradictory) or any(item not in facts_by_local_id for item in local_ids + contradictory):
                _fail("CLAIM_FACT_REFERENCE_INVALID")
            trusted_facts = {local_id: self.fact(facts_by_local_id[local_id].fact_id, project_id=task.project_id, policy=policy) for local_id in local_ids + contradictory}
            if any(trusted_facts[local_id] != facts_by_local_id[local_id] or trusted_facts[local_id].project_id != task.project_id or trusted_facts[local_id].policy_snapshot_id != policy.policy_snapshot_id or trusted_facts[local_id].policy_snapshot_hash != policy.policy_snapshot_hash for local_id in trusted_facts):
                _fail("CLAIM_FACT_REFERENCE_INVALID")
            start = raw["time_start"]; end = raw["time_end"]
            if start is not None: _iso_date(start)
            if end is not None: _iso_date(end)
            if start is not None and end is not None and start > end:
                _fail("CLAIM_TIME_INVALID")
            safe_wording = _tokens(raw["safe_wording_tokens"])
            if any(token not in policy.allowed_safe_wording_tokens for token in safe_wording):
                _fail("CLAIM_SAFETY_WORDING_INVALID")
            projection = {"project_id": task.project_id, "policy_snapshot_id": policy.policy_snapshot_id, "policy_snapshot_hash": policy.policy_snapshot_hash, "task_id": task.task_id, "task_hash": task.task_hash, "canonical_text": raw["canonical_text"], "claim_type": raw["claim_type"], "status": raw["status"], "confidence_millionths": raw["confidence_millionths"], "fact_ids": [trusted_facts[item].fact_id for item in local_ids], "contradicting_fact_ids": [trusted_facts[item].fact_id for item in contradictory], "time_start": start, "time_end": end, "visual_potential_tokens": list(_tokens(raw["visual_potential_tokens"])), "safe_wording_tokens": list(safe_wording)}
            digest = _hash(projection)
            record = ClaimRecordV1("clm_" + digest[7:27], digest, **{**projection, "fact_ids": tuple(projection["fact_ids"]), "contradicting_fact_ids": tuple(projection["contradicting_fact_ids"]), "visual_potential_tokens": tuple(projection["visual_potential_tokens"]), "safe_wording_tokens": tuple(projection["safe_wording_tokens"])})
            self._put(kind="claim", record_id=record.claim_id, record_hash=record.claim_hash, project_id=task.project_id, payload=_canonical_dataclass(record))
            for local_id in local_ids + contradictory:
                fact = trusted_facts[local_id]
                source = self.source(fact.source_id, project_id=task.project_id, policy=policy)
                relation = "supports" if local_id in local_ids else "contradicts"
                edge_projection = {
                    "project_id": task.project_id, "policy_snapshot_id": policy.policy_snapshot_id,
                    "policy_snapshot_hash": policy.policy_snapshot_hash,
                    "claim_id": record.claim_id, "claim_hash": record.claim_hash,
                    "source_id": source.source_id, "source_hash": source.source_hash,
                    "fact_id": fact.fact_id, "fact_hash": fact.fact_hash, "relation": relation,
                }
                edge_hash = _hash(edge_projection)
                edge = ClaimSourceEdgeV1("edge_" + edge_hash[7:27], edge_hash, **edge_projection)
                self._put(kind="claim_source_edge", record_id=edge.edge_id, record_hash=edge.edge_hash, project_id=task.project_id, payload=_canonical_dataclass(edge))
            values.append(record)
        self._put_response(task, payload, True)
        return tuple(values)

    def persist_contradictions(self, *, claims: Iterable[ClaimRecordV1], policy: ClaimResearchPolicyV1) -> tuple[ContradictionRecordV1, ...]:
        supplied = tuple(claims)
        ordered_supplied = tuple(sorted(supplied, key=lambda item: item.claim_id))
        values = tuple(self.claim(item.claim_id, project_id=item.project_id, policy=policy) for item in ordered_supplied)
        if any(stored != supplied_item or stored.policy_snapshot_id != policy.policy_snapshot_id or stored.policy_snapshot_hash != policy.policy_snapshot_hash for stored, supplied_item in zip(values, ordered_supplied)):
            _fail("CONTRADICTION_CLAIM_REFERENCE_INVALID")
        if len({item.project_id for item in values}) > 1:
            _fail("CONTRADICTION_PROJECT_MISMATCH")
        output: list[tuple[str, str, str]] = []
        for index, left in enumerate(values):
            for right in values[index + 1:]:
                if left.claim_type == right.claim_type and (left.status != right.status or set(left.fact_ids).intersection(right.contradicting_fact_ids) or set(right.fact_ids).intersection(left.contradicting_fact_ids)):
                    output.append((left.claim_id, right.claim_id, "status_conflict" if left.status != right.status else "value_conflict"))
        claims_by_id = {item.claim_id: item for item in values}
        records: list[ContradictionRecordV1] = []
        for left_id, right_id, kind in output:
            if kind not in policy.allowed_contradiction_kinds:
                _fail("CONTRADICTION_POLICY_INVALID")
            left, right = claims_by_id[left_id], claims_by_id[right_id]
            projection = {"project_id": left.project_id, "policy_snapshot_id": policy.policy_snapshot_id,
                          "policy_snapshot_hash": policy.policy_snapshot_hash, "claim_id": left.claim_id,
                          "claim_hash": left.claim_hash, "contradicting_claim_id": right.claim_id,
                          "contradicting_claim_hash": right.claim_hash, "kind": kind,
                          "visible_wording_tokens": list(policy.allowed_visible_contradiction_wording_tokens)}
            digest = _hash(projection)
            record = ContradictionRecordV1("ctr_" + digest[7:27], digest, **{**projection, "visible_wording_tokens": tuple(projection["visible_wording_tokens"])})
            self._put(kind="contradiction", record_id=record.contradiction_id, record_hash=record.contradiction_hash, project_id=left.project_id, payload=_canonical_dataclass(record))
            records.append(record)
        return tuple(records)

    @staticmethod
    def contradictions(claims: Iterable[ClaimRecordV1]) -> tuple[tuple[str, str, str], ...]:
        values = tuple(sorted(claims, key=lambda item: item.claim_id)); output: list[tuple[str, str, str]] = []
        for index, left in enumerate(values):
            for right in values[index + 1:]:
                if left.claim_type == right.claim_type and (left.status != right.status or set(left.fact_ids).intersection(right.contradicting_fact_ids) or set(right.fact_ids).intersection(left.contradicting_fact_ids)):
                    output.append((left.claim_id, right.claim_id, "status_conflict" if left.status != right.status else "value_conflict"))
        return tuple(output)

    @staticmethod
    def chronology(claims: Iterable[ClaimRecordV1]) -> tuple[ClaimRecordV1, ...]:
        values = tuple(claims)
        dated = sorted((item for item in values if item.time_start is not None), key=lambda item: (item.time_start or "", item.claim_id))
        unknown = sorted((item for item in values if item.time_start is None), key=lambda item: item.claim_id)
        return tuple(dated + unknown)

    def persist_chronology(self, *, claims: Iterable[ClaimRecordV1], policy: ClaimResearchPolicyV1) -> tuple[ChronologyRecordV1, ...]:
        supplied = tuple(claims)
        trusted = tuple(self.claim(item.claim_id, project_id=item.project_id, policy=policy) for item in supplied)
        if any(left != right or left.policy_snapshot_id != policy.policy_snapshot_id or left.policy_snapshot_hash != policy.policy_snapshot_hash for left, right in zip(trusted, supplied)):
            _fail("CHRONOLOGY_CLAIM_REFERENCE_INVALID")
        ordered = self.chronology(trusted)
        records: list[ChronologyRecordV1] = []
        for ordinal, claim in enumerate(ordered):
            unknown = claim.time_start is None
            precision = None if unknown else policy.allowed_date_precisions[0]
            if precision is not None and precision not in policy.allowed_date_precisions:
                _fail("CHRONOLOGY_POLICY_INVALID")
            projection = {"project_id": claim.project_id, "policy_snapshot_id": policy.policy_snapshot_id,
                          "policy_snapshot_hash": policy.policy_snapshot_hash, "claim_id": claim.claim_id,
                          "claim_hash": claim.claim_hash, "date_value": claim.time_start,
                          "date_precision": precision, "ordinal": ordinal, "unknown_date": unknown}
            digest = _hash(projection)
            record = ChronologyRecordV1("chr_" + digest[7:27], digest, **projection)
            self._put(kind="chronology", record_id=record.chronology_id, record_hash=record.chronology_hash, project_id=claim.project_id, payload=_canonical_dataclass(record))
            records.append(record)
        return tuple(records)

    def export_jsonl(self, destination: Path) -> Path:
        rows = self.connection.execute("SELECT record_kind,payload FROM phase9_records ORDER BY record_kind, record_id").fetchall()
        for kind, payload in rows:
            raw = _canonical_json_load(payload)
            if kind == "task": self.task(raw["task_id"])
            elif kind == "source": self.source(raw["source_id"])
            elif kind == "source_capture_plan":
                if (set(raw) != {"source_capture_plan_id", "source_capture_plan_hash", "source_package_hash", "canonical_url", "source_type"}
                        or raw["source_capture_plan_id"] != raw.get("source_capture_plan_id")
                        or not _hash_ok(raw["source_capture_plan_hash"]) or not _hash_ok(raw["source_package_hash"])):
                    _fail("EXPORT_LINEAGE_INVALID")
            elif kind == "fact": self.fact(raw["fact_id"])
            elif kind == "claim": self.claim(raw["claim_id"])
            elif kind == "claim_source_edge":
                claim, source, fact = self.claim(raw["claim_id"]), self.source(raw["source_id"]), self.fact(raw["fact_id"])
                if raw["claim_hash"] != claim.claim_hash or raw["source_hash"] != source.source_hash or raw["fact_hash"] != fact.fact_hash or raw["project_id"] != claim.project_id or raw["relation"] not in {"supports", "contradicts"}:
                    _fail("EXPORT_LINEAGE_INVALID")
            elif kind == "contradiction":
                left, right = self.claim(raw["claim_id"]), self.claim(raw["contradicting_claim_id"])
                if raw["claim_hash"] != left.claim_hash or raw["contradicting_claim_hash"] != right.claim_hash or raw["project_id"] != left.project_id or raw["project_id"] != right.project_id:
                    _fail("EXPORT_LINEAGE_INVALID")
            elif kind == "chronology":
                claim = self.claim(raw["claim_id"])
                if raw["claim_hash"] != claim.claim_hash or raw["project_id"] != claim.project_id:
                    _fail("EXPORT_LINEAGE_INVALID")
            elif kind == "candidate":
                if raw["candidate_hash"] != _hash({key: raw[key] for key in raw if key not in {"candidate_id", "candidate_hash"}}):
                    _fail("EXPORT_LINEAGE_INVALID")
            else:
                _fail("EXPORT_RECORD_KIND_INVALID")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"".join(payload + b"\n" for _, payload in rows))
        return destination


class SourceDiscoveryService:
    """Accept candidate proposals; it deliberately does no network discovery."""

    def import_result(self, *, store: ClaimStore, task: LLMTaskV1, payload: bytes,
                      policy: ClaimResearchPolicyV1) -> tuple[CandidateSourceV1, ...]:
        return store.put_candidates(task=task, response=payload, policy=policy)


class SourceRanker:
    """Policy-driven ranking delegated to the closed Phase 6 source contract."""

    def rank(self, *, policy: SourcePriorityPolicy,
             packages: Iterable[ReplaySourcePackage]) -> tuple[ReplaySourcePackage, ...]:
        return rank_source_packages(policy, packages)


class SourceCaptureIngress:
    """The only transition from an untrusted candidate to captured evidence."""

    def bind(self, *, store: ClaimStore, candidate: CandidateSourceV1,
             package: ReplaySourcePackage, adapters: SourceAdapterRegistry,
             project_id: str, policy: ClaimResearchPolicyV1) -> SourceRecordV1:
        return store.bind_capture(candidate=candidate, package=package, adapters=adapters,
                                  project_id=project_id, policy=policy)


class SourceExtractor:
    def import_result(self, *, store: ClaimStore, task: LLMTaskV1, payload: bytes,
                      policy: ClaimResearchPolicyV1) -> tuple[FactRecordV1, ...]:
        return store.import_extraction(task=task, payload=payload, policy=policy)


class DomainClaimTaxonomyValidator:
    def validate(self, *, claim_type: str, status: str,
                 policy: ClaimResearchPolicyV1) -> None:
        if claim_type not in policy.allowed_claim_types or status not in policy.allowed_claim_statuses:
            _fail("CLAIM_TAXONOMY_INVALID")


class ClaimNormalizer:
    def import_result(self, *, store: ClaimStore, task: LLMTaskV1, payload: bytes,
                      policy: ClaimResearchPolicyV1,
                      facts_by_local_id: dict[str, FactRecordV1]) -> tuple[ClaimRecordV1, ...]:
        return store.import_claims(task=task, payload=payload, policy=policy,
                                   facts_by_local_id=facts_by_local_id)


class ContradictionDetector:
    def detect(self, *, store: ClaimStore, claims: Iterable[ClaimRecordV1],
               policy: ClaimResearchPolicyV1) -> tuple[ContradictionRecordV1, ...]:
        return store.persist_contradictions(claims=claims, policy=policy)


class ChronologyBuilder:
    def build(self, *, store: ClaimStore, claims: Iterable[ClaimRecordV1],
              policy: ClaimResearchPolicyV1) -> tuple[ChronologyRecordV1, ...]:
        return store.persist_chronology(claims=claims, policy=policy)


class LLMResultImporter:
    """Single fail-closed import facade; invalid bytes are retained as rejected attempts."""

    def import_result(self, *, store: ClaimStore, task: LLMTaskV1, payload: bytes,
                      policy: ClaimResearchPolicyV1,
                      facts_by_local_id: dict[str, FactRecordV1] | None = None) -> object:
        try:
            if task.task_type is TaskType.SOURCE_DISCOVERY:
                return store.put_candidates(task=task, response=payload, policy=policy)
            if task.task_type is TaskType.SOURCE_EXTRACTION:
                return store.import_extraction(task=task, payload=payload, policy=policy)
            if task.task_type is TaskType.CLAIM_NORMALIZATION:
                return store.import_claims(task=task, payload=payload, policy=policy,
                                           facts_by_local_id=facts_by_local_id or {})
            _fail("RESULT_IMPORT_TASK_TYPE_INVALID")
        except ResearchError:
            store._put_response(task, payload, False)
            raise
