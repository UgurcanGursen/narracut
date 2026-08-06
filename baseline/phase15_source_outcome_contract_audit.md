# Phase 15 Source Outcome Validation Contract Audit

Decision: `FIX_REQUIRED`.

| ID | Severity | Finding | Required repair |
|---|---|---|---|
| P15-SO-001 | MAJOR | `SourceCapturePlan` does not contain a Domain Pack policy snapshot identity, so the stated policy-identity validation cannot be implemented from this input alone. | Require the existing typed `SourcePriorityPolicy` alongside the capture plan and bind its snapshot ID/hash to the supplied resolved snapshot identity. |
| P15-SO-002 | MAJOR | Stable public attachment errors and the exact quality-check identifier are not defined. | Freeze a closed error set and `source_outcome` check ID/evidence-reference requirements. |

The replay matrix, challenge fail-closed rule and Phase 17 ownership are sound.
No runtime implementation is authorized until this repair receives a targeted
re-audit.
