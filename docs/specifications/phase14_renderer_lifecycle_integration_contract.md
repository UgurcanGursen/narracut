# Phase 14 Renderer Lifecycle Integration Contract

Status: candidate; implementation authorization is separate.

Before a Phase 4 preview/full invocation, the orchestrator derives a canonical
profile-specific key, obtains read-only usage, and fail-closes on hard quota.
On an exact cache hit it returns only a verified receipt/output whose hashes
match the key-bound input lineage; otherwise it executes the existing renderer
unchanged, atomically promotes verified output, imports its artifact batch into
the durable registry, and writes a performance receipt. Failed/cancelled runs
register terminal evidence but never become cache hits. The adapter owns no
provider, generic queue/retry or FULL-render HTTP route.
