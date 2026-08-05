"""Phase 10 adapter over Phase 9 local task-package mechanics.

It deliberately imports the Phase 9 prompt resolver and backend enum instead
of introducing a provider/browser path.  Planner task types remain separate
because Phase 9's closed research enum must not be changed.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.research.gateway import BackendMode, DomainPromptResolver, ResearchError, _bytes_hash

from .policy import PlannerPolicyV1


PLANNER_TASK_V1 = "PHASE10-PLANNER-TASK-V1"
PLANNER_RESPONSE_V1 = "PHASE10-PLANNER-RESPONSE-V1"
TASK_TYPES = frozenset({"outline", "chapter_brief", "narrative_beats", "sequence_plan", "repair"})
STATUSES = frozenset({"created", "package_ready", "response_submitted", "accepted", "rejected", "superseded"})


def _hash(value: object) -> str:
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _fail(code: str) -> None:
    raise ResearchError(code)


def _snapshot_refs(value: tuple[str, ...]) -> tuple[str, ...]:
    allowed={"claim_evidence", "asset_catalog", "template_capability", "continuity"}
    if type(value) is not tuple: _fail("PLANNER_CONTEXT_INVALID")
    result=tuple(value)
    if any(type(item) is not str or len(item.split("|")) != 3 or item.split("|")[0] not in allowed or not item.split("|")[1].startswith("psnap_") or not item.split("|")[2].startswith("sha256:") for item in result) or len({item.split("|")[0] for item in result}) != len(result): _fail("PLANNER_CONTEXT_INVALID")
    return result


@dataclass(frozen=True)
class PlannerTaskV1:
    task_id: str; task_hash: str; logical_task_id: str; supersedes_task_id: str | None; task_type: str; project_id: str; policy_snapshot_id: str; policy_snapshot_hash: str; prompt_template_ref: str; prompt_hash: str; backend_mode: BackendMode; parent_id: str | None; parent_hash: str | None; context_snapshot_hashes: tuple[str,...]; expected_result_fields: tuple[str,...]; status: str; attempt: int; created_at: str; completed_at: str | None
    def data(self) -> dict[str, object]:
        body={"schema_version":PLANNER_TASK_V1,"logical_task_id":self.logical_task_id,"supersedes_task_id":self.supersedes_task_id,"task_type":self.task_type,"project_id":self.project_id,"policy_snapshot_id":self.policy_snapshot_id,"policy_snapshot_hash":self.policy_snapshot_hash,"prompt_template_ref":self.prompt_template_ref,"prompt_hash":self.prompt_hash,"backend_mode":self.backend_mode.value,"parent_id":self.parent_id,"parent_hash":self.parent_hash,"context_snapshot_hashes":list(self.context_snapshot_hashes),"expected_result_fields":list(self.expected_result_fields),"status":self.status,"attempt":self.attempt,"created_at":self.created_at,"completed_at":self.completed_at}
        digest=_hash(body)
        if self.task_type not in TASK_TYPES or self.status not in STATUSES or self.backend_mode not in {BackendMode.REPLAY,BackendMode.MANUAL_UI} or not self.task_id == "ptask_"+digest[7:27] or self.task_hash != digest: _fail("PLANNER_TASK_INVALID")
        return {"task_id":self.task_id,"task_hash":self.task_hash,**body}


class PlannerTaskService:
    def create(self, *, task_type: str, project_id: str, policy: PlannerPolicyV1, backend_mode: BackendMode, prompt_template_ref: str, domain_pack_root: Path, parent_id: str | None, parent_hash: str | None, context_snapshot_hashes: tuple[str,...], expected_result_fields: tuple[str,...], logical_task_id: str | None = None, supersedes_task_id: str | None = None, status: str = "created", attempt: int = 0, created_at: str = "2026-08-05T00:00:00Z", completed_at: str | None = None) -> PlannerTaskV1:
        context_snapshot_hashes=_snapshot_refs(context_snapshot_hashes)
        if task_type not in TASK_TYPES or not project_id.startswith("prj_") or backend_mode not in {BackendMode.REPLAY,BackendMode.MANUAL_UI} or (parent_id is None) != (parent_hash is None) or not expected_result_fields or status not in STATUSES or type(attempt) is not int or attempt < 0:
            _fail("PLANNER_TASK_CREATE_INVALID")
        try:
            manifest=json.loads((domain_pack_root/"manifest.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): _fail("PLANNER_DOMAIN_PACK_INVALID")
        prompt=DomainPromptResolver().resolve(pack_root=domain_pack_root, prompt_template_ref=prompt_template_ref)
        if _bytes_hash(encode_canonical_json_bytes(manifest)) != policy.manifest_hash or prompt_template_ref not in manifest.get("prompt_bundle_refs", []): _fail("PLANNER_DOMAIN_PACK_INVALID")
        logical=logical_task_id or "plog_"+_hash({"project_id":project_id,"task_type":task_type,"parent_id":parent_id,"context":list(context_snapshot_hashes)})[7:27]
        body={"schema_version":PLANNER_TASK_V1,"logical_task_id":logical,"supersedes_task_id":supersedes_task_id,"task_type":task_type,"project_id":project_id,"policy_snapshot_id":policy.policy_snapshot_id,"policy_snapshot_hash":policy.policy_snapshot_hash,"prompt_template_ref":prompt_template_ref,"prompt_hash":_bytes_hash(prompt.encode("utf-8")),"backend_mode":backend_mode.value,"parent_id":parent_id,"parent_hash":parent_hash,"context_snapshot_hashes":list(context_snapshot_hashes),"expected_result_fields":list(expected_result_fields),"status":status,"attempt":attempt,"created_at":created_at,"completed_at":completed_at}
        digest=_hash(body)
        return PlannerTaskV1("ptask_"+digest[7:27],digest,logical,supersedes_task_id,task_type,project_id,policy.policy_snapshot_id,policy.policy_snapshot_hash,prompt_template_ref,body["prompt_hash"],backend_mode,parent_id,parent_hash,context_snapshot_hashes,expected_result_fields,status,attempt,created_at,completed_at)

    def revise(self, *, previous: PlannerTaskV1, policy: PlannerPolicyV1, domain_pack_root: Path, status: str, created_at: str, completed_at: str | None = None) -> PlannerTaskV1:
        previous.data()
        if status not in {"package_ready", "response_submitted", "accepted", "rejected", "superseded"}: _fail("PLANNER_TASK_TRANSITION_INVALID")
        return self.create(task_type=previous.task_type, project_id=previous.project_id, policy=policy, backend_mode=previous.backend_mode, prompt_template_ref=previous.prompt_template_ref, domain_pack_root=domain_pack_root, parent_id=previous.parent_id, parent_hash=previous.parent_hash, context_snapshot_hashes=previous.context_snapshot_hashes, expected_result_fields=previous.expected_result_fields, logical_task_id=previous.logical_task_id, supersedes_task_id=previous.task_id, status=status, attempt=previous.attempt, created_at=created_at, completed_at=completed_at)


class PlannerTaskStore:
    """Phase 10's namespaced append-only task lifecycle, mirroring Phase 9."""

    def __init__(self, path: Path) -> None:
        self.connection = sqlite3.connect(path)
        self.connection.execute("CREATE TABLE IF NOT EXISTS phase10_tasks(task_id TEXT PRIMARY KEY, task_hash TEXT NOT NULL UNIQUE, project_id TEXT NOT NULL, payload BLOB NOT NULL)")
        self.connection.execute("CREATE TABLE IF NOT EXISTS phase10_task_responses(task_id TEXT NOT NULL, response_hash TEXT NOT NULL, payload BLOB NOT NULL, accepted INTEGER NOT NULL, PRIMARY KEY(task_id,response_hash))")

    def close(self) -> None:
        self.connection.close()

    def put(self, task: PlannerTaskV1) -> None:
        raw = task.data(); payload = encode_canonical_json_bytes(raw)
        if task.supersedes_task_id is None:
            if task.status != "created" or task.attempt != 0: _fail("PLANNER_TASK_INITIAL_INVALID")
        else:
            prior = self.get(task.supersedes_task_id)
            allowed = {"created": {"package_ready", "superseded"}, "package_ready": {"response_submitted", "superseded"}, "response_submitted": {"accepted", "rejected", "superseded"}, "rejected": {"created", "package_ready", "superseded"}}
            if task.status not in allowed.get(prior.status, set()) or task.logical_task_id != prior.logical_task_id or task.project_id != prior.project_id or (task.task_type != prior.task_type and not (prior.status == "rejected" and task.task_type == "repair" and task.attempt == prior.attempt + 1)) or task.policy_snapshot_hash != prior.policy_snapshot_hash:
                _fail("PLANNER_TASK_TRANSITION_INVALID")
        existing = self.connection.execute("SELECT payload FROM phase10_tasks WHERE task_id=?", (task.task_id,)).fetchone()
        if existing is not None:
            if existing[0] != payload: _fail("PLANNER_TASK_IMMUTABILITY")
            return
        self.connection.execute("INSERT INTO phase10_tasks(task_id,task_hash,project_id,payload) VALUES(?,?,?,?)", (task.task_id,task.task_hash,task.project_id,payload)); self.connection.commit()

    def get(self, task_id: str) -> PlannerTaskV1:
        row = self.connection.execute("SELECT payload FROM phase10_tasks WHERE task_id=?", (task_id,)).fetchone()
        if row is None: _fail("PLANNER_TASK_UNKNOWN")
        try:
            raw=json.loads(row[0].decode("utf-8"))
            if encode_canonical_json_bytes(raw) != row[0]: _fail("PLANNER_TASK_RECORD_INVALID")
            values={key: value for key, value in raw.items() if key != "schema_version"}
            task=PlannerTaskV1(**{**values,"backend_mode":BackendMode(values["backend_mode"]),"context_snapshot_hashes":tuple(values["context_snapshot_hashes"]),"expected_result_fields":tuple(values["expected_result_fields"])})
        except (UnicodeDecodeError,json.JSONDecodeError,KeyError,TypeError,ValueError): _fail("PLANNER_TASK_RECORD_INVALID")
        task.data(); return task

    def submit_response(self, *, task: PlannerTaskV1, payload: bytes, accepted: bool,
                        service: PlannerTaskService, policy: PlannerPolicyV1,
                        domain_pack_root: Path, created_at: str,
                        importer: Callable[[PlannerTaskV1, bytes], None] | None = None) -> PlannerTaskV1:
        stored = self.get(task.task_id)
        if stored != task or task.status != "response_submitted":
            _fail("PLANNER_RESPONSE_STATE_INVALID")
        if accepted:
            if importer is None: _fail("PLANNER_RESPONSE_IMPORTER_REQUIRED")
            importer(task, payload)
        response_hash = _bytes_hash(payload)
        prior = self.connection.execute("SELECT response_hash FROM phase10_task_responses WHERE task_id=? AND accepted=1", (task.task_id,)).fetchone()
        if accepted and prior is not None and prior[0] != response_hash:
            _fail("PLANNER_RESPONSE_ALREADY_ACCEPTED")
        self.connection.execute("INSERT OR IGNORE INTO phase10_task_responses(task_id,response_hash,payload,accepted) VALUES(?,?,?,?)", (task.task_id,response_hash,payload,int(accepted))); self.connection.commit()
        terminal = service.revise(previous=task, policy=policy, domain_pack_root=domain_pack_root, status="accepted" if accepted else "rejected", created_at=created_at, completed_at=created_at)
        self.put(terminal)
        return terminal


