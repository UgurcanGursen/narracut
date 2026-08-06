"""Phase 13 application use cases, intentionally independent of FastAPI."""

from __future__ import annotations

import hashlib
from typing import Any, Literal, Mapping

from engine.contracts._canonical_json import encode_canonical_json_bytes

from .errors import ApplicationError, ApplicationIssue
from .models import PreviewExecutionResult, PreviewJobRecord, ReviewSnapshotRecord, StudioTaskRecord, StudioTaskView
from .ports import (
    Clock,
    ManualTaskFactoryPort,
    ProjectRepository,
    StudioWorkflowRepository,
    PreviewExecutionPort,
    RenderJobRepositoryPort,
    PreviewDeliveryPort,
    StudioRenderInputResolverPort,
)


def _hash(value: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _error(code: str, pointer: str, message: str) -> ApplicationError:
    return ApplicationError(code, message, (ApplicationIssue(code, pointer, message),))


class StudioWorkflowService:
    def __init__(
        self,
        *,
        projects: ProjectRepository,
        workflow: StudioWorkflowRepository,
        task_factory: ManualTaskFactoryPort,
        clock: Clock,
        render_inputs: StudioRenderInputResolverPort | None = None,
        preview_executor: PreviewExecutionPort | None = None,
        preview_jobs: RenderJobRepositoryPort | None = None,
        preview_delivery: PreviewDeliveryPort | None = None,
    ) -> None:
        self.projects = projects
        self.workflow = workflow
        self.task_factory = task_factory
        self.clock = clock
        self.render_inputs = render_inputs
        self.preview_executor = preview_executor
        self.preview_jobs = preview_jobs
        self.preview_delivery = preview_delivery

    def create_task(
        self,
        *,
        project_id: str,
        family: Literal["research", "planner"],
        task_type: str,
        backend_mode: Literal["replay", "manual_ui"],
        topic: str,
    ) -> StudioTaskView:
        project = self._project(project_id)
        try:
            task = self.task_factory.create(
                project=project,
                family=family,
                task_type=task_type,
                backend_mode=backend_mode,
                topic=topic,
                created_at=self.clock.now_utc(),
            )
        except ValueError as exc:
            raise _error("TASK_UNAVAILABLE", "/task_type", "The requested task is unavailable for this project.") from exc
        self.workflow.put_task(task)
        self.workflow.record_task_result(
            task_id=task.task_id,
            status="waiting",
            response_hash=None,
            validation_issues=(),
            created_at=self.clock.now_utc(),
        )
        return self._task(task.task_id)

    def list_tasks(self, project_id: str) -> tuple[StudioTaskView, ...]:
        self._project(project_id)
        return self.workflow.list_tasks(project_id)

    def get_task(self, project_id: str, task_id: str) -> StudioTaskView:
        task = self._task(task_id)
        if task.record.project_id != project_id:
            raise _error("TASK_PROJECT_MISMATCH", "/task_id", "The task does not belong to this project.")
        return task

    def submit_task_response(
        self,
        *,
        project_id: str,
        task_id: str,
        payload: Mapping[str, Any],
    ) -> StudioTaskView:
        task = self.get_task(project_id, task_id)
        if task.status != "waiting":
            raise _error("TASK_STATE_INVALID", "/task_id", "The task is not waiting for a response.")
        accepted, issues, response_hash = self.task_factory.validate_response(
            task=task.record,
            payload=payload,
        )
        self.workflow.record_task_result(
            task_id=task_id,
            status="valid" if accepted else "repair_required",
            response_hash=response_hash,
            validation_issues=issues,
            created_at=self.clock.now_utc(),
        )
        return self._task(task_id)

    def approve_task(self, *, project_id: str, task_id: str) -> StudioTaskView:
        task = self.get_task(project_id, task_id)
        if task.status != "valid":
            raise _error("TASK_NOT_VALID", "/task_id", "Only a valid task result can be approved.")
        self.workflow.record_task_result(
            task_id=task_id,
            status="approved",
            response_hash=task.response_hash,
            validation_issues=(),
            created_at=self.clock.now_utc(),
        )
        return self._task(task_id)

    def create_repair(self, *, project_id: str, task_id: str) -> StudioTaskView:
        previous = self.get_task(project_id, task_id)
        if previous.status != "repair_required":
            raise _error("REPAIR_NOT_REQUIRED", "/task_id", "A repair is only available after validation fails.")
        project = self._project(project_id)
        try:
            repair = self.task_factory.create(
                project=project,
                family=previous.record.family,
                task_type="repair",
                backend_mode="manual_ui",
                topic=str(previous.record.context_package["topic"]),
                created_at=self.clock.now_utc(),
                parent=previous.record,
            )
        except ValueError as exc:
            raise _error("TASK_UNAVAILABLE", "/task_id", "A repair task is unavailable for this project.") from exc
        self.workflow.put_task(repair)
        self.workflow.record_task_result(
            task_id=repair.task_id,
            status="waiting",
            response_hash=None,
            validation_issues=(),
            created_at=self.clock.now_utc(),
        )
        return self._task(repair.task_id)

    def register_review_snapshot(
        self,
        *,
        project_id: str,
        executable_plan: Mapping[str, Any],
        final_edl_bundle: Mapping[str, Any],
    ) -> ReviewSnapshotRecord:
        project = self._project(project_id)
        snapshot = self._validate_snapshot(
            project_id=project_id,
            policy_snapshot_id=project.domain.policy_snapshot_id,
            policy_snapshot_hash=project.domain.policy_snapshot["canonical_hash"],
            executable_plan=executable_plan,
            final_edl_bundle=final_edl_bundle,
            created_at=self.clock.now_utc(),
        )
        self.workflow.put_review_snapshot(snapshot)
        return snapshot

    def sequence_review(self, *, project_id: str, sequence_id: str) -> Mapping[str, Any]:
        self._project(project_id)
        snapshot = self.workflow.get_review_snapshot(project_id)
        if snapshot is None:
            raise _error("REVIEW_SNAPSHOT_NOT_FOUND", "/project_id", "No executable editorial review snapshot is available.")
        sequence = next(
            (
                item for item in snapshot.executable_plan["sequences"]
                if item["executable_sequence_id"] == sequence_id
            ),
            None,
        )
        edl = next(
            (
                item for item in snapshot.final_edl_bundle["sequence_edls"]
                if item["executable_sequence_id"] == sequence_id
            ),
            None,
        )
        if sequence is None or edl is None:
            raise _error("REVIEW_SEQUENCE_NOT_FOUND", "/sequence_id", "The requested sequence is not in the review snapshot.")
        return {
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_hash": snapshot.snapshot_hash,
            "sequence": sequence,
            "edl_binding": edl,
            "decision": self.workflow.get_review_decision(project_id=project_id, sequence_id=sequence_id),
        }

    def project_review(self, *, project_id: str) -> Mapping[str, Any]:
        self._project(project_id)
        snapshot = self.workflow.get_review_snapshot(project_id)
        if snapshot is None:
            return {"status": "unavailable", "project_id": project_id, "snapshot_id": None, "snapshot_hash": None, "sequence_ids": []}
        return {
            "status": "available",
            "project_id": project_id,
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_hash": snapshot.snapshot_hash,
            "sequence_ids": [item["executable_sequence_id"] for item in snapshot.executable_plan["sequences"]],
        }

    def decide_sequence(
        self,
        *,
        project_id: str,
        sequence_id: str,
        action: Literal["approve", "replacement_requested"],
        replacement_kind: str | None,
    ) -> Mapping[str, Any]:
        review = self.sequence_review(project_id=project_id, sequence_id=sequence_id)
        if review["decision"] is not None:
            raise _error("REVIEW_SEQUENCE_LOCKED", "/sequence_id", "The sequence already has an immutable review decision.")
        if action == "approve" and replacement_kind is not None:
            raise _error("REVIEW_DECISION_INVALID", "/replacement_kind", "Approval cannot contain a replacement request.")
        if action == "replacement_requested" and replacement_kind not in {"asset_change", "replan"}:
            raise _error("REVIEW_DECISION_INVALID", "/replacement_kind", "A supported replacement kind is required.")
        body = {
            "project_id": project_id,
            "sequence_id": sequence_id,
            "snapshot_id": review["snapshot_id"],
            "snapshot_hash": review["snapshot_hash"],
            "executable_sequence_hash": review["sequence"]["executable_sequence_hash"],
            "video_edl_hash": review["edl_binding"]["video_edl_hash"],
            "audio_edl_hash": review["edl_binding"]["audio_edl_hash"],
            "action": action,
            "replacement_kind": replacement_kind,
            "created_at": self.clock.now_utc(),
            "producer": "studio-phase13",
            "producer_version": "0.1.0",
        }
        digest = _hash(body)
        decision = {"decision_id": "rdec_" + digest[7:27], "decision_hash": digest, **body}
        self.workflow.put_review_decision(decision)
        return decision

    def request_preview(self, *, project_id: str, sequence_id: str) -> PreviewJobRecord:
        project = self._project(project_id)
        review = self.workflow.get_review_snapshot(project_id)
        if review is None:
            raise _error("REVIEW_BINDING_INVALID", "/project_id", "No immutable review binding is available.")
        sequence = next((item for item in review.executable_plan["sequences"] if item["executable_sequence_id"] == sequence_id), None)
        if sequence is None:
            raise _error("SEQUENCE_NOT_REVIEWABLE", "/sequence_id", "The sequence is not reviewable.")
        if self.render_inputs is None or self.preview_executor is None or self.preview_jobs is None:
            raise _error("RENDER_INPUT_UNAVAILABLE", "/sequence_id", "No trusted REPLAY render input is available.")
        snapshot = self.render_inputs.resolve(project_id=project_id, sequence_id=sequence_id, review_snapshot=review)
        if snapshot is None:
            raise _error("RENDER_INPUT_UNAVAILABLE", "/sequence_id", "No trusted REPLAY render input is available.")
        if (snapshot.project_id, snapshot.executable_sequence_id, snapshot.executable_sequence_hash, snapshot.policy_snapshot_id, snapshot.policy_snapshot_hash, snapshot.domain_pack_version) != (project_id, sequence_id, sequence["executable_sequence_hash"], project.domain.policy_snapshot_id, project.domain.policy_snapshot["canonical_hash"], project.domain.domain_pack_version):
            raise _error("REVIEW_BINDING_INVALID", "/sequence_id", "The render input is not bound to the current review.")
        request_body = {"project_id": project_id, "sequence_id": sequence_id, "policy_snapshot_hash": snapshot.policy_snapshot_hash, "executable_plan_hash": snapshot.executable_plan_hash, "final_edl_bundle_hash": snapshot.final_edl_bundle_hash, "render_props_hash": snapshot.render_props_hash, "mode": "PREVIEW_REPLAY_V1"}
        request_hash = _hash(request_body)
        active = self.preview_jobs.get_active_preview_job(request_hash)
        if active is not None:
            return active
        attempt = self.preview_jobs.next_preview_attempt(request_hash)
        now = self.clock.now_utc()
        job = PreviewJobRecord(job_id="pjob_" + hashlib.sha256((request_hash + ":" + str(attempt)).encode()).hexdigest()[:24], preview_request_id="preq_" + request_hash[7:31], preview_request_hash=request_hash, attempt_ordinal=attempt, project_id=project_id, sequence_id=sequence_id, snapshot_id=snapshot.snapshot_id, snapshot_hash=snapshot.snapshot_hash, state="requested", created_at=now, updated_at=now)
        try:
            self.preview_jobs.create_preview_job(job)
        except ValueError as exc:
            active = self.preview_jobs.get_active_preview_job(request_hash)
            if active is not None:
                return active
            raise _error("RENDER_REQUEST_CONFLICT", "/sequence_id", "The preview request conflicts with another attempt.") from exc
        self.preview_jobs.transition_preview_job(job.job_id, state="admitted", created_at=self.clock.now_utc())
        self.preview_jobs.transition_preview_job(job.job_id, state="running", created_at=self.clock.now_utc())
        try:
            outcome = self.preview_executor.execute(snapshot, timestamp_utc=self.clock.now_utc())
        except Exception:
            outcome = PreviewExecutionResult(state="failed", receipt_hash=None, preview_manifest_bytes=None, frames={}, public_failure_code="PREVIEW_EXECUTION_FAILED")
        if outcome.state == "succeeded" and outcome.receipt_hash and outcome.preview_manifest_bytes is not None:
            manifest_hash = "sha256:" + hashlib.sha256(outcome.preview_manifest_bytes).hexdigest()
            delivery_id = "pdel_" + hashlib.sha256((job.job_id + manifest_hash).encode()).hexdigest()[:24]
            if self.preview_delivery is None:
                outcome = PreviewExecutionResult(state="failed", receipt_hash=outcome.receipt_hash, preview_manifest_bytes=None, frames={}, public_failure_code="PREVIEW_DELIVERY_UNAVAILABLE")
                self.preview_jobs.transition_preview_job(job.job_id, state="failed", created_at=self.clock.now_utc(), public_failure_code=outcome.public_failure_code, receipt_hash=outcome.receipt_hash)
                return self._preview_job(project_id, job.job_id)
            try:
                self.preview_delivery.put(delivery_id=delivery_id, project_id=project_id, job_id=job.job_id, manifest=outcome.preview_manifest_bytes, frames=outcome.frames)
            except (TypeError, ValueError):
                self.preview_jobs.transition_preview_job(job.job_id, state="failed", created_at=self.clock.now_utc(), public_failure_code="PREVIEW_DELIVERY_UNAVAILABLE", receipt_hash=outcome.receipt_hash)
                return self._preview_job(project_id, job.job_id)
            self.preview_jobs.transition_preview_job(job.job_id, state="succeeded", created_at=self.clock.now_utc(), receipt_hash=outcome.receipt_hash, preview_manifest_hash=manifest_hash, delivery_id=delivery_id)
        else:
            self.preview_jobs.transition_preview_job(job.job_id, state=outcome.state, created_at=self.clock.now_utc(), public_failure_code=outcome.public_failure_code or "PREVIEW_EXECUTION_FAILED", receipt_hash=outcome.receipt_hash)
        return self._preview_job(project_id, job.job_id)

    def preview_manifest(self, *, project_id: str, job_id: str) -> bytes:
        job = self._preview_job(project_id, job_id)
        if job.state != "succeeded" or not job.delivery_id or self.preview_delivery is None:
            raise _error("PREVIEW_DELIVERY_UNAVAILABLE", "/job_id", "Preview delivery is unavailable.")
        value = self.preview_delivery.manifest(delivery_id=job.delivery_id, project_id=project_id, job_id=job_id)
        if value is None:
            raise _error("PREVIEW_DELIVERY_UNAVAILABLE", "/job_id", "Preview delivery is unavailable.")
        return value

    def preview_frame(self, *, project_id: str, job_id: str, frame_index: int) -> bytes:
        job = self._preview_job(project_id, job_id)
        if frame_index < 0 or job.state != "succeeded" or not job.delivery_id or self.preview_delivery is None:
            raise _error("PREVIEW_DELIVERY_UNAVAILABLE", "/frame_index", "Preview delivery is unavailable.")
        value = self.preview_delivery.frame(delivery_id=job.delivery_id, project_id=project_id, job_id=job_id, frame_index=frame_index)
        if value is None:
            raise _error("PREVIEW_FRAME_UNAVAILABLE", "/frame_index", "The requested preview frame is unavailable.")
        return value

    def preview_job(self, *, project_id: str, job_id: str) -> PreviewJobRecord:
        return self._preview_job(project_id, job_id)

    def preview_events(self, *, project_id: str, job_id: str, after: int) -> tuple[Mapping[str, Any], ...]:
        if after < 0:
            raise _error("PREVIEW_EVENT_CURSOR_INVALID", "/after", "The event cursor is invalid.")
        self._preview_job(project_id, job_id)
        assert self.preview_jobs is not None
        return tuple({"ordinal": item.ordinal, "event_id": item.event_id, "state": item.state, "created_at": item.created_at, "public_code": item.public_code} for item in self.preview_jobs.list_preview_events(job_id, after=after))

    def _preview_job(self, project_id: str, job_id: str) -> PreviewJobRecord:
        if self.preview_jobs is None:
            raise _error("PREVIEW_JOB_NOT_FOUND", "/job_id", "The preview job was not found.")
        job = self.preview_jobs.get_preview_job(job_id)
        if job is None or job.project_id != project_id:
            raise _error("PREVIEW_JOB_NOT_FOUND", "/job_id", "The preview job was not found.")
        return job

    def _project(self, project_id: str):
        project = self.projects.get(project_id)
        if project is None:
            raise _error("PROJECT_NOT_FOUND", "/project_id", "The requested project was not found.")
        return project

    def _task(self, task_id: str) -> StudioTaskView:
        task = self.workflow.get_task(task_id)
        if task is None:
            raise _error("TASK_NOT_FOUND", "/task_id", "The requested task was not found.")
        return task

    @staticmethod
    def _validate_snapshot(
        *,
        project_id: str,
        policy_snapshot_id: str,
        policy_snapshot_hash: str,
        executable_plan: Mapping[str, Any],
        final_edl_bundle: Mapping[str, Any],
        created_at: str,
    ) -> ReviewSnapshotRecord:
        plan_required = {
            "executable_editorial_plan_id", "executable_editorial_plan_hash",
            "schema_version", "project_id", "policy_snapshot_id",
            "policy_snapshot_hash", "editorial_integration_policy_hash", "sequences",
        }
        bundle_required = {
            "final_edl_bundle_id", "final_edl_bundle_hash", "schema_version",
            "executable_editorial_plan_id", "executable_editorial_plan_hash", "sequence_edls",
        }
        if set(executable_plan) != plan_required or set(final_edl_bundle) != bundle_required:
            raise _error("REVIEW_SNAPSHOT_INVALID", "/", "The review snapshot is not a canonical Phase 12 bundle.")
        plan_body = {key: value for key, value in executable_plan.items() if key not in {"executable_editorial_plan_id", "executable_editorial_plan_hash"}}
        plan_hash = _hash(plan_body)
        if (
            executable_plan["executable_editorial_plan_hash"] != plan_hash
            or executable_plan["executable_editorial_plan_id"] != "eeplan_" + plan_hash[7:27]
            or executable_plan["project_id"] != project_id
            or executable_plan["policy_snapshot_id"] != policy_snapshot_id
            or executable_plan["policy_snapshot_hash"] != policy_snapshot_hash
            or not isinstance(executable_plan["sequences"], list)
            or not executable_plan["sequences"]
        ):
            raise _error("REVIEW_SNAPSHOT_INVALID", "/executable_plan", "The executable plan binding is invalid.")
        bundle_body = {key: value for key, value in final_edl_bundle.items() if key not in {"final_edl_bundle_id", "final_edl_bundle_hash"}}
        bundle_hash = _hash(bundle_body)
        if (
            final_edl_bundle["final_edl_bundle_hash"] != bundle_hash
            or final_edl_bundle["final_edl_bundle_id"] != "fedl_" + bundle_hash[7:27]
            or (final_edl_bundle["executable_editorial_plan_id"], final_edl_bundle["executable_editorial_plan_hash"])
            != (executable_plan["executable_editorial_plan_id"], executable_plan["executable_editorial_plan_hash"])
            or not isinstance(final_edl_bundle["sequence_edls"], list)
        ):
            raise _error("REVIEW_SNAPSHOT_INVALID", "/final_edl_bundle", "The final EDL bundle binding is invalid.")
        plan_pairs = {
            (item.get("executable_sequence_id"), item.get("executable_sequence_hash"))
            for item in executable_plan["sequences"]
            if isinstance(item, dict)
        }
        bundle_pairs = {
            (item.get("executable_sequence_id"), item.get("executable_sequence_hash"))
            for item in final_edl_bundle["sequence_edls"]
            if isinstance(item, dict)
        }
        if plan_pairs != bundle_pairs or len(plan_pairs) != len(executable_plan["sequences"]):
            raise _error("REVIEW_SNAPSHOT_INVALID", "/final_edl_bundle/sequence_edls", "Every executable sequence needs a bound EDL pair.")
        snapshot_body = {
            "project_id": project_id,
            "policy_snapshot_id": policy_snapshot_id,
            "policy_snapshot_hash": policy_snapshot_hash,
            "executable_plan_hash": plan_hash,
            "final_edl_bundle_hash": bundle_hash,
        }
        snapshot_hash = _hash(snapshot_body)
        return ReviewSnapshotRecord(
            snapshot_id="rsnap_" + snapshot_hash[7:27],
            snapshot_hash=snapshot_hash,
            project_id=project_id,
            policy_snapshot_id=policy_snapshot_id,
            policy_snapshot_hash=policy_snapshot_hash,
            executable_plan=dict(executable_plan),
            final_edl_bundle=dict(final_edl_bundle),
            created_at=created_at,
        )
