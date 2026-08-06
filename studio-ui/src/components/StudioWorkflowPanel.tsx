import { ChangeEvent, FormEvent, useState } from 'react';

import {
  StudioApiError,
  type ProjectReviewDto,
  type SequenceReviewDto,
  type StudioApi,
  type StudioTaskDto,
} from '../api/studioApi';

export interface StudioWorkflowPanelProps { api: StudioApi; projectId: string; }
type TaskFamily = 'research' | 'planner';

function safeError(error: unknown): StudioApiError {
  return error instanceof StudioApiError ? error : new StudioApiError('UNEXPECTED_ERROR', 'The Studio request could not be completed.');
}

function requiredText(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

export function StudioWorkflowPanel({ api, projectId }: StudioWorkflowPanelProps) {
  const [family, setFamily] = useState<TaskFamily>('research');
  const [topic, setTopic] = useState('');
  const [tasks, setTasks] = useState<StudioTaskDto[]>([]);
  const [selectedTask, setSelectedTask] = useState<StudioTaskDto | null>(null);
  const [responseText, setResponseText] = useState('');
  const [review, setReview] = useState<ProjectReviewDto | null>(null);
  const [sequence, setSequence] = useState<SequenceReviewDto | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<StudioApiError | null>(null);

  async function refreshTasks() {
    setBusy(true); setError(null);
    try { setTasks((await api.listStudioTasks(projectId)).items); }
    catch (caught) { setError(safeError(caught)); }
    finally { setBusy(false); }
  }

  async function createTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!topic.trim() || busy) return;
    setBusy(true); setError(null);
    try {
      const task = await api.createStudioTask(projectId, { family, task_type: family === 'research' ? 'source_discovery' : 'outline', backend_mode: 'manual_ui', topic: topic.trim() });
      setTasks((current) => [...current, task]); setSelectedTask(task); setResponseText('');
    } catch (caught) { setError(safeError(caught)); }
    finally { setBusy(false); }
  }

  async function submitResponse() {
    if (!selectedTask || busy) return;
    let payload: Record<string, unknown>;
    try {
      const parsed: unknown = JSON.parse(responseText);
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error();
      payload = parsed as Record<string, unknown>;
    } catch {
      setError(new StudioApiError('REQUEST_VALIDATION_FAILED', 'Paste one JSON object returned by the task.'));
      return;
    }
    setBusy(true); setError(null);
    try {
      const updated = await api.submitStudioTaskResponse(projectId, selectedTask.task_id, { payload });
      setSelectedTask(updated); setTasks((current) => current.map((item) => item.task_id === updated.task_id ? updated : item));
    } catch (caught) { setError(safeError(caught)); }
    finally { setBusy(false); }
  }

  async function taskAction(action: 'approve' | 'repair') {
    if (!selectedTask || busy) return;
    setBusy(true); setError(null);
    try {
      const updated = action === 'approve' ? await api.approveStudioTask(projectId, selectedTask.task_id) : await api.createStudioTaskRepair(projectId, selectedTask.task_id);
      setSelectedTask(updated); setTasks((current) => [...current.filter((item) => item.task_id !== updated.task_id), updated]);
    } catch (caught) { setError(safeError(caught)); }
    finally { setBusy(false); }
  }

  async function copyPrompt() {
    if (!selectedTask || !navigator.clipboard) return;
    await navigator.clipboard.writeText(selectedTask.prompt);
  }

  function downloadContext() {
    if (!selectedTask) return;
    const blob = new Blob([JSON.stringify(selectedTask.context_package, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = 'kurgu-task-context.json'; anchor.click();
    URL.revokeObjectURL(url);
  }

  async function loadResponseFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    if (!file) return;
    try { setResponseText(await file.text()); }
    catch { setError(new StudioApiError('REQUEST_VALIDATION_FAILED', 'The selected response file could not be read.')); }
  }

  async function checkReview() {
    setBusy(true); setError(null); setSequence(null);
    try { setReview(await api.getProjectReview(projectId)); }
    catch (caught) { setError(safeError(caught)); }
    finally { setBusy(false); }
  }

  async function openSequence(sequenceId: string) {
    setBusy(true); setError(null);
    try { setSequence(await api.getSequenceReview(projectId, sequenceId)); }
    catch (caught) { setError(safeError(caught)); }
    finally { setBusy(false); }
  }

  async function decide(action: 'approve' | 'replacement_requested') {
    if (!sequence || busy) return;
    setBusy(true); setError(null);
    try {
      const sequenceId = requiredText(sequence.sequence.executable_sequence_id);
      if (!sequenceId) throw new StudioApiError('API_ERROR', 'The review sequence is invalid.');
      const decision = await api.decideSequenceReview(projectId, sequenceId, action === 'approve' ? { action, replacement_kind: null } : { action, replacement_kind: 'asset_change' });
      setSequence({ ...sequence, decision });
    } catch (caught) { setError(safeError(caught)); }
    finally { setBusy(false); }
  }

  return <section className="workflow-grid" aria-label="Studio workflow">
    <section className="panel workflow-panel">
      <p className="section-kicker">Manual LLM</p><h2>Task inbox</h2>
      <p className="workflow-copy">Create an API-bound task, copy its prompt into your AI tool, then paste its JSON result here.</p>
      <form onSubmit={createTask}>
        <label htmlFor="task-family">Task family</label>
        <select id="task-family" value={family} onChange={(event) => setFamily(event.currentTarget.value as TaskFamily)}><option value="research">Research discovery</option><option value="planner">Planner outline</option></select>
        <label htmlFor="task-topic">Topic</label>
        <input id="task-topic" value={topic} onChange={(event) => setTopic(event.currentTarget.value)} placeholder="e.g. The economics of AI chips" maxLength={500} required />
        <button type="submit" disabled={busy || !topic.trim()}>Create Manual LLM task</button>
      </form>
      <button className="secondary-button" type="button" onClick={() => void refreshTasks()} disabled={busy}>Refresh task inbox</button>
      {tasks.length > 0 ? <ul className="task-list">{tasks.map((task) => <li key={task.task_id}><button type="button" className="task-select" onClick={() => { setSelectedTask(task); setResponseText(''); }}><strong>{task.task_type}</strong><span>{task.status}</span></button></li>)}</ul> : null}
    </section>
    <section className="panel workflow-panel" aria-live="polite">
      <p className="section-kicker">Task detail</p><h2>Validate and approve</h2>
      {!selectedTask ? <p className="empty-state">Select or create a task to view its prompt and validation state.</p> : <div className="workflow-detail">
        <p><strong>{selectedTask.task_type}</strong> · {selectedTask.status}</p>
        <label htmlFor="task-prompt">Prompt to copy</label><textarea id="task-prompt" readOnly value={selectedTask.prompt} /><div className="decision-actions"><button type="button" className="secondary-button" onClick={() => void copyPrompt()}>Copy prompt</button><button type="button" className="secondary-button" onClick={downloadContext}>Download context package</button><a className="external-link" href="https://chatgpt.com/" target="_blank" rel="noreferrer">Open web AI</a></div>
        {selectedTask.status === 'waiting' ? <><label htmlFor="task-response">Paste returned JSON</label><textarea id="task-response" value={responseText} onChange={(event) => setResponseText(event.currentTarget.value)} placeholder="Paste the structured result from the task" /><label htmlFor="task-response-file">Or upload returned JSON</label><input id="task-response-file" type="file" accept="application/json" onChange={(event) => void loadResponseFile(event)} /><button type="button" onClick={() => void submitResponse()} disabled={busy || !responseText.trim()}>Validate response</button></> : null}
        {selectedTask.status === 'repair_required' ? <><p className="validation-warning">{selectedTask.validation_issues.join(', ')}</p><button type="button" onClick={() => void taskAction('repair')} disabled={busy}>Create repair task</button></> : null}
        {selectedTask.status === 'valid' ? <button type="button" onClick={() => void taskAction('approve')} disabled={busy}>Approve valid result</button> : null}
      </div>}
    </section>
    <section className="panel workflow-panel review-panel">
      <p className="section-kicker">Editorial review</p><h2>Sequence decisions</h2>
      <p className="workflow-copy">Review is available only after the engine publishes a canonical Phase 12/Phase 3 snapshot. Rendering remains a later-phase capability.</p>
      <button type="button" onClick={() => void checkReview()} disabled={busy}>Check review availability</button>
      {review?.status === 'unavailable' ? <p className="empty-state">No executable review snapshot is available yet.</p> : null}
      {review?.status === 'available' ? <div className="review-list">{review.sequence_ids.map((sequenceId) => <button type="button" key={sequenceId} className="secondary-button" onClick={() => void openSequence(sequenceId)} disabled={busy}>Review sequence</button>)}</div> : null}
      {sequence ? <div className="workflow-detail"><p><strong>Video EDL:</strong> {requiredText(sequence.edl_binding.video_edl_hash)}</p><p><strong>Audio EDL:</strong> {requiredText(sequence.edl_binding.audio_edl_hash)}</p>{sequence.decision ? <p className="validation-warning">Decision locked: {requiredText(sequence.decision.action)}</p> : <div className="decision-actions"><button type="button" onClick={() => void decide('approve')} disabled={busy}>Approve sequence</button><button type="button" className="secondary-button" onClick={() => void decide('replacement_requested')} disabled={busy}>Request asset change</button></div>}</div> : null}
    </section>
    {error ? <div className="error-state workflow-error" role="alert"><strong>{error.code}</strong><span>{error.message}</span></div> : null}
  </section>;
}
