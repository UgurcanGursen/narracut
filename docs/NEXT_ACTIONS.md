# Next Actions

Aktif faz: Faz 0 CLOSED. Faz 1 CLOSED. Faz 2 CLOSED.

## NEXT AUTHORITATIVE TASK

Prepare a **planning-only Faz 3 + Faz 4 implementation roadmap**.

The package must reconcile and specify together:

```text
Faz 3 Multi-track EDL and Timeline Compiler
Faz 4 Motion Renderer Foundation
```

It may consume the already accepted canonical inputs and artifacts:

```text
CaptionGroupsArtifact
EmphasisEventsArtifact
WordToFrameArtifact
```

Required outcomes:

- explicit canonical named-file publication policy for accepted timing
  artifacts;
- end-to-end REPLAY fixture proving artifact lineage, publication, and the
  accepted preview/collision boundary without production media rendering;
- high-cardinality authoritative fixture for the performance evidence deferred
  by the sparse preview contract;
- final Master Roadmap Phase 2 acceptance reconciliation.

Use one specification, one implementation integration, one independent audit,
and one acceptance/documentation closure. Internal helpers do not receive
separate specification/authorization/remote-closure cycles. Disjoint modules
may be developed by parallel agents; shared exports, integration, git, and
documentation remain single-owner.

Do not implement Faz 3/4 production work before the user approves the plan.
Do not
assign a Slice number, total Slice count, or Phase 2 completion percentage.

## Current evidence boundary

- Temporal Compilation + Alignment Report implementation is accepted at
  `8eafe6e012d71bbca67f9902d8fe55fcad252973`.
- Acceptance report:
  `baseline/phase2_temporal_compilation_alignment_report_implementation_acceptance_report.md`.
- Final independent audit: PASS; findings `0 BLOCKER / 0 MAJOR / 0 MINOR`.
- Final focused gate: `253 passed`; exact public-export oracle: `1 passed`.
- Upstream contract regression: `1840 passed`.
- Broad top-level non-FastAPI regression: `2204 passed, 1 skipped`.
- Full collection is not claimed because optional FastAPI is absent from the
  active environment.
- `timing/word_timeline.json`, `timing/caption_groups.json`, and
  `timing/emphasis_events.json` filesystem publication remains open.
- Caption Preview and V5/V6 collision validation are accepted at
  `218c4bd277867b29d6812715311993a500e19d33`.
- Named timing-file publication and final Phase 2 reconciliation remain open.

```text
TEMPORAL_COMPILATION_ALIGNMENT_REPORT_IMPLEMENTATION_ACCEPTED=YES
PHASE2_SCOPE_DECISION=MORE_BOUNDED_PHASE2_WORK_REQUIRED
PHASE2_FINAL_ACCEPTANCE=ACCEPT
PHASE2_CLOSED=YES
NEXT_ACTION=PLAN_PHASE3_PHASE4
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
```
