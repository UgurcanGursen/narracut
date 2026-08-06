# Phase 14 Cache Lifecycle Implementation Audit

Decision: FIX_REQUIRED; no bounded package acceptance.

## Findings

### P14-CLI-001 — Existing cache writes do not emit lifecycle records

Severity: MAJOR. `engine/cache.py` writes payload bytes/metadata while
`engine/cache_lifecycle.py` models separate cache entries/payloads, but no
verified bridge binds them. The planner therefore cannot truthfully manage
objects produced by the active Phase 4 adapter.

Required repair: extend cache metadata and/or a trusted adapter so a successful
cache write exposes verified canonical lifecycle rows; cache hit integrity must
remain unchanged.

### P14-CLI-002 — Orphan payloads cannot be reclaimed

Severity: MAJOR. The dry-run skips a ready payload with zero live references.
An orphaned physical object is the safest cache reclaim candidate and must
produce a direct `TRASH_CACHE_PAYLOAD` row after snapshot revalidation.

### P14-CLI-003 — Resolver checks symlinks after resolving them

Severity: MAJOR. Calling `resolve()` before `is_symlink()` loses evidence that
the input fan-out object was a symlink. The trusted resolver must inspect every
unresolved component under the managed root before following it.

The implementation has good bounded coverage for deterministic reference-first
planning, retained references, snapshot drift and dedup arithmetic. The three
MAJOR findings block acceptance. No permanent deletion, providers, queues,
Studio FULL render or Phase 15 work is authorized.
