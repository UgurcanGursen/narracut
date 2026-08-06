# Phase 14 Cache Eviction and Soft-Quota Contract Audit

Decision: FIX_REQUIRED; implementation is not authorized.

## Reviewed evidence

- `docs/MASTER_ROADMAP.md`, Phase 14 acceptance criteria.
- `docs/specifications/phase14_cache_eviction_soft_quota_contract.md`.
- `engine/cache.py`, `engine/lifecycle.py` and the accepted trash/restore
  boundary.

## Findings

### P14-CE-001 — Cache-entry removal and payload reclamation are conflated

Severity: MAJOR.

The candidate says a cache entry can share a verified payload and defines
logical/physical bytes, but does not freeze the two distinct lifecycle
operations: retiring one cache-key reference versus moving a now-unreferenced
physical payload. Without an explicit reference-count/snapshot rule, an
eligible LRU key could reclaim bytes that are still referenced by another key
or a retained artifact.

Required repair: define immutable cache-entry and physical-payload rows,
their reference graph, plan row kinds, ordered two-step execution and exact
revalidation conditions. A payload move must be forbidden while any live cache
entry or retained artifact references it.

### P14-CE-002 — Path-free ownership has no trusted object resolver contract

Severity: MAJOR.

The candidate correctly forbids paths in registry/cache rows, but it does not
define how a plan candidate resolves a physical cache object under a trusted
storage scope, validates its hash/size or rejects a symlink/traversal before a
trash move. The existing artifact trash resolver cannot safely be assumed for
cache object fan-out paths.

Required repair: define an internal trusted `StorageObjectResolverV1`,
cache-object canonical fan-out, root-containment/symlink checks, and the
receipt fields needed to restore either a reference or a physical payload.

### P14-CE-003 — TTL eligibility cannot be reproduced from the policy snapshot

Severity: MAJOR.

The contract names durations and a reference time but not the exact expiry
function, terminal-status eligibility, timezone/clock format or whether an
append-only access event may race an eviction plan. Two implementations could
produce different candidate plans from the same evidence.

Required repair: define canonical UTC timestamp format, eligibility projection,
the accepted terminal statuses, access-event snapshot boundary and stale-plan
rejection when access/reference state changes.

## Result

The candidate’s boundaries and exclusions are sound, but the three MAJOR
findings block acceptance. No cache eviction, soft-quota cleanup, permanent
deletion, provider/queue/Studio/FULL-render or Phase 15 work is authorized.
