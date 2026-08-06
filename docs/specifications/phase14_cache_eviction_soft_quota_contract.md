# Phase 14 Cache Eviction and Soft-Quota Contract

Status: candidate; independent audit and implementation authorization are
separate.

## 1. Boundary

This contract adds a lifecycle-policy model for planning cache eviction and
soft-quota recovery. It consumes the accepted immutable deletion-plan and
trash/restore boundaries. It does not authorize mutation, permanent deletion,
providers, generic queue/retry, Studio FULL-render, minimum-free-disk cleanup
or Phase 15 validation.

## 2. Required canonical records

`ArtifactRegistryRecordV1` must persist the full verified artifact projection:

```text
artifact_id, artifact_hash, artifact_type, project_id, sequence_id?, job_id?
content_hash, size_bytes, created_at, last_accessed_at, retention_class
dependency_ids, locked, pinned, approved, producer, producer_version, status
```

`CacheEntryRecordV1` is a separate path-free record, bound to exactly one
profile-scoped cache key and payload:

```text
cache_entry_id, cache_entry_hash, storage_scope_id, cache_key, profile
payload_hash, payload_size_bytes, producer_input_hash, producer_version
created_at, last_accessed_at, registry_artifact_ids, status
```

The cache key is not the payload hash. A cache entry can share a payload only
when its payload hash and byte size match exactly. A missing, duplicate,
cross-scope or non-verified referenced registry artifact makes the entry
unusable and ineligible for eviction. Access updates are append-only,
monotonic records with a test-controlled clock; filesystem mtime is never an
LRU source.

## 3. Resolved policy and storage scope

Every plan binds an immutable `RetentionPolicySnapshotV1` containing policy
ID/hash, scope ID, soft and hard byte quota, approved retention durations,
the reference time and an explicit grace period. No runtime default, hidden
threshold or caller-supplied policy may choose candidates.

`StorageScopeV1` identifies either one project artifact store or the global
cache store. Its managed filesystem root is resolved by trusted local
configuration outside artifact/cache records. Project and global-cache totals
are reported separately. A missing scope, policy or measured usage is an
unavailable state, not permission to evict.

## 4. Protection and candidate ordering

Before any candidate is considered, the marker protects active project/job,
review-pending, approved, final, provenance, baseline, pinned and locked
artifacts, plus their dependency closure. A cache object is also protected if
any live cache entry or retained artifact references its payload.

For a fixed snapshot, candidate ordering is deterministic and records its
exact reason:

1. expired `ephemeral` artifacts;
2. terminal `failed`/`cancelled` artifacts eligible under the policy;
3. expired unlocked `temporary` artifacts;
4. expired unlocked review artifacts not awaiting review;
5. LRU eligible sequence-render cache;
6. LRU eligible chart/audio/alignment/subtitle cache;
7. LRU eligible re-downloadable normalized-asset cache.

Within a class the order is `(last_accessed_at, created_at, artifact_id)`.
Missing timestamps/statuses fail closed. A candidate may be proposed only when
its full dependency/protection decision is present in the plan.

## 5. Soft quota and two-stage execution

Soft quota produces an immutable `LifecycleDeletionPlanV1` sufficient to bring
the observed bytes below the requested target, or an explicit
`INSUFFICIENT_ELIGIBLE_RECLAIM` result. It never starts a render, deletes a file or silently
changes policy. A later mutation package may revalidate and move only those
candidates through the accepted plan-scoped trash/receipt protocol; it must
stop and surface a typed result if state changes or the target remains unmet.

Hard quota remains a render-admission guard. Cache hits may be reused after
integrity validation, but a cache miss must measure the trusted managed scope
and fail before renderer invocation if projected use exceeds the hard limit.

## 6. Deduplication accounting

Every storage report distinguishes:

```text
logical_bytes = sum of eligible logical references
physical_bytes = sum of unique verified payload hashes in the scope
dedup_saved_bytes = logical_bytes - physical_bytes
```

The report must not claim hardlink/reflink savings unless the platform-specific
physical-object evidence is available. Identical payload hash with unequal byte
size, or a reference to a missing object, fails closed.

## 7. Required verification before implementation acceptance

1. Missing policy/scope/timestamp/status/reference produces no candidate.
2. Protected and dependency-reachable artifacts/cache payloads never enter a
   plan.
3. Fixed registry/cache/policy/clock inputs produce byte-identical ordering and
   plan identity; any input drift invalidates it.
4. A projected soft-quota plan does not mutate; a later trash execution
   revalidates it and supports grace-period restore.
5. Profile separation, cache payload integrity, hard-quota miss blocking and
   exact cache-hit reuse remain covered by the existing adapter regression.
6. Logical/physical/dedup metrics are exact for duplicate and non-duplicate
   fixture payloads without a platform hardlink claim.

## 8. Explicit exclusions

Permanent deletion, automatic scheduler/worker behavior, provider transport,
browser automation, generic retry, Studio API/UI expansion, FULL-render route,
hardware encoding and Phase 15 validation/observability remain out of scope.
