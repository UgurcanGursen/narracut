# Next Actions

Aktif faz: Faz 0 CLOSED. Faz 1 CLOSED. Faz 2 CLOSED. Faz 3 IN_PROGRESS.

## NEXT AUTHORITATIVE TASK

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
PHASE3_CLOSED=NO
NEXT_ACTION=PHASE3B_AUDIO_SAMPLE_GRID_AND_BOUNDARY_CONTRACT
```