class PlannerTaskPackageBuilder:
    def build(self, *, task: PlannerTaskV1, workspace_root: Path, domain_pack_root: Path, store: object) -> Path:
        task_data=task.data()
        prompt=DomainPromptResolver().resolve(pack_root=domain_pack_root, prompt_template_ref=task.prompt_template_ref)
        if _bytes_hash(prompt.encode("utf-8")) != task.prompt_hash or not hasattr(store,"snapshot"): _fail("PLANNER_PACKAGE_INVALID")
        context={}
        for ref in task.context_snapshot_hashes:
            kind,snapshot_id,snapshot_hash=ref.split("|")
            context[kind]=store.snapshot(kind=kind,snapshot_id=snapshot_id,expected_hash=snapshot_hash,project_id=task.project_id)
        root=workspace_root.resolve(); target=(root/"llm_tasks"/task.task_id).resolve()
        if not target.is_relative_to(root): _fail("PLANNER_PACKAGE_PATH_INVALID")
        target.mkdir(parents=True,exist_ok=False); (target/"response").mkdir()
        files={"README.md":f"# {task.task_type}\n\nBackend: {task.backend_mode.value}\n".encode(),"prompt.md":prompt.encode(),"input_manifest.json":encode_canonical_json_bytes(task_data),"planner_context.json":encode_canonical_json_bytes(dict(context)),"expected_output.schema.json":encode_canonical_json_bytes({"schema_version":PLANNER_RESPONSE_V1,"task_type":task.task_type,"result_fields":list(task.expected_result_fields)})}
        for name,value in files.items(): (target/name).write_bytes(value)
        return target


