import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { createStudioApi } from '../api/studioApi';
import { ProjectConsole } from './ProjectConsole';
import {
  coreCreateResponse,
  coreStatusResponse,
  emptyArtifactsResponse,
  installRelativeRequestSupport,
  jsonResponse,
} from '../test/fixtures';

describe('ProjectConsole', () => {
  it('runs React through the real facade and generated client', async () => {
    installRelativeRequestSupport();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(coreCreateResponse, 201))
      .mockResolvedValueOnce(jsonResponse(coreStatusResponse))
      .mockResolvedValueOnce(jsonResponse(emptyArtifactsResponse));
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();

    render(<ProjectConsole api={createStudioApi()} />);

    expect(screen.getByLabelText('Project title')).toBeInTheDocument();
    expect(screen.getByLabelText('Domain selection')).toHaveValue('core_only');
    expect(
      screen.getByText(/persistence boundary returned by the API/i),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create project' })).toBeDisabled();

    await user.type(screen.getByLabelText('Project title'), 'Core project');
    await user.click(screen.getByRole('button', { name: 'Create project' }));

    expect(await screen.findByText(coreCreateResponse.project.project_id)).toBeInTheDocument();
    expect(screen.getAllByText('ready')).toHaveLength(2);
    expect(screen.getByText('process_lifetime')).toBeInTheDocument();
    expect(
      screen.getByText('No artifacts are registered for this project.'),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('maps the Business & Technology choice to its fixed request', async () => {
    installRelativeRequestSupport();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(coreCreateResponse, 201))
      .mockResolvedValueOnce(jsonResponse(coreStatusResponse))
      .mockResolvedValueOnce(jsonResponse(emptyArtifactsResponse));
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();

    render(<ProjectConsole api={createStudioApi()} />);
    await user.type(screen.getByLabelText('Project title'), 'Business project');
    await user.selectOptions(
      screen.getByLabelText('Domain selection'),
      'business_tech',
    );
    await user.click(screen.getByRole('button', { name: 'Create project' }));
    await screen.findByText(coreCreateResponse.project.project_id);

    const call = fetchMock.mock.calls[0];
    const request = call?.[0];
    if (!(request instanceof Request)) {
      throw new Error('Expected generated client request.');
    }
    expect(JSON.parse(await request.clone().text()).domain).toEqual({
      resolution_mode: 'domain_pack',
      domain_id: 'business-tech',
      domain_pack_version: '0.1.0',
      profile: {
        profile_id: 'dpf_business_default',
        enabled_extensions: [],
        policy_overrides: {},
      },
    });
  });

  it('shows a sanitized structured server error', async () => {
    installRelativeRequestSupport();
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(
        {
          error: {
            code: 'DOMAIN_UNKNOWN',
            message: 'private registry detail',
            issues: [],
          },
        },
        422,
      ),
    );
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();

    render(<ProjectConsole api={createStudioApi()} />);
    await user.type(screen.getByLabelText('Project title'), 'Rejected');
    await user.click(screen.getByRole('button', { name: 'Create project' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('DOMAIN_UNKNOWN');
    expect(screen.getByRole('alert')).toHaveTextContent(
      'The requested domain or version is not available.',
    );
    expect(screen.getByRole('alert')).not.toHaveTextContent('private registry');
  });

  it('prevents duplicate submit while the first create is pending', async () => {
    installRelativeRequestSupport();
    let release: ((value: Response) => void) | undefined;
    const pending = new Promise<Response>((resolve) => {
      release = resolve;
    });
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() => pending)
      .mockResolvedValueOnce(jsonResponse(coreStatusResponse))
      .mockResolvedValueOnce(jsonResponse(emptyArtifactsResponse));
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();

    render(<ProjectConsole api={createStudioApi()} />);
    await user.type(screen.getByLabelText('Project title'), 'Single submit');
    const submit = screen.getByRole('button', { name: 'Create project' });
    await user.click(submit);

    expect(screen.getByRole('button', { name: 'Creating project…' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Creating project…' }));
    expect(fetchMock).toHaveBeenCalledTimes(1);

    release?.(jsonResponse(coreCreateResponse, 201));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
  });

  it('does not expose unsupported fields, domains, or future controls', () => {
    render(<ProjectConsole api={createStudioApi()} />);

    expect(screen.queryByLabelText(/project id/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/path|workspace|output/i)).not.toBeInTheDocument();
    expect(
      screen.queryByRole('option', { name: /true crime/i }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /render/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/progress/i)).not.toBeInTheDocument();
  });
});
