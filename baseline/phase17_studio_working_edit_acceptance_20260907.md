# Phase 17 — Studio working-edit execution

Date: 2026-09-07. Phase **17 SCOPE_RECONCILIATION, OPEN**.
Project `prj_f01b4d80f4744c619f9b9567f819ba2f`. Result: **WORKING_EDIT_EXECUTION_VERIFIED**.

## Product result

The real saved Studio project now produces a six-scene, approximately 88-second,
1920×1080, 30 fps motion-graphics explainer from its saved joint treatment.
The engine executes 23 visual events at measured narration word positions.
This is actual local Kokoro speech, local WhisperX alignment, Remotion graphics,
FFmpeg muxing, a persistent production job and playable/downloadable MP4.
No commercial API calls were used. The authoring helper only supplies manual
direction data; it does not contain a private video-production path.

The sequence explains a facility's request, delivery through its local grid,
the qualified DOE 350/15-day illustration, conditional backup, a common-axis EIA
comparison and a qualified ERCOT consequence returning to the delivery question.
Current treatment has 23 events after two early comparison actions were added.
The scene-3 opening grid is visible immediately; scene 5 establishes a demand/
supply mechanism before introducing its numerical axes. Source qualifications
remain visible, including requested capacity and scenario uncertainty.

Treatment: `sha256:c8d0ba970aa12560e318c523047de0369e704ae0166e4d49fc10aa41f4e6232e`.
Direction: `sha256:3ebd1d1784655a36a027fa376a7cc56232643272a19b536611b76064481baaa7`.
Verified base job: `ejob_c3e7249372304f43a8bb326d5dfb1d46`.
Verified selected-scene revision: `ejob_625336760cc24f69b3d91f59bb044dca`.
Video hash: `sha256:37955bd9bfbf3d9511a8bbed53f95716cdddd591ac1c357a596e5d6b786df01c`.
Video: `output/studio-editorial-production/prj_f01b4d80f4744c619f9b9567f819ba2f/ejob_625336760cc24f69b3d91f59bb044dca/video.mp4`.

The browser opened this same project, played the second scene, changed its
framing through the UI and started production. The final second-scene change
preserves the other five scene files byte-for-byte and reuses unchanged speech
and alignment. MP4 endpoints serve the full cut and the actual selected scene.
The video appears above the planning fields and has a direct navigation link.

## Phase scope and acceptance

In scope: generic executable motion inputs, MANUAL_UI import/export, local
speech/timing, source-qualified graphics, real Studio jobs/review/download,
selected-scene reuse, visible invalid/stale inputs, exact audio muxing.
Out of scope: new domains, commercial APIs, automatic research approval,
universal creative quality, canonical chapter-duration migration/publication.

| Criterion | Result |
|---|---|
| Saved project/treatment ancestry; no replacement demo project | PASS |
| Exact treatment/scene hashes and coverage; event bindings validated | PASS |
| Invalid geometry rejected before rendering | PASS |
| Direction-only revisions make previous videos visibly stale | PASS |
| Persistent jobs, immutable input snapshots, cache/media hash checks | PASS |
| Local voice, measured word alignment and 23 executed visual cues | PASS |
| 2636 video frames, 30 fps, 1920×1080, exact 87.866667 s video track | PASS |
| Full MP4 decodes without errors | PASS |
| Full-cut and individual-scene PCM comparison after mux | PASS: max 0.0 ms measured offset |
| UI-selected scene changes; five others retain video hashes | PASS |
| Visual-only change reuses speech/alignment | PASS |
| Build, API/client, HTTP boundary and targeted regression checks | PASS |
| Autonomous professional editing on arbitrary unseen topics | NOT PROVEN / NOT IMPLEMENTED as an automated creative service |
| Automatic footage search/selection, music/SFX sound design | NOT IMPLEMENTED in this working-edit path |
| Canonical duration migration and accepted snapshot export | OUTSTANDING |
| Owner creative/listening approval; Phase 17 closure | NOT CLAIMED |

