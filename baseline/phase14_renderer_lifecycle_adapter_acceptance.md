# Phase 14 Renderer Lifecycle Adapter Acceptance

Decision: ACCEPT (bounded adapter package); Phase 14 Master acceptance remains
OPEN.

The adapter wraps an existing Phase 4 REPLAY preview callable without changing
renderer semantics. It uses a profile-scoped canonical key, verifies cache
payload metadata and SHA-256 before a hit, reads managed storage usage before
admitting a miss, fails closed at hard quota, accepts only successful
`PreviewRun` manifest bytes, and imports the already-validated Phase 4 artifact
DAG into the durable registry. Failed or cancelled attempts cannot become cache
entries.

Evidence:

- Focused lifecycle/cache/adapter regression: `19 passed, 1 deselected`.
- Actual Phase 4 REPLAY preview followed by exact cache reuse: `1 passed, 2
  deselected in 31.19s`.

Exclusions: cache eviction, soft quota, LRU, free-disk guard, deduplication
measurement, permanent delete, provider transport, generic queue/retry, Studio
FULL render and Phase 15 validation. The next authoritative task is a
read-only cache-eviction/soft-quota scope reconciliation.
