# Phase 17 — Joint narration and visual treatment workbench

Date: 2026-09-06. Project: `prj_f01b4d80f4744c619f9b9567f819ba2f`.
Phase: **17 SCOPE_RECONCILIATION, OPEN**.
Result: **PREPRODUCTION_DRAFT_WORKBENCH_AVAILABLE**.

## Product outcome and limits

The owner rejected the prior 39-second cut for weak editing and narration/visual
relevance. That feedback is decisive creative evidence. Successful audio-start
measurements and playback do not overturn it. The previous MP4 is retained.

The actual Studio project now holds six jointly authored narration/visual scenes,
covering all ten current beats once, with 21 ordered word-cued visual events.
Proposed duration is 83–109 seconds; this is an estimate, not recorded audio or
a rendered video. The agent authored this particular plan; the Studio does not
automatically invent these creative decisions. The same input can be produced
through the MANUAL_UI task-package download/import workflow.

Latest treatment: `etreat_33231dd0a14a464bbd02eb20`.
Hash: `sha256:33231dd0a14a464bbd02eb208b9017b8eedd39a28984d9fc9849e350cb356ca9`.
Three immutable versions exist, including the final real-UI save/reopen check.
The invalid QA narration was rejected and is absent from the stored draft.

The story follows one facility's demand, delivery through its local grid, the
qualified DOE 350/15-day illustration, backup limitations, EIA scenario comparison
and a qualified ERCOT price consequence returning to the opening delivery question.
Directions distinguish demand requests from measured facility consumption, days of
coverage from an invented outage calendar, and scenario deltas from certain prices.

## Bounded scope and acceptance

In scope: evidence-bound joint preproduction planning, manual AI portability,
revision persistence, editable project UI, explicit validation failures.
Out of this package: canonical duration migration, actual voice/timing publication,
rendered object actions, sound design, automated shot selection, production approval,
scene regeneration, other domain packs and commercial APIs.

| Criterion | Result |
|---|---|
| Actual project data, no replacement demo project | PASS |
| Every current beat covered once with current chapter/evidence parents | PASS |
| Narration phrase occurrence and ordered event matching | PASS |
| Repeated object state continuity across scenes | PASS |
| Draft duration can exceed old chapter allocation without changing it | PASS |
| Persistent hash-checked versions and concurrent-edit rejection | PASS |
| Chapter activation makes old draft stale and prevents resave | PASS |
| Imported AI task includes captured sources and approved research payloads | PASS |
| UI edits/save, visible errors, save lock and project-switch ownership | PASS |
| Automatic semantic/creative quality validation | NOT IMPLEMENTED |
| This treatment executed through Director/timing/renderer | NOT IMPLEMENTED |
| New narration or finished video | NOT PRODUCED |
| Human creative/listening/timing approval | NOT CLAIMED |

## Commands and verification

From repo root, Python checks use `.venv-studio/Scripts/python.exe` with
`sys.path[:0]=['studio-api/src','.']` before invoking pytest.

- `pytest -q studio-api/tests/test_editorial_treatment.py studio-api/tests/test_chapter_revision_activation.py studio-api/tests/test_openapi_project_contract.py --basetemp=.codex-test-temp/editorial-treatment-repaired-20260906`: **20 passed**. One existing Starlette TestClient deprecation warning.
- From `studio-ui`, `npm test -- src/components/EditorialTreatmentPanel.test.tsx src/components/ChapterRevisionPanel.test.tsx src/components/ProjectConsole.test.tsx src/api/studioApi.test.ts src/test/generatedClientContract.test.ts`: **38 passed** before the final HTTP-error-message regression addition.
- Final focused rerun, `npm test -- src/components/EditorialTreatmentPanel.test.tsx src/api/studioApi.test.ts`: **29 passed**, including that added regression. 39 distinct UI tests exercised across these runs.
- `npm run build`: **PASS**, TypeScript checks and Vite production build.
- `npm run check:client`: **PASS**, generated client matches frozen OpenAPI bytes; A/B regeneration identical.
- `npm run verify:http-boundary`: **PASS**.
- OpenAPI export/write and `npm run generate:client`: **PASS**. OpenAPI hash `b92e73f04d4e3bce0dede64754808410dcbd9667b6699c4a401f3dbd52f5b6ce`.
- Real localhost Studio QA: opened saved project, saw six scenes, selected scene 2,
  rejected an unmatched narration with a specific Turkish message, restored original
  narration, saved and reopened immutable version. Screenshot visually inspected.
