# Phase 17 — repeatable MANUAL_UI editorial cycle

Date: 2026-09-07. Phase **17 SCOPE_RECONCILIATION stays OPEN**.
User authorized the bounded workflow proposed in
`output/phase17-opening-20260907/studio-workflow-assessment.md` by saying
“Tamam yapalım.” This is a continuation of active opening/creative repair scope,
not a later phase or a claim that the entire Studio is complete.

## Outcome and acceptance

A persistent manual workflow now connects whole-video outline and visual needs,
portable task export, AI result-file import, working media ingress, existing
rendering, and version-bound feedback. A source need cannot be marked matched
without catalog/task candidates; exact subject/document needs require the stated
source identity. AI fit is explicitly a declaration, not independent semantic
verification. Missing, mismatched and unverified needs or failing editorial checks
block new production. Legacy import cannot bypass an unresolved/stale cycle gate.

The existing canonical catalog is immutable. The adapter reopens its exact media
through Phase17VisualMediaStore; supplementary uploads enter an explicitly
unapproved project working pool with source URL, credit, rights statement, what
is depicted and what it does not establish. No catalog or accepted chapter was
silently replaced. Uploaded files and task assets are hash-bound, bounded and
project-owned. Images and clips up to 32 MB can travel in the task ZIP; longer
originals get sampled previews and are blocked for new selection until a short
reviewed clip is supplied. A ZIP includes actual image/contact previews, small
media, captured source text/PDF, response schema, pack prompt and a snapshot of
an existing rendered cut when available. Old vector instructions are removed
from the task context; accepted chapter context is labelled ancestry only.

Imports check the exact immutable task, parent and current plan; media/source
records cannot be rewritten by the response. Every executed shot needs a visual
need record; every scene needs a declared editorial review. The plan and its
result receipt publish in one BEGIN IMMEDIATE transaction. A failed receipt
rolls back the plan. Competing imports admit one winner. Job creation rechecks
readiness against its captured plan under a write lock. Selected-scene repair
preserves other scene content and the media/source dependencies they use.

The UI accepts the AI's result file: the owner need not hand-edit JSON, shot IDs,
or cue timings. The AI still authors executable direction. This is not a newly
implemented autonomous editor or an independent visual-understanding model.
The response format is versioned; future API transport is not implemented.

| Acceptance scenario | Evidence | Status |
|---|---|---|
| Empty/inadequate media produces explicit needs | Empty-catalog API test and missing/mismatch engine cases | PASS |
| Candidate ingress with bytes and source/rights identity | Working-upload API test; portable exact media bytes | PASS at API boundary |
| Export/import/render without a project-specific production helper | Ordinary API adapters; standard AI-result JSON artifacts; existing renderer | PASS at API boundary |
| Full same flow using live Studio controls | New API launch rejected; old 8006 lacks cycle routes | PENDING |
| Source mismatch/stale/forged metadata rejected | Negative engine/API tests, task and source checks | PASS |
| Scene repair preserves rest | Actual first scene video hash identical; second scene changed | PASS |
| New passage uses same workflow | 28.433-second SECTION_EXCERPT via same import and job endpoints | PASS technically |
| Professional creative quality / owner approval / retention | No such conclusion established | OPEN |

## Actual outputs

Project `prj_f01b4d80f4744c619f9b9567f819ba2f`.
- Opening reimported and rendered: `ejob_296f3b4deb0745cc9abdc5a3d7f3e2ff`, **46.5 seconds**, five
  narration scenes, 13 word-cued shots. The previously delivered positive opening
  remains preserved. It was not expanded into a complete video.
- New later passage: `ejob_41d281db6f3a4ecabed36ef42aa9e969`, **28.433333 seconds**,
  two scenes, seven shots, 1920×1080 at 30 fps. The actual DOE source says 350
  **days** and remaining 15 **days** in an illustrative example. It does not
  establish MW values, a national average or a forecast of blackout days.