The accepted legacy chapter allocation remains 39 seconds. This new measured
working edit is not a rewrite or activation of that accepted chronology. Its
inputs retain exact ancestry. `human_approved=false`, `canonical_publication=false`.
The old snapshot review/export and overview counters still represent canonical
state; working-edit MP4 review/download is available in the production panel.

## Verification and repairs

- Python: `pytest -q studio-api/tests/test_editorial_production_api.py studio-api/tests/test_editorial_treatment.py studio-api/tests/test_openapi_project_contract.py tests/test_editorial_production.py tests/test_editorial_production_mux.py --basetemp=.codex-test-temp/studio-production-accepted-20260907-final`: **31 passed**. Run through `.venv-studio/Scripts/python.exe` with `sys.path[:0]=['studio-api/src','.']`. Existing Starlette/httpx deprecation warning remains.
- UI: `npm test -- src/components/EditorialProductionPanel.test.tsx src/components/EditorialTreatmentPanel.test.tsx src/components/ProjectConsole.test.tsx src/api/studioApi.test.ts src/test/generatedClientContract.test.ts`: **40 passed** after final UI changes.
- `studio-ui`: `npm run build`, `npm run check:client`, `npm run verify:http-boundary`: **PASS**.
- `renderer-remotion`: `npm run typecheck`: **PASS**.
- OpenAPI SHA256: `863a7909e24e9c8afbd00e60068ef2e7c937649038d3936383793ae6d395cbfd`; generated client aggregate `c5502318b2bb6eb4bf2fbc5077b666b7c2d90c970141c374aa74626d3571e943`, A/B byte-identical.
- Real browser review/selected-scene production and `verify_final.py ejob_c3e7249372304f43a8bb326d5dfb1d46`: **PASS**.
- Final audit found direction-only freshness and negative SVG dimension acceptance; repaired with focused regressions. Implementation-agent QA additionally repaired preview/variant target disagreement and asynchronous task-download ownership.
- Actual decoded audio measurement caught a material render bug that unit mocks could not: browser AAC priming plus concatenated container duration caused about 300 ms cumulative displacement in an earlier cut. Those earlier files remain historical and are superseded. The worker now remuxes each scene with its normalized PCM narration, sets exact video durations, resamples before padding each scene to its exact sample count and encodes one continuous PCM track for the final cut. Actual-output QA also caught short normalization tails; per-scene padding prevents their accumulation. A real three-scene FFmpeg regression verifies both scene timing and cumulative duration.
- Final measurement compares decoded MP4 audio against normalized PCM at two positions in each of six scenes, both individually and in the final cut, plus original-voice to normalized-PCM checks (36 comparisons). It measures mux displacement, not the linguistic correctness of forced alignment or human listening approval. Cue-to-frame quantization stays within 17 ms. Word-alignment confidence includes uncertain words; no semantic/listening acceptance is inferred.
- Final MP4 loudness measurement: integrated -17.21 LUFS, true peak -4.31 dBTP. These are measured input values, not the hypothetical output of the analysis filter.
- Visual QA inspected extracted frames from all six scenes, including repaired scene-3/5 openings and scene-6 payoff. This is an agent review, not a substitute for audience/owner judgment.

No full repository test suite was run. Failed intermediate outputs, original
assets, cache and old review videos were preserved.

## Manual operation and current local runtime

Open `http://127.0.0.1:5173/#studio-video`, open the saved project if the UI has
been freshly reloaded, then use **Videoyu izle ve düzenle**. Full video, scene
selection, framing presets and MP4 download are available. Arbitrary creative
scene changes require an external/manual AI direction response imported through
the same panel; the service does not invent those decisions. The task package
contains the actual treatment, scene hashes, evidence and business-tech motion
instructions. The current six-scene direction was authored by the agent.

The source renderer is generic vector/motion execution. This particular result
uses original explanatory diagrams with narration and captions; it does not
contain researched documentary footage, music or effects sound design.