- One independent final audit found async UI overwrite and cross-scene continuity
  bugs; both repaired with targeted regression tests. Real browser QA additionally
  found missing frontend error-code mapping; repaired and rerun.

Earlier failures were actionable: the test fixture used the older pack without
the new prompt, frozen OpenAPI inventory/hash needed the new endpoints, and two
strict-TypeScript test array accesses required explicit non-null assertions.
Final checks above passed. No full repository suite or new render was run for
this preproduction-only change.

## Changed files and artifacts

Implementation files touched in this package (shared files contain earlier work):

- `engine/planner/editorial_treatment.py`
- `domain-packs/business-tech-v0.3.2/prompts/editorial_treatment.md`
- `studio-api/src/kurgu_studio_api/application/studio_workflow_service.py`
- `studio-api/src/kurgu_studio_api/api/errors.py`
- `studio-api/src/kurgu_studio_api/api/v1/dto.py`
- `studio-api/src/kurgu_studio_api/api/v1/studio_workflow.py`
- `studio-api/tests/test_editorial_treatment.py`
- `studio-api/tests/test_openapi_project_contract.py`
- `shared-schemas/openapi/openapi.json`
- `studio-ui/src/App.tsx`
- `studio-ui/src/api/studioApi.ts`
- `studio-ui/src/api/studioApi.test.ts`
- `studio-ui/src/components/ProjectConsole.tsx`
- `studio-ui/src/components/EditorialTreatmentPanel.tsx`
- `studio-ui/src/components/EditorialTreatmentPanel.test.tsx`
- `studio-ui/src/components/editorial-treatment.css`
- `studio-ui/src/generated/kurgu-api/index.ts`
- `studio-ui/src/generated/kurgu-api/sdk.gen.ts`
- `studio-ui/src/generated/kurgu-api/types.gen.ts`
- `studio-ui/src/test/generatedClientContract.test.ts`

Local artifacts under `output/phase17-editorial-treatment-20260906/`:

- `treatment-draft.json`: authored six-scene input.
- `manual-ui-task-package.json`: exported current project context, seven captured
  source records, five approved research responses and business-tech prompt.
- `studio-publication.json`: actual latest persisted project record after UI QA.
- `prepare_project_treatment.py`: input authoring/publishing helper, not a renderer.
- `implementation-file-manifest.json`: current touched-file hashes; not a claim of
  clean implementation commit isolation.
- `documentation-sync.json`: separate documentation commit/push evidence after sync.

Studio URL: `http://127.0.0.1:5173/#editorial-treatment`.
Project data lives in the existing local Studio/planner SQLite stores. A cold UI
reload requires reopening the saved project. No API keys or paid calls were used.

## Remaining work and single next task

`PHASE17_TREATMENT_TO_STUDIO_EXECUTION`: connect this treatment to the existing
Studio production path, with explicit duration/lineage migration, local narration,
measured word timing, persistent-object visual action execution, and a project
review output. Validate the delivery-constraint scene against its spoken verbs
and viewer inference; do not fill unsupported actions with generic stock or count
these draft descriptions as a professional edit. Preserve source qualifications
and require actual owner judgment for creative/timing acceptance.

The full professional Studio goal is not complete. The present boundary is a
working joint preproduction editor, with production execution still outstanding.

## DOCUMENTATION_IMPACT_MATRIX

| Document | Impact | Reason |
|---|---|---|
| CURRENT_STATE.md | Updated | Actual draft workbench and user rejection of the old cut. |
| CHANGELOG.md | Updated | Joint planning, persistence, API/UI and targeted validation. |
| NEXT_ACTIONS.md | Updated | One authoritative treatment-to-execution task. |
| KNOWN_LIMITATIONS.md | Updated | No treatment execution bridge, timing, new video or semantic approval. |
| PHASE_ACCEPTANCE.md | Updated | Bounded draft-workbench criteria only; Phase 17 remains open. |
| QUALITY_BENCHMARKS.md | Updated | Mechanical timing success did not satisfy the user’s creative requirements. |
| ARCHITECTURE_DECISIONS.md | Reviewed, unchanged | Existing domain-neutral core / domain-pack architecture retained. |
| MASTER_ROADMAP.md | Reviewed, unchanged | No roadmap or phase closure change authorized or claimed. |
