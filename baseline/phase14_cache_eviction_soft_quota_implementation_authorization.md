# Phase 14 Cache Eviction and Soft-Quota Implementation Authorization

Decision: GRANTED for one bounded Phase 14 package.

Authorized implementation:

1. full immutable registry/cache-entry/payload projections and verified import;
2. trusted content-addressed object resolution under a caller-owned managed
   scope;
3. deterministic, policy/snapshot-bound soft-quota dry-run planning with
   reference retirement before unreferenced payload trash eligibility;
4. exact logical/physical/deduplication reporting; and
5. focused REPLAY fixture tests including protected references and stale-plan
   rejection.

The package must preserve existing Phase 4 behavior, cache profile isolation,
hard-quota admission, immutable deletion-plan/trash/restore boundaries and
fail-closed handling for missing policy/metadata/state. It must not add
permanent delete, automatic worker/scheduler behavior, providers, generic
queue/retry, Studio FULL-render/API/UI work, hardware encoding or Phase 15
validation.

Acceptance requires an independent implementation audit and explicit
documentation reconciliation; this authorization is not acceptance or Phase
14 closure.
