# Phase 15 Validation/Observability Contract Audit

Decision: `FIX_REQUIRED`. The candidate is correctly scoped to a local
fail-closed boundary and does not prematurely enable transport, but three
contract omissions would allow incompatible implementations to disagree about
the meaning of a passing run.

| ID | Severity | Finding | Required repair |
|---|---|---|---|
| P15-001 | MAJOR | `category`, `event`, `status`, metric keys and public codes are called closed but their enumerations and admissible combinations are not defined. | Define the exact token tables and transition matrix, including which terminal observation can satisfy each declared check. |
| P15-002 | MAJOR | The gate says it consumes typed evidence references, but their bytes, identity/hash, run binding and Phase 4/14 validation procedure are unspecified. | Define a closed evidence-reference envelope and require canonical receipt/registry/admission parsing before a check can pass. |
| P15-003 | MAJOR | “Terminal failure cannot be overwritten” is not mechanically expressed for a run containing mixed observations. | Define a terminal state reducer and precedence table: malformed/cross-run evidence, failure, missing/unsupported and warning/success. |

Passed audit points:

- Phase 15 ownership is kept separate from Phase 17 live transport.
- Missing/not-implemented work is explicitly prohibited from producing a
  `PASS` or `WARNING` result.
- The candidate preserves Phase 4 renderer and Phase 14 lifecycle ownership,
  and excludes worker, queue, provider, UI and Phase 16 work.

No implementation is authorized by this result. The next task is one bounded
contract repair for P15-001 through P15-003, followed by a targeted re-audit.