- Final selected-scene repair: `ejob_d8afc9ddd8a14f75a0411786c5bb0964`, same measured duration. Visual
  inspection flagged repeated full-paragraph framing and an artificial equipment
  comparison. A feedback record and repair task carried the fix into scene 2.
  Scene 1 `reliability_example` reused the exact video hash
  `sha256:caf8350673aebb3283481800c5c6556d6baedae58703f61d32f493ef78686327`; scene 2's video changed. Speech was unchanged.
- Final video:
  `output/studio-editorial-production/prj_f01b4d80f4744c619f9b9567f819ba2f/ejob_d8afc9ddd8a14f75a0411786c5bb0964/video.mp4`.
- Ready manual review task: `ect_d0249e72ea224492947a58869223f7e8`. Its ZIP contains the current cut,
  actual media/source previews and recorded feedback. It does not approve or
  automatically render a further edit.

Both opening and continuation pass actual decoded-video, source, word-cue,
frame-count and PCM correlation verification. Maximum measured mux offset is
**0.0 ms**. Final section mix: **-17.04 LUFS**, **-0.97 dBTP**; original underscore
**-33.71 LUFS**. These are technical audio measurements, not human listening
approval. Browser playback of the final section reached `ended=true`, with
container duration 28.454333 seconds (AAC container tail); video frames remain
28.433333 seconds. The UI identifies this as a later excerpt, not an opening or
complete film.

## Verification commands and results

- `.venv-studio/Scripts/python.exe -m pytest tests/test_editorial_cycle.py tests/test_documentary_direction.py tests/test_editorial_production.py tests/test_editorial_production_mux.py -q --basetemp=output/phase17-manual-editorial-cycle-20260907/tests-engine-final`: 41 PASS before the final context case; targeted final cycle run 17 PASS. Unique engine/mux cases: **42**.
- With PYTHONPATH including repo and studio-api/src: `pytest studio-api/tests/test_editorial_cycle_api.py studio-api/tests/test_editorial_production_api.py studio-api/tests/test_editorial_treatment.py studio-api/tests/test_openapi_project_contract.py -q --basetemp=output/phase17-manual-editorial-cycle-20260907/tests-api-final`: **17 PASS**.
- UI `npm test -- src/components/EditorialCyclePanel.test.tsx src/components/EditorialProductionPanel.test.tsx src/components/EditorialTreatmentPanel.test.tsx src/api/studioApi.test.ts src/test/generatedClientContract.test.ts`: **44 PASS**.
- UI `npm run build`: typecheck and Vite build PASS.
- OpenAPI `python -m kurgu_studio_api.openapi_export --write`, `npm run generate:client`, `npm run check:client`, `npm run verify:http-boundary`: PASS. OpenAPI hash `8cb75c7f0a1c25e997a0b1d9de202a9cf7a1d1a43b50256e21022d51de82413c`.
- Renderer `npm exec tsc -- --noEmit`: PASS.
- `verify_cycle_outputs.py <job.json> <qa-directory>` with .venv-kokoro: actual opening, initial section and repaired section PASS. Detailed per-shot frames, decoded comparisons and loudness saved in respective QA directories.
- Actual task export, import, feedback and render used FastAPI TestClient against the real project database, then the existing engine/Remotion/FFmpeg path. No new network server or paid provider was launched for these checks.
- Independent reviewer identified the atomicity and legacy bypass defects. Both repaired together and regression-tested; no repeated audit loop.
- Initial API inventory/UI-label failures were corrected; final contract tests pass. One initial temporary task brief misstated DOE units; reading the actual source corrected it before any imported direction/render. The immutable unused task remains history; delivered script uses days.

## Runtime handoff / blocker

Automatic approval review rejected the attempted hidden new local API startup
and UI-origin update with **blocked by policy**. No more detailed reason was
provided. The command was not retried through another launcher. Existing workers
and ignored `studio-ui/.env.local` remain unchanged, targeting **8006**. In-process
API verification is a separate non-listening test mode, not a substitute claim
for live UI acceptance. Actual browser shows the old-version warning and blocks
production. `output/phase17-manual-editorial-cycle-20260907/live-api-handoff.md`
contains user-run steps for activation; it does not execute them.

