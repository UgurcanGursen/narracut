import { createStudioApi } from './api/studioApi';
import { ProjectConsole } from './components/ProjectConsole';

const studioApi = createStudioApi();

export function App() {
  return (
    <main className="app-shell">
      <header className="hero">
        <p className="eyebrow">Kurgu Engine · Phase 1</p>
        <h1>Studio workflow console</h1>
        <p className="hero-copy">
          Create or reopen a contract-valid project, then manage manual tasks
          and inspect its read-only editorial review state.
        </p>
      </header>
      <ProjectConsole api={studioApi} />
    </main>
  );
}
