# Phase 13 REPLAY Preview Implementation Acceptance Audit

Date: 2026-08-06  
Scope: commit `ca055bd` only; PREVIEW/REPLAY control plane and UI boundary.  
Decision: **FIX_REQUIRED**

## Evidence run

`studio-api/tests/test_phase13_studio_workflow.py`, the Studio OpenAPI/factory
contract tests, and the current Studio API suite passed (`64 passed`). React
generated-client, type, test and HTTP-boundary gates also passed. These gates
prove route and local state mechanics, not canonical renderer handoff.

## Findings

### P13-PA-001 — BLOCKER: render-input persistence is not verified

`SQLiteProjectRepository.put_render_input()` writes arbitrary opaque
`video_edl_bytes`, `audio_edl_bytes`, `render_props_bytes` and caller-provided
IDs/hashes. It does not load the Phase 3 EDL bytes, derive/check their IDs and
hashes, load canonical `RenderProps`, verify snapshot identity, or bind the
Phase 12 bundle row before persistence. `PersistedRenderInputResolver` then
returns that record to job admission. This violates the accepted canonical
handoff contract's “verified before persistence” boundary; a forged package
can become a persisted attempted render input and fail only after a job starts.

### P13-PA-002 — MAJOR: no canonical two-sequence API proof

The success test injects a hand-made `RenderInputSnapshotRecord` with `{}`
bytes and replaces the real Phase 4 executor with `_SuccessfulPreviewExecutor`.
It proves only the control-plane shape. It does not prove the required two
Phase 12/3 sequences, byte-identical reopen, exact EDL/bundle binding, or an
actual `run_headless_preview` terminal receipt/manifest through Studio.

### P13-PA-003 — MAJOR: delivery descriptor boundary is incomplete

`InMemoryPreviewDelivery` stores whatever manifest/frame mapping it receives;
it neither validates the manifest's declared-frame identity set nor records the
required descriptor metadata/expiry. A fake executor can therefore make a
frame available without a canonical manifest binding. This does not meet the
safe-delivery acceptance gate.

### P13-PA-004 — MAJOR: UI does not consume preview evidence

The generated client exposes preview media/event endpoints, but
`StudioWorkflowPanel` only submits once and prints terminal state. It neither
polls/subscribes to progress nor renders server-declared frames. The stated UI
acceptance boundary is therefore incomplete.

## Required bounded repair

Keep the implementation PREVIEW-only/REPLAY-only. Add a server-owned canonical
two-sequence fixture handoff builder; validate every snapshot before SQLite
persistence; make delivery derive allowed frame indexes from the verified
manifest; and make the UI use generated API methods to show job updates and
declared frames. Re-run the actual Phase 4 fixture through the Studio API.
No Phase 14 lifecycle, FULL render, provider, generic queue/retry or storage
accounting work is authorized by this audit.