Remaining limitations: externally authored manual intelligence; declared fit
cannot independently detect a lying/poor AI assessment; limited/reused footage,
480p facility crops and simple procedural audio; no full-video assembly or
professional/retention benchmark; no canonical promotion or human approval.
Accepted 39-second chapter allocations and existing claims remain unchanged.
Other domains, paid API setup and automatic subscribed-AI website use are excluded.

## Changed files and artifacts

Implementation file inventory (local changes, no bulk staging/push):
- `engine/planner/editorial_cycle.py`
- `engine/planner/editorial_production.py`
- `domain-packs/business-tech-v0.3.2/prompts/editorial_cycle.md`
- `shared-schemas/editorial-cycle-result-v1.schema.json`
- `shared-schemas/editorial-documentary-direction-v1.schema.json`
- `shared-schemas/openapi/openapi.json`
- `studio-api/src/kurgu_studio_api/application/studio_workflow_service.py`
- `studio-api/src/kurgu_studio_api/api/v1/dto.py`
- `studio-api/src/kurgu_studio_api/api/v1/studio_workflow.py`
- `studio-ui/src/components/EditorialCyclePanel.tsx`
- `studio-ui/src/components/EditorialProductionPanel.tsx`
- `studio-ui/src/api/studioApi.ts`
- `studio-ui/src/app.css`
- `studio-ui/src/generated/kurgu-api/index.ts`
- `studio-ui/src/generated/kurgu-api/sdk.gen.ts`
- `studio-ui/src/generated/kurgu-api/types.gen.ts`
- `tests/test_editorial_cycle.py`
- `studio-api/tests/test_editorial_cycle_api.py`
- `studio-api/tests/test_openapi_project_contract.py`
- `studio-ui/src/components/EditorialCyclePanel.test.tsx`
- `studio-ui/src/components/EditorialProductionPanel.test.tsx`
- `studio-ui/src/api/studioApi.test.ts`
- `studio-ui/src/test/generatedClientContract.test.ts`

All new receipts and QA artifacts are under
`output/phase17-manual-editorial-cycle-20260907/`: task records, AI result files,
import/job receipts, feedback, scene-preservation proof, three QA directories,
UI verification, handoff note and implementation-file-manifest.json.
Portable task folders live under `output/studio-editorial-cycle/<project>/<task>/`;
videos use the existing `output/studio-editorial-production/` artifact lifecycle.
No source media, cache, fixture or previous output was deleted.

## Next single task

`PHASE17_MANUAL_EDITORIAL_LIVE_UI_ACCEPTANCE`: activate the current local API after
the blocked launch, then complete task download → returned-file import → render →
feedback through Studio controls. Obtain owner review of the complete working
cut without asking them to author baseline editing decisions. Do not start a new
feature slice until this documentation sync is remote-closed. Phase 17 remains OPEN.

## DOCUMENTATION_IMPACT_MATRIX

| Document | Impact | Evidence / reason |
|---|---|---|
| CURRENT_STATE.md | Updated | Implemented workflow, actual jobs, live API activation pending. |
| CHANGELOG.md | Updated | Portable tasks, missing-media gate, atomic import, feedback and section scope. |
| NEXT_ACTIONS.md | Updated | One authoritative live-UI acceptance task; no further feature slice. |
| KNOWN_LIMITATIONS.md | Updated | AI-declared fit, manual external AI, limited media, blocked API launch. |
| PHASE_ACCEPTANCE.md | Updated | Engine/API/render PASS; live cycle still pending; Phase 17 OPEN. |
| QUALITY_BENCHMARKS.md | Updated | Exact mux, scene preservation and measured excerpts, not audience quality. |
| ARCHITECTURE_DECISIONS.md | Updated | Working-cycle records adapt existing catalog and renderer; no canonical promotion. |
| MASTER_ROADMAP.md | Reviewed, unchanged | Multi-domain core + business-tech pack unchanged. No roadmap amendment. |
