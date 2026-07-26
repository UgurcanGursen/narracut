import { FormEvent, useState } from 'react';

import {
  StudioApiError,
  type ProjectArtifactsResponseDto,
  type ProjectCreateRequestDto,
  type ProjectCreateResponseDto,
  type ProjectStatusResponseDto,
  type StudioApi,
} from '../api/studioApi';

type DomainChoice = 'core_only' | 'business_tech';

interface ProjectResult {
  created: ProjectCreateResponseDto;
  status: ProjectStatusResponseDto;
  artifacts: ProjectArtifactsResponseDto;
}

export interface ProjectConsoleProps {
  api: StudioApi;
}

function domainRequest(
  choice: DomainChoice,
): ProjectCreateRequestDto['domain'] {
  switch (choice) {
    case 'core_only':
      return { resolution_mode: 'core_only' };
    case 'business_tech':
      return {
        resolution_mode: 'domain_pack',
        domain_id: 'business-tech',
        domain_pack_version: '0.1.0',
        profile: {
          profile_id: 'dpf_business_default',
          enabled_extensions: [],
          policy_overrides: {},
        },
      };
  }
}

function display(value: string | null | undefined): string {
  return value ?? 'Not provided';
}

export function ProjectConsole({ api }: ProjectConsoleProps) {
  const [title, setTitle] = useState('');
  const [domainChoice, setDomainChoice] =
    useState<DomainChoice>('core_only');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ProjectResult | null>(null);
  const [error, setError] = useState<StudioApiError | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedTitle = title.trim();
    if (!normalizedTitle || busy) {
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const created = await api.createProject({
        title: normalizedTitle,
        domain: domainRequest(domainChoice),
      });
      const projectId = created.project.project_id;
      const [status, artifacts] = await Promise.all([
        api.getProjectStatus(projectId),
        api.listProjectArtifacts(projectId),
      ]);
      setResult({ created, status, artifacts });
    } catch (caught) {
      setError(
        caught instanceof StudioApiError
          ? caught
          : new StudioApiError(
              'UNEXPECTED_ERROR',
              'The project request could not be completed.',
            ),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="console-grid" aria-label="Project console">
      <section className="panel form-panel">
        <div className="section-heading">
          <p className="section-kicker">Project contract</p>
          <h2>Create a project</h2>
          <p>
            Choose one of the currently eligible domain configurations. The
            server remains the contract source of truth.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <label htmlFor="project-title">Project title</label>
          <input
            id="project-title"
            name="project-title"
            value={title}
            maxLength={240}
            onChange={(event) => setTitle(event.currentTarget.value)}
            placeholder="e.g. The infrastructure behind AI chips"
            autoComplete="off"
            required
          />

          <label htmlFor="domain-choice">Domain selection</label>
          <select
            id="domain-choice"
            name="domain-choice"
            value={domainChoice}
            onChange={(event) =>
              setDomainChoice(event.currentTarget.value as DomainChoice)
            }
          >
            <option value="core_only">Core only</option>
            <option value="business_tech">Business &amp; Technology</option>
          </select>

          <button type="submit" disabled={busy || title.trim().length === 0}>
            {busy ? 'Creating project…' : 'Create project'}
          </button>
        </form>

        <aside className="persistence-note" aria-label="Persistence limitation">
          <strong>Process-lifetime storage</strong>
          <p>
            Project data is stored only for the lifetime of the current API
            process. Restarting the API clears this project.
          </p>
        </aside>
      </section>

      <section className="panel result-panel" aria-live="polite">
        <div className="section-heading">
          <p className="section-kicker">Canonical response</p>
          <h2>Project state</h2>
          <p>Status and artifacts are read back from their API endpoints.</p>
        </div>

        {!busy && !error && !result ? (
          <div className="empty-state">
            Create a project to inspect its canonical state.
          </div>
        ) : null}

        {busy ? (
          <div className="busy-state" role="status">
            Creating and reading the project…
          </div>
        ) : null}

        {error ? (
          <div className="error-state" role="alert">
            <strong>{error.code}</strong>
            <span>{error.message}</span>
          </div>
        ) : null}

        {result ? (
          <div className="result-stack">
            <dl className="facts">
              <div>
                <dt>Project ID</dt>
                <dd>{result.created.project.project_id}</dd>
              </div>
              <div>
                <dt>Canonical status</dt>
                <dd>{result.created.project.status}</dd>
              </div>
              <div>
                <dt>Status endpoint</dt>
                <dd>{result.status.status}</dd>
              </div>
              <div>
                <dt>Version</dt>
                <dd>{result.status.version}</dd>
              </div>
              <div>
                <dt>Domain mode</dt>
                <dd>{result.status.domain.resolution_mode}</dd>
              </div>
              <div>
                <dt>Domain ID</dt>
                <dd>{display(result.status.domain.domain_id)}</dd>
              </div>
              <div>
                <dt>Pack version</dt>
                <dd>{display(result.status.domain.domain_pack_version)}</dd>
              </div>
              <div>
                <dt>Profile ID</dt>
                <dd>{display(result.status.domain.profile_id)}</dd>
              </div>
              <div>
                <dt>Policy snapshot</dt>
                <dd>{result.status.domain.policy_snapshot_id}</dd>
              </div>
              <div>
                <dt>Persistence scope</dt>
                <dd>{result.status.persistence_scope}</dd>
              </div>
            </dl>

            <section className="artifact-section" aria-labelledby="artifacts-title">
              <div className="artifact-heading">
                <h3 id="artifacts-title">Artifacts</h3>
                <span>{result.artifacts.count}</span>
              </div>
              {result.artifacts.items.length === 0 ? (
                <p className="empty-state">
                  No artifacts are registered for this project.
                </p>
              ) : (
                <ul className="artifact-list">
                  {result.artifacts.items.map((artifact) => (
                    <li key={artifact.artifact_id}>
                      <strong>{artifact.artifact_id}</strong>
                      <span>
                        {artifact.artifact_type} · {artifact.status}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        ) : null}
      </section>
    </section>
  );
}
