# Next Actions

## Latest checkpoint — 2026-09-07, actual Studio working edit

The saved business-tech project now renders a measured 87.866667-second,
six-scene, 1080p/30fps working edit with local speech, word alignment and 23
executed visual cues. Final job `ejob_625336760cc24f69b3d91f59bb044dca`. UI review and selected-scene
production work; the final revision changes only scene 2 and preserves the other
five scene video hashes. Speech/alignment are reused for visual-only changes.

Actual-output QA caught and repaired cumulative AAC/concat timing displacement.
Final decoded full-cut and single-scene PCM comparison maximum offset is
0.0 ms across 36 comparisons. This is mux accuracy,
not human listening or semantic approval. 31 backend/mux and 40 UI tests pass;
build, renderer typecheck, generated client and HTTP boundary pass.

This is an unapproved working edit with independent measured duration and exact
accepted chapter ancestry. Old canonical 39-second allocations are unchanged.
Automatic creative planning/footage selection, sound design and canonical
promotion remain outstanding. The current manual direction was agent-authored;
one result does not establish reliable professional first-pass quality.
Phase 17 SCOPE_RECONCILIATION remains OPEN. No commercial API calls.

Current UI: `http://127.0.0.1:5173/#studio-video`; final API: localhost **8003**,
selected through ignored `studio-ui/.env.local`. Existing servers were preserved
after automatic approval review blocked a restart command.

Acceptance, commands, file inventory and DOCUMENTATION_IMPACT_MATRIX: `baseline/phase17_studio_working_edit_acceptance_20260907.md`.

## NEXT AUTHORITATIVE TASK

`PHASE17_WORKING_EDIT_CREATIVE_ACCEPTANCE_AND_REPAIR` is the single authoritative next task.
Assess the whole current cut for narration relevance, viewer inference and
editing rhythm. Repair recurring weaknesses across scenes; do not push baseline
editing work onto the owner as repeated individual scene rejections. Record
owner feedback separately from technical PASS. No new domains or automatic
professional-quality claims. Canonical promotion is not part of this review.
Separate documentation sync must close before subsequent implementation;
evidence: `output/phase17-studio-production-20260907/documentation-sync.json`.

## Previous checkpoints (historical)

## Latest checkpoint — 2026-09-06, joint narration/visual treatment

The owner rejected the 39-second cut's creative quality and narration/visual
relevance. Mechanical timing/playback PASS does not mean creative acceptance.
The earlier video remains an unaccepted editorial draft.

The actual business-tech 0.3.2 project now has a persistent Studio joint planning
workbench: six scenes, ten current beats, 21 word-cued visual events, estimated
83–109 seconds. The agent authored this plan; MANUAL_UI task download/import is
available for the owner's external AI tools. No commercial API calls.
Latest treatment: `etreat_33231dd0a14a464bbd02eb20`.
UI: `http://127.0.0.1:5173/#editorial-treatment`.

Evidence/parent checks, cue ordering, cross-scene object state continuity,
immutable revisions, stale/concurrent edit rejection and actual UI save/reopen
pass. Twenty backend tests, targeted UI tests, production build and client/boundary
checks pass. This is PREPRODUCTION_DRAFT only: no new audio/video, measured timing,
canonical activation or creative approval. The old canonical 39-second allocation
remains; migration and treatment-to-Director/renderer execution are still required.
Phase 17 SCOPE_RECONCILIATION stays OPEN.

Acceptance, file inventory and DOCUMENTATION_IMPACT_MATRIX: `baseline/phase17_joint_editorial_treatment_acceptance_20260906.md`.

## Previous next-task record (historical)

`PHASE17_TREATMENT_TO_STUDIO_EXECUTION` is the single authoritative next task.
Connect the saved joint treatment to the existing Studio production path:
explicit duration/lineage migration, local narration and measured word timing,
persistent visual objects/actions and a reviewable project output. The delivery
constraint must be explained on screen at the corresponding spoken phrases.
Do not substitute generic stock, fake canonical or human approval, or treat the
plan as a finished edit. Full professional production remains unproven.
Separate documentation sync must close before that implementation starts;
evidence: `output/phase17-editorial-treatment-20260906/documentation-sync.json`.

## Previous checkpoints (historical)

## Latest checkpoint — 2026-09-06, full editorial cut

The user-authorized full first cut is rendered: 39 seconds, 1920×1080,
30 fps / 1170 frames, 3 current chapters, 10 beats and 16 selected shots.
It combines real illustrative footage, short source inserts, explanatory
graphics, measured local narration, captions and an original quiet sound bed.
Audio: −16.11 LUFS, −1.38 dBTP; all ten decoded voice placements have 0 ms
measured start error. Full decode and 39-second browser playback pass.
Shot seeking and local revision-note save/retrieval pass; QA notes were cleared.
Final: `output/phase17-full-review-20260906/full-39s-editorial-review.mp4`.
SHA-256: `2d34e8582b1f7d92ca1a82cf0ba5c86f1f3cf7f7136fbc82ec8c15471acc5fbf`.
Review: `http://127.0.0.1:5173/reviews/full-39s/2d34e8582b1f/index.html`.
This supersedes the earlier “remaining 28 seconds unrendered” limitation.
Status is EDITORIAL_REVIEW_DRAFT. Shot selection/cuts were agent-directed;
automatic production, canonical publication and human listening/timing approval
are still absent. Review notes do not trigger regeneration. Some facility
footage is limited by its 480p original. No commercial API calls. Phase 17 open.
Acceptance and DOCUMENTATION_IMPACT_MATRIX: `baseline/phase17_full_editorial_review_acceptance_20260906.md`.

