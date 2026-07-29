# Phase 2 Slice 5 Specification Path Decision Report

Date: 29 Temmuz 2026

## 1. Status

```text
Status: Candidate decision report
Accepted: No
Specification creation authorized: No
Implementation authorized: No
Phase 2 closed: No
```

Decision classification:

```text
Decision type:
New bounded specification-placement decision candidate

Applies to:
PHASE2-SLICE-5-CANDIDATE only

Establishes a repository-wide specification convention:
No

Accepted:
No

Specification creation authorized:
No

Implementation authorized:
No

Phase 2 closed:
No
```

## 2. Decision subject

```text
PHASE2-SLICE-5-CANDIDATE
Canonical Adapter Execution Provenance Contract
```

## 3. Triggering blocker

The preceding specification draft task was correctly blocked because:

- no accepted specification path convention was found;
- the original Phase 2 specification path is
  `EVIDENCE_PATH_NOT_FOUND`;
- silently inventing a specification filename was forbidden; and
- consequently, no specification file was created.

This report resolves only that placement and naming blocker. It does not act
as the Slice 5 specification.

## 4. Authority and evidence

The bounded decision uses these repository sources:

- `docs/NEXT_ACTIONS.md`: authorizes a specification-only next task while
  stating that the task does not invent a specification filename.
- `baseline/phase2_slice1_4_reconciliation_report.md`: records the original
  Phase 2 specification path and all Slice 1-4 specification paths as
  `EVIDENCE_PATH_NOT_FOUND`.
- `baseline/phase2_post_slice4_scope_report.md`: records that no accepted
  committed Phase 2 specification, amendment, or correction chain was found
  and selects `PHASE2-SLICE-5-CANDIDATE`.
- `docs/ARCHITECTURE_DECISIONS.md`: contains architecture decisions but does
  not provide an exact Slice 5 specification path.

The authority chain does not provide an exact specification path. Repository
path and history inspection found Phase 2 evidence reports under `baseline/`
but no accepted normative specification placement convention.

## 5. Decision

The exact future specification path is:

```text
docs/specifications/phase2_slice5_canonical_adapter_execution_provenance_contract.md
```

This path is selected by this report as a new bounded decision candidate. It
was not discovered as an existing accepted convention. It applies only to
`PHASE2-SLICE-5-CANDIDATE` and creates no automatic convention for another
Phase or Slice.

## 6. Rationale

The following points are bounded design rationale, not evidence of a
historically accepted convention:

- A specification is normative documentation, not an evidence or closure
  report, so it does not belong under `baseline/`.
- The path is separate from production and test implementation areas.
- `docs/specifications/` separates normative specification content from
  general state, roadmap, limitation, acceptance, and changelog documents.
- The filename explicitly identifies the Phase, Slice, and contract title.
- The lowercase underscore-delimited name is deterministic and
  collision-resistant within the selected directory.
- The path cannot be confused with the proposed future production module or
  focused test module.

## 7. Rejected placements

These evaluations are bounded repository-structure design rationale, not
historical accepted convention:

- `baseline/`: rejected because it is the evidence, reconciliation, audit, and
  closure-report area.
- `engine/contracts/`: rejected because it is production code territory.
- `tests/`: rejected because it is test implementation territory.
- `docs/` root: rejected because it would unnecessarily mix the Slice
  specification with existing high-level authority and state documents.

## 8. Directory creation policy

The following directory is not created by this report:

```text
docs/specifications/
```

The directory and specification file may be created by a separate
specification draft task only after this placement decision has:

1. passed manual verification;
2. passed an independent Terra read-only audit;
3. been committed;
4. passed exact-SHA verification;
5. been pushed to remote `main`; and
6. completed remote-closed documentation synchronization.

## 9. Scope boundaries

This report defines only the exact future path and filename. It does not
define:

```text
Specification data model
Execution modes
Execution statuses
Evidence models
Canonical serialization
Canonical hashing
Golden oracle
Production implementation
Test implementation
Runtime behavior
Provider behavior
Word timings
AlignmentReport
Failure artifact
Total Phase 2 Slice count
Phase 2 completion percentage
```

## 10. Decision consequences

After this decision is remote-closed, the next authorized task may create
exactly:

```text
docs/specifications/phase2_slice5_canonical_adapter_execution_provenance_contract.md
```

The following states remain unchanged:

```text
Specification acceptance:
No

Implementation authorization:
No

Phase 2 closure:
No
```

## 11. Acceptance gates

This candidate decision report requires:

```text
Manual report verification
Independent Terra read-only audit
Bounded correction if required
Report commit
Exact-SHA commit verification
Remote push verification
Documentation synchronization
```

## 12. Explicit non-claims

No accepted repository-wide specification convention was discovered.

This report proposes a new bounded path decision for Slice 5 only.

The Slice 5 specification has not been created.

The Slice 5 specification has not been accepted.

Slice 5 has not been implemented.

No implementation is authorized.

Phase 2 is not closed.

The total Phase 2 Slice count is not established here.
