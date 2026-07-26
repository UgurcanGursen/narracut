import {
  createProject as generatedCreateProject,
  getProjectStatus as generatedGetProjectStatus,
  listProjectArtifacts as generatedListProjectArtifacts,
} from '../generated/kurgu-api';
import { createClient } from '../generated/kurgu-api/client';
import type {
  ErrorEnvelopeDto,
  ProjectArtifactsResponseDto,
  ProjectCreateRequestDto,
  ProjectCreateResponseDto,
  ProjectStatusResponseDto,
} from '../generated/kurgu-api/types.gen';

import { StudioApiError } from './studioApiError';

export { StudioApiError } from './studioApiError';
export type {
  ProjectArtifactsResponseDto,
  ProjectCreateRequestDto,
  ProjectCreateResponseDto,
  ProjectStatusResponseDto,
};

export interface StudioApi {
  createProject(
    request: ProjectCreateRequestDto,
  ): Promise<ProjectCreateResponseDto>;
  getProjectStatus(projectId: string): Promise<ProjectStatusResponseDto>;
  listProjectArtifacts(
    projectId: string,
  ): Promise<ProjectArtifactsResponseDto>;
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
  });
}
