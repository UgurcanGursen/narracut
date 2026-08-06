# Phase 14 Two-Stage Trash and Restore Contract

Status: candidate; implementation authorization is separate.

Only a valid, revalidated `LIFECYCLE-DELETION-PLAN-V1` may be executed. Each
candidate is moved atomically from a project-scoped managed artifact root to a
project-scoped `.trash/<plan_id>/<artifact_id>` target. The operation writes an
append-only receipt containing plan hash, registry snapshot hash, before/after
content hashes and timestamp. Any protected/stale/missing/changed candidate
fails closed and no other candidate is attempted.

Restore consumes that receipt, requires the same content hash and an empty
managed destination, then atomically moves the object back. Permanent deletion
is forbidden. User-supplied paths, absolute paths, URIs, traversal, symlinks,
cache eviction, quota enforcement, FULL render and queue/retry are excluded.
