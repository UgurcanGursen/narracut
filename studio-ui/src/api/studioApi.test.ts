import { describe, expect, it, vi } from 'vitest';

import { createStudioApi, StudioApiError } from './studioApi';
import {
  coreCreateResponse,
  coreStatusResponse,
  emptyArtifactsResponse,
  installRelativeRequestSupport,
  jsonResponse,
  projectId,
} from '../test/fixtures';

function requestAt(
  mock: ReturnType<typeof vi.fn>,
  index: number,
): Request {
  const call = mock.mock.calls[index];
  const request = call?.[0];
  if (!(request instanceof Request)) {
    throw new Error('Expected generated client to call fetch with Request.');
  }
  return request;
}

describe('createStudioApi', () => {
  it('uses the generated client with same-origin paths for the core flow', async () => {
    installRelativeRequestSupport();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(coreCreateResponse, 201))
      .mockResolvedValueOnce(jsonResponse(coreStatusResponse))
      .mockResolvedValueOnce(jsonResponse(emptyArtifactsResponse));
    vi.stubGlobal('fetch', fetchMock);
    const api = createStudioApi();

    await api.createProject({
      title: 'Core project',
      domain: { resolution_mode: 'core_only' },
    });
    await api.getProjectStatus(projectId);
    await api.listProjectArtifacts(projectId);

    const createRequest = requestAt(fetchMock, 0);
    expect(createRequest.method).toBe('POST');
    expect(new URL(createRequest.url).pathname).toBe('/api/v1/projects');
    expect(JSON.parse(await createRequest.clone().text())).toEqual({
      title: 'Core project',
      domain: { resolution_mode: 'core_only' },
    });

    const statusRequest = requestAt(fetchMock, 1);
    expect(statusRequest.method).toBe('GET');
    expect(new URL(statusRequest.url).pathname).toBe(
      `/api/v1/projects/${projectId}/status`,
    );

    const artifactsRequest = requestAt(fetchMock, 2);
    expect(artifactsRequest.method).toBe('GET');
    expect(new URL(artifactsRequest.url).pathname).toBe(
      `/api/v1/projects/${projectId}/artifacts`,
    );
  });

  it('sends the exact eligible business-tech request', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(coreCreateResponse, 201));
    vi.stubGlobal('fetch', fetchMock);
    const api = createStudioApi({ baseUrl: 'https://studio.example' });

    await api.createProject({
      title: 'Business project',
      domain: {
        resolution_mode: 'domain_pack',
        domain_id: 'business-tech',
        domain_pack_version: '0.1.0',
        profile: {
          profile_id: 'dpf_business_default',
          enabled_extensions: [],
          policy_overrides: {},
        },
      },
    });

    const request = requestAt(fetchMock, 0);
    expect(request.url).toBe('https://studio.example/api/v1/projects');
    expect(JSON.parse(await request.clone().text())).toEqual({
      title: 'Business project',
      domain: {
        resolution_mode: 'domain_pack',
        domain_id: 'business-tech',
        domain_pack_version: '0.1.0',
        profile: {
          profile_id: 'dpf_business_default',
          enabled_extensions: [],
          policy_overrides: {},
        },
      },
    });
  });

  it('uses generated HTTP operations for the Manual LLM task boundary', async () => {
    installRelativeRequestSupport();
    const task = {
      task_id: 'task_abc', task_hash: 'sha256:abc', project_id: projectId,
      policy_snapshot_id: 'dps_snapshot', policy_snapshot_hash: 'sha256:policy',
      family: 'research', task_type: 'source_discovery', backend_mode: 'manual_ui',
      prompt: 'Return JSON.', context_package: { topic: 'AI chips' }, parent_task_id: null,
      attempt: 0, created_at: '2026-08-06T00:00:00Z', status: 'waiting',
      validation_issues: [], response_hash: null,
    };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(task, 201));
    vi.stubGlobal('fetch', fetchMock);
    const api = createStudioApi();

    await api.createStudioTask(projectId, {
      family: 'research', task_type: 'source_discovery', backend_mode: 'manual_ui', topic: 'AI chips',
    });

    const request = requestAt(fetchMock, 0);
    expect(request.method).toBe('POST');
    expect(new URL(request.url).pathname).toBe(`/api/v1/projects/${projectId}/tasks`);
    expect(JSON.parse(await request.clone().text())).toEqual({
      family: 'research', task_type: 'source_discovery', backend_mode: 'manual_ui', topic: 'AI chips',
    });
  });

  it('keeps explicit client base URLs isolated per facade instance', async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(() =>
        Promise.resolve(jsonResponse(coreCreateResponse, 201)),
      );
    vi.stubGlobal('fetch', fetchMock);
    const first = createStudioApi({ baseUrl: 'http://127.0.0.1:8101' });
    const second = createStudioApi({ baseUrl: 'http://127.0.0.1:8102' });

    await first.createProject({
      title: 'First',
      domain: { resolution_mode: 'core_only' },
    });
    await second.createProject({
      title: 'Second',
      domain: { resolution_mode: 'core_only' },
    });

    expect(new URL(requestAt(fetchMock, 0).url).origin).toBe(
      'http://127.0.0.1:8101',
    );
    expect(new URL(requestAt(fetchMock, 1).url).origin).toBe(
      'http://127.0.0.1:8102',
    );
  });

  it('supports a root-relative base path without exposing endpoint strings', async () => {
    installRelativeRequestSupport();
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(coreCreateResponse, 201));
    vi.stubGlobal('fetch', fetchMock);
    const api = createStudioApi({ baseUrl: '/studio-api' });

    await api.createProject({
      title: 'Relative',
      domain: { resolution_mode: 'core_only' },
    });

    expect(new URL(requestAt(fetchMock, 0).url).pathname).toBe(
      '/studio-api/api/v1/projects',
    );
  });

  it('normalizes a structured API error without leaking raw values', async () => {
    const rawSecret = 'raw-profile-secret';
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(
        {
          error: {
            code: 'DOMAIN_PROFILE_MISMATCH',
            message: `Do not expose ${rawSecret}`,
            issues: [
              {
                code: 'DOMAIN_PROFILE_MISMATCH',
                json_pointer: '/domain/profile/profile_id',
                message: rawSecret,
              },
            ],
          },
        },
        422,
      ),
    );
    vi.stubGlobal('fetch', fetchMock);
    const api = createStudioApi({ baseUrl: 'https://studio.example' });

    const caught = await api
      .createProject({
        title: 'Rejected',
        domain: { resolution_mode: 'core_only' },
      })
      .catch((error: unknown) => error);

    expect(caught).toBeInstanceOf(StudioApiError);
    expect(caught).toMatchObject({
      code: 'DOMAIN_PROFILE_MISMATCH',
      message: 'The profile does not match the selected domain pack.',
      status: 422,
    });
    expect(String(caught)).not.toContain(rawSecret);
  });

  it('bounds network failures to a generic public error', async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValue(new Error('socket failed with private detail'));
    vi.stubGlobal('fetch', fetchMock);
    const api = createStudioApi({ baseUrl: 'https://studio.example' });

    const caught = await api
      .createProject({
        title: 'Network',
        domain: { resolution_mode: 'core_only' },
      })
      .catch((error: unknown) => error);

    expect(caught).toMatchObject({
      code: 'NETWORK_ERROR',
      message: 'The Studio API could not be reached.',
    });
    expect(String(caught)).not.toContain('private');
  });

  it.each([
    ['file', '///tmp/api'].join(':'),
    'javascript:alert(1)',
    'data:text/plain,no',
    'ftp://example.test',
    ['C:', 'workspace', 'api'].join('\\'),
    '//example.test',
    '/../private',
    'https://example.test/path',
    ['https://user', 'pass@example.test'].join(':'),
  ])('rejects unsafe base URL %s', (baseUrl) => {
    expect(() => createStudioApi({ baseUrl })).toThrowError(
      expect.objectContaining({ code: 'INVALID_BASE_URL' }),
    );
  });
});
