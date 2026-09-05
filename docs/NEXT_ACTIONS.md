# Next Actions

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

## NEXT AUTHORITATIVE TASK

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
