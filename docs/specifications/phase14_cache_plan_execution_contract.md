# Phase 14 Cache Plan Execution Contract

Status: candidate; audit and implementation authorization are separate.

## Execution model

Only a valid `CACHE-SOFT-QUOTA-PLAN-V1` with status `PLANNED` may be executed.
The executor resolves cache objects exclusively through the trusted
content-addressed scope resolver. It does not accept caller paths, scans or
implicit candidates.

For every payload row the executor first verifies that all preceding
`RETIRE_CACHE_ENTRY` rows exactly cover every live entry referring to that
payload. It revalidates plan identity, policy hash, scope, payload/entry
snapshot hashes, entry metadata, retained artifact references, payload hash,
byte size, root containment and absence of target collision. Any mismatch is
`CACHE_PLAN_STALE` and no entry/payload is changed.

## Append-only state and transaction

The trusted scope owns an append-only `cache-lifecycle-events.jsonl` ledger.
Each event has canonical ID/hash and contains event kind, plan hash, entry or
payload ID, timestamp and receipt ID. The effective state is the latest valid
event for an immutable ID; only `ready`, `retired` and `restored` transitions
are legal. Original cache metadata is never rewritten.

Execution is all-or-nothing for one plan:

1. complete non-mutating preflight;
2. move eligible payloads to `.trash/<plan_id>/sha256/...` atomically;
3. append one immutable receipt and ordered retirement events with fsync;
4. if any move, receipt or ledger append fails, move all payloads back and
   publish no successful retirement state.

The receipt records plan/policy/snapshot hashes, scope, retired entry IDs,
moved payload IDs/hashes/sizes, before/after measured bytes and trash tokens.
It is the sole restore authority.

## Restore

Restore revalidates the receipt, exact trash object hash/size, empty canonical
destination and trusted-root containment. It atomically restores payloads,
then appends `restored` events for the receipt's entries. Failure to publish
the restoration ledger rolls payload moves back to trash. Permanent deletion is
forbidden.

## Verification and exclusions

Tests must prove stale policy/snapshot/reference rejection, protected reference
rejection, no partial move on forced ledger failure, exact receipt restore,
effective state replay and soft-quota before/after accounting. No worker,
automatic background cleanup, provider, generic queue/retry, Studio/FULL route
or Phase 15 behavior is authorized.
