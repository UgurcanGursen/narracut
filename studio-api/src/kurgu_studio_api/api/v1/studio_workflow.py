"""Thin HTTP mappings for the Phase 13 Studio workflow."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status
from fastapi.responses import StreamingResponse

from ...application.models import StudioTaskView
from ...application.studio_workflow_service import StudioWorkflowService
from ..errors import ErrorEnvelopeDTO
from .dto import (
    ReviewDecisionDTO,
    ReviewDecisionRequestDTO,
    ReviewSnapshotCreateDTO,
    ReviewSnapshotDTO,
    ProjectReviewDTO,
    SequenceReviewDTO,
    StudioTaskCollectionDTO,
    StudioTaskCreateRequestDTO,
    StudioTaskDTO,
    StudioTaskResponseSubmitDTO,
    PreviewEventCollectionDTO,
    PreviewJobDTO,
)


PROJECT_ID_PATTERN = r"^prj_[a-z0-9][a-z0-9_-]{2,63}$"
TASK_ID_PATTERN = r"^(task|ptask)_[a-z0-9]+$"
SEQUENCE_ID_PATTERN = r"^eseq_[a-z0-9]+$"
ProjectIdPath = Annotated[str, Path(pattern=PROJECT_ID_PATTERN)]
TaskIdPath = Annotated[str, Path(pattern=TASK_ID_PATTERN)]
SequenceIdPath = Annotated[str, Path(pattern=SEQUENCE_ID_PATTERN)]


def _task_dto(view: StudioTaskView) -> StudioTaskDTO:
    record = view.record
    return StudioTaskDTO(
        task_id=record.task_id,
        task_hash=record.task_hash,
        project_id=record.project_id,
        policy_snapshot_id=record.policy_snapshot_id,
        policy_snapshot_hash=record.policy_snapshot_hash,
        family=record.family,
        task_type=record.task_type,
        backend_mode=record.backend_mode,
        prompt=record.prompt,
        context_package=dict(record.context_package),
        parent_task_id=record.parent_task_id,
        attempt=record.attempt,
        created_at=record.created_at,
        status=view.status,
        validation_issues=list(view.validation_issues),
        response_hash=view.response_hash,
    )


def _preview_job_dto(value) -> PreviewJobDTO:
    return PreviewJobDTO(**{field: getattr(value, field) for field in value.__dataclass_fields__})


def create_studio_workflow_router(service: StudioWorkflowService) -> APIRouter:
    router = APIRouter(prefix="/projects/{project_id}", tags=["studio-workflow"])

    @router.get("/tasks", operation_id="listStudioTasks", response_model=StudioTaskCollectionDTO, responses={404: {"model": ErrorEnvelopeDTO}, 422: {"model": ErrorEnvelopeDTO}})
    def list_tasks(project_id: ProjectIdPath) -> StudioTaskCollectionDTO:
        values = service.list_tasks(project_id)
        return StudioTaskCollectionDTO(project_id=project_id, items=[_task_dto(item) for item in values], count=len(values))

    @router.post("/tasks", operation_id="createStudioTask", status_code=status.HTTP_201_CREATED, response_model=StudioTaskDTO, responses={404: {"model": ErrorEnvelopeDTO}, 409: {"model": ErrorEnvelopeDTO}, 422: {"model": ErrorEnvelopeDTO}})
    def create_task(project_id: ProjectIdPath, request: StudioTaskCreateRequestDTO) -> StudioTaskDTO:
        return _task_dto(service.create_task(project_id=project_id, family=request.family, task_type=request.task_type, backend_mode=request.backend_mode, topic=request.topic))

    @router.get("/tasks/{task_id}", operation_id="getStudioTask", response_model=StudioTaskDTO, responses={404: {"model": ErrorEnvelopeDTO}, 409: {"model": ErrorEnvelopeDTO}, 422: {"model": ErrorEnvelopeDTO}})
    def get_task(project_id: ProjectIdPath, task_id: TaskIdPath) -> StudioTaskDTO:
        return _task_dto(service.get_task(project_id, task_id))

    @router.post("/tasks/{task_id}/response", operation_id="submitStudioTaskResponse", response_model=StudioTaskDTO, responses={404: {"model": ErrorEnvelopeDTO}, 409: {"model": ErrorEnvelopeDTO}, 422: {"model": ErrorEnvelopeDTO}})
    def submit_response(project_id: ProjectIdPath, task_id: TaskIdPath, request: StudioTaskResponseSubmitDTO) -> StudioTaskDTO:
        return _task_dto(service.submit_task_response(project_id=project_id, task_id=task_id, payload=request.payload))

    @router.post("/tasks/{task_id}/approve", operation_id="approveStudioTask", response_model=StudioTaskDTO, responses={404: {"model": ErrorEnvelopeDTO}, 409: {"model": ErrorEnvelopeDTO}, 422: {"model": ErrorEnvelopeDTO}})
    def approve_task(project_id: ProjectIdPath, task_id: TaskIdPath) -> StudioTaskDTO:
        return _task_dto(service.approve_task(project_id=project_id, task_id=task_id))

    @router.post("/tasks/{task_id}/repair", operation_id="createStudioTaskRepair", status_code=status.HTTP_201_CREATED, response_model=StudioTaskDTO, responses={404: {"model": ErrorEnvelopeDTO}, 409: {"model": ErrorEnvelopeDTO}, 422: {"model": ErrorEnvelopeDTO}})
    def create_repair(project_id: ProjectIdPath, task_id: TaskIdPath) -> StudioTaskDTO:
        return _task_dto(service.create_repair(project_id=project_id, task_id=task_id))

    @router.post("/review-snapshots", operation_id="registerReviewSnapshot", status_code=status.HTTP_201_CREATED, response_model=ReviewSnapshotDTO, responses={404: {"model": ErrorEnvelopeDTO}, 422: {"model": ErrorEnvelopeDTO}})
    def register_snapshot(project_id: ProjectIdPath, request: ReviewSnapshotCreateDTO) -> ReviewSnapshotDTO:
        value = service.register_review_snapshot(project_id=project_id, executable_plan=request.executable_plan, final_edl_bundle=request.final_edl_bundle)
        return ReviewSnapshotDTO(snapshot_id=value.snapshot_id, snapshot_hash=value.snapshot_hash, project_id=value.project_id, policy_snapshot_id=value.policy_snapshot_id, policy_snapshot_hash=value.policy_snapshot_hash, created_at=value.created_at)

    @router.get("/review", operation_id="getProjectReview", response_model=ProjectReviewDTO, responses={404: {"model": ErrorEnvelopeDTO}, 422: {"model": ErrorEnvelopeDTO}})
    def get_project_review(project_id: ProjectIdPath) -> ProjectReviewDTO:
        return ProjectReviewDTO(**service.project_review(project_id=project_id))

    @router.get("/review/sequences/{sequence_id}", operation_id="getSequenceReview", response_model=SequenceReviewDTO, responses={404: {"model": ErrorEnvelopeDTO}, 422: {"model": ErrorEnvelopeDTO}})
    def get_sequence_review(project_id: ProjectIdPath, sequence_id: SequenceIdPath) -> SequenceReviewDTO:
        return SequenceReviewDTO(**service.sequence_review(project_id=project_id, sequence_id=sequence_id))

    @router.post("/review/sequences/{sequence_id}/decision", operation_id="decideSequenceReview", response_model=ReviewDecisionDTO, responses={404: {"model": ErrorEnvelopeDTO}, 409: {"model": ErrorEnvelopeDTO}, 422: {"model": ErrorEnvelopeDTO}})
    def decide_sequence(project_id: ProjectIdPath, sequence_id: SequenceIdPath, request: ReviewDecisionRequestDTO) -> ReviewDecisionDTO:
        return ReviewDecisionDTO(**service.decide_sequence(project_id=project_id, sequence_id=sequence_id, action=request.action, replacement_kind=request.replacement_kind))

    @router.post("/sequences/{sequence_id}/preview-renders", operation_id="requestSequencePreview", status_code=status.HTTP_201_CREATED, response_model=PreviewJobDTO, responses={404: {"model": ErrorEnvelopeDTO}, 409: {"model": ErrorEnvelopeDTO}, 422: {"model": ErrorEnvelopeDTO}})
    def request_preview(project_id: ProjectIdPath, sequence_id: SequenceIdPath) -> PreviewJobDTO:
        return _preview_job_dto(service.request_preview(project_id=project_id, sequence_id=sequence_id))

    @router.get("/preview-renders/{job_id}", operation_id="getPreviewJob", response_model=PreviewJobDTO, responses={404: {"model": ErrorEnvelopeDTO}, 422: {"model": ErrorEnvelopeDTO}})
    def get_preview(project_id: ProjectIdPath, job_id: Annotated[str, Path(pattern=r"^pjob_[a-f0-9]{24}$")]) -> PreviewJobDTO:
        return _preview_job_dto(service.preview_job(project_id=project_id, job_id=job_id))

    @router.get("/preview-renders/{job_id}/events", operation_id="listPreviewEvents", response_model=PreviewEventCollectionDTO, responses={404: {"model": ErrorEnvelopeDTO}, 422: {"model": ErrorEnvelopeDTO}})
    def list_preview_events(project_id: ProjectIdPath, job_id: Annotated[str, Path(pattern=r"^pjob_[a-f0-9]{24}$")], after: int = Query(default=0)) -> PreviewEventCollectionDTO:
        items = service.preview_events(project_id=project_id, job_id=job_id, after=after)
        return PreviewEventCollectionDTO(job_id=job_id, items=items, count=len(items))

    @router.get("/preview-renders/{job_id}/events/stream", operation_id="streamPreviewEvents", responses={404: {"model": ErrorEnvelopeDTO}, 422: {"model": ErrorEnvelopeDTO}})
    def stream_preview_events(project_id: ProjectIdPath, job_id: Annotated[str, Path(pattern=r"^pjob_[a-f0-9]{24}$")], after: int = Query(default=0)) -> StreamingResponse:
        items = service.preview_events(project_id=project_id, job_id=job_id, after=after)
        def stream():
            for item in items:
                yield f"id: {item['ordinal']}\nevent: preview\ndata: {json.dumps(item, separators=(',', ':'), sort_keys=True)}\n\n"
        return StreamingResponse(stream(), media_type="text/event-stream")

    @router.get("/preview-renders/{job_id}/manifest", operation_id="getPreviewManifest", responses={404: {"model": ErrorEnvelopeDTO}, 409: {"model": ErrorEnvelopeDTO}, 422: {"model": ErrorEnvelopeDTO}})
    def preview_manifest(project_id: ProjectIdPath, job_id: Annotated[str, Path(pattern=r"^pjob_[a-f0-9]{24}$")]) -> Response:
        return Response(content=service.preview_manifest(project_id=project_id, job_id=job_id), media_type="application/json")

    @router.get("/preview-renders/{job_id}/frames/{frame_index}", operation_id="getPreviewFrame", responses={404: {"model": ErrorEnvelopeDTO}, 409: {"model": ErrorEnvelopeDTO}, 422: {"model": ErrorEnvelopeDTO}})
    def preview_frame(project_id: ProjectIdPath, job_id: Annotated[str, Path(pattern=r"^pjob_[a-f0-9]{24}$")], frame_index: Annotated[int, Path(ge=0)]) -> Response:
        return Response(content=service.preview_frame(project_id=project_id, job_id=job_id, frame_index=frame_index), media_type="image/png")

    return router
