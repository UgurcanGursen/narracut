# Next Actions

Aktif faz: Faz 0 CLOSED. Faz 1 CLOSED. Faz 2 CLOSED. Faz 3 CLOSED. Faz 4 CLOSED. Faz 5 CLOSED. Faz 6 CLOSED. Faz 7 CLOSED. Faz 8 CLOSED. Faz 9 CLOSED. Faz 10 CLOSED. Faz 11 CLOSED. Faz 12 NEXT.

## AI execution policy

All remaining work follows `docs/AI_DEVELOPMENT_EXECUTION_POLICY.md`.
The active package uses one grouped implementation repair and one final
independent audit; repeated micro-audit loops and repeated full render gates
are not the default workflow.

## NEXT AUTHORITATIVE TASK

Perform a read-only Phase 12 Continuity/Pacing and Executable Editorial
Integration scope reconciliation. Freeze the policy, immutable input/output
contracts, Phase 10 planner / Phase 8 approved asset-range-crop / Phase 5
capability / Phase 7 visualization / Phase 11 audio-direction handoffs, and
the Phase 3 final-EDL compiler boundary before authorizing implementation.

Do not implement Phase 12 in this task. Do not introduce provider API
execution, browser-driven LLM automation, paid LLM calls, queue/retry
infrastructure, UI expansion or a renderer bypass. Phase 12 must fail closed
on missing provenance, approval, capability, policy or continuity input.

Phase 11 closure evidence: `6717de4`, `24daca7`; final focused regression:
`57 passed`. There is no open Phase 11 blocker. Phase 12 has not yet received
an implementation authorization.

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
