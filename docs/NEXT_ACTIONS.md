# Next Actions

Aktif faz: Faz 0 CLOSED. Faz 1 CLOSED. Faz 2 IN_PROGRESS.

## NEXT AUTHORITATIVE TASK

Prepare and execute one cohesive **Caption Preview + V5/V6 Collision
Validation** macro-package for Phase 2.

The package must reconcile and specify together:

```text
CaptionPreviewRenderer
Deterministic V5/V6 collision validation
```

It may consume only accepted canonical inputs and frame artifacts:

```text
CaptionGroupsArtifact
EmphasisEventsArtifact
WordToFrameArtifact
```

Required outcomes:

- deterministic, reviewable caption preview output from canonical frame spans;
- explicit V5/V6 layout ownership and collision rules;
- fail-closed collision findings with stable IDs, provenance, and sanitized
  error behavior;
- no string search, caller-authored seconds/frames, or renderer-global timing;
- bounded memory/runtime behavior with no per-video unbounded retention;
- REPLAY-only focused, visual-oracle, and upstream regression fixtures.

Use one specification, one implementation integration, one independent audit,
and one acceptance/documentation closure. Internal helpers do not receive
separate specification/authorization/remote-closure cycles. Disjoint modules
may be developed by parallel agents; shared exports, integration, git, and
documentation remain single-owner.

Do not yet implement timing-file publication, Remotion/EDL production work,
providers, UI, additional Domain Packs, or any later-phase feature. Do not
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
- `CaptionPreviewRenderer`, V5/V6 collision validation, and named timing-file
  publication remain incomplete.

```text
TEMPORAL_COMPILATION_ALIGNMENT_REPORT_IMPLEMENTATION_ACCEPTED=YES
PHASE2_SCOPE_DECISION=MORE_BOUNDED_PHASE2_WORK_REQUIRED
NEXT_MACRO_PACKAGE=Caption Preview + V5/V6 Collision Validation
NEXT_ACTION=MACRO_PACKAGE_SPECIFICATION_AND_IMPLEMENTATION
PHASE2_CLOSED=NO
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
```
