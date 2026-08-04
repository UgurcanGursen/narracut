# Next Actions

Aktif faz: Faz 0 CLOSED. Faz 1 CLOSED. Faz 2 IN_PROGRESS.

## NEXT AUTHORITATIVE TASK

This is the single authoritative next task.

Implement only the authorized bounded **Canonical Emphasis Events Contract**:

```text
docs/specifications/phase2_canonical_emphasis_events_contract.md
COMMIT=d4c978eb0df8d11ab033edbd50dc2eca17eab74a
SHA256=5806aa26f798489e475d03b68e451cdbf2c2efd39f450ea7335cb96fc442f3b7
UTF8_BYTES=45380
```

The read-only authorization decision is `AUTHORIZE` and is recorded in
`baseline/phase2_canonical_emphasis_events_implementation_authorization_decision_report.md`.

Change exactly:

```text
engine/contracts/emphasis_events.py
engine/contracts/__init__.py
tests/test_emphasis_events.py
tests/test_alignment_request.py
```

Implement the exact 15-symbol surface and every normative behavior/test oracle
from the accepted specification. Domain Packs and upstream contracts are
read-only. Run focused, eight-module upstream, broad non-FastAPI, and available
full-collection gates using REPLAY-only fixtures.

Do not change any other path, publish the roadmap artifact, execute providers,
add frames/preview/report work, assign a Slice number, state a total Slice count
or completion percentage, accept the implementation, or close Phase 2.

```text
POST_CAPTION_GROUPS_SCOPE_RECONCILIATION_STATUS=PASS
PHASE2_SCOPE_DECISION=MORE_BOUNDED_PHASE2_WORK_REQUIRED
NEXT_BOUNDED_CANDIDATE_TITLE=Canonical Emphasis Events Contract
SPECIFICATION_PATH_DECISION=CLOSED
SPECIFICATION_DRAFTED=YES
SPECIFICATION_ACCEPTANCE_DECISION=ACCEPT
SPECIFICATION_ACCEPTED=YES
IMPLEMENTATION_AUTHORIZATION_DECISION=AUTHORIZE
IMPLEMENTATION_AUTHORIZED=YES
IMPLEMENTATION_STATUS=NOT_STARTED
NEXT_ACTION=BOUNDED_IMPLEMENTATION
NEXT_IMPLEMENTATION_ALLOWED=YES
PHASE2_CLOSED=NO
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
```
