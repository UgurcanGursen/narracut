# Phase 13 Preview Audit Repair Authorization

Date: 2026-08-06
Decision: **AUTHORIZE one bounded repair package**

## Authorized purpose

Close only `P13-PA-001` through `P13-PA-004` from
`phase13_replay_preview_implementation_acceptance_audit.md`.

## Authorized implementation boundary

- `studio-api/src/kurgu_studio_api/application/models.py`
- `studio-api/src/kurgu_studio_api/application/ports.py`
- `studio-api/src/kurgu_studio_api/application/studio_workflow_service.py`
- `studio-api/src/kurgu_studio_api/infrastructure/sqlite_project_repository.py`
- `studio-api/src/kurgu_studio_api/infrastructure/preview_adapters.py`
- `studio-api/src/kurgu_studio_api/infrastructure/runtime.py`
- Studio preview API DTO/routes/errors, OpenAPI artifact and generated client
- `studio-ui/src/api/studioApi.ts`, `StudioWorkflowPanel.tsx` and focused tests

The repair must add a server-owned canonical two-sequence REPLAY handoff
fixture, validate EDL/RenderProps/snapshot identity before persistence, derive
delivery permissions from the verified manifest, and use only generated HTTP
client methods for event/frame display.

## Excluded

Phase 14 durable lifecycle/storage/GC, FULL render, provider/media transport,
browser automation, generic queue/retry, source acquisition, cache, quota and
artifact registry changes are excluded.

## Acceptance evidence required

1. Two canonical project-bound snapshots persist/reopen byte-identically and
   invoke the actual Phase 4 REPLAY preview path through Studio.
2. Forged bytes/hashes/lineage and stale review binding fail before job
   admission; no fake executor proves the success path.
3. Delivery permits only manifest-declared frame indexes and becomes explicitly
   unavailable after restart.
4. UI polls safe job state and renders only server-delivered declared frames.
5. Studio API, Phase 4, Phase 12, OpenAPI/generated-client and UI boundary
   gates pass. Phase 13 remains MASTER OPEN until Phase 14 handoff.
