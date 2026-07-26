import type {
  ProjectArtifactsResponseDto,
  ProjectCreateResponseDto,
  ProjectStatusResponseDto,
} from '../api/studioApi';
import { vi } from 'vitest';

export const projectId = 'prj_abc123';

export const coreCreateResponse: ProjectCreateResponseDto = {
  project: {
    schema_version: '3.0.0',
    project_id: projectId,
    title: 'Contract project',
    created_at: '2026-07-26T12:00:00Z',
    updated_at: '2026-07-26T12:00:00Z',
    domain_id: 'core-generic',
    domain_pack_version: '0.0.0',
    policy_snapshot_id: 'dps_1234567890abcdefghij',
    status: 'ready',
    version: 1,
  },
  domain: {
    resolution_mode: 'core_only',
    domain_id: 'core-generic',
    domain_pack_version: '0.0.0',
    profile_id: 'dpf_core_default',
    policy_snapshot_id: 'dps_1234567890abcdefghij',
  },
  persistence_scope: 'process_lifetime',
};

export const coreStatusResponse: ProjectStatusResponseDto = {
  project_id: projectId,
  status: 'ready',
  updated_at: '2026-07-26T12:00:00Z',
  version: 1,
  domain: coreCreateResponse.domain,
  persistence_scope: 'process_lifetime',
};

export const emptyArtifactsResponse: ProjectArtifactsResponseDto = {
  project_id: projectId,
  items: [],
  count: 0,
  persistence_scope: 'process_lifetime',
};

export function jsonResponse(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export function installRelativeRequestSupport() {
  const NativeRequest = globalThis.Request;
  class BrowserLikeRequest extends NativeRequest {
    constructor(input: RequestInfo | URL, init?: RequestInit) {
      const resolved =
        typeof input === 'string' && input.startsWith('/')
          ? new URL(input, 'http://same-origin.test')
          : input;
      super(resolved, init);
    }
  }
  vi.stubGlobal('Request', BrowserLikeRequest);
}
