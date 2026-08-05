"""Phase 10 adapter over Phase 9 local task-package mechanics.

It deliberately imports the Phase 9 prompt resolver and backend enum instead
of introducing a provider/browser path.  Planner task types remain separate
because Phase 9's closed research enum must not be changed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

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


class PlannerTaskPackageBuilder:
    def build(self, *, task: PlannerTaskV1, workspace_root: Path, domain_pack_root: Path, context: Mapping[str, object]) -> Path:
        task_data=task.data()
        prompt=DomainPromptResolver().resolve(pack_root=domain_pack_root, prompt_template_ref=task.prompt_template_ref)
        if _bytes_hash(prompt.encode("utf-8")) != task.prompt_hash or type(context) is not dict: _fail("PLANNER_PACKAGE_INVALID")
        root=workspace_root.resolve(); target=(root/"llm_tasks"/task.task_id).resolve()
        if not target.is_relative_to(root): _fail("PLANNER_PACKAGE_PATH_INVALID")
        target.mkdir(parents=True,exist_ok=False); (target/"response").mkdir()
        files={"README.md":f"# {task.task_type}\n\nBackend: {task.backend_mode.value}\n".encode(),"prompt.md":prompt.encode(),"input_manifest.json":encode_canonical_json_bytes(task_data),"planner_context.json":encode_canonical_json_bytes(dict(context)),"expected_output.schema.json":encode_canonical_json_bytes({"schema_version":PLANNER_RESPONSE_V1,"task_type":task.task_type,"result_fields":list(task.expected_result_fields)})}
        for name,value in files.items(): (target/name).write_bytes(value)
        return target


class PlannerRepairBuilder:
    def build(self, *, failed_task: PlannerTaskV1, policy: PlannerPolicyV1, service: PlannerTaskService, workspace_root: Path, domain_pack_root: Path, context: Mapping[str, object], original_response: bytes, validation_errors: tuple[str,...], created_at: str = "2026-08-05T00:00:00Z") -> tuple[PlannerTaskV1, Path]:
        if not validation_errors or failed_task.status != "rejected": _fail("PLANNER_REPAIR_INVALID")
        task=service.create(task_type="repair",project_id=failed_task.project_id,policy=policy,backend_mode=BackendMode.MANUAL_UI,prompt_template_ref=failed_task.prompt_template_ref,domain_pack_root=domain_pack_root,parent_id=failed_task.task_id,parent_hash=failed_task.task_hash,context_snapshot_hashes=failed_task.context_snapshot_hashes,expected_result_fields=("original_task_id","errors"),attempt=failed_task.attempt+1,created_at=created_at)
        path=PlannerTaskPackageBuilder().build(task=task,workspace_root=workspace_root,domain_pack_root=domain_pack_root,context=context)
        (path/"response"/"original_response.json").write_bytes(original_response); (path/"response"/"validation_errors.json").write_bytes(encode_canonical_json_bytes({"errors":list(validation_errors)}))
        return task,path


def validate_response(*, task: PlannerTaskV1, payload: bytes) -> dict[str, object]:
    try: raw=json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError,json.JSONDecodeError): _fail("PLANNER_RESPONSE_INVALID")
    if encode_canonical_json_bytes(raw)!=payload or type(raw) is not dict or set(raw)!={"schema_version","task_id","task_hash","task_type","policy_snapshot_id","policy_snapshot_hash","result"} or (raw["schema_version"],raw["task_id"],raw["task_hash"],raw["task_type"],raw["policy_snapshot_id"],raw["policy_snapshot_hash"]) != (PLANNER_RESPONSE_V1,task.task_id,task.task_hash,task.task_type,task.policy_snapshot_id,task.policy_snapshot_hash) or type(raw["result"]) is not dict or set(raw["result"])!=set(task.expected_result_fields): _fail("PLANNER_RESPONSE_INVALID")
    return raw
