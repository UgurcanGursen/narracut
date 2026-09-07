# Phase 17 — Studio API activation, 2026-09-07

## Outcome and scope

The owner's explicit “başlat o zaman” request authorized starting the updated
local backend. Uvicorn PID 6428 serves localhost:8007. Vite localhost:5173 uses
that backend through the ignored `studio-ui/.env.local` setting. Existing API8006
was preserved. No production code, paid provider or credential was changed.
Phase 17 SCOPE_RECONCILIATION remains OPEN.

## Acceptance and verification

Activation acceptance PASS: `/health` reports `ok`; a real request through the
Vite proxy to the saved project's `/editorial-cycle` endpoint reports
`READY_FOR_WORKING_RENDER`, stale false and five task records. Browser tab 8
loads the saved project and its production dossier. Render and task preparation
buttons are enabled; old-API warning count is zero. Existing task ZIP link points
to `ect_d0249e72ea224492947a58869223f7e8`.

Commands executed: hidden `Start-Process` with the repository Python, uvicorn
`kurgu_studio_api.app:create_app --factory --host 127.0.0.1 --port 8007`;
`Set-Content studio-ui/.env.local` for the proxy; `Invoke-RestMethod` against
direct health and direct/proxied editorial-cycle endpoints; real browser project
selection and DOM control checks. All activation checks passed. No new render
or regression test run was needed for this process/configuration activation.

Artifacts: `output/phase17-manual-editorial-cycle-20260907/api-8007.stdout.log`,
`api-8007.stderr.log`, and `api-activation/verification.json` in that directory.
Documentation remote verification is recorded in `api-activation/documentation-sync.json`.

## Limits and next task

Full live download/import/render/feedback acceptance remains pending. The current
28.433333-second cut is a later section, not the opening or a complete video.
Startup does not establish creative quality or user approval. No permanent
startup service was installed; process availability is local to this run.
Single next task: `PHASE17_MANUAL_EDITORIAL_LIVE_UI_ACCEPTANCE`.

## Changed files and DOCUMENTATION_IMPACT_MATRIX

| File | Impact |
| --- | --- |
| studio-ui/.env.local | Ignored local proxy changed from 8006 to 8007 |
| docs/CURRENT_STATE.md | Current runtime activation and verified status |
| docs/CHANGELOG.md | Activation checkpoint |
| docs/NEXT_ACTIONS.md | Completed activation removed from remaining work; same single task |
| docs/KNOWN_LIMITATIONS.md | Previous startup blocker resolved; live-cycle gap retained |
| docs/PHASE_ACCEPTANCE.md | Activation passes; full Phase 17 remains open |
| docs/baseline/phase17_studio_api_activation_20260907.md | This bounded verification report |
| docs/QUALITY_BENCHMARKS.md | Reviewed, unchanged; no new creative benchmark |
| docs/ARCHITECTURE_DECISIONS.md | Reviewed, unchanged; no architecture change |
| docs/MASTER_ROADMAP.md | Reviewed, unchanged; no roadmap or phase change |
