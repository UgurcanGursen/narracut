import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import {
  createProject,
  getProjectStatus,
  listProjectArtifacts,
} from '../generated/kurgu-api';
import type {
  ProjectCreateRequestDto,
  ProjectCreateResponseDto,
  ProjectStatusResponseDto,
  ProjectArtifactsResponseDto,
  ErrorEnvelopeDto,
} from '../generated/kurgu-api/types.gen';

const exactOperations = {
  createProject,
  getProjectStatus,
  listProjectArtifacts,
};

describe('generated client contract', () => {
  it('exports the exact three project operations', () => {
    expect(Object.keys(exactOperations).sort()).toEqual([
      'createProject',
      'getProjectStatus',
      'listProjectArtifacts',
    ]);
    expect(Object.values(exactOperations).every((value) => typeof value === 'function')).toBe(true);
  });

  it('preserves the discriminated request and explicit response/error types', () => {
    const core = {
      title: 'Core project',
      domain: { resolution_mode: 'core_only' },
    } satisfies ProjectCreateRequestDto;
    const business = {
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
    } satisfies ProjectCreateRequestDto;
    const typedSurface:
      | ProjectCreateResponseDto
      | ProjectStatusResponseDto
      | ProjectArtifactsResponseDto
      | ErrorEnvelopeDto
      | undefined = undefined;

    expect(core.domain.resolution_mode).toBe('core_only');
    expect(business.domain.resolution_mode).toBe('domain_pack');
    expect(typedSurface).toBeUndefined();
  });

  it('is tied to the frozen committed OpenAPI bytes', () => {
    const openApi = readFileSync(
      join(
        process.cwd(),
        '..',
        'shared-schemas',
        'openapi',
        'openapi.json',
      ),
    );
    expect(createHash('sha256').update(openApi).digest('hex')).toBe(
      'c64d9713dbaa7e7afbd1ad5eb07faf1da404e5871466a8012ddb5e3a00f05128',
    );
  });
});
