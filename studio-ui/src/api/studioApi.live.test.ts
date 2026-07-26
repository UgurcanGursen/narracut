import { describe, expect, it } from 'vitest';

import { createStudioApi } from './studioApi';
import { requireLiveTestBaseUrl } from '../test/liveTestBaseUrl';

describe('StudioApi live FastAPI smoke', () => {
  it('creates and reads a real process-lifetime core project', async () => {
    const baseUrl = process.env.KURGU_STUDIO_API_BASE_URL;
    if (!baseUrl) {
      throw new Error('KURGU_STUDIO_API_BASE_URL is required for the live test.');
    }
    const api = createStudioApi({ baseUrl: requireLiveTestBaseUrl(baseUrl) });
    const created = await api.createProject({
      title: 'Live generated client smoke',
      domain: { resolution_mode: 'core_only' },
    });
    const status = await api.getProjectStatus(created.project.project_id);
    const artifacts = await api.listProjectArtifacts(
      created.project.project_id,
    );

    expect(created.persistence_scope).toBe('process_lifetime');
    expect(status.project_id).toBe(created.project.project_id);
    expect(status.status).toBe(created.project.status);
    expect(status.persistence_scope).toBe('process_lifetime');
    expect(artifacts.project_id).toBe(created.project.project_id);
    expect(artifacts.count).toBe(0);
    expect(artifacts.items).toEqual([]);
    expect(artifacts.persistence_scope).toBe('process_lifetime');
  });
});
