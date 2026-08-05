# Next Actions

Aktif faz: Faz 0 CLOSED. Faz 1 CLOSED. Faz 2 CLOSED. Faz 3 CLOSED. Faz 4 IN_PROGRESS.

## NEXT AUTHORITATIVE TASK

Implement **Phase 4A - Motion Renderer Foundation**.

Consume accepted Phase 3 video/audio EDL artifacts without re-scheduling them.
Deliver a bounded Python-to-Remotion typed props bridge, composition registry
foundation, deterministic headless fixture preview, and render-artifact
registration hooks. Keep the existing V2 path intact.

Do not implement Phase 5 templates, provider acquisition, queue/retry, UI
expansion, production asset-catalog behavior, full lifecycle/GC, or Phase 4B
terminal-job cleanup/overwrite completion in this task.

## Current evidence boundary

- Phase 3 is ACCEPTED / CLOSED / REMOTE CLOSED. See
  `baseline/phase3_final_acceptance_report.md`.
- Accepted commits: video `fbee3b7ae1f1d6b607fa913f4cb4ff8ba3bbfc9f` and
  audio `3ae26f8a3f958a9e470a02b7a6afa0c05efe82a9`.
- Final gates: `115 passed` cross-contract; `64 passed` clean-clone exact.

```text
PHASE3_FINAL_ACCEPTANCE=ACCEPT
PHASE3_CLOSED=YES
NEXT_ACTION=PHASE4A_MOTION_RENDERER_FOUNDATION
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
