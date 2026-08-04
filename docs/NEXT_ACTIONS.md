# Next Actions

Aktif faz: Faz 0 CLOSED. Faz 1 CLOSED. Faz 2 IN_PROGRESS.

## NEXT AUTHORITATIVE TASK

This is the single authoritative next task.

Perform a targeted independent, adversarial, read-only re-audit of the
corrected candidate specification:

```text
docs/specifications/phase2_canonical_phrase_grouping_caption_groups_contract.md
```

Corrected identity:

```text
COMMIT=5bd2401544693a9a0bfe9e3e9d398f96b786cb27
SHA256=c0e8925e598bac0414c1c7b96adf256ed0f4072d2196efedf3b90b0961859baf
UTF8_BYTES=43985
```

The re-audit must decide whether `CGS-SPEC-AUD-001` is closed. Verify that
every range, coverage, timing, confidence, loader, identity, and multi-fault
condition now has exactly one fixed pointer/reason/issue-code outcome and exact
precedence. Regression-check the previously passing grouping algorithm,
sentence-length properties, scope, upstream compatibility, encoding, and
FX-CGS-01 golden values. Report any new findings by severity.

This task is read-only. Do not edit files, accept the specification, authorize
implementation, assign a Slice number, or close Phase 2. PASS permits only a
separate specification-acceptance decision; otherwise return to bounded repair.

```text
ORIGINAL_SPECIFICATION_AUDIT=FIX_REQUIRED
CGS_SPEC_AUD_001_STATUS=REPAIRED_PENDING_TARGETED_REAUDIT
SPECIFICATION_ACCEPTED=NO
IMPLEMENTATION_AUTHORIZED=NO
NEXT_ACTION=TARGETED_INDEPENDENT_READ_ONLY_REAUDIT
NEXT_IMPLEMENTATION_ALLOWED=NO
PHASE2_CLOSED=NO
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
```
