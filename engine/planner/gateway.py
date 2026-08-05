"""Local-only Phase 10 planner task packages and canonical response binding."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.research.gateway import BackendMode, ResearchError

from .policy import PlannerPolicyV1


PLANNER_TASK_V1 = "PHASE10-PLANNER-TASK-V1"
PLANNER_RESPONSE_V1 = "PHASE10-PLANNER-RESPONSE-V1"
TASK_TYPES = frozenset({"outline", "chapter_brief", "narrative_beats", "sequence_plan", "repair"})


def _hash(value: object) -> str: return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()
def _fail(code: str) -> None: raise ResearchError(code)


@dataclass(frozen=True)
class PlannerTaskV1:
    task_id: str; task_hash: str; task_type: str; project_id: str; policy_snapshot_id: str; policy_snapshot_hash: str; backend_mode: BackendMode; parent_id: str | None; parent_hash: str | None; context_snapshot_hashes: tuple[str,...]; expected_result_fields: tuple[str,...]

    def data(self) -> dict[str, object]:
        body={"schema_version":PLANNER_TASK_V1,"task_type":self.task_type,"project_id":self.project_id,"policy_snapshot_id":self.policy_snapshot_id,"policy_snapshot_hash":self.policy_snapshot_hash,"backend_mode":self.backend_mode.value,"parent_id":self.parent_id,"parent_hash":self.parent_hash,"context_snapshot_hashes":list(self.context_snapshot_hashes),"expected_result_fields":list(self.expected_result_fields)}
        digest=_hash(body)
        if self.task_type not in TASK_TYPES or self.backend_mode not in {BackendMode.REPLAY,BackendMode.MANUAL_UI} or self.task_id!="ptask_"+digest[7:27] or self.task_hash!=digest: _fail("PLANNER_TASK_INVALID")
        return {"task_id":self.task_id,"task_hash":self.task_hash,**body}


class PlannerTaskService:
    def create(self, *, task_type: str, project_id: str, policy: PlannerPolicyV1, backend_mode: BackendMode, parent_id: str | None, parent_hash: str | None, context_snapshot_hashes: tuple[str,...], expected_result_fields: tuple[str,...]) -> PlannerTaskV1:
        if task_type not in TASK_TYPES or type(project_id) is not str or not project_id.startswith("prj_") or backend_mode not in {BackendMode.REPLAY,BackendMode.MANUAL_UI} or not expected_result_fields or (parent_id is None)!=(parent_hash is None) or any(type(value) is not str or not value.startswith("sha256:") for value in context_snapshot_hashes): _fail("PLANNER_TASK_CREATE_INVALID")
        body={"schema_version":PLANNER_TASK_V1,"task_type":task_type,"project_id":project_id,"policy_snapshot_id":policy.policy_snapshot_id,"policy_snapshot_hash":policy.policy_snapshot_hash,"backend_mode":backend_mode.value,"parent_id":parent_id,"parent_hash":parent_hash,"context_snapshot_hashes":list(context_snapshot_hashes),"expected_result_fields":list(expected_result_fields)}
        digest=_hash(body); return PlannerTaskV1("ptask_"+digest[7:27],digest,task_type,project_id,policy.policy_snapshot_id,policy.policy_snapshot_hash,backend_mode,parent_id,parent_hash,context_snapshot_hashes,expected_result_fields)


class PlannerTaskPackageBuilder:
    def build(self, *, task: PlannerTaskV1, workspace_root: Path, prompt_text: str, context: Mapping[str, object]) -> Path:
        data=task.data()
        if type(prompt_text) is not str or not prompt_text.strip() or type(context) is not dict: _fail("PLANNER_PACKAGE_INVALID")
        target=(workspace_root.resolve()/"llm_tasks"/task.task_id).resolve()
        if not target.is_relative_to(workspace_root.resolve()): _fail("PLANNER_PACKAGE_PATH_INVALID")
        target.mkdir(parents=True,exist_ok=False); (target/"response").mkdir()
        for name,value in {"README.md":f"# {task.task_type}\n\nBackend: {task.backend_mode.value}\n".encode(),"prompt.md":prompt_text.encode(),"input_manifest.json":encode_canonical_json_bytes(data),"context.json":encode_canonical_json_bytes(dict(context)),"expected_output.schema.json":encode_canonical_json_bytes({"schema_version":PLANNER_RESPONSE_V1,"task_type":task.task_type,"result_fields":list(task.expected_result_fields)})}.items(): (target/name).write_bytes(value)
        return target


class PlannerRepairBuilder:
    def build(self, *, failed_task: PlannerTaskV1, policy: PlannerPolicyV1,
              service: PlannerTaskService, workspace_root: Path,
              prompt_text: str, context: Mapping[str, object],
              original_response: bytes, validation_errors: tuple[str, ...]) -> tuple[PlannerTaskV1, Path]:
        if not validation_errors or any(type(item) is not str or not item for item in validation_errors): _fail("PLANNER_REPAIR_INVALID")
        task = service.create(task_type="repair", project_id=failed_task.project_id, policy=policy, backend_mode=BackendMode.MANUAL_UI, parent_id=failed_task.task_id, parent_hash=failed_task.task_hash, context_snapshot_hashes=failed_task.context_snapshot_hashes, expected_result_fields=("original_task_id","errors"))
        path = PlannerTaskPackageBuilder().build(task=task, workspace_root=workspace_root, prompt_text=prompt_text, context=context)
        (path/"response"/"original_response.json").write_bytes(original_response)
        (path/"response"/"validation_errors.json").write_bytes(encode_canonical_json_bytes({"errors":list(validation_errors)}))
        return task,path


def validate_response(*, task: PlannerTaskV1, payload: bytes) -> dict[str, object]:
    try: raw=json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError,json.JSONDecodeError): _fail("PLANNER_RESPONSE_INVALID")
    if encode_canonical_json_bytes(raw)!=payload or type(raw) is not dict or set(raw)!={"schema_version","task_id","task_hash","task_type","policy_snapshot_id","policy_snapshot_hash","result"} or (raw["schema_version"],raw["task_id"],raw["task_hash"],raw["task_type"],raw["policy_snapshot_id"],raw["policy_snapshot_hash"]) != (PLANNER_RESPONSE_V1,task.task_id,task.task_hash,task.task_type,task.policy_snapshot_id,task.policy_snapshot_hash) or type(raw["result"]) is not dict or set(raw["result"])!=set(task.expected_result_fields): _fail("PLANNER_RESPONSE_INVALID")
    return raw
