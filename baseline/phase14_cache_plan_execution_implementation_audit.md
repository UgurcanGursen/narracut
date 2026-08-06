# Phase 14 Cache Plan Execution Implementation Audit

Decision: FIX_REQUIRED; bounded execution package is not accepted.

## Findings

### P14-CPI-001 — Retirement coverage is global instead of per payload

Severity: MAJOR. `execute_cache_plan` compares each payload's live references
with the cumulative `retired` list. A plan containing more than one payload
will fail once the second payload is reached, even if its own retirement rows
are complete. Group retirement IDs per payload and reject only missing/extra
rows for that payload.

### P14-CPI-002 — Receipt misses storage accounting and effective-state replay

Severity: MAJOR. The transaction has moved objects and entry IDs but no
before/after physical-byte measurements, storage scope, or public
effective-state reader. The Master/contract requires soft-quota accounting and
state replay rather than merely an append-log parser.

Required repair: bind storage scope and before/after bytes to the transaction,
add a hash-valid effective cache-entry/payload state projection, and test two
payloads plus retired/restored replay.

The existing preflight, content-addressed trash, rollback-on-publication-fail
and exact payload restore tests are sound. No permanent deletion, worker,
provider, queue, Studio/FULL render or Phase 15 work is authorized.
