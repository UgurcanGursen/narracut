# Phase 15 Source Outcome Implementation Audit

Decision: `FIX_REQUIRED`.

| ID | Severity | Finding | Required repair |
|---|---|---|---|
| P15-SOI-001 | MAJOR | A directly constructed `SourcePriorityPolicy` with matching snapshot strings but malformed ranking/mandatory fields can pass. | Validate the typed policy’s version, enum tuples, uniqueness and mandatory-subset invariant before attachment. |
| P15-SOI-002 | MAJOR | `MANUAL_UI` accepts a non-manual Phase 6 adapter plan, obscuring the evidence origin. | Require `MANUAL_UI` to consume only `MANUAL_CAPTURE` evidence; reject mismatches with a stable safe code. |

Focused tests pass but do not cover these two trust-boundary cases. No scope
expansion is authorized; repair and targeted re-audit are next.
