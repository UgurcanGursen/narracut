# Phase 17 — Studio chapter revision acceptance, 2026-09-05

Status: LOCAL_IMPLEMENTATION_AND_LIVE_ACTIVATION_VERIFIED. Phase 17 remains open.

## Delivered behavior and scope

Studio now shows accepted chapters and beat durations in the “Hikâye ve
bölümler” workspace. The operator can edit chapter direction, beat intent,
duration and viewer continuity, persist a proposal, compare it with the active
version, and activate it with a named approval. The backend publishes the
chapter and beats together through existing MANUAL_UI planner contracts.
History remains readable. Active planning excludes the superseded branch.
Old task response/approval and final-render execution reject obsolete ancestry.
Domain language, policy snapshots, claim/evidence links and total duration are
retained; no new domain pack or commercial API integration was added.

Scope excludes new TTS, word timing, renderer templates, completed video,
chapter insertion/deletion, total-duration changes and automatic professional
creative approval. This is a working chapter editor, not a completed studio.

## Live acceptance

- Project: `prj_f01b4d80f4744c619f9b9567f819ba2f`.
- Existing source-qualified September 4 proposal registered through local HTTP.
- Browser UI showed before/after and activated `crev_0880cd0230a76af43ba2`.
- Active chapter: `chap_e8aa8b74e3b3b9e46fd8`, version 2, 11,000 ms.
- Three beats: 3,000 / 4,500 / 3,500 ms. Project total: 39,000 ms.
- Chapters 2 and 3 remain exactly equal to the before snapshot.
- All 16 pre-existing planner record payloads remain byte-identical.
- A fresh application runtime reopens the new active state successfully.
- Old timing approval was not transferred. No new audio or render was created.
- Reviewer attribution explicitly says Codex applied the user's revision
  instruction; it does not claim a new human listening or creative review.
- Local Studio and planner SQLite backups were taken before activation.
- CUA visual inspection: three chapter cards, version labels, duration bars,
  editor, comparison and success notice rendered legibly. Local browser entry:
  `http://127.0.0.1:5173/#chapter-editor` (open the saved project when needed).

## Validation commands and results

Python commands use `.venv-studio/Scripts/python.exe -B`, PYTHONPATH containing
the repo and `studio-api/src`, and isolated `--basetemp` directories.

| Check | Result |
| --- | --- |
| pytest `test_chapter_revision_activation.py` | 6 passed |
| pytest `test_openapi_project_contract.py test_app_factory.py` | 6 passed |
| pytest v031 chapter/beat, v032 Director narration and asset fulfillment acceptance files | 36 passed |
| `npm --prefix studio-ui test -- --reporter=dot` | 106 passed |
| `npm --prefix studio-ui run build` | TypeScript and Vite passed |
| `npm --prefix studio-ui run check:client` | Exact regenerated client, A/B deterministic |
| `npm --prefix studio-ui run verify:http-boundary` | Passed |
| `python -m kurgu_studio_api.openapi_export --write`, subsequent contract byte comparison | Passed |
| `prepare_live_revision.py` | Backups and persisted proposal created |
| `verify_live_revision.py` | Fresh runtime, history, unaffected chapters and obsolete dependency checks passed |

Backend coverage includes two business-tech examples, rollback during the
second package, duplicate activation, stale proposal/hash/duration rejection,
two successive revisions and successful new-parent sequence submission.
The worker test compiles a real request with executable identities from a real
product chain, publishes its closure through the production store, activates
its parent chapter through HTTP, and verifies rejection before runner invocation.
Renderable media in that test is a transport fixture, not creative video proof.

One independent final audit found two defects: historical supersedes references
were being treated as active dependencies, and compiled requests carried closure
IDs rather than planner IDs. Both were repaired and covered by positive
successive-revision and real compiled-request tests. Initial failing runs were
repaired; final results above are the final checks. One existing FastAPI/Starlette
TestClient deprecation warning remains. No full repository suite or full render
was run for this bounded editor change.

## Changed implementation files

- `engine/planner/revisions.py` (new), `engine/planner/store.py`.
- `engine/contracts/director_editorial_sequence.py`.
- `studio-api/src/kurgu_studio_api/infrastructure/engine_manual_task_factory.py`.
- `studio-api/src/kurgu_studio_api/infrastructure/phase17_final_av_executor.py`.
- `studio-api/src/kurgu_studio_api/application/studio_workflow_service.py`.
- `studio-api/src/kurgu_studio_api/api/errors.py`, `api/v1/dto.py`,
  `api/v1/studio_workflow.py` under the same package.
- `studio-api/tests/test_chapter_revision_activation.py` (new),
  `test_openapi_project_contract.py`, `test_app_factory.py`.
- `studio-ui/src/components/ChapterRevisionPanel.tsx`,
  `ChapterRevisionPanel.test.tsx`, `chapter-revision.css` (new).
- `studio-ui/src/components/ProjectConsole.tsx`, `studio-ui/src/App.tsx`,
  `studio-ui/src/api/studioApi.ts`, `studio-ui/src/test/generatedClientContract.test.ts`.
- `shared-schemas/openapi/openapi.json` and generated client index/SDK/types.

The repository already contained substantial uncommitted accumulated work.
This task did not bulk-stage or commit that implementation tree. Documentation
reconciliation is kept separate; a docs commit does not publish the implementation.

## Artifacts and limitations

Local evidence is under `output/phase17-chapter-revision-studio-20260905/`:
before/after JSON, prepared request/response, verification JSON, preparation and
verification scripts, server logs, and the two pre-activation SQLite backups.
Database backups stay local and are not part of documentation publication.

Existing English editorial content is shown as stored. Editing preserves beat
count, chapter order, claims/evidence and total chapter duration. Viewer-state
continuity currently requires exact matching text. This is intentionally bounded;
the editor does not regenerate pictures, voice or a video when activated.
The historical research/status panels are not a unified production progress
dashboard. Only business-tech is exercised; no second production domain is claimed.

## Single recommended next task

`PHASE17_BUSINESS_TECH_V032_V2_OPENING_VISUAL_PROOF`: use the active first
chapter to make an 11-second source-qualified visual/audio preview with actual
source media, then review it on screen. This belongs to the existing genuine
30–45 second proof program; do not claim the entire 39-second film is complete.

## DOCUMENTATION_IMPACT_MATRIX

| Document | Impact |
| --- | --- |
| CURRENT_STATE.md | Updated: live V2 activation, editor and verification |
| CHANGELOG.md | Updated: bounded implementation and live result |
| NEXT_ACTIONS.md | Updated: one authoritative next task; old context historical |
| KNOWN_LIMITATIONS.md | Updated: editor scope and remaining audio/visual work |
| PHASE_ACCEPTANCE.md | Updated: local editor acceptance; Phase 17 remains open |
| QUALITY_BENCHMARKS.md | Reviewed, unchanged: no new creative quality evidence |
| ARCHITECTURE_DECISIONS.md | Reviewed, unchanged: existing version/lineage and thin API decisions retained |
| MASTER_ROADMAP.md | Reviewed, unchanged: no phase or product-model change |
