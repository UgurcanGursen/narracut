# Phase 14 Cache Plan Execution Scope Reconciliation

Decision: bounded execution contract required before implementation.

The accepted cache lifecycle planner emits `RETIRE_CACHE_ENTRY` followed by
`TRASH_CACHE_PAYLOAD`, but it intentionally does not mutate state. The existing
artifact trash manager cannot consume those rows directly because cache payload
paths are content-addressed and cache-entry retirement is a logical,
append-only transition.

The required execution contract must provide:

1. a trusted resolver from cache key/payload hash to the managed cache root;
2. an append-only lifecycle event ledger whose effective view determines a
   cache entry's live/retired/restored state without rewriting its provenance;
3. immutable execution receipts binding plan hash, policy/snapshot hashes,
   retired cache entry IDs/keys, moved payload IDs/hashes, before/after bytes
   and plan-scoped trash tokens;
4. preflight validation of plan identity, cache-entry/payload metadata, current
   effective reference state, payload integrity and target collision;
5. rollback of moved payloads if durable receipt/ledger publication fails; and
6. grace-period restore that restores the payload then appends a distinct
   restoration event.

Permanent deletion, background cleanup/worker behavior, provider/queue,
Studio/FULL render and Phase 15 remain excluded. No implementation is
authorized by this reconciliation.
