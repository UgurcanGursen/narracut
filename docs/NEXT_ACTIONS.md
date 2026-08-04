# Next Actions

Aktif faz: Faz 0 CLOSED. Faz 1 CLOSED. Faz 2 IN_PROGRESS.

## NEXT AUTHORITATIVE TASK

This is the single authoritative next task.

Perform an independent, adversarial, read-only specification audit of the exact
remote-closed candidate:

```text
docs/specifications/phase2_canonical_phrase_grouping_caption_groups_contract.md
```

Audit identity:

```text
COMMIT=171078ca1c50a43ac9a395fe135e6bc044079b28
SHA256=d379e02e84883a08da66fd6289ca973d0f49a89f007bf68a524c7981dc7cbd46
UTF8_BYTES=35784
```

The audit must verify roadmap alignment, upstream contract compatibility,
deterministic grouping and remainder safety, punctuation/display derivation,
complete word coverage, timing/confidence propagation, canonical identity and
serialization, validation precedence, mutation/provenance/no-leak rules,
performance bounds, golden values, exact scope, and implementation feasibility.
Findings must be reported as BLOCKER/MAJOR/MINOR/INFO with exact section and
repair guidance.

This task is read-only. Do not edit the specification or any repository file,
accept the specification, authorize implementation, assign a Slice number, or
close Phase 2. If findings exist, the next gate is bounded specification repair;
otherwise the next gate is a separate acceptance decision.

```text
SPECIFICATION_STATUS=CANDIDATE_REMOTE_CLOSED
SPECIFICATION_DRAFTED=YES
SPECIFICATION_ACCEPTED=NO
IMPLEMENTATION_AUTHORIZED=NO
INDEPENDENT_SPECIFICATION_AUDIT_REQUIRED=YES
NEXT_ACTION=INDEPENDENT_READ_ONLY_SPECIFICATION_AUDIT
NEXT_IMPLEMENTATION_ALLOWED=NO
PHASE2_CLOSED=NO
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
```