## Previous next-task record (historical)

`PHASE17_FULL_CUT_CREATIVE_REVIEW_AND_ONE_REVISION` is the single authoritative
next task. Review the delivered whole cut, collect the user's actual viewing
and listening response, then apply one bounded revision to named shots.
Do not infer human approval from successful playback or automatic timing.
The next implementation follows the separate documentation synchronization
gate; remote evidence is `output/phase17-full-review-20260906/documentation-sync.json`.

## Previous checkpoints (historical)

## Latest checkpoint — 2026-09-06

The active V2 opening has a real 11-second editorial-review MP4: 1920×1080,
30 fps / 330 frames, new local Kokoro narration, measured WhisperX word timing,
source-bound highlights and captions. Final audio measures -16.29 LUFS;
per-voice synchronization errors are 0.333/0/0 ms. Actual browser playback
completed at 11 seconds without error. Source-frame visual inspection passes.
Artifact: `output/phase17-opening-review-20260906/opening-11s-review-v3.mp4`.
SHA-256: `f93445215bac0ee3f9ce99d8be533534aa49c4c1431a410235bd7ac87060c481`.
Status remains EDITORIAL_REVIEW_DRAFT: no canonical production publication or
human timing approval. The remaining 28 seconds are unrendered; Phase 17 open.
Acceptance and DOCUMENTATION_IMPACT_MATRIX: `baseline/phase17_opening_review_acceptance_20260906.md`.
This scoped documentation commit does not publish local implementation/media.

## Previous next-task record (historical)

`PHASE17_V2_OPENING_CREATIVE_AND_TIMING_REVIEW` is the single authoritative
next task: inspect the delivered video, collect actual feedback/timing approval,
then apply any bounded corrections before canonical production promotion.
The acronym token E's has 0.505 automatic alignment confidence; playback
completion is not human listening approval. Do not reuse old timing approval.

Documentation synchronization is verified and published on this bounded branch;
it does not merge accumulated implementation or generated media.

## Previous next-task context — historical, not an execution queue


## Latest checkpoint — 2026-09-05

LOCAL_IMPLEMENTATION_AND_LIVE_ACTIVATION_VERIFIED. The Studio chapter editor
now persists proposals, shows before/after review and atomically activates a
new chapter/beat version. Real first chapter is V2 at 3/4.5/3.5 seconds;
the other chapters and 39-second total are unchanged. Existing planner rows
remain byte-identical; stale task and compiled-render ancestry is rejected.
No new audio, timing or finished video was created. Phase 17 remains open.
48 relevant Python and 106 UI tests passed, plus build/client checks and
fresh-runtime live verification. This scoped documentation commit does not
publish the authoritative workspace's accumulated implementation changes.
Acceptance and DOCUMENTATION_IMPACT_MATRIX: `baseline/phase17_chapter_revision_studio_acceptance_20260905.md`.

## Previous next-task record (historical)

`PHASE17_BUSINESS_TECH_V032_V2_OPENING_VISUAL_PROOF` is the single authoritative
next task: build and review an 11-second source-qualified visual/audio preview
from active chapter `chap_e8aa8b74e3b3b9e46fd8`. New planning must use its active
beat IDs. Previous audio timing approval cannot transfer to changed audio.
This remains part of the genuine 30–45 second Studio proof program.

Documentation reconciliation is separately verified and published on this
bounded branch. It does not merge or publish the accumulated implementation.

## Previous next-task context — historical, not an execution queue


Latest 2026-09-04 checkpoint: first chapter V2 proposals prepared at
3,000/4,500/3,500 ms; six package checks pass, total remains 39 seconds.
Not activated in Studio; no audio/render or creative acceptance. Next single
step: `PHASE17_BUSINESS_TECH_V032_CHAPTER_REVISION_ACTIVATION`.
Evidence/impact matrix: `docs/PHASE17_CHAPTER01_REVISION_PROPOSAL.md`.

## Phase 17 scoped workspace evidence — 2026-09-04

This branch synchronizes only the beat-01 source/renderer reconciliation
checkpoint. It does not publish the authoritative workspace's 22 local code
commits or its unrelated dirty files. Older entries below remain historical.
Current checkpoint and documentation impact matrix:
`docs/PHASE17_BEAT01_RECONCILIATION_CHECKPOINT.md`.


