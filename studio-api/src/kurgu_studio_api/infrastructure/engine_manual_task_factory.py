"""Infrastructure adapter that exposes Phase 9/10 MANUAL_UI packages safely."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.models import DomainPolicySnapshot
from engine.planner import PlannerTaskService, planner_policy_from_snapshot
from engine.planner.gateway import PlannerTaskV1, validate_response as validate_planner_response
from engine.research import (
    BackendMode,
    DomainPromptResolver,
    LLMResultValidator,
    LLMTaskService,
    LLMTaskV1,
    TaskStatus,
    TaskType,
    claim_research_policy_from_snapshot,
)

from ..application.models import ProjectAggregate, StudioTaskRecord


def _bytes_hash(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


class EngineManualTaskFactory:
    def __init__(self, *, domain_packs_root: Path) -> None:
        self.domain_packs_root = Path(domain_packs_root)

    def create(
        self,
        *,
        project: ProjectAggregate,
        family: str,
        task_type: str,
        backend_mode: str,
        topic: str,
        created_at: str,
        parent: StudioTaskRecord | None = None,
    ) -> StudioTaskRecord:
        if project.domain.domain_id != "business-tech":
            raise ValueError("TASK_DOMAIN_UNAVAILABLE")
        if family not in {"research", "planner"} or backend_mode not in {"replay", "manual_ui"}:
            raise ValueError("TASK_REQUEST_INVALID")
        snapshot = DomainPolicySnapshot(**project.domain.policy_snapshot)
        pack_root = self.domain_packs_root / project.domain.domain_id
        mode = BackendMode(backend_mode)
        if family == "research":
            return self._research_task(
                project=project, snapshot=snapshot, pack_root=pack_root, task_type=task_type,
                backend_mode=mode, topic=topic, created_at=created_at, parent=parent,
            )
        return self._planner_task(
            project=project, snapshot=snapshot, pack_root=pack_root, task_type=task_type,
            backend_mode=mode, topic=topic, created_at=created_at, parent=parent,
        )

    def validate_response(
        self,
        *,
        task: StudioTaskRecord,
        payload: Mapping[str, Any],
    ) -> tuple[bool, tuple[str, ...], str]:
        raw = encode_canonical_json_bytes(dict(payload))
        response_hash = _bytes_hash(raw)
        try:
            if task.family == "research":
                engine_task = self._research_from_payload(task.payload)
                LLMResultValidator().response(task=engine_task, payload=raw)
            else:
                engine_task = self._planner_from_payload(task.payload)
                validate_planner_response(task=engine_task, payload=raw)
        except Exception:
            return False, ("RESPONSE_INVALID",), response_hash
        return True, (), response_hash

    def _research_task(self, *, project: ProjectAggregate, snapshot: DomainPolicySnapshot, pack_root: Path, task_type: str, backend_mode: BackendMode, topic: str, created_at: str, parent: StudioTaskRecord | None) -> StudioTaskRecord:
        policy = claim_research_policy_from_snapshot(snapshot)
        if parent is None:
            if task_type != "source_discovery":
                raise ValueError("TASK_TYPE_UNAVAILABLE")
            task = LLMTaskService().create_task(
                task_type=TaskType.SOURCE_DISCOVERY, project_id=project.project["project_id"],
                policy=policy, backend_mode=backend_mode, prompt_template_ref="prompts/research_discovery.md",
                domain_pack_root=pack_root, topic=topic, status=TaskStatus.CREATED,
                created_at=created_at,
            )
        else:
            original = self._research_from_payload(parent.payload)
            task = LLMTaskService().create_task(
                task_type=TaskType.REPAIR, project_id=project.project["project_id"], policy=policy,
                backend_mode=BackendMode.MANUAL_UI, prompt_template_ref=original.prompt_template_ref,
                domain_pack_root=pack_root, topic=topic, parent_task_id=original.task_id,
                attempt=original.attempt + 1, created_at=created_at,
                repair_prompt_text="Repair only the validation errors reported by Studio.",
            )
        payload = self._research_payload(task)
        prompt = DomainPromptResolver().resolve(pack_root=pack_root, prompt_template_ref=task.prompt_template_ref) if task.task_type is not TaskType.REPAIR else "Repair only the validation errors reported by Studio."
        return StudioTaskRecord(task.task_id, task.task_hash, task.project_id, str(task.input_manifest["policy_snapshot_id"]), str(task.input_manifest["policy_snapshot_hash"]), "research", task.task_type.value, task.backend_mode.value, prompt, {"topic": topic, "expected_output_schema": task.expected_output_schema}, payload, parent.task_id if parent else None, task.attempt, created_at)

    def _planner_task(self, *, project: ProjectAggregate, snapshot: DomainPolicySnapshot, pack_root: Path, task_type: str, backend_mode: BackendMode, topic: str, created_at: str, parent: StudioTaskRecord | None) -> StudioTaskRecord:
        policy = planner_policy_from_snapshot(snapshot)
        service = PlannerTaskService()
        if parent is None:
            if task_type != "outline":
                raise ValueError("TASK_TYPE_UNAVAILABLE")
            task = service.create(task_type="outline", project_id=project.project["project_id"], policy=policy, backend_mode=backend_mode, prompt_template_ref="prompts/planner_outline.md", domain_pack_root=pack_root, parent_id=None, parent_hash=None, context_snapshot_hashes=(), expected_result_fields=("outline",), created_at=created_at)
        else:
            original = self._planner_from_payload(parent.payload)
            task = service.create(task_type="repair", project_id=project.project["project_id"], policy=policy, backend_mode=BackendMode.MANUAL_UI, prompt_template_ref=original.prompt_template_ref, domain_pack_root=pack_root, parent_id=original.task_id, parent_hash=original.task_hash, context_snapshot_hashes=original.context_snapshot_hashes, expected_result_fields=("original_task_id", "errors"), logical_task_id=original.logical_task_id, supersedes_task_id=original.task_id, attempt=original.attempt + 1, created_at=created_at)
        payload = task.data()
        prompt = DomainPromptResolver().resolve(pack_root=pack_root, prompt_template_ref=task.prompt_template_ref)
        return StudioTaskRecord(task.task_id, task.task_hash, task.project_id, task.policy_snapshot_id, task.policy_snapshot_hash, "planner", task.task_type, task.backend_mode.value, prompt, {"topic": topic, "expected_output_fields": list(task.expected_result_fields)}, payload, parent.task_id if parent else None, task.attempt, created_at)

    @staticmethod
    def _research_payload(task: LLMTaskV1) -> dict[str, Any]:
        return {
            "task_id": task.task_id, "task_hash": task.task_hash, "logical_task_id": task.logical_task_id,
            "supersedes_task_id": task.supersedes_task_id, "task_type": task.task_type.value,
            "project_id": task.project_id, "input_manifest": task.input_manifest,
            "prompt_template_ref": task.prompt_template_ref, "context_artifacts": list(task.context_artifacts),
            "expected_output_schema": task.expected_output_schema, "backend_mode": task.backend_mode.value,
            "status": task.status.value, "attempt": task.attempt, "parent_task_id": task.parent_task_id,
            "created_at": task.created_at, "completed_at": task.completed_at,
        }

    @staticmethod
    def _research_from_payload(value: Mapping[str, Any]) -> LLMTaskV1:
        return LLMTaskV1(**{**value, "task_type": TaskType(value["task_type"]), "backend_mode": BackendMode(value["backend_mode"]), "status": TaskStatus(value["status"]), "context_artifacts": tuple(value["context_artifacts"])})

    @staticmethod
    def _planner_from_payload(value: Mapping[str, Any]) -> PlannerTaskV1:
        raw = {key: item for key, item in value.items() if key != "schema_version"}
        return PlannerTaskV1(**{**raw, "backend_mode": BackendMode(raw["backend_mode"]), "context_snapshot_hashes": tuple(raw["context_snapshot_hashes"]), "expected_result_fields": tuple(raw["expected_result_fields"])})