An automatic approval review blocked the compound server-restart command and
a later compound helper-launch command, providing only a generic policy reason.
No protected process was stopped. Updated API workers were instead started on
separate localhost ports and the existing Vite UI was pointed to the final one
through its ignored `.env.local`. Current UI is **5173**, current API is **8003**.
The prior workers remain running; do not direct new production to their old
ports. `KURGU_STUDIO_API_ORIGIN` supports the override; without it the default
remains 8000. This local environment override is not a committed credential.

## Files, artifacts and remaining boundary

Changed implementation files (shared files also contain earlier work):

- `engine/planner/editorial_production.py`
- `engine/planner/editorial_treatment.py`
- `domain-packs/business-tech-v0.3.2/prompts/editorial_motion_direction.md`
- `renderer-remotion/src/editorial-motion.tsx`
- `renderer-remotion/src/editorial-motion-entry.tsx`
- `studio-api/src/kurgu_studio_api/application/studio_workflow_service.py`
- `studio-api/src/kurgu_studio_api/api/errors.py`
- `studio-api/src/kurgu_studio_api/api/v1/dto.py`
- `studio-api/src/kurgu_studio_api/api/v1/studio_workflow.py`
- `studio-api/tests/test_editorial_production_api.py`
- `studio-api/tests/test_openapi_project_contract.py`
- `tests/test_editorial_production.py`
- `tests/test_editorial_production_mux.py`
- `shared-schemas/openapi/openapi.json`
- `studio-ui/vite.config.ts`
- `studio-ui/src/App.tsx`
- `studio-ui/src/api/studioApi.ts`
- `studio-ui/src/components/EditorialProductionPanel.tsx`
- `studio-ui/src/components/EditorialProductionPanel.test.tsx`
- `studio-ui/src/components/EditorialTreatmentPanel.tsx`
- `studio-ui/src/generated/kurgu-api/index.ts`
- `studio-ui/src/generated/kurgu-api/sdk.gen.ts`
- `studio-ui/src/generated/kurgu-api/types.gen.ts`
- `studio-ui/src/test/generatedClientContract.test.ts`

Artifacts under `output/phase17-studio-production-20260907/`:
`direction.json`, `direction-publication.json`, `author_direction.py`,
`verify_final.py`, `final-verification.json`, `final-loudness.log`,
`qa-current/`, `implementation-file-manifest.json`, `documentation-sync.json`.
Job-owned inputs, video, voice/timing and scene receipts live under
`output/studio-editorial-production/`. The SQLite stores remain the existing
local Studio/planner databases. Implementation changes are local; the separate
documentation commit does not claim they were pushed as an isolated code slice.

Single recommended next task: **PHASE17_WORKING_EDIT_CREATIVE_ACCEPTANCE_AND_REPAIR**.
Assess the entire current cut against narration relevance, viewer inference and
editing rhythm; repair recurring weaknesses across the cut instead of requiring
the owner to reject every scene. Do not expand domains or claim autonomous
professional quality from one example. Canonical promotion remains a separate,
explicitly scoped later implementation after the creative boundary is resolved.

The user's full professional Studio objective is not complete. This package
delivers a working, reviewable treatment-to-video loop and proves targeted reuse.

## DOCUMENTATION_IMPACT_MATRIX

| Document | Impact | Reason |
|---|---|---|
| CURRENT_STATE.md | Updated | Real project video production and selected-scene execution. |
| CHANGELOG.md | Updated | Worker, motion renderer, API/UI, codec-delay repair and checks. |
| NEXT_ACTIONS.md | Updated | Exactly one whole-cut creative acceptance/repair task. |
| KNOWN_LIMITATIONS.md | Updated | Manual creative authoring, no automatic quality assurance, canonical migration outstanding. |
| PHASE_ACCEPTANCE.md | Updated | Bounded working-edit execution passes; Phase 17 remains open. |
| QUALITY_BENCHMARKS.md | Updated | Actual frame/PCM synchronization and reuse evidence, distinct from creative approval. |
| ARCHITECTURE_DECISIONS.md | Updated | Measured, unapproved working edits with immutable canonical ancestry. |
| MASTER_ROADMAP.md | Reviewed, unchanged | Multi-domain core plus business-tech pack retained; no roadmap amendment. |