class PlannerResultImporter:
    """Accept a response only after its proposed planner record enters the store."""

    _kinds = {"outline": ("outline", "outline"), "chapter_brief": ("chapter_brief", "chapter_brief"), "narrative_beats": ("narrative_beats", "narrative_beat"), "sequence_plan": ("sequence_plan", "sequence_plan")}

    def __init__(self, store: object, *, claim_evidence_pairs: tuple[tuple[str, str], ...] = (), capability_pairs: tuple[tuple[str, str], ...] = (), continuity_pairs: tuple[tuple[str, str], ...] = ()) -> None:
        self.store = store
        self.claim_evidence_pairs, self.capability_pairs, self.continuity_pairs = set(claim_evidence_pairs), set(capability_pairs), set(continuity_pairs)

    def __call__(self, task: PlannerTaskV1, payload: bytes) -> None:
        raw = validate_response(task=task, payload=payload)
        if task.task_type not in self._kinds: _fail("PLANNER_RESPONSE_IMPORT_INVALID")
        result_key, kind = self._kinds[task.task_type]
        value = raw["result"][result_key]
        values = value if task.task_type == "narrative_beats" else [value]
        if type(values) is not list or not values: _fail("PLANNER_RESPONSE_IMPORT_INVALID")
        for record in values:
            if type(record) is not dict or record.get("project_id") != task.project_id or record.get("policy_snapshot_id") != task.policy_snapshot_id or record.get("policy_snapshot_hash") != task.policy_snapshot_hash:
                _fail("PLANNER_RESPONSE_IMPORT_INVALID")
            if task.task_type == "outline":
                if record.get("parent_id") is not None or record.get("parent_hash") is not None: _fail("PLANNER_RESPONSE_PARENT_INVALID")
            elif record.get("parent_id") != task.parent_id or record.get("parent_hash") != task.parent_hash:
                _fail("PLANNER_RESPONSE_PARENT_INVALID")
            for key in ("claim_id_hash_pairs", "required_evidence_id_hash_pairs", "evidence_id_hash_pairs"):
                if key in record and not set(map(tuple, record[key])) <= self.claim_evidence_pairs: _fail("PLANNER_RESPONSE_CLOSURE_INVALID")
            if "template_capability_id_hash_pairs" in record and not set(map(tuple, record["template_capability_id_hash_pairs"])) <= self.capability_pairs: _fail("PLANNER_RESPONSE_CLOSURE_INVALID")
            for key in ("incoming_continuity_state_id_hash", "outgoing_continuity_state_id_hash"):
                if key in record and record[key] is not None and tuple(record[key]) not in self.continuity_pairs: _fail("PLANNER_RESPONSE_CLOSURE_INVALID")
            self.store.put(kind=kind, record=record)


