import {
  createProject as generatedCreateProject,
  createStudioTask as generatedCreateStudioTask,
  createStudioTaskRepair as generatedCreateStudioTaskRepair,
  approveStudioTask as generatedApproveStudioTask,
  decideSequenceReview as generatedDecideSequenceReview,
  getProjectReview as generatedGetProjectReview,
  getPreviewJob as generatedGetPreviewJob,
  listPreviewEvents as generatedListPreviewEvents,
  getProjectStatus as generatedGetProjectStatus,
  listProjects as generatedListProjects,
  getSequenceReview as generatedGetSequenceReview,
  listStudioTasks as generatedListStudioTasks,
  listProjectArtifacts as generatedListProjectArtifacts,
  submitStudioTaskResponse as generatedSubmitStudioTaskResponse,
  requestSequencePreview as generatedRequestSequencePreview,
} from '../generated/kurgu-api';
import { createClient } from '../generated/kurgu-api/client';
import type {
  ErrorEnvelopeDto,
  ProjectArtifactsResponseDto,
  ProjectCreateRequestDto,
  ProjectCreateResponseDto,
  ProjectStatusResponseDto,
  ProjectListResponseDto,
  ProjectReviewDto,
  ReviewDecisionDto,
  ReviewDecisionRequestDto,
  SequenceReviewDto,
  StudioTaskCollectionDto,
  StudioTaskCreateRequestDto,
  StudioTaskDto,
  StudioTaskResponseSubmitDto,
  PreviewEventCollectionDto,
  PreviewJobDto,
} from '../generated/kurgu-api/types.gen';

import { StudioApiError } from './studioApiError';

export { StudioApiError } from './studioApiError';
export type {
  ProjectArtifactsResponseDto,
  ProjectCreateRequestDto,
  ProjectCreateResponseDto,
  ProjectStatusResponseDto,
  ProjectListResponseDto,
  ProjectReviewDto,
  ReviewDecisionDto,
  ReviewDecisionRequestDto,
  SequenceReviewDto,
  StudioTaskCollectionDto,
  StudioTaskCreateRequestDto,
  StudioTaskDto,
  StudioTaskResponseSubmitDto,
  PreviewEventCollectionDto,
  PreviewJobDto,
};

export interface StudioApi {
  createProject(
    request: ProjectCreateRequestDto,
  ): Promise<ProjectCreateResponseDto>;
  listProjects(): Promise<ProjectListResponseDto>;
  getProjectStatus(projectId: string): Promise<ProjectStatusResponseDto>;
  listProjectArtifacts(
    projectId: string,
  ): Promise<ProjectArtifactsResponseDto>;
  listStudioTasks(projectId: string): Promise<StudioTaskCollectionDto>;
  createStudioTask(
    projectId: string,
    request: StudioTaskCreateRequestDto,
  ): Promise<StudioTaskDto>;
  submitStudioTaskResponse(
    projectId: string,
    taskId: string,
    request: StudioTaskResponseSubmitDto,
  ): Promise<StudioTaskDto>;
  approveStudioTask(projectId: string, taskId: string): Promise<StudioTaskDto>;
  createStudioTaskRepair(
    projectId: string,
    taskId: string,
  ): Promise<StudioTaskDto>;
  getProjectReview(projectId: string): Promise<ProjectReviewDto>;
  getSequenceReview(
    projectId: string,
    sequenceId: string,
  ): Promise<SequenceReviewDto>;
  decideSequenceReview(
    projectId: string,
    sequenceId: string,
    request: ReviewDecisionRequestDto,
  ): Promise<ReviewDecisionDto>;
  requestSequencePreview(projectId: string, sequenceId: string): Promise<PreviewJobDto>;
  getPreviewJob(projectId: string, jobId: string): Promise<PreviewJobDto>;
  listPreviewEvents(projectId: string, jobId: string, after?: number): Promise<PreviewEventCollectionDto>;
}

