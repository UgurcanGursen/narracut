# Phase 15 Evidence Attachment Implementation Audit

Decision: `FIX_REQUIRED` (repaired before acceptance).

| ID | Finding | Repair result |
|---|---|---|
| P15-EA-001 | Storage attachment accepted an independent hash instead of a typed Phase 14 pressure-policy identity. | Closed: canonical hash is now derived from `StoragePressurePolicy` scope/limits and used in the evidence reference. |
| P15-EA-002 | Two contract failure codes had no explicit implementation path. | Closed: invalid attachment request and invalid domain snapshot type have stable codes before any observation is emitted. |

Focused real Phase 4/14/domain integration gate after repair: `1 passed in
32.85s`. No live transport, retry, queue/worker, media validator, Studio/UI,
Phase 16 or Phase 17 behavior was added.