class PlannerRepairBuilder:
    def build(self, *, failed_task: PlannerTaskV1, policy: PlannerPolicyV1, service: PlannerTaskService, workspace_root: Path, domain_pack_root: Path, store: object, original_response: bytes, validation_errors: tuple[str,...], created_at: str = "2026-08-05T00:00:00Z") -> tuple[PlannerTaskV1, Path]:
        if not validation_errors or failed_task.status != "rejected": _fail("PLANNER_REPAIR_INVALID")
        task=service.create(task_type="repair",project_id=failed_task.project_id,policy=policy,backend_mode=BackendMode.MANUAL_UI,prompt_template_ref=failed_task.prompt_template_ref,domain_pack_root=domain_pack_root,parent_id=failed_task.task_id,parent_hash=failed_task.task_hash,context_snapshot_hashes=failed_task.context_snapshot_hashes,expected_result_fields=("original_task_id","errors"),logical_task_id=failed_task.logical_task_id,supersedes_task_id=failed_task.task_id,attempt=failed_task.attempt+1,created_at=created_at)
        path=PlannerTaskPackageBuilder().build(task=task,workspace_root=workspace_root,domain_pack_root=domain_pack_root,store=store)
        (path/"response"/"original_response.json").write_bytes(original_response); (path/"response"/"validation_errors.json").write_bytes(encode_canonical_json_bytes({"errors":list(validation_errors)}))
        return task,path


def validate_response(*, task: PlannerTaskV1, payload: bytes) -> dict[str, object]:
    try: raw=json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError,json.JSONDecodeError): _fail("PLANNER_RESPONSE_INVALID")
    if encode_canonical_json_bytes(raw)!=payload or type(raw) is not dict or set(raw)!={"schema_version","task_id","task_hash","task_type","policy_snapshot_id","policy_snapshot_hash","result"} or (raw["schema_version"],raw["task_id"],raw["task_hash"],raw["task_type"],raw["policy_snapshot_id"],raw["policy_snapshot_hash"]) != (PLANNER_RESPONSE_V1,task.task_id,task.task_hash,task.task_type,task.policy_snapshot_id,task.policy_snapshot_hash) or type(raw["result"]) is not dict or set(raw["result"])!=set(task.expected_result_fields): _fail("PLANNER_RESPONSE_INVALID")
    return raw