const SAFE_ERROR_MESSAGES: Readonly<Record<string, string>> = {
  REQUEST_VALIDATION_FAILED: 'The request did not pass validation.',
  CONTRACT_VALIDATION_FAILED:
    'The generated data failed canonical contract validation.',
  DOMAIN_CONFIGURATION_REQUIRED:
    'A complete domain configuration is required.',
  DOMAIN_UNKNOWN: 'The requested domain or version is not available.',
  DOMAIN_PROFILE_MISMATCH:
    'The profile does not match the selected domain pack.',
  PROJECT_NOT_FOUND: 'The requested project was not found.',
  PROJECT_ID_COLLISION: 'The project could not be created.',
  TASK_NOT_FOUND: 'The requested task was not found.',
  TASK_PROJECT_MISMATCH: 'The task does not belong to this project.',
  TASK_STATE_INVALID: 'The task is not waiting for a response.',
  TASK_NOT_VALID: 'Only a valid task result can be approved.',
  TASK_UNAVAILABLE: 'The requested task is unavailable for this project.',
  REPAIR_NOT_REQUIRED: 'A repair is not required for this task.',
  REVIEW_SNAPSHOT_NOT_FOUND: 'No executable review snapshot is available.',
  REVIEW_SEQUENCE_NOT_FOUND: 'The requested review sequence was not found.',
  REVIEW_SNAPSHOT_INVALID: 'The review snapshot is not valid.',
  REVIEW_SEQUENCE_LOCKED: 'The sequence already has a review decision.',
  REVIEW_DECISION_INVALID: 'The review decision is invalid.',
  RENDER_INPUT_UNAVAILABLE: 'No trusted REPLAY render input is available.',
  REVIEW_BINDING_INVALID: 'No immutable review binding is available.',
  SEQUENCE_NOT_REVIEWABLE: 'The sequence is not reviewable.',
  PREVIEW_DELIVERY_UNAVAILABLE: 'Preview delivery is unavailable.',
  PREVIEW_FRAME_UNAVAILABLE: 'The requested preview frame is unavailable.',
  INTERNAL_ERROR: 'An internal error occurred.',
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelopeDto {
  if (!isRecord(value) || !isRecord(value.error)) {
    return false;
  }
  return (
    typeof value.error.code === 'string' &&
    typeof value.error.message === 'string' &&
    Array.isArray(value.error.issues)
  );
}

function normalizedBaseUrl(baseUrl: string | undefined): string {
  const value = baseUrl?.trim() ?? '';
  if (value === '') {
    return '';
  }
  if (
    /[\u0000-\u001f\u007f\\]/.test(value) ||
    /^[a-zA-Z]:[\\/]/.test(value) ||
    value.startsWith('//') ||
    value.includes('?') ||
    value.includes('#')
  ) {
    throw new StudioApiError(
      'INVALID_BASE_URL',
      'The Studio API base URL is invalid.',
    );
  }
  if (value.startsWith('/')) {
    if (value.split('/').some((segment) => segment === '..')) {
      throw new StudioApiError(
        'INVALID_BASE_URL',
        'The Studio API base URL is invalid.',
      );
    }
    return value.endsWith('/') ? value.slice(0, -1) : value;
  }
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    throw new StudioApiError(
      'INVALID_BASE_URL',
      'The Studio API base URL is invalid.',
    );
  }
  if (
    !['http:', 'https:'].includes(parsed.protocol) ||
    parsed.username ||
    parsed.password ||
    parsed.search ||
    parsed.hash ||
    parsed.pathname !== '/'
  ) {
    throw new StudioApiError(
      'INVALID_BASE_URL',
      'The Studio API base URL is invalid.',
    );
  }
  return parsed.origin;
}

function apiFailure(error: unknown, status: number | undefined): StudioApiError {
  if (isErrorEnvelope(error)) {
    const safeCode =
      error.error.code in SAFE_ERROR_MESSAGES
        ? error.error.code
        : 'API_ERROR';
    return new StudioApiError(
      safeCode,
      SAFE_ERROR_MESSAGES[safeCode] ?? 'The Studio API request failed.',
      status,
    );
  }
  return new StudioApiError(
    'API_ERROR',
    'The Studio API request failed.',
    status,
  );
}

