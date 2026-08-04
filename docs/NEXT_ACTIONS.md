# Next Actions

Aktif faz: Faz 0 CLOSED. Faz 1 CLOSED. Faz 2 IN_PROGRESS.

## NEXT AUTHORITATIVE TASK

Prepare and execute one cohesive **Temporal Compilation + Alignment Report**
macro-package for Phase 2.

The package must reconcile and specify together:

```text
WordToFrameCompiler
AlignmentReport
```

It may reuse only accepted canonical inputs:

```text
AlignmentResult
CaptionGroupsArtifact
EmphasisEventsArtifact
```

Required outcomes:

- explicit rational/integer frame-rate policy;
- deterministic word, caption, and emphasis frame boundaries;
- no caller/LLM-authored seconds or frames;
- at most one-frame boundary drift under the accepted mapping policy;
- explicit low-confidence, confidence-unavailable, and confidence-not-applicable
  report states with stable issue codes;
- canonical bytes, stable IDs/hashes, provenance, mutation resistance, and
  sanitized fail-closed errors;
- REPLAY-only focused and upstream regression fixtures.

Use one specification, one implementation integration, one independent audit,
and one acceptance/documentation closure for this macro-package. Internal
helpers do not receive separate specification/authorization/remote-closure
cycles. Disjoint production/test modules may be developed by parallel agents;
shared exports, integration, git, and documentation remain single-owner.

Do not yet implement Caption Preview/V5-V6 collision validation, timing-file
publication, Remotion/EDL work, providers, UI, additional Domain Packs, or any
later-phase feature. Do not assign a Slice number, total Slice count, or Phase
2 completion percentage.

## Current evidence boundary

- Canonical Emphasis Events implementation is accepted and remote closed at
  `9bfdceed69b3fd769d02b6a9130f62235fbd630e`.
- Acceptance report:
  `baseline/phase2_canonical_emphasis_events_implementation_acceptance_report.md`.
- Final targeted audit: PASS; findings `0 BLOCKER / 0 MAJOR / 0 MINOR`.
- Final focused compatibility gate: `280 passed`.
- Upstream contract regression: `1674 passed`.
- Broad top-level non-FastAPI regression: `1951 passed, 1 skipped`.
- Full collection is not claimed because optional FastAPI is absent from the
  active environment.
- `timing/word_timeline.json`, `timing/caption_groups.json`, and
  `timing/emphasis_events.json` filesystem publication remains open.
- `CaptionPreviewRenderer`, V5/V6 collision validation, and `AlignmentReport`
  remain incomplete until their respective macro-packages close.

```text
EMPHASIS_EVENTS_IMPLEMENTATION_ACCEPTED=YES
EMPHASIS_EVENTS_IMPLEMENTATION_REMOTE_CLOSED=YES
PHASE2_SCOPE_DECISION=MORE_BOUNDED_PHASE2_WORK_REQUIRED
NEXT_MACRO_PACKAGE=Temporal Compilation + Alignment Report
NEXT_ACTION=MACRO_PACKAGE_SPECIFICATION_AND_IMPLEMENTATION
PHASE2_CLOSED=NO
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
```