Aktif faz: Faz 0 CLOSED. Faz 1 CLOSED. Faz 2 CLOSED. Faz 3 CLOSED. Faz 4 CLOSED. Faz 5 CLOSED. Faz 6 CLOSED. Faz 7 CLOSED. Faz 8 CLOSED. Faz 9 CLOSED. Faz 10 CLOSED. Faz 11 CLOSED. Faz 12 CLOSED. Faz 13 FOUNDATION_ACCEPTED / MASTER OPEN. Faz 14 MASTER_PHASE_CLOSED. Faz 15 MASTER_PHASE_CLOSED.

## AI execution policy

All remaining work follows `docs/AI_DEVELOPMENT_EXECUTION_POLICY.md`.
The active package uses one grouped implementation repair and one final
independent audit; repeated micro-audit loops and repeated full render gates
are not the default workflow.

## Previous next-task record (historical)

Implement a bounded P17 local non-REPLAY timing-adapter contract and its
fail-closed integration for the two selected real projects. Preserve existing
`REPLAY` behaviour; do not add a commercial API, provider credential, browser
automation or an unbounded background worker. The implementation must make
timeout, cancellation, resource limits, raw-output lineage, confidence and
manual calibration evidence explicit. Its scope baseline is
`baseline/phase17_ibm_wework_evidence_preparation.md`.

The separately audited local import/export/archive/recovery operations still
need thin FastAPI/UI exposure and durable-queue route integration before the
product gate can close; neither task is replaced by the timing adapter.

All instructions below this section are historical evidence only and are not
active work authorization.

Independently audit the historical candidate **Phase 4B - Render Terminality, Full Render
and Artifact Lifecycle Completion** contract.

Phase 4A is ACCEPTED / CLOSED / REMOTE CLOSED at
`d3f99d0c766924cc6ee7d07e80a6ea53a27e806f`. The next task is read-only and
must assess `docs/specifications/phase4b_render_terminality_full_render_artifact_lifecycle_contract.md`.
It must not authorize or implement Phase 4B.

Do not implement Phase 4B, Phase 5 templates, provider acquisition,
queue/retry, UI expansion, production asset-catalog behavior, cache/GC or any
later phase in this task.

## Historical Phase 4 evidence boundary (superseded)

- Phase 4A is ACCEPTED / CLOSED / REMOTE CLOSED. See
  `baseline/phase4a_motion_renderer_foundation_acceptance_report.md`.
- Accepted implementation: `d3f99d0c766924cc6ee7d07e80a6ea53a27e806f`.
- Final gates: bridge `16 passed`; Remotion typecheck `PASS`; Node canonical
  tests `3/3 PASS`; final targeted audit `PASS` (`0/0/0`).

```text
PHASE4A_ACCEPTANCE=ACCEPT
PHASE4A_CLOSED=YES
PHASE4A_REMOTE_CLOSED=YES
PHASE4B_IMPLEMENTATION_AUTHORIZED=NO
NEXT_ACTION=PHASE4B_SPECIFICATION_INDEPENDENT_AUDIT
```

The historical Phase 3B instruction below is superseded and retained only for
the accepted Phase 3A-to-3B audit trail.

## Historical Phase 3A-to-3B instruction (superseded)

Historical active state: Faz 0 CLOSED. Faz 1 CLOSED. Faz 2 CLOSED. Faz 3 IN_PROGRESS.

Implement **Phase 3B — Audio Sample Grid and Boundary Contract**.

The task must consume the accepted Phase 3A EDL without re-scheduling video
events and must deliver, with REPLAY-only evidence:

- deterministic 48 kHz audio-sample-grid compilation for A1–A5;
- normalization, encoder delay/padding compensation and explicit audio
  boundary-policy metadata;
- zero-crossing, micro-fade, overlap-crossfade and collision-resolution
  planning;
- planned-silence preservation and protection of TTS word boundaries;
- deterministic audio debug/export evidence and a Phase 3 end-to-end
  acceptance reconciliation.

Use one bounded specification, implementation integration, independent audit,
and acceptance/documentation closure. Do not implement Remotion rendering,
artifact lifecycle, providers, queues/retries, UI, or any Phase 4 capability
in this task.

## Current evidence boundary

- Phase 3A Video EDL implementation is accepted and remote closed at
  `fbee3b7ae1f1d6b607fa913f4cb4ff8ba3bbfc9f`.
- Final independent audit: `PASS`; findings `0 BLOCKER / 0 MAJOR / 0 MINOR`.
- Focused contract, integration, high-cardinality and export gate: `113 passed`.
- A1–A5 are deliberately empty in Phase 3A; audio behavior is not yet
  implemented or accepted.

```text
PHASE3A_VIDEO_EDL_IMPLEMENTATION_ACCEPTED=YES
PHASE3A_VIDEO_EDL_IMPLEMENTATION_REMOTE_CLOSED=YES
HISTORICAL_PHASE3_CLOSED_AT_3A=NO
HISTORICAL_NEXT_ACTION_AT_3A=PHASE3B_AUDIO_SAMPLE_GRID_AND_BOUNDARY_CONTRACT
```
