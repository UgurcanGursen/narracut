# Phase 14 Cache Eviction and Soft-Quota Scope Reconciliation

Decision: PASS for a bounded contract-design task; eviction implementation is
not yet authorized.

## Evidence reviewed

- `docs/MASTER_ROADMAP.md` Phase 14 retention, mark-and-sweep, quota,
  content-addressing and acceptance requirements.
- `engine/lifecycle.py`, `engine/cache.py` and the Phase 4 lifecycle adapter.
- Current Phase 14 acceptance and limitations records.

## What exists

The registry validates immutable identity, project-local dependency edges and
protected roots. Deletion is a revalidated, two-stage move to trash. The cache
has profile-isolated key/payload integrity and the preview adapter checks actual
managed-root usage before a cache miss can invoke a renderer.

## Blocking gaps for eviction

1. A registry row has no canonical `artifact_type`, terminal status,
   `created_at`, `last_accessed_at`, job ownership or resolved retention-policy
   snapshot. It cannot honestly evaluate TTL or LRU.
2. Cache objects have no durable registry/reference row tying a cache key to
   its payload, producer inputs or consumer dependencies. Deleting a cache
   object could therefore break a still-referenced artifact.
3. There is no explicit project/global storage scope, minimum-free-disk
   measurement, soft-quota policy, deterministic eviction ordering or
   deduplication accounting. Current `storage_usage` is only an observed byte
   total, not a cleanup policy.
4. A deletion plan must continue to be immutable and revalidated; soft quota
   may propose or trash only eligible entries. It may never silently delete an
   approved, final, provenance, baseline, pinned, locked, review-pending or
   dependency-reachable entry.

## Required bounded contract

The next design artifact must define a versioned cache-entry/registry bridge,
resolved retention snapshot, explicit storage scope and quota values, stable
LRU access semantics, ordered candidate reasons, cache payload deduplication
metrics, dry-run receipt fields and fail-closed behavior for missing policy or
metadata. It must preserve the existing plan-to-trash boundary and exclude
permanent delete, provider transport, generic queue/retry, Studio FULL render
and Phase 15 validation.

## Outcome

Phase 14 remains open. No cache eviction or soft-quota cleanup code is
authorized by this reconciliation alone.
