# Phase 14 Closure Repair Scope Reconciliation

Decision: bounded closure contract required before implementation.

1. **Sequence rebuild evidence:** introduce a pure, canonical
`SequenceDependencySnapshotV1` keyed by stable sequence ID and input hash.
`plan_incremental_sequences` may return only ordered `REUSE`/`REBUILD` decisions
from two snapshots. A multi-sequence test must change exactly one input hash and
prove one rebuild. It does not reschedule frames or rewrite Phase 3/4 renderer.

2. **Soft quota visibility:** trusted render admission receives an optional
`StorageQuotaManager` snapshot. On soft quota it returns a typed visible
`SOFT_QUOTA_PLAN_REQUIRED` with immutable dry-run plan/insufficient-reclaim
result; it never moves files. Hard/min-free rejection remains fail-closed.

3. **FULL A/V replay receipt:** benchmark two fixed local Phase 4B REPLAY
outputs and compare SHA-256 for final MP4 plus independently supplied canonical
audio-plan/filter-script/PCM-manifest evidence. It must fail on any hash drift;
hardware/provider claims are excluded.

No permanent deletion, worker, queue, provider, Studio route or Phase 15 work
is authorized by this reconciliation.