async function execute<T>(
  request: Promise<{
    data?: T;
    error?: unknown;
    response?: Response;
  }>,
): Promise<T> {
  try {
    const result = await request;
    if (result.data !== undefined && result.response?.ok) {
      return result.data;
    }
    if (!result.response) {
      throw new StudioApiError(
        'NETWORK_ERROR',
        'The Studio API could not be reached.',
      );
    }
    throw apiFailure(result.error, result.response.status);
  } catch (error) {
    if (error instanceof StudioApiError) {
      throw error;
    }
    throw new StudioApiError(
      'NETWORK_ERROR',
      'The Studio API could not be reached.',
    );
  }
}

export function createStudioApi(options: { baseUrl?: string } = {}): StudioApi {
  const baseUrl = normalizedBaseUrl(options.baseUrl);
  const client = createClient(baseUrl ? { baseUrl } : {});

  return Object.freeze({
    createProject(request: ProjectCreateRequestDto) {
      return execute<ProjectCreateResponseDto>(
        generatedCreateProject({
          body: request,
          client,
        }),
      );
    },
    listProjects() {
      return execute<ProjectListResponseDto>(generatedListProjects({ client }));
    },
    getProjectStatus(projectId: string) {
      return execute<ProjectStatusResponseDto>(
        generatedGetProjectStatus({
          client,
          path: { project_id: projectId },
        }),
      );
    },
    listProjectArtifacts(projectId: string) {
      return execute<ProjectArtifactsResponseDto>(
        generatedListProjectArtifacts({
          client,
          path: { project_id: projectId },
        }),
      );
    },
    listStudioTasks(projectId: string) {
      return execute<StudioTaskCollectionDto>(
        generatedListStudioTasks({ client, path: { project_id: projectId } }),
      );
    },
    createStudioTask(projectId: string, request: StudioTaskCreateRequestDto) {
      return execute<StudioTaskDto>(
        generatedCreateStudioTask({
          body: request,
          client,
          path: { project_id: projectId },
        }),
      );
    },
    submitStudioTaskResponse(
      projectId: string,
      taskId: string,
      request: StudioTaskResponseSubmitDto,
    ) {
      return execute<StudioTaskDto>(
        generatedSubmitStudioTaskResponse({
          body: request,
          client,
          path: { project_id: projectId, task_id: taskId },
        }),
      );
    },
    approveStudioTask(projectId: string, taskId: string) {
      return execute<StudioTaskDto>(
        generatedApproveStudioTask({
          client,
          path: { project_id: projectId, task_id: taskId },
        }),
      );
    },
    createStudioTaskRepair(projectId: string, taskId: string) {
      return execute<StudioTaskDto>(
        generatedCreateStudioTaskRepair({
          client,
          path: { project_id: projectId, task_id: taskId },
        }),
      );
    },
    getProjectReview(projectId: string) {
      return execute<ProjectReviewDto>(
        generatedGetProjectReview({ client, path: { project_id: projectId } }),
      );
    },
    getSequenceReview(projectId: string, sequenceId: string) {
      return execute<SequenceReviewDto>(
        generatedGetSequenceReview({
          client,
          path: { project_id: projectId, sequence_id: sequenceId },
        }),
      );
    },
    decideSequenceReview(
      projectId: string,
      sequenceId: string,
      request: ReviewDecisionRequestDto,
    ) {
      return execute<ReviewDecisionDto>(
        generatedDecideSequenceReview({
          body: request,
          client,
          path: { project_id: projectId, sequence_id: sequenceId },
        }),
      );
    },
    requestSequencePreview(projectId: string, sequenceId: string) {
      return execute<PreviewJobDto>(generatedRequestSequencePreview({ client, path: { project_id: projectId, sequence_id: sequenceId } }));
    },
    getPreviewJob(projectId: string, jobId: string) {
      return execute<PreviewJobDto>(generatedGetPreviewJob({ client, path: { project_id: projectId, job_id: jobId } }));
    },
    listPreviewEvents(projectId: string, jobId: string, after = 0) {
      return execute<PreviewEventCollectionDto>(generatedListPreviewEvents({ client, path: { project_id: projectId, job_id: jobId }, query: { after } }));
    },
  });
}
