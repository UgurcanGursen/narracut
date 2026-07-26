import { createStudioApi } from './api/studioApi';
import { ProjectConsole } from './components/ProjectConsole';

const studioApi = createStudioApi();

export function App() {
  return (
    <main className="app-shell">
      <header className="hero">
        <p className="eyebrow">Kurgu Engine · Phase 1</p>
        <h1>Studio project console</h1>
        <p className="hero-copy">
          Create a contract-valid project, then inspect its canonical status
          and current artifact catalog.
        </p>
      </header>
      <ProjectConsole api={studioApi} />
    </main>
  );
}
